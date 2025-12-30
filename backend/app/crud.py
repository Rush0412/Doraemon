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
