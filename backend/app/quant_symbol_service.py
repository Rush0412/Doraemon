from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db
from .quant_base import *
def list_feature_map():
    data = {
        "legacy": [
            {"name": "股票基础信息查询", "source": "abupy_ui/widget_stock_info.py", "api": "/api/v1/quant/symbols"},
            {"name": "数据下载与更新", "source": "abupy_ui/widget_update_ui.py", "api": "/api/v1/quant/kl/update"},
            {"name": "历史回测任务", "source": "abupy_ui/widget_loop_back.py", "api": "/api/v1/quant/backtest"},
            {"name": "参数寻优交叉验证", "source": "abupy/WidgetBu/ABuWGGridSearch.py", "api": "/api/v1/quant/grid-search"},
            {"name": "独立选股任务", "source": "abupy strategy batch evaluator", "api": "/api/v1/quant/stock-select"},
            {"name": "量化分析工具", "source": "abupy_ui/widget_quant_tool.py", "api": "/api/v1/quant/tools"},
            {"name": "环境验证工具", "source": "abupy_ui/widget_verify_tool.py", "api": "/api/v1/quant/verify"},
        ],
        "phase_plan": [
            {"phase": 1, "scope": ["symbol search", "kl update", "backtest jobs", "job status sync"]},
            {"phase": 2, "scope": ["grid search jobs", "analysis tools", "report export", "result persistence"]},
            {"phase": 3, "scope": ["strategy library", "fine-grained permissions", "audit logs"]},
        ],
    }
    return schemas.APIResponse(data=data)


def import_symbols(payload: dict, db: Session = Depends(get_db)):
    market = (payload.get("market") or "CN").upper()
    rows = _build_symbol_rows(market)
    count = crud.upsert_stock_symbols(db, rows)
    return schemas.APIResponse(message="Symbols imported", data={"count": count})


def upsert_manual_symbols(payload: dict, db: Session = Depends(get_db)):
    rows, skipped = _build_manual_symbol_rows(payload)
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No symbols provided")
    count = crud.upsert_stock_symbols(db, rows)
    return schemas.APIResponse(message="Symbols upserted", data={"count": count, "skipped": skipped})


def search_symbols(
    market: str = "CN",
    q: Optional[str] = None,
    kind: str = "stock",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    query = (q or "").strip()
    market = (market or "CN").upper()
    markets = _market_scope(market)
    kind = (kind or "all").strip().lower()
    if kind not in {"stock", "index", "all"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid kind")
    items, total = crud.search_stock_symbols(db, markets, query, kind, page, page_size)
    if total == 0 and query and market in {"CN", "SH", "SZ", "300"}:
        if _ensure_symbol_from_akshare(db, market, query):
            items, total = crud.search_stock_symbols(db, markets, query, kind, page, page_size)
    payload = [
        schemas.StockSymbolRead(
            symbol=item.symbol,
            market=item.market,
            name=item.name,
            exchange=item.exchange,
            industry=item.industry,
            kind=_symbol_kind(item.symbol, item.name, item.industry),
        )
        for item in items
    ]
    if total == 0:
        kline_rows, total = crud.search_stock_symbols_from_klines(db, markets, query, kind, page, page_size)
        payload = [
            schemas.StockSymbolRead(
                symbol=symbol,
                market=market_value,
                name=None,
                exchange=market_value,
                industry=None,
                kind=_symbol_kind(symbol, None, None),
            )
            for market_value, symbol in kline_rows
        ]
    return schemas.APIResponse(
        data={
            "items": payload,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


def get_symbol(symbol: str, market: str = "CN", db: Session = Depends(get_db)):
    market = (market or "CN").upper()
    want = symbol.strip()
    item = None
    for market_key in _market_scope(market):
        item = crud.get_stock_symbol(db, market_key, want)
        if item:
            break
    if not item and market in {"CN", "SH", "SZ", "300"}:
        if _ensure_symbol_from_akshare(db, market, want):
            for market_key in _market_scope(market):
                item = crud.get_stock_symbol(db, market_key, want)
                if item:
                    break
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")
    return schemas.APIResponse(
        data=schemas.StockSymbolRead(
            symbol=item.symbol,
            market=item.market,
            name=item.name,
            exchange=item.exchange,
            industry=item.industry,
            kind=_symbol_kind(item.symbol, item.name, item.industry),
        )
    )


def get_klines(
    symbol: str,
    market: str = "CN",
    start: Optional[str] = None,
    end: Optional[str] = None,
    n_folds: int = 1,
    limit: int = 400,
    db: Session = Depends(get_db),
):
    if not symbol:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol is required")
    market = (market or "CN").upper()
    normalized = _normalize_symbol(symbol, market) or symbol
    n_folds = max(1, int(n_folds or 1))
    if market in CN_MARKETS or market == "CN":
        _ensure_symbol_klines(db, normalized, start, end, n_folds)
    target_market = _market_from_symbol(normalized)
    rows = crud.load_klines(db, target_market, normalized, start=_parse_date_str(start), end=_parse_date_str(end))
    if limit and len(rows) > limit:
        rows = rows[-limit:]
    items = [
        {
            "date": int(row.trade_date.strftime("%Y%m%d")),
            "open": row.open,
            "close": row.close,
            "high": row.high,
            "low": row.low,
            "volume": row.volume,
        }
        for row in rows
    ]
    return schemas.APIResponse(
        data={
            "symbol": normalized,
            "market": target_market,
            "items": items,
        }
    )


def list_strategies():
    return schemas.APIResponse(data=STRATEGY_CATALOG)



