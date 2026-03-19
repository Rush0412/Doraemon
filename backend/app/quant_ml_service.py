from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from . import crud, schemas
from .quant_ml_model_utils import (
    ml_model_markets,
    ml_model_scope,
    ml_model_symbol_count,
    model_artifact_available,
    recommended_market_model_min_symbol_count,
    resolve_best_ml_model,
)


def _is_index_symbol(symbol: str) -> bool:
    lower = str(symbol or "").strip().lower()
    return lower.startswith("sh000") or lower.startswith("sz399")


def list_ml_models(
    db: Session,
    market: str = "CN",
    target: str = "y_up_5d",
    limit: int = 100,
):
    request_market = str(market or "CN").strip().upper()
    rows = crud.list_ml_models(
        db,
        market=request_market,
        target=target,
        limit=limit,
        expand_market_scope=True,
    )
    request_markets = crud.ml_market_scope(request_market)
    min_symbol_count_required_by_market = {
        item_market: recommended_market_model_min_symbol_count(db, item_market)
        for item_market in request_markets
    }
    recommended_ids = set()
    for item_market in request_markets:
        try:
            recommended = resolve_best_ml_model(
                db,
                market=item_market,
                target=target,
                require_market_scope=True,
                min_symbol_count=min_symbol_count_required_by_market.get(item_market, 0),
                allow_fallback_to_best=True,
            )
            recommended_ids.add(int(recommended.id))
        except Exception:
            continue
    data = [
        {
            "id": item.id,
            "name": item.name,
            "market": item.market,
            "markets": ml_model_markets(item),
            "target": item.target,
            "algo": item.algo,
            "feature_version": item.feature_version,
            "metrics": item.metrics or {},
            "params": item.params or {},
            "scope": ml_model_scope(item),
            "symbol_count": ml_model_symbol_count(item),
            "min_symbol_count_required": int(
                min_symbol_count_required_by_market.get(str(item.market or "").strip().upper(), 0)
            ),
            "is_qualified_market_model": bool(
                ml_model_scope(item) == "market"
                and (ml_model_symbol_count(item) or 0)
                >= int(
                    min_symbol_count_required_by_market.get(
                        str(item.market or "").strip().upper(),
                        0,
                    )
                )
            ),
            "is_recommended": bool(int(item.id) in recommended_ids),
            "status": item.status,
            "is_active": bool(item.is_active),
            "artifact_available": model_artifact_available(item),
            "train_start": item.train_start.isoformat() if item.train_start else None,
            "train_end": item.train_end.isoformat() if item.train_end else None,
            "val_start": item.val_start.isoformat() if item.val_start else None,
            "val_end": item.val_end.isoformat() if item.val_end else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in rows
    ]
    return schemas.APIResponse(data=data)


def promote_ml_model(model_id: int, db: Session):
    model = crud.get_ml_model(db, model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    activated = crud.set_ml_model_active(db, model)
    return schemas.APIResponse(
        message="Model promoted",
        data={
            "id": activated.id,
            "name": activated.name,
            "market": activated.market,
            "target": activated.target,
            "status": activated.status,
            "is_active": bool(activated.is_active),
        },
    )


def list_ml_predictions(
    db: Session,
    market: str = "CN",
    target: str = "y_up_5d",
    model_id: Optional[int] = None,
    limit: int = 100,
    actions: Optional[str] = None,
    recommended_only: bool = True,
    unique_symbols: bool = True,
    include_indices: bool = False,
):
    request_market = str(market or "CN").strip().upper()
    request_target = str(target or "y_up_5d").strip()
    selected_model_id = model_id
    if selected_model_id is None and recommended_only:
        try:
            selected = resolve_best_ml_model(
                db,
                market=request_market,
                target=request_target,
                require_market_scope=True,
                min_symbol_count=recommended_market_model_min_symbol_count(db, request_market),
                allow_fallback_to_best=True,
                attempt_repair=True,
            )
            selected_model_id = int(selected.id)
        except Exception:
            selected_model_id = None

    fetch_limit = max(1, int(limit or 100))
    if unique_symbols or actions or recommended_only:
        fetch_limit = max(fetch_limit * 20, 500)
    rows = crud.list_latest_ml_predictions(
        db,
        market=request_market,
        model_id=selected_model_id,
        limit=fetch_limit,
        include_indices=include_indices,
    )

    action_filter: Optional[set[str]] = None
    if actions:
        action_filter = {
            str(item).strip().lower()
            for item in str(actions).split(",")
            if str(item).strip()
        }
    elif recommended_only:
        action_filter = {"buy", "light_buy"}

    picked = []
    seen_symbols = set()
    for item in rows:
        action_text = str(item.action or "").strip().lower()
        if action_filter and action_text not in action_filter:
            continue
        symbol_text = str(item.symbol or "").strip()
        if not include_indices and _is_index_symbol(symbol_text):
            continue
        if unique_symbols:
            if symbol_text in seen_symbols:
                continue
            seen_symbols.add(symbol_text)
        picked.append(item)
        if len(picked) >= max(1, int(limit or 100)):
            break

    data = [
        {
            "id": item.id,
            "model_id": item.model_id,
            "market": item.market,
            "symbol": item.symbol,
            "trade_date": item.trade_date.isoformat() if item.trade_date else None,
            "score_up_5d": item.score_up_5d,
            "expected_ret_5d": item.expected_ret_5d,
            "risk_mdd_10d": item.risk_mdd_10d,
            "action": item.action,
            "position_min": item.position_min,
            "position_max": item.position_max,
            "meta": item.meta or {},
        }
        for item in picked
    ]
    return schemas.APIResponse(data=data)
