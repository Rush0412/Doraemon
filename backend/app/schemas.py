from typing import Optional
from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    message: str = Field(default="success")
    data: Optional[object] = None


class TaskBase(BaseModel):
    title: str = Field(..., max_length=255, description="Short title for the task")
    description: Optional[str] = Field(None, description="Optional details")
    completed: bool = Field(default=False, description="Completion status")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    completed: Optional[bool] = None


class TaskRead(TaskBase):
    id: int

    class Config:
        from_attributes = True
