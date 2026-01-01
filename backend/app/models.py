from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Float, BigInteger, UniqueConstraint, Index
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
