from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=schemas.APIResponse)
def list_tasks(db: Session = Depends(get_db)):
    tasks = crud.get_tasks(db)
    return schemas.APIResponse(data=[schemas.TaskRead.from_orm(task) for task in tasks])


@router.post("/", response_model=schemas.APIResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = crud.create_task(db, payload)
    return schemas.APIResponse(message="Task created", data=schemas.TaskRead.from_orm(task))


@router.get("/{task_id}", response_model=schemas.APIResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return schemas.APIResponse(data=schemas.TaskRead.from_orm(task))


@router.put("/{task_id}", response_model=schemas.APIResponse)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    task = crud.update_task(db, task, payload)
    return schemas.APIResponse(message="Task updated", data=schemas.TaskRead.from_orm(task))


@router.delete("/{task_id}", response_model=schemas.APIResponse)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    crud.delete_task(db, task)
    return schemas.APIResponse(message="Task deleted", data={"id": task_id})
