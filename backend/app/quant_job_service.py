from fastapi import Depends
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db
from .quant_base import executor
from .quant_task_runner import _run_job


def _enqueue_job(job_type: str, payload: dict, db: Session):
    job = crud.create_quant_job(db, schemas.QuantJobCreate(type=job_type, params=payload))
    executor.submit(_run_job, job.id)
    return schemas.APIResponse(message="Job queued", data=schemas.QuantJobRead.model_validate(job))


def start_kl_update(payload: dict, db: Session = Depends(get_db)):
    return _enqueue_job("kl_update", payload, db)


def start_backtest(payload: dict, db: Session = Depends(get_db)):
    return _enqueue_job("backtest", payload, db)


def start_grid_search(payload: dict, db: Session = Depends(get_db)):
    return _enqueue_job("grid_search", payload, db)


def start_stock_select(payload: dict, db: Session = Depends(get_db)):
    return _enqueue_job("stock_select", payload, db)


def start_quant_tools(payload: dict, db: Session = Depends(get_db)):
    return _enqueue_job("analysis", payload, db)


def verify_quant_env(db: Session = Depends(get_db)):
    return _enqueue_job("verify", {}, db)


def start_ml_feature_build(payload: dict, db: Session = Depends(get_db)):
    return _enqueue_job("ml_feature", payload, db)


def start_ml_train(payload: dict, db: Session = Depends(get_db)):
    return _enqueue_job("ml_train", payload, db)


def start_ml_predict(payload: dict, db: Session = Depends(get_db)):
    return _enqueue_job("ml_predict", payload, db)
