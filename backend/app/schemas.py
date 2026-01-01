from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class APIResponse(BaseModel):
    message: str = Field(default="success")
    data: Optional[object] = None


class SymbolRead(BaseModel):
    symbol: str
    market: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    industry: Optional[str] = None
    kind: Optional[str] = None


class StockSymbolRead(SymbolRead):
    pass


class QuantJobCreate(BaseModel):
    type: str = Field(..., max_length=50)
    params: dict = Field(default_factory=dict)


class QuantJobRead(BaseModel):
    id: int
    type: str
    status: str
    params: dict
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
