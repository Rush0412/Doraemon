from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from . import models, schemas


def get_tasks(db: Session) -> list[models.Task]:
    result = db.execute(select(models.Task).order_by(models.Task.id))
    return result.scalars().all()


def get_task(db: Session, task_id: int) -> Optional[models.Task]:
    return db.get(models.Task, task_id)


def create_task(db: Session, payload: schemas.TaskCreate) -> models.Task:
    task = models.Task(**payload.dict())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, db_task: models.Task, payload: schemas.TaskUpdate) -> models.Task:
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(db_task, field, value)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, db_task: models.Task) -> None:
    db.delete(db_task)
    db.commit()


def create_quant_job(db: Session, payload: schemas.QuantJobCreate) -> models.QuantJob:
    job = models.QuantJob(type=payload.type, params=payload.params, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_quant_job(db: Session, job_id: int) -> Optional[models.QuantJob]:
    return db.get(models.QuantJob, job_id)


def list_quant_jobs(db: Session, limit: int = 50) -> list[models.QuantJob]:
    result = db.execute(select(models.QuantJob).order_by(models.QuantJob.id.desc()).limit(limit))
    return result.scalars().all()


def set_quant_job_running(db: Session, job: models.QuantJob) -> models.QuantJob:
    job.status = "running"
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def set_quant_job_result(db: Session, job: models.QuantJob, result: dict) -> models.QuantJob:
    job.status = "succeeded"
    job.result = result
    job.error = None
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def set_quant_job_error(db: Session, job: models.QuantJob, error: str) -> models.QuantJob:
    job.status = "failed"
    job.error = error
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
