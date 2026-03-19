import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sqlalchemy.orm import Session

from . import crud
from .quant_base import _normalize_symbols

logger = logging.getLogger("doraemon")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _model_store_dir() -> Path:
    model_dir = _repo_root() / "backend" / "model_store"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


def _safe_float_or_none(v):
    if v is None:
        return None
    try:
        value = float(v)
        if pd.isna(value):
            return None
        return value
    except Exception:
        return None


def _is_under_model_store(path_obj: Path) -> bool:
    model_store = _model_store_dir().resolve()
    resolved = path_obj.resolve()
    return model_store in resolved.parents


def _artifact_candidates(path_text: str) -> list[Path]:
    value = str(path_text or "").strip()
    if not value:
        return []
    raw = Path(value)
    model_store = _model_store_dir().resolve()
    repo_backend = (_repo_root() / "backend").resolve()
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
        candidates.append(model_store / raw.name)
    else:
        candidates.append(model_store / raw)
        candidates.append(repo_backend / raw)
        candidates.append(model_store / raw.name)

    seen = set()
    unique = []
    for item in candidates:
        try:
            resolved = item.resolve()
        except Exception:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if _is_under_model_store(resolved):
            unique.append(resolved)
    return unique


def _resolve_existing_artifact_path(path_text: str) -> Optional[Path]:
    for item in _artifact_candidates(path_text):
        if item.exists():
            return item
    return None


def model_artifact_available(model_row) -> bool:
    return _resolve_existing_artifact_path(model_row.artifact_path or "") is not None


def _artifact_file_exists(model_row) -> bool:
    return model_artifact_available(model_row)


def _build_training_frame_for_recovery(feature_rows: list) -> tuple[pd.DataFrame, list[str]]:
    records = []
    feature_cols = None
    for item in feature_rows:
        feats = item.features or {}
        if not feats:
            continue
        if feature_cols is None:
            feature_cols = sorted([str(key) for key in feats.keys()])
        rec = {col: _safe_float_or_none(feats.get(col)) for col in feature_cols}
        rec["market"] = item.market
        rec["symbol"] = item.symbol
        rec["trade_date"] = item.trade_date
        rec["y_up_5d"] = item.y_up_5d
        rec["y_ret_5d"] = item.y_ret_5d
        rec["y_mdd_10d"] = item.y_mdd_10d
        records.append(rec)
    if not records or not feature_cols:
        return pd.DataFrame(), []
    frame = pd.DataFrame.from_records(records)
    frame = frame.dropna(subset=feature_cols)
    return frame, feature_cols


def _derive_train_ratio(model_row) -> float:
    params = model_row.params or {}
    metrics = model_row.metrics or {}
    try:
        ratio = float(params.get("train_ratio"))
        if 0.5 < ratio < 0.96:
            return min(max(ratio, 0.6), 0.95)
    except Exception:
        pass
    try:
        samples_total = float(metrics.get("samples_total"))
        samples_train = float(metrics.get("samples_train"))
        if samples_total > 0:
            ratio = samples_train / samples_total
            if 0.5 < ratio < 0.96:
                return min(max(ratio, 0.6), 0.95)
    except Exception:
        pass
    return 0.8


def _derive_max_samples(model_row) -> int:
    params = model_row.params or {}
    metrics = model_row.metrics or {}
    raw = params.get("max_samples", metrics.get("samples_total", 300000))
    try:
        value = int(raw)
    except Exception:
        value = 300000
    return max(1000, min(value, 1_000_000))


def _artifact_reference_for_db(artifact_path: Path) -> str:
    return f"model_store/{artifact_path.name}"


def _rebuild_model_artifact(db: Session, model_row) -> Path:
    algo = str(model_row.algo or "")
    if algo != "HistGradientBoostingClassifier":
        raise RuntimeError(f"Unsupported model algo for rebuild: {algo}")

    request_market = str(model_row.market or "CN").strip().upper()
    target = str(model_row.target or "y_up_5d").strip()
    feature_version = str(model_row.feature_version or "v1").strip()
    params = dict(model_row.params or {})
    requested_symbols_raw = params.get("requested_symbols") or []
    requested_symbols = [
        str(item).strip()
        for item in requested_symbols_raw
        if str(item).strip()
    ]
    if not requested_symbols:
        requested_symbols = None

    max_samples = _derive_max_samples(model_row)
    feature_rows = crud.list_ml_feature_snapshots(
        db,
        market=request_market,
        feature_version=feature_version,
        symbols=requested_symbols,
        limit=max_samples,
    )
    if not feature_rows:
        raise RuntimeError(
            "Cannot rebuild model artifact: no feature snapshots found in database."
        )

    frame, feature_cols = _build_training_frame_for_recovery(feature_rows)
    if frame.empty:
        raise RuntimeError("Cannot rebuild model artifact: training frame is empty after cleaning.")
    if target not in frame.columns:
        raise RuntimeError(f"Cannot rebuild model artifact: target column {target} not found.")

    frame = frame.dropna(subset=[target]).copy()
    if frame.empty:
        raise RuntimeError("Cannot rebuild model artifact: no labeled rows available.")
    frame = frame.sort_values("trade_date").reset_index(drop=True)

    train_ratio = _derive_train_ratio(model_row)
    split_idx = int(len(frame) * train_ratio)
    if len(frame) >= 300:
        split_idx = min(max(split_idx, 200), len(frame) - 100)
    else:
        split_idx = min(max(split_idx, max(1, len(frame) // 2)), len(frame) - 1)
    if split_idx <= 0 or split_idx >= len(frame):
        raise RuntimeError("Cannot rebuild model artifact: invalid train/validation split.")

    train_df = frame.iloc[:split_idx]
    val_df = frame.iloc[split_idx:]
    if train_df[target].nunique() < 2:
        raise RuntimeError("Cannot rebuild model artifact: training labels contain only one class.")
    if val_df.empty:
        raise RuntimeError("Cannot rebuild model artifact: validation set is empty.")

    model_params = {
        "max_iter": int(params.get("max_iter", 300)),
        "learning_rate": float(params.get("learning_rate", 0.05)),
        "max_depth": int(params.get("max_depth", 6)),
        "l2_regularization": float(params.get("l2_regularization", 0.0)),
        "min_samples_leaf": int(params.get("min_samples_leaf", 30)),
        "random_state": 42,
    }
    clf = HistGradientBoostingClassifier(**model_params)
    clf.fit(train_df[feature_cols], train_df[target].astype(int))

    y_val = val_df[target].astype(int).values
    val_prob = clf.predict_proba(val_df[feature_cols])[:, 1]
    val_pred = (val_prob >= 0.5).astype(int)
    recovered_metrics = {
        "samples_total": int(len(frame)),
        "samples_train": int(len(train_df)),
        "samples_val": int(len(val_df)),
        "symbol_count": int(frame["symbol"].nunique()),
        "accuracy": float(accuracy_score(y_val, val_pred)),
    }
    if pd.Series(y_val).nunique() > 1:
        recovered_metrics["auc"] = float(roc_auc_score(y_val, val_prob))
        recovered_metrics["log_loss"] = float(log_loss(y_val, val_prob, labels=[0, 1]))
    else:
        recovered_metrics["auc"] = None
        recovered_metrics["log_loss"] = None

    now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact_name = f"{str(model_row.name or 'model').strip()}_{now_tag}_rebuild.pkl"
    artifact_path = _model_store_dir() / artifact_name
    artifact_payload = {
        "model_id": model_row.id,
        "model_name": model_row.name,
        "market": request_market,
        "target": target,
        "feature_version": feature_version,
        "feature_cols": feature_cols,
        "metrics": recovered_metrics,
        "training_scope": params.get("training_scope") or ("custom" if requested_symbols else "market"),
        "training_symbol_count": int(frame["symbol"].nunique()),
        "trained_at": datetime.now().isoformat(),
        "rebuild_from_db": True,
        "estimator": clf,
    }
    with open(artifact_path, "wb") as f:
        pickle.dump(artifact_payload, f)

    old_path = str(model_row.artifact_path or "").strip()
    params["artifact_rebuild_count"] = int(params.get("artifact_rebuild_count", 0) or 0) + 1
    params["artifact_rebuilt_at"] = datetime.now().isoformat()
    if old_path:
        params["artifact_previous_path"] = old_path
    params["train_ratio"] = train_ratio
    params["max_samples"] = max_samples
    if requested_symbols is not None:
        params["requested_symbols"] = requested_symbols

    metrics = dict(model_row.metrics or {})
    metrics["rebuild_latest"] = recovered_metrics

    model_row.params = params
    model_row.metrics = metrics
    model_row.artifact_path = _artifact_reference_for_db(artifact_path)
    db.add(model_row)
    db.commit()
    db.refresh(model_row)
    logger.warning("ml model artifact rebuilt model_id=%s old_path=%s new_path=%s", model_row.id, old_path, model_row.artifact_path)
    return artifact_path


def ensure_model_artifact(db: Session, model_row, *, attempt_repair: bool = False) -> Path:
    existing = _resolve_existing_artifact_path(model_row.artifact_path or "")
    if existing is not None:
        desired_ref = _artifact_reference_for_db(existing)
        if str(model_row.artifact_path or "").strip() != desired_ref:
            model_row.artifact_path = desired_ref
            db.add(model_row)
            db.commit()
            db.refresh(model_row)
        return existing
    if not attempt_repair:
        raise RuntimeError(f"Model artifact not found: {model_row.artifact_path}")
    return _rebuild_model_artifact(db, model_row)


def ml_model_scope(model_row) -> str:
    params = model_row.params or {}
    scope = str(params.get("training_scope") or "").strip().lower()
    if scope in {"market", "custom"}:
        return scope
    requested = params.get("requested_symbols") or []
    return "custom" if requested else "market"


def ml_model_symbol_count(model_row) -> Optional[int]:
    params = model_row.params or {}
    metrics = model_row.metrics or {}
    raw = params.get("training_symbol_count", metrics.get("symbol_count"))
    try:
        value = int(raw)
    except Exception:
        return None
    return value if value > 0 else None


def ml_model_markets(model_row) -> list[str]:
    params = model_row.params or {}
    raw = params.get("training_markets")
    if isinstance(raw, list):
        values = [str(item).strip().upper() for item in raw if str(item).strip()]
        if values:
            return values
    market = str(model_row.market or "").strip().upper()
    return [market] if market else []


def market_symbol_universe_count(db: Session, market: str, *, min_rows: int = 120) -> int:
    rows = crud.list_kline_symbols_by_markets(
        db,
        crud.ml_market_scope(market),
        min_rows=min_rows,
        limit=50000,
    )
    return len(rows)


def recommended_market_model_min_symbol_count(db: Session, market: str, *, min_rows: int = 120) -> int:
    universe_count = market_symbol_universe_count(db, market, min_rows=min_rows)
    if universe_count <= 0:
        return 10
    baseline = max(10, min(100, universe_count // 5))
    return min(universe_count, baseline)


def _infer_market_from_symbol_text(symbol: str, default_market: str = "CN") -> str:
    text = str(symbol or "").strip().lower()
    if text.startswith("sh"):
        return "SH"
    if text.startswith("sz3"):
        return "300"
    if text.startswith("sz"):
        return "SZ"
    return str(default_market or "CN").strip().upper()


def is_composite_market_request(market: str) -> bool:
    return len(crud.ml_market_scope(market)) > 1


def resolve_market_model_bundle(
    db: Session,
    market: str,
    target: str = "y_up_5d",
    *,
    require_market_scope: bool = True,
    min_rows: int = 120,
    attempt_repair: bool = False,
) -> tuple[dict[str, object], dict[str, str]]:
    request_markets = crud.ml_market_scope(market)
    model_rows: dict[str, object] = {}
    errors: dict[str, str] = {}
    for market_key in request_markets:
        try:
            model_rows[market_key] = resolve_best_ml_model(
                db,
                market=market_key,
                target=target,
                require_market_scope=require_market_scope,
                min_symbol_count=(
                    recommended_market_model_min_symbol_count(db, market_key, min_rows=min_rows)
                    if require_market_scope
                    else 0
                ),
                allow_fallback_to_best=True,
                attempt_repair=attempt_repair,
            )
        except Exception as exc:
            errors[market_key] = str(exc)
    if model_rows:
        return model_rows, errors
    detail = "; ".join(f"{key}: {value}" for key, value in errors.items()) or "no market model available"
    raise RuntimeError(
        f"No qualified sub-market model available for request market={str(market or 'CN').strip().upper()}, "
        f"target={str(target or 'y_up_5d').strip()}. {detail}"
    )


def resolve_best_ml_model(
    db: Session,
    market: str,
    target: str = "y_up_5d",
    model_id: Optional[int] = None,
    *,
    require_market_scope: bool = False,
    min_symbol_count: int = 0,
    allow_fallback_to_best: bool = False,
    attempt_repair: bool = False,
):
    request_market = str(market or "CN").strip().upper()
    request_target = str(target or "y_up_5d").strip()
    explicit_error = None
    if model_id:
        model_row = crud.get_ml_model(db, int(model_id))
        if model_row is None:
            explicit_error = f"ML model {model_id} not found."
        elif str(model_row.market or "").upper() != request_market:
            explicit_error = f"Model market mismatch: model={model_row.market}, request={request_market}"
        elif str(model_row.target or "").strip() != request_target:
            explicit_error = f"Model target mismatch: model={model_row.target}, request={request_target}"
        elif require_market_scope and ml_model_scope(model_row) != "market":
            explicit_error = (
                f"Model {model_row.id} is not a market-wide model for {request_market}. "
                "Train a market model first."
            )
        elif min_symbol_count > 0 and (ml_model_symbol_count(model_row) or 0) < min_symbol_count:
            explicit_error = (
                f"Model {model_row.id} coverage is too low for market={request_market}. "
                "Train a full-market model first."
            )
        else:
            try:
                ensure_model_artifact(db, model_row, attempt_repair=attempt_repair)
                return model_row
            except Exception as exc:
                explicit_error = str(exc)
        if not allow_fallback_to_best:
            raise RuntimeError(explicit_error)

    rows = crud.list_ml_models(db, market=request_market, target=request_target, limit=200)
    if not rows:
        raise RuntimeError(
            explicit_error
            or
            f"No ML model available for market={request_market}, target={request_target}. "
            "Train a market-wide model first."
        )
    if require_market_scope:
        rows = [item for item in rows if ml_model_scope(item) == "market"]
    if min_symbol_count > 0:
        rows = [item for item in rows if (ml_model_symbol_count(item) or 0) >= min_symbol_count]
    if not rows:
        raise RuntimeError(
            explicit_error
            or
            f"No qualified model available for market={request_market}, target={request_target}. "
            "Train and promote a qualified market model."
        )

    def rank_key(item):
        metrics = item.metrics or {}
        scope = ml_model_scope(item)
        symbol_count = ml_model_symbol_count(item) or 0
        auc = metrics.get("auc")
        try:
            auc = float(auc) if auc is not None else -1.0
        except Exception:
            auc = -1.0
        return (
            1 if scope == "market" else 0,
            1 if bool(item.is_active) else 0,
            symbol_count,
            auc,
            int(item.id or 0),
        )

    rows = sorted(rows, key=rank_key, reverse=True)
    candidate_errors = []
    for item in rows:
        try:
            ensure_model_artifact(db, item, attempt_repair=attempt_repair)
            return item
        except Exception as exc:
            candidate_errors.append(f"id={item.id}: {exc}")
            continue
    if candidate_errors:
        detail = "; ".join(candidate_errors[:3])
        raise RuntimeError(
            explicit_error
            or
            f"No model with available artifact for market={request_market}, target={request_target}. {detail}"
        )
    raise RuntimeError(
        explicit_error
        or
        f"No model available for market={request_market}, target={request_target}."
    )


def load_ml_model_artifact(model_row, *, db: Optional[Session] = None, attempt_repair: bool = False) -> dict:
    if db is not None:
        artifact_path = ensure_model_artifact(db, model_row, attempt_repair=attempt_repair)
    else:
        artifact_path = _resolve_existing_artifact_path(model_row.artifact_path or "")
        if artifact_path is None:
            raise RuntimeError(f"Model artifact not found: {model_row.artifact_path}")

    with open(artifact_path, "rb") as f:
        artifact = pickle.load(f)

    feature_cols = artifact.get("feature_cols") or []
    estimator = artifact.get("estimator")
    if estimator is None or not feature_cols:
        raise RuntimeError("Model artifact is invalid.")
    return artifact


def score_to_action(score: float):
    if score >= 0.7:
        return "buy", 0.30, 0.50
    if score >= 0.55:
        return "light_buy", 0.10, 0.20
    if score <= 0.45:
        return "avoid", 0.00, 0.05
    return "hold", 0.05, 0.10


def score_latest_features_for_model(
    db: Session,
    model_row,
    market: str,
    target: str = "y_up_5d",
    symbols=None,
    limit: int = 100,
    persist: bool = True,
) -> dict:
    request_market = str(market or model_row.market or "CN").strip().upper()
    request_target = str(target or model_row.target or "y_up_5d").strip()
    if str(model_row.market or "").strip().upper() != request_market:
        raise RuntimeError(
            f"Model market mismatch: model={model_row.market}, request={request_market}"
        )
    if str(model_row.target or "").strip() != request_target:
        raise RuntimeError(
            f"Model target mismatch: model={model_row.target}, request={request_target}"
        )

    artifact = load_ml_model_artifact(model_row, db=db, attempt_repair=True)
    feature_version = str(artifact.get("feature_version") or model_row.feature_version or "v1")
    feature_cols = artifact.get("feature_cols") or []
    estimator = artifact.get("estimator")

    normalized_symbols = (
        _normalize_symbols(symbols, request_market, fallback_default=False) if symbols else None
    )
    if not normalized_symbols:
        normalized_symbols = None
    feature_fetch_limit = max(int(limit or 100), 200)
    if not normalized_symbols:
        feature_fetch_limit = max(feature_fetch_limit, 20000)
    latest_rows = crud.list_latest_ml_feature_snapshots(
        db,
        market=request_market,
        feature_version=feature_version,
        symbols=normalized_symbols,
        limit=feature_fetch_limit,
    )
    if not latest_rows:
        raise RuntimeError(
            f"No latest feature snapshots found for market={request_market}. Run ml_feature first."
        )

    prediction_rows = []
    scored_rows = []
    for item in latest_rows:
        feats = item.features or {}
        x = pd.DataFrame(
            [[float(feats.get(col, 0.0) or 0.0) for col in feature_cols]],
            columns=feature_cols,
        )
        prob = float(estimator.predict_proba(x)[0, 1])
        action, pos_min, pos_max = score_to_action(prob)
        expected_ret = float((prob - 0.5) * 0.12)
        vol_20 = feats.get("vol_20")
        try:
            vol_20 = float(vol_20 or 0.0)
        except Exception:
            vol_20 = 0.0
        risk_mdd = float(-abs(vol_20) * 2.0)
        row = {
            "model_id": model_row.id,
            "market": item.market,
            "symbol": item.symbol,
            "trade_date": item.trade_date,
            "score_up_5d": prob,
            "expected_ret_5d": expected_ret,
            "risk_mdd_10d": risk_mdd,
            "action": action,
            "position_min": pos_min,
            "position_max": pos_max,
            "meta": {
                "feature_version": feature_version,
                "target": request_target,
            },
        }
        prediction_rows.append(row)
        scored_rows.append(
            {
                "symbol": item.symbol,
                "trade_date": item.trade_date.isoformat() if item.trade_date else None,
                "score_up_5d": prob,
                "expected_ret_5d": expected_ret,
                "risk_mdd_10d": risk_mdd,
                "action": action,
                "position_range": [pos_min, pos_max],
                "feature_version": feature_version,
            }
        )

    rows_upserted = 0
    if persist and prediction_rows:
        rows_upserted = int(crud.upsert_ml_predictions(db, prediction_rows))
    scored_rows = sorted(scored_rows, key=lambda r: r.get("score_up_5d", 0.0), reverse=True)
    return {
        "feature_version": feature_version,
        "rows_scored": len(prediction_rows),
        "rows_upserted": rows_upserted,
        "predictions": prediction_rows,
        "top_predictions": scored_rows[: max(1, int(limit or 100))],
    }


def score_latest_features_for_model_bundle(
    db: Session,
    model_rows_by_market: dict[str, object],
    market: str,
    target: str = "y_up_5d",
    symbols=None,
    limit: int = 100,
    persist: bool = True,
) -> dict:
    request_market = str(market or "CN").strip().upper()
    request_target = str(target or "y_up_5d").strip()
    normalized_symbols = (
        _normalize_symbols(symbols, request_market, fallback_default=False) if symbols else None
    )
    symbols_by_market: dict[str, list[str]] = {}
    if normalized_symbols:
        for item in normalized_symbols:
            market_key = _infer_market_from_symbol_text(item, request_market)
            symbols_by_market.setdefault(market_key, []).append(item)

    combined_predictions = []
    combined_top_predictions = []
    feature_versions: dict[str, str] = {}
    rows_scored = 0
    rows_upserted = 0
    scored_markets = []
    for market_key, model_row in model_rows_by_market.items():
        scoped_symbols = symbols_by_market.get(market_key)
        if normalized_symbols and not scoped_symbols:
            continue
        scoped_limit = max(int(limit or 100), 200)
        if not scoped_symbols:
            scoped_limit = max(scoped_limit, market_symbol_universe_count(db, market_key))
        result = score_latest_features_for_model(
            db,
            model_row=model_row,
            market=market_key,
            target=request_target,
            symbols=scoped_symbols,
            limit=scoped_limit,
            persist=persist,
        )
        feature_versions[market_key] = str(result.get("feature_version") or "")
        rows_scored += int(result.get("rows_scored") or 0)
        rows_upserted += int(result.get("rows_upserted") or 0)
        combined_predictions.extend(result.get("predictions") or [])
        combined_top_predictions.extend(result.get("top_predictions") or [])
        scored_markets.append(market_key)

    combined_predictions = sorted(
        combined_predictions,
        key=lambda item: (
            float(item.get("score_up_5d", 0.0) or 0.0),
            float(item.get("expected_ret_5d", 0.0) or 0.0),
        ),
        reverse=True,
    )
    combined_top_predictions = sorted(
        combined_top_predictions,
        key=lambda item: (
            float(item.get("score_up_5d", 0.0) or 0.0),
            float(item.get("expected_ret_5d", 0.0) or 0.0),
        ),
        reverse=True,
    )
    unique_feature_versions = {value for value in feature_versions.values() if value}
    feature_version = ""
    if len(unique_feature_versions) == 1:
        feature_version = next(iter(unique_feature_versions))
    elif unique_feature_versions:
        feature_version = "multi"

    return {
        "feature_version": feature_version,
        "feature_versions": feature_versions,
        "rows_scored": rows_scored,
        "rows_upserted": rows_upserted,
        "predictions": combined_predictions,
        "top_predictions": combined_top_predictions[: max(1, int(limit or 100))],
        "markets_scored": scored_markets,
        "models_by_market": {
            market_key: {
                "id": getattr(model_row, "id", None),
                "name": getattr(model_row, "name", None),
                "market": getattr(model_row, "market", None),
                "scope": ml_model_scope(model_row),
                "symbol_count": ml_model_symbol_count(model_row),
            }
            for market_key, model_row in model_rows_by_market.items()
        },
    }
