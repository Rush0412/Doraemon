import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sqlalchemy.orm import Session

from . import crud
from .quant_base import _market_scope, _normalize_symbols


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
        if isinstance(v, (float, int, np.floating, np.integer)):
            if np.isnan(v):
                return None
            return float(v)
        return float(v)
    except Exception:
        return None


def _load_kline_frame(
    db: Session,
    market: str,
    symbols: list[str],
    start: Optional[str] = None,
    end: Optional[str] = None,
    min_rows: int = 120,
) -> pd.DataFrame:
    start_date = None
    end_date = None
    if start:
        start_date = pd.to_datetime(start).date()
    if end:
        end_date = pd.to_datetime(end).date()

    records = []
    for symbol in symbols:
        rows = crud.load_klines(db, market=_market_from_symbol(symbol), symbol=symbol, start=start_date, end=end_date)
        if len(rows) < min_rows:
            continue
        for row in rows:
            records.append(
                {
                    "market": row.market,
                    "symbol": row.symbol,
                    "trade_date": row.trade_date,
                    "open": row.open,
                    "close": row.close,
                    "high": row.high,
                    "low": row.low,
                    "pre_close": row.pre_close,
                    "p_change": row.p_change,
                    "volume": row.volume,
                    "atr14": row.atr14,
                    "atr21": row.atr21,
                }
            )
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame.from_records(records)
    df = df.sort_values(["symbol", "trade_date"]).reset_index(drop=True)
    return df


def _market_from_symbol(symbol: str) -> str:
    lower = str(symbol or "").lower()
    if lower.startswith("us"):
        return "US"
    if lower.startswith("hk"):
        return "HK"
    if lower.startswith("sh"):
        return "SH"
    if lower.startswith("sz3"):
        return "300"
    if lower.startswith("sz"):
        return "SZ"
    return "CN"


def _build_feature_frame(kline_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    if kline_df.empty:
        return kline_df, []

    df = kline_df.copy()
    g = df.groupby("symbol", group_keys=False)

    df["ret_1"] = g["close"].pct_change(1)
    df["ret_3"] = g["close"].pct_change(3)
    df["ret_5"] = g["close"].pct_change(5)
    df["ret_10"] = g["close"].pct_change(10)

    df["ma_5"] = g["close"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    df["ma_10"] = g["close"].transform(lambda s: s.rolling(10, min_periods=10).mean())
    df["ma_20"] = g["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    df["ma_ratio_5_20"] = df["ma_5"] / df["ma_20"] - 1.0
    df["ma_ratio_10_20"] = df["ma_10"] / df["ma_20"] - 1.0

    df["vol_5"] = g["ret_1"].transform(lambda s: s.rolling(5, min_periods=5).std())
    df["vol_20"] = g["ret_1"].transform(lambda s: s.rolling(20, min_periods=20).std())

    df["vol_mean_5"] = g["volume"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    df["vol_mean_20"] = g["volume"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    df["vol_ratio_5"] = df["volume"] / df["vol_mean_5"]
    df["vol_ratio_20"] = df["volume"] / df["vol_mean_20"]

    atr_base = df["atr14"].where(df["atr14"].notna(), df["atr21"])
    atr_base = atr_base.where(atr_base.notna(), (df["high"] - df["low"]).abs())
    df["atr_ratio"] = atr_base / df["close"]

    # Forward labels for supervision (nullable on recent rows).
    df["y_ret_5d"] = g["close"].shift(-5) / df["close"] - 1.0
    low_future = pd.concat([g["low"].shift(-i) for i in range(1, 11)], axis=1)
    df["y_mdd_10d"] = low_future.min(axis=1) / df["close"] - 1.0
    df["y_up_5d"] = (df["y_ret_5d"] > 0).astype(float)
    df.loc[df["y_ret_5d"].isna(), "y_up_5d"] = np.nan

    feature_cols = [
        "ret_1",
        "ret_3",
        "ret_5",
        "ret_10",
        "ma_ratio_5_20",
        "ma_ratio_10_20",
        "vol_5",
        "vol_20",
        "vol_ratio_5",
        "vol_ratio_20",
        "atr_ratio",
        "p_change",
    ]

    # Keep rows with valid feature vectors; labels can be null for latest dates.
    feature_frame = df.dropna(subset=feature_cols).copy()
    return feature_frame, feature_cols


def run_ml_feature_job(job_params: dict, db: Session) -> dict:
    market = (job_params.get("market") or "CN").upper()
    feature_version = str(job_params.get("feature_version") or "v1")
    start = job_params.get("start")
    end = job_params.get("end")
    min_rows = int(job_params.get("min_rows", 120))
    symbol_limit = max(10, min(int(job_params.get("symbol_limit", 300)), 2000))

    raw_symbols = job_params.get("symbols")
    symbols = _normalize_symbols(raw_symbols, market)
    if not raw_symbols:
        markets = _market_scope(market)
        symbols = [
            item.symbol for item in crud.list_stock_symbols_by_markets(db, markets)[:symbol_limit]
        ]
    symbols = list(dict.fromkeys([str(s).strip() for s in symbols if str(s).strip()]))
    if not symbols:
        raise RuntimeError("No symbols available for ml_feature")

    kline_df = _load_kline_frame(db, market=market, symbols=symbols, start=start, end=end, min_rows=min_rows)
    if kline_df.empty:
        raise RuntimeError("No kline rows available to build ML features")

    feature_df, feature_cols = _build_feature_frame(kline_df)
    if feature_df.empty:
        raise RuntimeError("No valid feature rows after feature engineering")

    rows = []
    for _, row in feature_df.iterrows():
        features = {key: _safe_float_or_none(row.get(key)) for key in feature_cols}
        y_up = _safe_float_or_none(row.get("y_up_5d"))
        y_ret = _safe_float_or_none(row.get("y_ret_5d"))
        y_mdd = _safe_float_or_none(row.get("y_mdd_10d"))
        rows.append(
            {
                "market": str(row["market"]),
                "symbol": str(row["symbol"]),
                "trade_date": pd.to_datetime(row["trade_date"]).date(),
                "feature_version": feature_version,
                "features": features,
                "y_up_5d": None if y_up is None else int(y_up > 0.5),
                "y_ret_5d": y_ret,
                "y_mdd_10d": y_mdd,
            }
        )

    upserted = crud.upsert_ml_feature_rows(db, rows)
    labeled = int(feature_df["y_up_5d"].notna().sum())
    return {
        "message": "ml_feature finished",
        "market": market,
        "feature_version": feature_version,
        "symbols": len(set(feature_df["symbol"].tolist())),
        "rows_total": int(len(feature_df)),
        "rows_labeled": labeled,
        "rows_upserted": int(upserted),
        "feature_cols": feature_cols,
        "date_start": str(feature_df["trade_date"].min()),
        "date_end": str(feature_df["trade_date"].max()),
    }


def _build_training_frame(feature_rows: list) -> tuple[pd.DataFrame, list[str]]:
    records = []
    feature_cols = None
    for item in feature_rows:
        feats = item.features or {}
        if not feats:
            continue
        if feature_cols is None:
            feature_cols = sorted(feats.keys())
        rec = {col: _safe_float_or_none(feats.get(col)) for col in feature_cols}
        rec["market"] = item.market
        rec["symbol"] = item.symbol
        rec["trade_date"] = item.trade_date
        rec["y_up_5d"] = item.y_up_5d
        rec["y_ret_5d"] = item.y_ret_5d
        rec["y_mdd_10d"] = item.y_mdd_10d
        records.append(rec)
    if not records:
        return pd.DataFrame(), []
    df = pd.DataFrame.from_records(records)
    if not feature_cols:
        return pd.DataFrame(), []
    df = df.dropna(subset=feature_cols)
    return df, feature_cols


def run_ml_train_job(job_params: dict, db: Session) -> dict:
    market = (job_params.get("market") or "CN").upper()
    feature_version = str(job_params.get("feature_version") or "v1")
    target = str(job_params.get("target") or "y_up_5d")
    train_ratio = float(job_params.get("train_ratio", 0.8))
    train_ratio = min(max(train_ratio, 0.6), 0.95)
    max_samples = max(1000, min(int(job_params.get("max_samples", 300000)), 1_000_000))
    symbols = _normalize_symbols(job_params.get("symbols"), market) if job_params.get("symbols") else None

    feature_rows = crud.list_ml_feature_snapshots(
        db,
        market=market,
        feature_version=feature_version,
        symbols=symbols,
        limit=max_samples,
    )
    if not feature_rows:
        raise RuntimeError("No feature snapshots found. Run ml_feature first.")

    frame, feature_cols = _build_training_frame(feature_rows)
    if frame.empty:
        raise RuntimeError("Training frame is empty after cleaning.")
    if target not in frame.columns:
        raise RuntimeError(f"Target column {target} not found")

    frame = frame.dropna(subset=[target]).copy()
    if frame.empty:
        raise RuntimeError("No labeled rows for training.")
    frame = frame.sort_values("trade_date").reset_index(drop=True)

    split_idx = int(len(frame) * train_ratio)
    split_idx = min(max(split_idx, 200), len(frame) - 100)
    train_df = frame.iloc[:split_idx]
    val_df = frame.iloc[split_idx:]
    if train_df[target].nunique() < 2:
        raise RuntimeError("Training labels only contain one class; need more diversified samples.")
    if val_df.empty:
        raise RuntimeError("Validation set is empty; increase sample size.")

    model_params = {
        "max_iter": int(job_params.get("max_iter", 300)),
        "learning_rate": float(job_params.get("learning_rate", 0.05)),
        "max_depth": int(job_params.get("max_depth", 6)),
        "l2_regularization": float(job_params.get("l2_regularization", 0.0)),
        "min_samples_leaf": int(job_params.get("min_samples_leaf", 30)),
        "random_state": 42,
    }
    clf = HistGradientBoostingClassifier(**model_params)
    clf.fit(train_df[feature_cols], train_df[target].astype(int))

    val_prob = clf.predict_proba(val_df[feature_cols])[:, 1]
    val_pred = (val_prob >= 0.5).astype(int)
    y_val = val_df[target].astype(int).values
    metrics = {
        "samples_total": int(len(frame)),
        "samples_train": int(len(train_df)),
        "samples_val": int(len(val_df)),
        "pos_rate_train": float(train_df[target].mean()),
        "pos_rate_val": float(val_df[target].mean()),
        "accuracy": float(accuracy_score(y_val, val_pred)),
    }
    if len(np.unique(y_val)) > 1:
        metrics["auc"] = float(roc_auc_score(y_val, val_prob))
        metrics["log_loss"] = float(log_loss(y_val, val_prob, labels=[0, 1]))
    else:
        metrics["auc"] = None
        metrics["log_loss"] = None

    now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = str(job_params.get("model_name") or f"hgb_{market}_{target}_{feature_version}")
    artifact_path = _model_store_dir() / f"{model_name}_{now_tag}.pkl"

    payload = {
        "name": model_name,
        "market": market,
        "target": target,
        "algo": "HistGradientBoostingClassifier",
        "feature_version": feature_version,
        "train_start": train_df["trade_date"].min(),
        "train_end": train_df["trade_date"].max(),
        "val_start": val_df["trade_date"].min(),
        "val_end": val_df["trade_date"].max(),
        "params": model_params,
        "metrics": metrics,
        "artifact_path": str(artifact_path),
        "status": "trained",
        "is_active": False,
    }
    model_row = crud.create_ml_model(db, payload)

    artifact_payload = {
        "model_id": model_row.id,
        "model_name": model_name,
        "market": market,
        "target": target,
        "feature_version": feature_version,
        "feature_cols": feature_cols,
        "metrics": metrics,
        "trained_at": datetime.now().isoformat(),
        "estimator": clf,
    }
    with open(artifact_path, "wb") as f:
        pickle.dump(artifact_payload, f)

    active = crud.get_active_ml_model(db, market=market, target=target)
    auto_promoted = False
    if active is None:
        crud.set_ml_model_active(db, model_row)
        auto_promoted = True

    return {
        "message": "ml_train finished",
        "model_id": model_row.id,
        "model_name": model_name,
        "market": market,
        "target": target,
        "feature_version": feature_version,
        "metrics": metrics,
        "artifact_path": str(artifact_path),
        "auto_promoted": auto_promoted,
    }


def _score_to_action(score: float):
    if score >= 0.7:
        return "buy", 0.30, 0.50
    if score >= 0.55:
        return "light_buy", 0.10, 0.20
    if score <= 0.45:
        return "avoid", 0.00, 0.05
    return "hold", 0.05, 0.10


def run_ml_predict_job(job_params: dict, db: Session) -> dict:
    market = (job_params.get("market") or "CN").upper()
    target = str(job_params.get("target") or "y_up_5d")
    limit = max(1, min(int(job_params.get("limit", 50)), 500))
    symbols = _normalize_symbols(job_params.get("symbols"), market) if job_params.get("symbols") else None

    model_id = job_params.get("model_id")
    model_row = crud.get_ml_model(db, int(model_id)) if model_id else None
    if model_row is None:
        model_row = crud.get_active_ml_model(db, market=market, target=target)
    if model_row is None:
        raise RuntimeError("No active model found. Train and promote a model first.")
    if not model_row.artifact_path:
        raise RuntimeError("Model artifact path is empty.")

    artifact_path = Path(model_row.artifact_path)
    if not artifact_path.exists():
        raise RuntimeError(f"Model artifact not found: {artifact_path}")
    with open(artifact_path, "rb") as f:
        artifact = pickle.load(f)

    feature_version = str(artifact.get("feature_version") or model_row.feature_version or "v1")
    feature_cols = artifact.get("feature_cols") or []
    estimator = artifact.get("estimator")
    if estimator is None or not feature_cols:
        raise RuntimeError("Model artifact is invalid.")

    latest_rows = crud.list_latest_ml_feature_snapshots(
        db,
        market=market,
        feature_version=feature_version,
        symbols=symbols,
        limit=max(limit * 4, 200),
    )
    if not latest_rows:
        raise RuntimeError("No latest feature snapshots found. Run ml_feature first.")

    score_rows = []
    prediction_rows = []
    for item in latest_rows:
        feats = item.features or {}
        x = np.array([[float(feats.get(col, 0.0) or 0.0) for col in feature_cols]], dtype=float)
        prob = float(estimator.predict_proba(x)[0, 1])
        action, pos_min, pos_max = _score_to_action(prob)
        expected_ret = float((prob - 0.5) * 0.12)
        vol_20 = _safe_float_or_none(feats.get("vol_20")) or 0.0
        risk_mdd = float(-abs(vol_20) * 2.0)
        prediction_rows.append(
            {
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
                    "target": target,
                },
            }
        )
        score_rows.append(
            {
                "symbol": item.symbol,
                "trade_date": item.trade_date.isoformat() if item.trade_date else None,
                "score_up_5d": prob,
                "expected_ret_5d": expected_ret,
                "risk_mdd_10d": risk_mdd,
                "action": action,
                "position_range": [pos_min, pos_max],
            }
        )

    upserted = crud.upsert_ml_predictions(db, prediction_rows)
    score_rows = sorted(score_rows, key=lambda r: r.get("score_up_5d", 0.0), reverse=True)[:limit]

    return {
        "message": "ml_predict finished",
        "model_id": model_row.id,
        "model_name": model_row.name,
        "market": market,
        "target": target,
        "feature_version": feature_version,
        "rows_scored": len(prediction_rows),
        "rows_upserted": int(upserted),
        "top_predictions": score_rows,
    }
