from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    Float,
    BigInteger,
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .database import Base


class QuantJob(Base):
    __tablename__ = "quant_jobs"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True, default="queued")
    params = Column(JSONB, nullable=False, default=dict)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class StockSymbol(Base):
    __tablename__ = "stock_symbols"

    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(8), nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    exchange = Column(String(64), nullable=True)
    industry = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("market", "symbol", name="uq_stock_symbol_market_symbol"),)


class StockKline(Base):
    __tablename__ = "stock_klines"

    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(8), nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    pre_close = Column(Float, nullable=True)
    p_change = Column(Float, nullable=True)
    volume = Column(BigInteger, nullable=True)
    date_week = Column(Integer, nullable=True)
    key = Column(Integer, nullable=True)
    atr14 = Column(Float, nullable=True)
    atr21 = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("market", "symbol", "trade_date", name="uq_stock_kline_market_symbol_date"),
        Index("ix_stock_kline_symbol_date", "symbol", "trade_date"),
    )


class MLFeatureSnapshot(Base):
    __tablename__ = "ml_feature_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(8), nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    feature_version = Column(String(32), nullable=False, default="v1", index=True)
    features = Column(JSONB, nullable=False, default=dict)
    y_up_5d = Column(Integer, nullable=True)
    y_ret_5d = Column(Float, nullable=True)
    y_mdd_10d = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "market",
            "symbol",
            "trade_date",
            "feature_version",
            name="uq_ml_feature_snapshot_key",
        ),
        Index("ix_ml_feature_snapshot_symbol_date", "symbol", "trade_date"),
    )


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    market = Column(String(8), nullable=False, index=True, default="CN")
    target = Column(String(64), nullable=False, index=True, default="y_up_5d")
    algo = Column(String(64), nullable=False, default="HistGradientBoostingClassifier")
    feature_version = Column(String(32), nullable=False, default="v1")
    train_start = Column(Date, nullable=True)
    train_end = Column(Date, nullable=True)
    val_start = Column(Date, nullable=True)
    val_end = Column(Date, nullable=True)
    params = Column(JSONB, nullable=False, default=dict)
    metrics = Column(JSONB, nullable=False, default=dict)
    artifact_path = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="trained", index=True)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_ml_models_market_target_active", "market", "target", "is_active"),
    )


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, nullable=False, index=True)
    market = Column(String(8), nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    score_up_5d = Column(Float, nullable=True)
    expected_ret_5d = Column(Float, nullable=True)
    risk_mdd_10d = Column(Float, nullable=True)
    action = Column(String(32), nullable=True)
    position_min = Column(Float, nullable=True)
    position_max = Column(Float, nullable=True)
    meta = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("model_id", "symbol", "trade_date", name="uq_ml_prediction_key"),
        Index("ix_ml_prediction_market_date", "market", "trade_date"),
    )
