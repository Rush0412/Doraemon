from typing import Optional, Union
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


class QuantPayloadBase(BaseModel):
    market: str = "CN"
    symbols: Optional[Union[str, list[str]]] = None
    n_folds: int = Field(default=1, ge=1, le=20)
    start: Optional[str] = None
    end: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class KlineUpdatePayload(QuantPayloadBase):
    n_jobs: int = Field(default=8, ge=1, le=64)
    how: str = "thread"
    all: bool = False


class BacktestPayload(QuantPayloadBase):
    cash: float = Field(default=1000000, gt=0)
    buy_strategy: Optional[str] = None
    sell_strategy: Optional[str] = None
    buy_params: dict = Field(default_factory=dict)
    sell_params: dict = Field(default_factory=dict)


class GridSearchPayload(BacktestPayload):
    max_runs: int = Field(default=50, ge=1, le=5000)
    validation_mode: Optional[str] = None
    train_ratio: Optional[float] = Field(default=None, gt=0.0, lt=1.0)
    symbol_top_n: Optional[int] = Field(default=None, ge=1, le=100)
    symbol_eval_limit: Optional[int] = Field(default=None, ge=10, le=5000)


class AnalysisPayload(QuantPayloadBase):
    tool: str
    limit: int = Field(default=200, ge=1, le=20000)
    options: dict = Field(default_factory=dict)


class MLPredictPayload(BaseModel):
    market: str = "CN"
    target: str = "y_up_5d"
    model_id: Optional[int] = Field(default=None, ge=1)
    symbols: Optional[Union[str, list[str]]] = None
    limit: int = Field(default=50, ge=1, le=500)

    model_config = ConfigDict(extra="allow", protected_namespaces=())


class MLStockSelectPayload(BacktestPayload):
    target: str = "y_up_5d"
    model_id: Optional[int] = Field(default=None, ge=1)
    min_score: float = Field(default=0.55, ge=0.0, le=1.0)
    min_expected_ret_5d: Optional[float] = None
    allowed_actions: list[str] = Field(default_factory=lambda: ["buy", "light_buy"])
    prediction_limit: int = Field(default=300, ge=20, le=2000)
    candidate_limit: int = Field(default=120, ge=10, le=1000)
    symbol_top_n: int = Field(default=20, ge=1, le=100)
    symbol_eval_limit: int = Field(default=120, ge=10, le=1000)
    min_kline_rows: int = Field(default=120, ge=60, le=2000)


class MLTrainPayload(BaseModel):
    market: str = "CN"
    feature_version: str = "v1"
    target: str = "y_up_5d"
    train_ratio: float = Field(default=0.8, gt=0.5, lt=0.96)
    max_samples: int = Field(default=300000, ge=1000, le=1000000)
    model_name: Optional[str] = None
    max_iter: int = Field(default=300, ge=50, le=5000)
    learning_rate: float = Field(default=0.05, gt=0.0, le=1.0)
    max_depth: int = Field(default=6, ge=2, le=32)
    min_samples_leaf: int = Field(default=30, ge=1, le=10000)
    l2_regularization: float = Field(default=0.0, ge=0.0, le=1000.0)

    model_config = ConfigDict(extra="allow", protected_namespaces=())


class MLFeaturePayload(QuantPayloadBase):
    feature_version: str = "v1"
    min_rows: int = Field(default=120, ge=30, le=3000)
    symbol_limit: int = Field(default=300, ge=10, le=10000)


class JobBatchDeletePayload(BaseModel):
    ids: Optional[list[int]] = None
    statuses: Optional[list[str]] = None
    delete_finished: bool = True
    scan_limit: int = Field(default=2000, ge=1, le=10000)
