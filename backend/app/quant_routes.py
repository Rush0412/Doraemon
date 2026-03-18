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
def import_symbols(payload: schemas.QuantPayloadBase, db: Session = Depends(get_db)):
    return service.import_symbols(payload.model_dump(exclude_none=True), db)


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
def start_kl_update(payload: schemas.KlineUpdatePayload, db: Session = Depends(get_db)):
    return service.start_kl_update(payload.model_dump(exclude_none=True), db)


@quant_router.post("/backtest", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_backtest(payload: schemas.BacktestPayload, db: Session = Depends(get_db)):
    return service.start_backtest(payload.model_dump(exclude_none=True), db)


@quant_router.post("/grid-search", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_grid_search(payload: schemas.GridSearchPayload, db: Session = Depends(get_db)):
    return service.start_grid_search(payload.model_dump(exclude_none=True), db)


@quant_router.post("/stock-select", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_stock_select(payload: schemas.BacktestPayload, db: Session = Depends(get_db)):
    return service.start_stock_select(payload.model_dump(exclude_none=True), db)


@quant_router.post("/tools", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_quant_tools(payload: schemas.AnalysisPayload, db: Session = Depends(get_db)):
    return service.start_quant_tools(payload.model_dump(exclude_none=True), db)


@quant_router.post("/ml/features/build", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_ml_feature_build(payload: schemas.MLFeaturePayload, db: Session = Depends(get_db)):
    return service.start_ml_feature_build(payload.model_dump(exclude_none=True), db)


@quant_router.post("/ml/train", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_ml_train(payload: schemas.MLTrainPayload, db: Session = Depends(get_db)):
    return service.start_ml_train(payload.model_dump(exclude_none=True), db)


@quant_router.post("/ml/predict", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_ml_predict(payload: schemas.MLPredictPayload, db: Session = Depends(get_db)):
    return service.start_ml_predict(payload.model_dump(exclude_none=True), db)


@quant_router.post("/ml/stock-select", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_ml_stock_select(payload: schemas.MLStockSelectPayload, db: Session = Depends(get_db)):
    return service.start_ml_stock_select(payload.model_dump(exclude_none=True), db)


@quant_router.get("/ml/models", response_model=schemas.APIResponse)
def list_ml_models(
    market: str = "CN",
    target: str = "y_up_5d",
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return service.list_ml_models(db, market=market, target=target, limit=limit)


@quant_router.post("/ml/models/{model_id}/promote", response_model=schemas.APIResponse)
def promote_ml_model(model_id: int, db: Session = Depends(get_db)):
    return service.promote_ml_model(model_id, db)


@quant_router.get("/ml/predictions", response_model=schemas.APIResponse)
def list_ml_predictions(
    market: str = "CN",
    target: str = "y_up_5d",
    model_id: Optional[int] = None,
    limit: int = 100,
    actions: Optional[str] = None,
    recommended_only: bool = True,
    unique_symbols: bool = True,
    include_indices: bool = False,
    db: Session = Depends(get_db),
):
    return service.list_ml_predictions(
        db,
        market=market,
        target=target,
        model_id=model_id,
        limit=limit,
        actions=actions,
        recommended_only=recommended_only,
        unique_symbols=unique_symbols,
        include_indices=include_indices,
    )


@quant_router.get("/verify", response_model=schemas.APIResponse)
def verify_quant_env(db: Session = Depends(get_db)):
    return service.verify_quant_env(db)
