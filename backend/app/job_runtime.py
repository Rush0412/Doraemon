from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from . import crud, models
from .database import SessionLocal

DEFAULT_JOB_TIMEOUTS = {
    "verify": 10 * 60,
    "analysis": 20 * 60,
    "backtest": 90 * 60,
    "stock_select": 90 * 60,
    "grid_search": 4 * 60 * 60,
    "kl_update": 6 * 60 * 60,
    "ml_feature": 90 * 60,
    "ml_train": 4 * 60 * 60,
    "ml_predict": 60 * 60,
    "ml_stock_select": 90 * 60,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _job_timeout_seconds(job: models.QuantJob) -> int:
    params = job.params or {}
    try:
        custom = int(params.get("timeout_seconds", 0) or 0)
    except Exception:
        custom = 0
    if custom > 0:
        return custom
    return DEFAULT_JOB_TIMEOUTS.get(job.type, 2 * 60 * 60)


def _job_deadline(job: models.QuantJob) -> Optional[datetime]:
    base = job.updated_at or job.created_at
    if not base or str(job.status or "").lower() != "running":
        return None
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base + timedelta(seconds=_job_timeout_seconds(job))


def expire_stale_job(db: Session, job: models.QuantJob, now: Optional[datetime] = None) -> models.QuantJob:
    now = now or _utc_now()
    deadline = _job_deadline(job)
    if deadline is None or deadline > now:
        return job
    timeout_seconds = _job_timeout_seconds(job)
    return (
        crud.set_quant_job_error(
            db,
            job.id,
            f"Job exceeded timeout of {timeout_seconds} seconds and was marked failed automatically.",
            overwrite_terminal=False,
        )
        or job
    )


def expire_stale_jobs(db: Session, jobs: Iterable[models.QuantJob]) -> list[models.QuantJob]:
    now = _utc_now()
    normalized = []
    for job in jobs:
        normalized.append(expire_stale_job(db, job, now=now))
    return normalized


def cleanup_stale_jobs(limit: int = 10000) -> int:
    db = SessionLocal()
    try:
        jobs = crud.list_quant_jobs(db, limit=max(1, int(limit)))
        now = _utc_now()
        expired = 0
        for job in jobs:
            previous = str(job.status or "").lower()
            current = expire_stale_job(db, job, now=now)
            if previous == "running" and str(current.status or "").lower() == "failed":
                expired += 1
        return expired
    finally:
        db.close()
