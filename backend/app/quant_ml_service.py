from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from . import crud, schemas


def list_ml_models(
    db: Session,
    market: str = "CN",
    target: str = "y_up_5d",
    limit: int = 100,
):
    rows = crud.list_ml_models(db, market=market, target=target, limit=limit)
    data = [
        {
            "id": item.id,
            "name": item.name,
            "market": item.market,
            "target": item.target,
            "algo": item.algo,
            "feature_version": item.feature_version,
            "metrics": item.metrics or {},
            "params": item.params or {},
            "status": item.status,
            "is_active": bool(item.is_active),
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
    model_id: Optional[int] = None,
    limit: int = 100,
):
    rows = crud.list_latest_ml_predictions(db, market=market, model_id=model_id, limit=limit)
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
        for item in rows
    ]
    return schemas.APIResponse(data=data)
