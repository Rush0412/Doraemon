import pickle
from pathlib import Path
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from . import crud
from .quant_base import _normalize_symbols


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _model_store_dir() -> Path:
    model_dir = _repo_root() / "backend" / "model_store"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


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
        [str(market or "CN").strip().upper()],
        min_rows=min_rows,
        limit=10000,
    )
    return len(rows)


def recommended_market_model_min_symbol_count(db: Session, market: str, *, min_rows: int = 120) -> int:
    universe_count = market_symbol_universe_count(db, market, min_rows=min_rows)
    if universe_count <= 0:
        return 10
    return max(10, min(100, universe_count // 5))


def resolve_best_ml_model(
    db: Session,
    market: str,
    target: str = "y_up_5d",
    model_id: Optional[int] = None,
    *,
    require_market_scope: bool = False,
    min_symbol_count: int = 0,
    allow_fallback_to_best: bool = False,
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
            return model_row
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
            f"No qualified market-wide model available for market={request_market}, target={request_target}. "
            "Train the market model first."
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
    return rows[0]


def load_ml_model_artifact(model_row) -> dict:
    if not model_row.artifact_path:
        raise RuntimeError("Model artifact path is empty.")

    artifact_path = Path(model_row.artifact_path).resolve()
    model_store = _model_store_dir().resolve()
    if model_store not in artifact_path.parents:
        raise RuntimeError("Model artifact path is not allowed.")
    if not artifact_path.exists():
        raise RuntimeError(f"Model artifact not found: {artifact_path}")

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

    artifact = load_ml_model_artifact(model_row)
    feature_version = str(artifact.get("feature_version") or model_row.feature_version or "v1")
    feature_cols = artifact.get("feature_cols") or []
    estimator = artifact.get("estimator")

    normalized_symbols = (
        _normalize_symbols(symbols, request_market) if symbols else None
    )
    feature_fetch_limit = max(int(limit or 100), 200)
    if not normalized_symbols:
        feature_fetch_limit = max(feature_fetch_limit, 5000)
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
        x = np.array([[float(feats.get(col, 0.0) or 0.0) for col in feature_cols]], dtype=float)
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
