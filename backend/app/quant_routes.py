from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from . import schemas
from .database import get_db
from . import quant_service as service

quant_router = APIRouter(prefix="/quant", tags=["quant"])


@quant_router.get("/features", response_model=schemas.APIResponse)
def list_feature_map():
    return service.list_feature_map()


@quant_router.post("/symbols/import", response_model=schemas.APIResponse)
def import_symbols(payload: dict, db: Session = Depends(get_db)):
    return service.import_symbols(payload, db)


@quant_router.post("/symbols/manual", response_model=schemas.APIResponse)
def upsert_manual_symbols(payload: dict, db: Session = Depends(get_db)):
    return service.upsert_manual_symbols(payload, db)


@quant_router.get("/symbols", response_model=schemas.APIResponse)
def search_symbols(
    market: str = "CN",
    q: str = "",
    kind: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    return service.search_symbols(market, q, kind, page, page_size, db)


@quant_router.get("/symbols/{symbol}", response_model=schemas.APIResponse)
def get_symbol(symbol: str, market: str = "CN", db: Session = Depends(get_db)):
    return service.get_symbol(symbol, market, db)


@quant_router.get("/klines", response_model=schemas.APIResponse)
def get_klines(
    symbol: str,
    market: str = "CN",
    start: Optional[date] = None,
    end: Optional[date] = None,
    n_folds: int = 1,
    limit: int = 2000,
    db: Session = Depends(get_db),
):
    return service.get_klines(symbol, market, start, end, n_folds, limit, db)


@quant_router.get("/strategies", response_model=schemas.APIResponse)
def list_strategies():
    return service.list_strategies()


@quant_router.post("/kl/update", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_kl_update(payload: dict, db: Session = Depends(get_db)):
    return service.start_kl_update(payload, db)


@quant_router.post("/backtest", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_backtest(payload: dict, db: Session = Depends(get_db)):
    return service.start_backtest(payload, db)


@quant_router.post("/grid-search", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_grid_search(payload: dict, db: Session = Depends(get_db)):
    return service.start_grid_search(payload, db)


@quant_router.post("/stock-select", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_stock_select(payload: dict, db: Session = Depends(get_db)):
    return service.start_stock_select(payload, db)


@quant_router.post("/tools", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_quant_tools(payload: dict, db: Session = Depends(get_db)):
    return service.start_quant_tools(payload, db)


@quant_router.get("/verify", response_model=schemas.APIResponse)
def verify_quant_env(db: Session = Depends(get_db)):
    return service.verify_quant_env(db)
