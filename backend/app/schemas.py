from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ANALYSIS_TOOLS = {
    "support_resistance",
    "support",
    "resistance",
    "jump_gap",
    "jump",
    "trend_speed",
    "pair_speed",
    "shift_distance",
    "regress",
    "price_channel",
    "golden_ratio",
    "golden",
    "correlation",
    "distance",
    "p_change_stats",
    "date_week_wave",
    "date_week_win",
    "bcut_change_vc",
    "qcut_change_vc",
    "wave_change_rate",
}
VALIDATION_MODES = {"none", "holdout", "walk_forward"}
KLINE_COVERAGE_MODES = {"all", "missing", "below_min_rows"}
KLINE_RUN_MODES = {"thread", "main", "process"}


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_market(value: Any) -> str:
    raw = (_clean_text(value) or "CN").upper()
    aliases = {
        "A": "CN",
        "ALL": "CN",
        "ASHARE": "CN",
        "A_SHARE": "CN",
    }
    return aliases.get(raw, raw)


def _normalize_symbols(value: Any) -> Optional[Union[str, list[str]]]:
    if value is None:
        return None
    if isinstance(value, str):
        parts = [item.strip().upper() for item in value.replace(";", ",").split(",")]
        parts = [item for item in parts if item]
        return ", ".join(dict.fromkeys(parts)) or None
    if isinstance(value, (list, tuple, set)):
        cleaned = []
        for item in value:
            text = _clean_text(item)
            if text:
                cleaned.append(text.upper())
        deduped = list(dict.fromkeys(cleaned))
        return deduped or None
    raise ValueError("symbols must be a comma separated string or string array")


def _normalize_date_text(value: Any) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("date must use YYYY-MM-DD format") from exc


def _normalize_optional_slug(value: Any, *, lower: bool = False) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    return text.lower() if lower else text


def _normalize_string_list(value: Any) -> Optional[list[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        items = [item.strip().lower() for item in value.replace(";", ",").split(",")]
        items = [item for item in items if item]
        return list(dict.fromkeys(items)) or None
    if isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            text = _clean_text(item)
            if text:
                items.append(text.lower())
        return list(dict.fromkeys(items)) or None
    raise ValueError("value must be a string list")


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


class ManualSymbolItem(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    market: str = Field(default="CN", min_length=2, max_length=12)
    name: Optional[str] = Field(default=None, max_length=120)
    exchange: Optional[str] = Field(default=None, max_length=32)
    industry: Optional[str] = Field(default=None, max_length=120)
    kind: Optional[str] = Field(default="stock", max_length=32)

    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    @field_validator("symbol", mode="before")
    @classmethod
    def validate_symbol(cls, value: Any) -> str:
        text = _clean_text(value)
        if not text:
            raise ValueError("symbol is required")
        return text.upper()

    @field_validator("market", mode="before")
    @classmethod
    def validate_market(cls, value: Any) -> str:
        return _normalize_market(value)

    @field_validator("name", "exchange", "industry", "kind", mode="before")
    @classmethod
    def trim_optional_text(cls, value: Any) -> Optional[str]:
        return _clean_text(value)


class ManualSymbolsPayload(BaseModel):
    market: str = Field(default="CN", min_length=2, max_length=12)
    symbols: list[ManualSymbolItem] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    @field_validator("market", mode="before")
    @classmethod
    def validate_market(cls, value: Any) -> str:
        return _normalize_market(value)

    @model_validator(mode="after")
    def validate_symbols(self):
        if not self.symbols:
            raise ValueError("symbols cannot be empty")
        normalized = []
        for item in self.symbols:
            if not item.market:
                item.market = self.market
            normalized.append(item)
        self.symbols = normalized
        return self


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

    model_config = ConfigDict(extra="allow", protected_namespaces=())

    @field_validator("market", mode="before")
    @classmethod
    def validate_market(cls, value: Any) -> str:
        return _normalize_market(value)

    @field_validator("symbols", mode="before")
    @classmethod
    def validate_symbols(cls, value: Any) -> Optional[Union[str, list[str]]]:
        return _normalize_symbols(value)

    @field_validator("start", "end", mode="before")
    @classmethod
    def validate_dates(cls, value: Any) -> Optional[str]:
        return _normalize_date_text(value)

    @model_validator(mode="after")
    def ensure_date_range(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must be earlier than or equal to end")
        return self


class KlineUpdatePayload(QuantPayloadBase):
    n_jobs: int = Field(default=8, ge=1, le=64)
    how: str = "thread"
    all: bool = False
    coverage_mode: Optional[str] = "all"
    min_kline_rows: Optional[int] = Field(default=120, ge=1, le=5000)

    @field_validator("how", mode="before")
    @classmethod
    def validate_run_mode(cls, value: Any) -> str:
        mode = (_normalize_optional_slug(value, lower=True) or "thread")
        if mode not in KLINE_RUN_MODES:
            raise ValueError(f"how must be one of: {', '.join(sorted(KLINE_RUN_MODES))}")
        return mode

    @field_validator("coverage_mode", mode="before")
    @classmethod
    def validate_coverage_mode(cls, value: Any) -> str:
        mode = (_normalize_optional_slug(value, lower=True) or "all")
        if mode not in KLINE_COVERAGE_MODES:
            raise ValueError(f"coverage_mode must be one of: {', '.join(sorted(KLINE_COVERAGE_MODES))}")
        return mode

    @model_validator(mode="after")
    def ensure_update_scope(self):
        if not self.all and not self.symbols:
            raise ValueError("symbols is required when all is false")
        return self


class BacktestPayload(QuantPayloadBase):
    cash: float = Field(default=1000000, gt=0)
    commission_rate: float = Field(default=0.00025, ge=0.0, le=0.05)
    min_commission: float = Field(default=5.0, ge=0.0, le=1000.0)
    stamp_tax_rate: float = Field(default=0.0005, ge=0.0, le=0.05)
    slippage_bp: float = Field(default=0.0, ge=0.0, le=500.0)
    buy_strategy: Optional[str] = None
    sell_strategy: Optional[str] = None
    buy_params: dict = Field(default_factory=dict)
    sell_params: dict = Field(default_factory=dict)

    @field_validator("buy_strategy", "sell_strategy", mode="before")
    @classmethod
    def normalize_strategy_name(cls, value: Any) -> Optional[str]:
        return _normalize_optional_slug(value, lower=True)


class GridSearchPayload(BacktestPayload):
    max_runs: int = Field(default=50, ge=1, le=5000)
    validation_mode: Optional[str] = None
    train_ratio: Optional[float] = Field(default=None, gt=0.0, lt=1.0)
    symbol_top_n: Optional[int] = Field(default=None, ge=1, le=100)
    symbol_eval_limit: Optional[int] = Field(default=None, ge=10, le=5000)

    @field_validator("validation_mode", mode="before")
    @classmethod
    def validate_validation_mode(cls, value: Any) -> Optional[str]:
        mode = _normalize_optional_slug(value, lower=True)
        if mode is None:
            return None
        if mode not in VALIDATION_MODES:
            raise ValueError(f"validation_mode must be one of: {', '.join(sorted(VALIDATION_MODES))}")
        return mode


class AnalysisPayload(QuantPayloadBase):
    tool: str
    limit: int = Field(default=200, ge=1, le=20000)
    options: dict = Field(default_factory=dict)

    @field_validator("tool", mode="before")
    @classmethod
    def validate_tool(cls, value: Any) -> str:
        tool = _normalize_optional_slug(value, lower=True)
        if not tool:
            raise ValueError("tool is required")
        if tool not in ANALYSIS_TOOLS:
            raise ValueError("unsupported analysis tool")
        return tool

    @model_validator(mode="after")
    def ensure_symbols_present(self):
        if not self.symbols:
            raise ValueError("analysis requires at least one symbol")
        return self


class MLPredictPayload(BaseModel):
    market: str = "CN"
    target: str = "y_up_5d"
    model_id: Optional[int] = Field(default=None, ge=1)
    symbols: Optional[Union[str, list[str]]] = None
    limit: int = Field(default=50, ge=1, le=500)

    model_config = ConfigDict(extra="allow", protected_namespaces=())

    @field_validator("market", mode="before")
    @classmethod
    def validate_market(cls, value: Any) -> str:
        return _normalize_market(value)

    @field_validator("symbols", mode="before")
    @classmethod
    def validate_symbols(cls, value: Any) -> Optional[Union[str, list[str]]]:
        return _normalize_symbols(value)

    @field_validator("target", mode="before")
    @classmethod
    def validate_target(cls, value: Any) -> str:
        return _normalize_optional_slug(value, lower=True) or "y_up_5d"


class MLStockSelectPayload(BacktestPayload):
    target: str = "y_up_5d"
    model_id: Optional[int] = Field(default=None, ge=1)
    min_score: float = Field(default=0.55, ge=0.0, le=1.0)
    min_expected_ret_5d: Optional[float] = None
    allowed_actions: list[str] = Field(default_factory=lambda: ["buy", "light_buy"])
    prediction_limit: int = Field(default=300, ge=20, le=50000)
    candidate_limit: int = Field(default=120, ge=10, le=50000)
    symbol_top_n: int = Field(default=20, ge=1, le=100)
    symbol_eval_limit: int = Field(default=120, ge=10, le=50000)
    min_kline_rows: int = Field(default=120, ge=60, le=2000)

    @field_validator("target", mode="before")
    @classmethod
    def validate_target(cls, value: Any) -> str:
        return _normalize_optional_slug(value, lower=True) or "y_up_5d"

    @field_validator("allowed_actions", mode="before")
    @classmethod
    def validate_allowed_actions(cls, value: Any) -> list[str]:
        actions = _normalize_string_list(value) or ["buy", "light_buy"]
        return actions


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

    @field_validator("market", mode="before")
    @classmethod
    def validate_market(cls, value: Any) -> str:
        return _normalize_market(value)

    @field_validator("feature_version", "target", mode="before")
    @classmethod
    def trim_ml_contract_text(cls, value: Any) -> Optional[str]:
        return _normalize_optional_slug(value, lower=True)

    @field_validator("model_name", mode="before")
    @classmethod
    def trim_model_name(cls, value: Any) -> Optional[str]:
        return _clean_text(value)


class MLFeaturePayload(QuantPayloadBase):
    feature_version: str = "v1"
    min_rows: int = Field(default=120, ge=30, le=3000)
    symbol_limit: int = Field(default=10000, ge=10, le=50000)

    @field_validator("feature_version", mode="before")
    @classmethod
    def validate_feature_version(cls, value: Any) -> str:
        return _normalize_optional_slug(value, lower=True) or "v1"


class JobBatchDeletePayload(BaseModel):
    ids: Optional[list[int]] = None
    statuses: Optional[list[str]] = None
    delete_finished: bool = True
    scan_limit: int = Field(default=2000, ge=1, le=10000)

    @field_validator("statuses", mode="before")
    @classmethod
    def validate_statuses(cls, value: Any) -> Optional[list[str]]:
        return _normalize_string_list(value)


class TrendFeatureRow(BaseModel):
    trade_date: Optional[str] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    ma5: Optional[float] = None
    ma20: Optional[float] = None
    rsi14: Optional[float] = None
    macd: Optional[float] = None

    model_config = ConfigDict(extra="allow", protected_namespaces=())

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value: Any) -> Optional[str]:
        return _normalize_date_text(value)


class TrendAnalysisDemoPayload(BaseModel):
    market: str = Field(default="CN", min_length=2, max_length=12)
    symbol: str = Field(..., min_length=1, max_length=32)
    horizon_days: int = Field(default=5, ge=1, le=90)
    chart_image_name: Optional[str] = Field(default=None, max_length=260)
    chart_image_type: Optional[str] = Field(default=None, max_length=80)
    chart_image_size_kb: Optional[float] = Field(default=None, ge=0.0, le=10240.0)
    feature_rows: list[TrendFeatureRow] = Field(default_factory=list)
    note: Optional[str] = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    @field_validator("market", mode="before")
    @classmethod
    def validate_market(cls, value: Any) -> str:
        return _normalize_market(value)

    @field_validator("symbol", mode="before")
    @classmethod
    def validate_symbol(cls, value: Any) -> str:
        text = _clean_text(value)
        if not text:
            raise ValueError("symbol is required")
        return text.upper()

    @field_validator("chart_image_name", "chart_image_type", "note", mode="before")
    @classmethod
    def trim_optional_fields(cls, value: Any) -> Optional[str]:
        return _clean_text(value)

    @model_validator(mode="after")
    def ensure_demo_inputs(self):
        if not self.chart_image_name and not self.feature_rows:
            raise ValueError("feature_rows or chart_image_name is required")
        return self
