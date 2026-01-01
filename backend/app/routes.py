from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
import csv
import io
import json
import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db, SessionLocal

router = APIRouter()
quant_router = APIRouter(prefix="/quant", tags=["quant"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])

executor = ThreadPoolExecutor(max_workers=4)
logger = logging.getLogger("doraemon")
SYMBOL_PREFIXES = ("us", "hk", "sh", "sz")
CN_MARKETS = {"SH", "SZ", "300"}
DEFAULT_SYMBOLS = {
    "US": ["usAAPL"],
    "HK": ["hk00700"],
    "CN": ["sh600036"],
    "SH": ["sh600036"],
    "SZ": ["sz000001"],
    "300": ["sz300750"],
}
DEFAULT_BENCHMARKS = {
    "US": "usSPY",
    "HK": "hk00001",
    "CN": "sh000001",
    "SH": "sh000001",
    "SZ": "sz399001",
    "300": "sz399006",
}


def _split_symbols(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [item for item in re.split(r"[\s,;]+", raw) if item]
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw if str(item).strip()]
    return [str(raw)]


def _normalize_symbol(symbol: str, market: str) -> Optional[str]:
    if not symbol:
        return None
    sym = symbol.strip()
    if not sym:
        return None
    lower = sym.lower()
    for prefix in SYMBOL_PREFIXES:
        if lower.startswith(prefix):
            suffix = sym[len(prefix) :]
            if prefix == "us":
                suffix = suffix.upper()
            return f"{prefix}{suffix}"
    if market == "US":
        return f"us{sym.upper()}"
    if market == "HK":
        return f"hk{sym}"
    if market in {"CN"}:
        prefix = "sh" if sym.startswith("6") else "sz"
        return f"{prefix}{sym}"
    if market in {"SH"}:
        return f"sh{sym}"
    if market in {"SZ", "300"}:
        return f"sz{sym}"
    return sym


def _normalize_symbols(raw, market: str) -> list[str]:
    symbols = [_normalize_symbol(item, market) for item in _split_symbols(raw)]
    symbols = [item for item in symbols if item]
    if symbols:
        return symbols
    return DEFAULT_SYMBOLS.get(market, DEFAULT_SYMBOLS["US"])


@contextmanager
def _with_market_env(market: str):
    from abupy.CoreBu import ABuEnv
    from abupy import EMarketTargetType

    market_map = {
        "CN": EMarketTargetType.E_MARKET_TARGET_CN,
        "SH": EMarketTargetType.E_MARKET_TARGET_CN,
        "SZ": EMarketTargetType.E_MARKET_TARGET_CN,
        "300": EMarketTargetType.E_MARKET_TARGET_CN,
        "US": EMarketTargetType.E_MARKET_TARGET_US,
        "HK": EMarketTargetType.E_MARKET_TARGET_HK,
    }
    target = market_map.get(market)
    prev = None
    if target is not None:
        prev = ABuEnv.g_market_target
        ABuEnv.g_market_target = target
    try:
        yield
    finally:
        if target is not None and prev is not None:
            ABuEnv.g_market_target = prev


def _safe_float(value):
    try:
        if value is None:
            return None
        if hasattr(value, "item"):
            value = value.item()
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value):
    try:
        if value is None:
            return None
        if hasattr(value, "item"):
            value = value.item()
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_trade_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    try:
        value = int(value)
        return datetime.strptime(str(value), "%Y%m%d").date()
    except (TypeError, ValueError):
        return None


def _parse_date_str(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.strptime(value, "%Y/%m/%d").date()
    except (TypeError, ValueError):
        return None


def _date_to_int(value) -> Optional[int]:
    dt = _parse_trade_date(value)
    if dt is None:
        return None
    return int(dt.strftime("%Y%m%d"))


def _date_week_from_int(value) -> Optional[int]:
    try:
        return datetime.strptime(str(int(value)), "%Y%m%d").weekday()
    except (TypeError, ValueError):
        return None


def _resolve_date_range(start: Optional[str], end: Optional[str], n_folds: int) -> tuple[date, date]:
    today = date.today()
    end_date = _parse_date_str(end) or today
    if end_date > today:
        end_date = today
    folds = max(1, int(n_folds or 1))
    start_date = _parse_date_str(start)
    if start_date is None:
        start_date = end_date - timedelta(days=365 * folds)
    if start_date > end_date:
        start_date = end_date - timedelta(days=365 * folds)
    return start_date, end_date


def _kl_rows_from_df(df, market: str, symbol: str) -> list[dict]:
    if df is None or getattr(df, "empty", False):
        return []
    df = _normalize_kl_df(df)
    if df is None or getattr(df, "empty", False):
        return []
    rows = []
    for _, row in df.iterrows():
        trade_date = _parse_trade_date(row.get("date")) or _parse_trade_date(getattr(row, "name", None))
        if trade_date is None:
            continue
        rows.append(
            {
                "market": market,
                "symbol": symbol,
                "trade_date": trade_date,
                "open": _safe_float(row.get("open")),
                "close": _safe_float(row.get("close")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "pre_close": _safe_float(row.get("pre_close")),
                "p_change": _safe_float(row.get("p_change")),
                "volume": _safe_int(row.get("volume")),
                "date_week": _safe_int(row.get("date_week")),
                "key": _safe_int(row.get("key")),
                "atr14": _safe_float(row.get("atr14")),
                "atr21": _safe_float(row.get("atr21")),
            }
        )
    return rows


def _kl_df_from_rows(rows: list) -> Optional["pandas.DataFrame"]:
    import pandas as pd

    if not rows:
        return None
    data = []
    for row in rows:
        trade_date = row.trade_date
        data.append(
            {
                "date": int(trade_date.strftime("%Y%m%d")),
                "date_week": row.date_week if row.date_week is not None else trade_date.weekday(),
                "key": row.key,
                "open": row.open,
                "close": row.close,
                "high": row.high,
                "low": row.low,
                "pre_close": row.pre_close,
                "p_change": row.p_change,
                "volume": row.volume,
                "atr14": row.atr14,
                "atr21": row.atr21,
            }
        )
    df = pd.DataFrame(data)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    if "pre_close" not in df.columns or df["pre_close"].isna().all():
        df["pre_close"] = df["close"].shift(1)
        df.loc[df["pre_close"].isna(), "pre_close"] = df["open"]
    if "p_change" not in df.columns or df["p_change"].isna().all():
        base = df["pre_close"].replace(0, float("nan"))
        df["p_change"] = (df["close"] - df["pre_close"]) / base * 100
        df["p_change"] = df["p_change"].fillna(0)
    if "date_week" not in df.columns or df["date_week"].isna().all():
        df["date_week"] = df["date"].apply(_date_week_from_int)
    if "key" not in df.columns or df["key"].isna().all():
        df["key"] = list(range(len(df)))
    for col in ("atr14", "atr21"):
        if col in df.columns and df[col].isna().all():
            df.drop(columns=[col], inplace=True)
    df.index = pd.to_datetime(df["date"].astype(str))
    return df


def _market_from_symbol(symbol: str) -> str:
    if not symbol:
        return "CN"
    lower = symbol.lower()
    if lower.startswith("sh"):
        return "SH"
    if lower.startswith("sz"):
        code = symbol[2:]
        return "300" if code.startswith("3") else "SZ"
    if lower.startswith("hk"):
        return "HK"
    if lower.startswith("us"):
        return "US"
    return "CN"


def _resolve_benchmark_symbol(market: str) -> str:
    key = (market or "CN").upper()
    return DEFAULT_BENCHMARKS.get(key, DEFAULT_BENCHMARKS["CN"])


def _symbol_kind(symbol: str, name: Optional[str], industry: Optional[str]) -> str:
    if name and "指数" in name:
        return "index"
    if industry and "指数" in industry:
        return "index"
    lower = (symbol or "").lower()
    if lower.startswith("sh000") or lower.startswith("sz399"):
        return "index"
    return "stock"


def _is_index_symbol(symbol: Optional[str]) -> bool:
    lower = (symbol or "").lower()
    return lower.startswith("sh000") or lower.startswith("sz399")


def _normalize_kl_df(df):
    if df is None or getattr(df, "empty", False):
        return df
    df = df.copy()
    if "date" not in df.columns:
        df["date"] = df.index
    df["date"] = df["date"].apply(_date_to_int)
    df = df[df["date"].notna()]
    if "open" not in df.columns and "close" in df.columns:
        df["open"] = df["close"]
    if "high" not in df.columns and "close" in df.columns:
        df["high"] = df["close"]
    if "low" not in df.columns and "close" in df.columns:
        df["low"] = df["close"]
    if "pre_close" not in df.columns or df["pre_close"].isna().all():
        df["pre_close"] = df["close"].shift(1)
        df.loc[df["pre_close"].isna(), "pre_close"] = df["open"]
    if "p_change" not in df.columns or df["p_change"].isna().all():
        base = df["pre_close"].replace(0, float("nan"))
        df["p_change"] = (df["close"] - df["pre_close"]) / base * 100
        df["p_change"] = df["p_change"].fillna(0)
    if "date_week" not in df.columns or df["date_week"].isna().all():
        df["date_week"] = df["date"].apply(_date_week_from_int)
    if "key" not in df.columns or df["key"].isna().all():
        df["key"] = list(range(len(df)))
    return df


def _fetch_akshare_df(symbol: str, start: Optional[str], end: Optional[str], n_folds: int):
    try:
        import akshare as ak
    except Exception:
        return None

    start_date, end_date = _resolve_date_range(start, end, n_folds)
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    lower = (symbol or "").lower()

    if _is_index_symbol(lower):
        df = None
        if hasattr(ak, "stock_zh_index_daily_em"):
            try:
                df = ak.stock_zh_index_daily_em(symbol=lower, start_date=start_str, end_date=end_str)
            except Exception:
                df = None
        if df is None or getattr(df, "empty", False):
            if hasattr(ak, "index_zh_a_hist"):
                try:
                    code = re.sub(r"^(sh|sz)", "", lower)
                    df = ak.index_zh_a_hist(symbol=code, period="daily", start_date=start_str, end_date=end_str)
                except Exception:
                    df = None
        if df is None or getattr(df, "empty", False):
            return None
        rename_map = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "涨跌幅": "p_change",
        }
        return df.rename(columns=rename_map)

    if not hasattr(ak, "stock_zh_a_hist"):
        return None
    try:
        code = re.sub(r"^(sh|sz)", "", lower)
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_str,
            end_date=end_str,
            adjust="",
        )
    except Exception:
        return None
    if df is None or getattr(df, "empty", False):
        return None
    rename_map = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "涨跌幅": "p_change",
    }
    return df.rename(columns=rename_map)


def _ensure_symbol_klines(
    db: Session,
    symbol: str,
    start: Optional[str],
    end: Optional[str],
    n_folds: int,
) -> bool:
    market = _market_from_symbol(symbol)
    start_date = _parse_date_str(start)
    end_date = _parse_date_str(end)
    rows = crud.load_klines(db, market, symbol, start=start_date, end=end_date)
    if rows:
        return True
    from abupy.MarketBu import ABuSymbolPd

    with _with_pg_data_env(market):
        df = ABuSymbolPd.make_kl_df(symbol, n_folds=max(1, n_folds), start=start, end=end)
        if (df is None or getattr(df, "empty", False)) and (start or end):
            df = ABuSymbolPd.make_kl_df(symbol, n_folds=max(2, n_folds), start=None, end=None)
    if df is None or getattr(df, "empty", False):
        return False
    df_rows = _kl_rows_from_df(df, market, symbol)
    if not df_rows:
        return False
    crud.upsert_stock_klines(db, df_rows)
    return True


def _ensure_symbols_klines(
    db: Session,
    symbols: list[str],
    start: Optional[str],
    end: Optional[str],
    n_folds: int,
) -> list[str]:
    missing = []
    for symbol in symbols:
        if not _ensure_symbol_klines(db, symbol, start, end, n_folds):
            missing.append(symbol)
    return missing


@contextmanager
def _with_benchmark_fallback(fallback_symbol: Optional[str]):
    import abupy.CoreBu.ABu as abu_module
    from abupy.TradeBu.ABuBenchmark import AbuBenchmark as BaseBenchmark

    if not fallback_symbol:
        yield
        return

    class PatchedBenchmark(BaseBenchmark):
        def __init__(self, benchmark=None, start=None, end=None, n_folds=2, rs=True, benchmark_kl_pd=None):
            try:
                super().__init__(benchmark, start, end, n_folds, rs, benchmark_kl_pd)
            except ValueError as exc:
                if "benchmark kl_pd is None" not in str(exc):
                    raise
                session = SessionLocal()
                try:
                    _ensure_symbol_klines(session, fallback_symbol, start, end, n_folds)
                    market = _market_from_symbol(fallback_symbol)
                    rows = crud.load_klines(
                        session,
                        market,
                        fallback_symbol,
                        start=_parse_date_str(start),
                        end=_parse_date_str(end),
                    )
                    df = _kl_df_from_rows(rows)
                finally:
                    session.close()
                if df is None or getattr(df, "empty", False):
                    raise ValueError("Benchmark data unavailable; run kl_update for selected symbols first.") from exc
                super().__init__(
                    benchmark=fallback_symbol,
                    start=start,
                    end=end,
                    n_folds=n_folds,
                    rs=rs,
                    benchmark_kl_pd=df,
                )

    prev = abu_module.AbuBenchmark
    abu_module.AbuBenchmark = PatchedBenchmark
    try:
        yield
    finally:
        abu_module.AbuBenchmark = prev


def _get_pg_market_source():
    from abupy.MarketBu.ABuDataBase import StockBaseMarket, SupportMixin

    class PGMarketData(StockBaseMarket, SupportMixin):
        def minute(self, *args, **kwargs):
            return None

        def kline(self, n_folds=2, start=None, end=None):
            from abupy.CoreBu import ABuEnv
            from abupy.MarketBu.ABuDataSource import source_dict
            from abupy.CoreBu.ABuEnv import EMarketSourceType

            session = SessionLocal()
            try:
                symbol_value = self._symbol.value
                market = _market_from_symbol(symbol_value)
                start_date = _parse_date_str(start)
                end_date = _parse_date_str(end)
                rows = crud.load_klines(session, market, symbol_value, start=start_date, end=end_date)
                if rows:
                    first = rows[0].trade_date
                    last = rows[-1].trade_date
                    if (not start_date or first <= start_date) and (not end_date or last >= end_date):
                        return _kl_df_from_rows(rows)
                source_order = [
                    ABuEnv.g_market_source.value,
                    EMarketSourceType.E_MARKET_SOURCE_tx.value,
                    EMarketSourceType.E_MARKET_SOURCE_nt.value,
                    EMarketSourceType.E_MARKET_SOURCE_bd.value,
                ]
                seen = set()
                df = None
                for source_value in source_order:
                    if source_value in seen:
                        continue
                    seen.add(source_value)
                    source_cls = source_dict.get(source_value)
                    if not source_cls:
                        continue
                    df = source_cls(self._symbol).kline(n_folds=n_folds, start=start, end=end)
                    if df is not None and not getattr(df, "empty", False):
                        break
                if df is None or getattr(df, "empty", False):
                    if market in CN_MARKETS or market == "CN":
                        df = _fetch_akshare_df(symbol_value, start, end, n_folds)
                if df is None or getattr(df, "empty", False):
                    return df
                rows = _kl_rows_from_df(df, market, symbol_value)
                crud.upsert_stock_klines(session, rows)
                return df
            finally:
                session.close()

    return PGMarketData


@contextmanager
def _with_pg_data_env(market: str):
    from abupy.CoreBu import ABuEnv
    from abupy.CoreBu.ABuEnv import EMarketDataFetchMode

    prev_source = ABuEnv.g_private_data_source
    prev_mode = ABuEnv.g_data_fetch_mode
    ABuEnv.g_private_data_source = _get_pg_market_source()
    ABuEnv.g_data_fetch_mode = EMarketDataFetchMode.E_DATA_FETCH_FORCE_NET
    try:
        with _with_market_env(market):
            yield
    finally:
        ABuEnv.g_private_data_source = prev_source
        ABuEnv.g_data_fetch_mode = prev_mode


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _market_csv_path(market: str) -> Path:
    key = market.upper()
    if key in {"CN", "SH", "SZ", "300"}:
        return _repo_root() / "abupy" / "RomDataBu" / "stock_code_CN.csv"
    if key == "HK":
        return _repo_root() / "abupy" / "RomDataBu" / "stock_code_HK.csv"
    if key == "US":
        return _repo_root() / "abupy" / "RomDataBu" / "stock_code_US.csv"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported market")


def _read_stock_rows(market: str):
    path = _market_csv_path(market)
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row
    except UnicodeDecodeError:
        with path.open("r", encoding="gbk", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row


def _market_scope(market: str) -> list[str]:
    key = (market or "CN").upper()
    if key in {"CN", "ALL", "A"}:
        return ["SH", "SZ", "300"]
    return [key]


def _build_symbol_rows(market: str) -> list[dict]:
    target_market = (market or "CN").upper()
    rows = []
    for row in _read_stock_rows(target_market):
        symbol = (row.get("symbol") or "").strip()
        if not symbol:
            continue
        row_market = (row.get("market") or "").strip().upper()
        market_value = row_market or target_market
        if row_market == "SZ" and symbol.startswith("3"):
            market_value = "300"
        if target_market in CN_MARKETS or target_market == "CN":
            if target_market in CN_MARKETS and market_value != target_market:
                continue
        elif target_market and market_value != target_market:
            continue
        normalized = _normalize_symbol(symbol, market_value)
        if not normalized:
            continue
        exchange = row.get("exchange") or row.get("cc") or None
        if market_value in {"CN", "SH", "SZ", "300"}:
            exchange = exchange or row.get("market") or None
        if isinstance(exchange, str):
            exchange = exchange.strip() or None
        rows.append(
            {
                "market": market_value,
                "symbol": normalized,
                "name": (row.get("co_name") or "").strip() or None,
                "exchange": exchange,
                "industry": (row.get("industry") or None),
            }
        )
    return rows


def _seed_symbols_if_empty(db: Session, market: str) -> int:
    markets = _market_scope(market)
    if crud.has_stock_symbols_any(db, markets):
        return 0
    total = 0
    if (market or "").upper() in {"CN", "ALL", "A"}:
        rows = _build_symbol_rows("CN")
        total += crud.upsert_stock_symbols(db, rows)
    else:
        rows = _build_symbol_rows(market)
        total += crud.upsert_stock_symbols(db, rows)
    return total


@quant_router.get("/features", response_model=schemas.APIResponse)
def list_feature_map():
    data = {
        "legacy": [
            {"name": "股票基本信息查询", "source": "abupy_ui/widget_stock_info.py", "api": "/api/v1/quant/symbols"},
            {"name": "数据下载界面操作", "source": "abupy_ui/widget_update_ui.py", "api": "/api/v1/quant/kl/update"},
            {"name": "历史回测界面操作", "source": "abupy_ui/widget_loop_back.py", "api": "/api/v1/quant/backtest"},
            {"name": "参数最优交叉验证", "source": "abupy/WidgetBu/ABuWGGridSearch.py", "api": "/api/v1/quant/grid-search"},
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


@quant_router.post("/symbols/import", response_model=schemas.APIResponse)
def import_symbols(payload: dict, db: Session = Depends(get_db)):
    market = (payload.get("market") or "CN").upper()
    rows = _build_symbol_rows(market)
    count = crud.upsert_stock_symbols(db, rows)
    return schemas.APIResponse(message="Symbols imported", data={"count": count})


@quant_router.get("/symbols", response_model=schemas.APIResponse)
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
    return schemas.APIResponse(
        data={
            "items": payload,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@quant_router.get("/symbols/{symbol}", response_model=schemas.APIResponse)
def get_symbol(symbol: str, market: str = "CN", db: Session = Depends(get_db)):
    market = (market or "CN").upper()
    want = symbol.strip()
    item = None
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


def _run_job(job_id: int):
    db = SessionLocal()
    try:
        job = crud.get_quant_job(db, job_id)
        if not job:
            return
        crud.set_quant_job_running(db, job)

        if job.type == "kl_update":
            from abupy.MarketBu import ABuSymbolPd

            market = (job.params.get("market") or "CN").upper()
            raw_symbols = job.params.get("symbols")
            symbols = _normalize_symbols(raw_symbols, market)
            seeded = 0
            if job.params.get("all"):
                seeded = _seed_symbols_if_empty(db, market)
                market_keys = _market_scope(market)
                symbols = [
                    _normalize_symbol(item.symbol, market)
                    for item in crud.list_stock_symbols_by_markets(db, market_keys)
                ]
                symbols = [item for item in symbols if item]
            if not symbols:
                raise RuntimeError("No symbols available; import symbols into database first.")

            n_folds = job.params.get("n_folds", 1)
            start = job.params.get("start")
            end = job.params.get("end")
            total_rows = 0
            updated_symbols = 0
            missing_symbols = []
            with _with_pg_data_env(market):
                for symbol in symbols:
                    kl = ABuSymbolPd.make_kl_df(symbol, n_folds=n_folds, start=start, end=end)
                    if kl is None or getattr(kl, "empty", False):
                        missing_symbols.append(symbol)
                        continue
                    rows = _kl_rows_from_df(kl, _market_from_symbol(symbol), symbol)
                    total_rows += crud.upsert_stock_klines(db, rows)
                    updated_symbols += 1

            crud.set_quant_job_result(
                db,
                job,
                {
                    "message": "kl_update finished",
                    "symbols": symbols,
                    "rows": total_rows,
                    "seeded_symbols": seeded,
                    "updated_symbols": updated_symbols,
                    "missing_symbols": missing_symbols[:200],
                },
            )
            return

        if job.type == "backtest":
            from abupy import abu
            from abupy.FactorBuyBu import AbuFactorBuyBreak
            from abupy.FactorSellBu import AbuFactorAtrNStop

            market = (job.params.get("market") or "CN").upper()
            symbols = _normalize_symbols(job.params.get("symbols"), market)
            if not symbols:
                raise RuntimeError("No symbols specified for backtest.")
            missing_symbols = _ensure_symbols_klines(
                db,
                symbols,
                job.params.get("start"),
                job.params.get("end"),
                job.params.get("n_folds", 1),
            )
            available_symbols = [sym for sym in symbols if sym not in missing_symbols]
            if not available_symbols:
                raise RuntimeError(
                    "No kline data available for selected symbols; data source returned empty. "
                    f"Try kl_update with a wider range (omit start/end), or check data source. Missing: {missing_symbols[:10]}"
                )
            benchmark_symbol = _resolve_benchmark_symbol(market)
            if not _ensure_symbol_klines(
                db,
                benchmark_symbol,
                job.params.get("start"),
                job.params.get("end"),
                job.params.get("n_folds", 1),
            ):
                benchmark_symbol = available_symbols[0]
            buy_factors = [{"class": AbuFactorBuyBreak, "xd": job.params.get("buy_xd", 42)}]
            sell_factors = [
                {
                    "class": AbuFactorAtrNStop,
                    "stop_loss_n": job.params.get("stop_loss_n", 0.5),
                    "stop_win_n": job.params.get("stop_win_n", 3.0),
                }
            ]
            fallback_symbol = benchmark_symbol
            with _with_pg_data_env(market), _with_benchmark_fallback(fallback_symbol):
                abu_result, _ = abu.run_loop_back(
                    read_cash=job.params.get("cash", 1000000),
                    buy_factors=buy_factors,
                    sell_factors=sell_factors,
                    choice_symbols=symbols,
                    n_folds=job.params.get("n_folds", 1),
                    start=job.params.get("start"),
                    end=job.params.get("end"),
                    n_process_kl=1,
                    n_process_pick=1,
                )
            if abu_result is None:
                raise RuntimeError("Backtest returned empty result")
            summary = {
                "market": market,
                "symbols": symbols,
                "orders_rows": int(getattr(abu_result.orders_pd, "shape", [0])[0]),
                "actions_rows": int(getattr(abu_result.action_pd, "shape", [0])[0]),
                "benchmark": getattr(getattr(abu_result, "benchmark", None), "symbol", None),
            }
            orders_preview = None
            actions_preview = None
            try:
                orders_pd = getattr(abu_result, "orders_pd", None)
                if orders_pd is not None and hasattr(orders_pd, "head") and hasattr(orders_pd, "to_json"):
                    orders_json = orders_pd.head(200).to_json(orient="records", date_format="iso")
                    orders_preview = json.loads(orders_json)
            except Exception:
                orders_preview = None
            try:
                action_pd = getattr(abu_result, "action_pd", None)
                if action_pd is not None and hasattr(action_pd, "head") and hasattr(action_pd, "to_json"):
                    actions_json = action_pd.head(200).to_json(orient="records", date_format="iso")
                    actions_preview = json.loads(actions_json)
            except Exception:
                actions_preview = None

            result = {"summary": summary}
            if orders_preview is not None:
                result["orders"] = orders_preview
            if actions_preview is not None:
                result["actions"] = actions_preview
            crud.set_quant_job_result(db, job, result)
            return

        if job.type == "grid_search":
            from itertools import product

            from abupy import abu
            from abupy.FactorBuyBu import AbuFactorBuyBreak
            from abupy.FactorSellBu import AbuFactorAtrNStop

            market = (job.params.get("market") or "CN").upper()
            symbols = _normalize_symbols(job.params.get("symbols"), market)
            cash = job.params.get("cash", 1000000)
            n_folds = job.params.get("n_folds", 1)
            start = job.params.get("start")
            end = job.params.get("end")
            if not symbols:
                raise RuntimeError("No symbols specified for grid search.")
            missing_symbols = _ensure_symbols_klines(db, symbols, start, end, n_folds)
            available_symbols = [sym for sym in symbols if sym not in missing_symbols]
            if not available_symbols:
                raise RuntimeError(
                    "No kline data available for selected symbols; data source returned empty. "
                    f"Try kl_update with a wider range (omit start/end), or check data source. Missing: {missing_symbols[:10]}"
                )
            benchmark_symbol = _resolve_benchmark_symbol(market)
            if not _ensure_symbol_klines(db, benchmark_symbol, start, end, n_folds):
                benchmark_symbol = available_symbols[0]

            buy_xd_list = job.params.get("buy_xd_list") or [20, 42, 60]
            stop_loss_n_list = job.params.get("stop_loss_n_list") or [0.5, 1.0]
            stop_win_n_list = job.params.get("stop_win_n_list") or [2.0, 3.0]
            max_runs = int(job.params.get("max_runs", 30))
            max_runs = max(1, min(max_runs, 200))

            runs = []
            fallback_symbol = benchmark_symbol
            with _with_pg_data_env(market), _with_benchmark_fallback(fallback_symbol):
                for i, (buy_xd, stop_loss_n, stop_win_n) in enumerate(
                    product(buy_xd_list, stop_loss_n_list, stop_win_n_list)
                ):
                    if i >= max_runs:
                        break
                    buy_factors = [{"class": AbuFactorBuyBreak, "xd": buy_xd}]
                    sell_factors = [{"class": AbuFactorAtrNStop, "stop_loss_n": stop_loss_n, "stop_win_n": stop_win_n}]
                    abu_result, _ = abu.run_loop_back(
                        read_cash=cash,
                        buy_factors=buy_factors,
                        sell_factors=sell_factors,
                        choice_symbols=symbols,
                        n_folds=n_folds,
                        start=start,
                        end=end,
                        n_process_kl=1,
                        n_process_pick=1,
                    )
                    if abu_result is None:
                        continue
                    summary = {
                        "buy_xd": buy_xd,
                        "stop_loss_n": stop_loss_n,
                        "stop_win_n": stop_win_n,
                        "orders_rows": int(getattr(abu_result.orders_pd, "shape", [0])[0]),
                        "actions_rows": int(getattr(abu_result.action_pd, "shape", [0])[0]),
                        "benchmark": getattr(getattr(abu_result, "benchmark", None), "symbol", None),
                    }
                    runs.append(summary)

            runs_sorted = sorted(runs, key=lambda x: (x.get("orders_rows", 0), x.get("actions_rows", 0)), reverse=True)
            best = runs_sorted[0] if runs_sorted else None
            crud.set_quant_job_result(
                db,
                job,
                {
                    "market": market,
                    "symbols": symbols,
                    "max_runs": max_runs,
                    "best": best,
                    "runs": runs_sorted[:200],
                },
            )
            return

        if job.type == "analysis":
            result = _run_analysis_job(job.params, db)
            crud.set_quant_job_result(db, job, result)
            return

        if job.type == "verify":
            import platform

            abupy_version = None
            import_error = None
            try:
                import abupy  # noqa: F401

                abupy_version = getattr(abupy, "__version__", None)
            except Exception as exc:
                import_error = str(exc)
                init_path = _repo_root() / "abupy" / "__init__.py"
                try:
                    init_text = init_path.read_text(encoding="utf-8")
                    for line in init_text.splitlines():
                        if line.strip().startswith("__version__"):
                            abupy_version = line.split("=", 1)[1].strip().strip("'\"")
                            break
                except Exception:
                    abupy_version = None

            crud.set_quant_job_result(
                db,
                job,
                {
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "abupy_version": abupy_version,
                    "abupy_import_error": import_error,
                },
            )
            return

        raise RuntimeError("Unsupported job type")
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        job = crud.get_quant_job(db, job_id)
        if job:
            crud.set_quant_job_error(db, job, str(exc))
    finally:
        db.close()


def _df_to_records(df, limit: int = 200):
    if limit:
        df = df.head(limit)
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _df_to_matrix(df):
    if hasattr(df, "to_frame") and not hasattr(df, "columns"):
        df = df.to_frame()
    df = df.copy()
    df = df.fillna(0)
    return {
        "columns": [str(col) for col in df.columns],
        "index": [str(idx) for idx in df.index],
        "data": df.values.tolist(),
    }


def _series_points(series, limit: int = 200):
    series = series.tail(limit)
    points = []
    for idx, val in series.items():
        try:
            y = float(val)
        except (TypeError, ValueError):
            y = None
        points.append({"x": str(idx), "y": y})
    return points


def _run_analysis_job(params: dict, db: Session) -> dict:
    import numpy as np
    import pandas as pd
    from abupy.TLineBu import AbuTLine, EShiftDistanceHow
    from abupy.TLineBu.ABuTLExecute import (
        calc_kl_speed,
        find_golden_point,
        find_golden_point_ex,
        regress_trend_channel,
    )
    from abupy.SimilarBu import ABuCorrcoef, ECoreCorrType
    from abupy.TLineBu.ABuTLJump import calc_jump, calc_jump_line, calc_jump_line_weight
    from abupy.SimilarBu.ABuCorrcoef import corr_matrix
    from abupy.UtilBu import ABuKLUtil
    from abupy.UtilBu.ABuStatsUtil import (
        manhattan_distance_matrix,
        euclidean_distance_matrix,
        cosine_distance_matrix,
    )

    tool = (params.get("tool") or "").strip().lower()
    market = (params.get("market") or "US").upper()
    symbols = _normalize_symbols(params.get("symbols"), market)
    start = params.get("start")
    end = params.get("end")
    n_folds = params.get("n_folds", 1)
    limit = int(params.get("limit", 200))
    options = params.get("options") or {}

    def _resolve_dates():
        if start or end:
            start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None
            end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else None
            return start_date, end_date
        end_date = date.today()
        start_date = end_date - timedelta(days=365 * int(n_folds))
        return start_date, end_date

    def _fetch_kl(symbol: str):
        start_date, end_date = _resolve_dates()
        rows = crud.load_klines(db, market, symbol, start=start_date, end=end_date)
        return _kl_df_from_rows(rows)

    def _fetch_kl_dict(items: list[str]):
        data = {}
        for sym in items:
            kl = _fetch_kl(sym)
            if kl is not None:
                data[sym] = kl
        return data

    def _sample_series(series, max_points: int):
        if not max_points or len(series) <= max_points:
            return series
        step = max(1, int(len(series) / max_points))
        return series[::step]

    with _with_market_env(market):
        if tool in {"support_resistance", "support", "resistance"}:
            symbol = symbols[0]
            kl = _fetch_kl(symbol)
            if kl is None:
                raise RuntimeError(f"No data for {symbol}")
            tl = AbuTLine(kl.close, symbol)
            only_last_raw = options.get("only_last", True)
            if isinstance(only_last_raw, str):
                only_last = only_last_raw.strip().lower() in {"true", "1", "yes", "y"}
            else:
                only_last = bool(only_last_raw)
            trends = tl.show_support_resistance_trend(only_last=only_last, show=False, show_step=False)
            if trends is None:
                trends = {}
            trend_lines = []
            x_start = 0
            x_end = len(tl.tl) - 1
            for key, lines in trends.items():
                for line in lines:
                    if line is None:
                        continue
                    try:
                        y_start = float(line[0])
                        y_end = float(line[1])
                    except Exception:
                        continue
                    trend_lines.append(
                        {
                            "type": key,
                            "x_start": x_start,
                            "x_end": x_end,
                            "y_start": y_start,
                            "y_end": y_end,
                        }
                    )
            return {
                "tool": tool,
                "symbol": symbol,
                "trend_lines": trend_lines,
                "close": _series_points(kl.close, limit=limit),
            }

        if tool in {"jump_gap", "jump"}:
            symbol = symbols[0]
            kl = _fetch_kl(symbol)
            if kl is None:
                raise RuntimeError(f"No data for {symbol}")
            mode = (options.get("mode") or "stats").lower()
            jump_diff_factor = float(options.get("jump_diff_factor", 1.0))
            power_threshold = float(options.get("power_threshold", 2.0))
            weight = options.get("weight") or (0.5, 0.5)
            if isinstance(weight, (list, tuple)) and len(weight) == 2:
                weight = (float(weight[0]), float(weight[1]))
            else:
                weight = (0.5, 0.5)
            if mode == "gap":
                result = calc_jump_line(kl, power_threshold=power_threshold, jump_diff_factor=jump_diff_factor)
            elif mode == "weighted":
                result = calc_jump_line_weight(
                    kl, sw=weight, power_threshold=power_threshold, jump_diff_factor=jump_diff_factor
                )
            else:
                result = calc_jump(kl, jump_diff_factor=jump_diff_factor)
            return {
                "tool": tool,
                "symbol": symbol,
                "mode": mode,
                "rows": _df_to_records(result, limit=limit),
            }

        if tool in {"trend_speed", "pair_speed"}:
            symbol = symbols[0]
            benchmark = options.get("benchmark") or (
                symbols[1] if len(symbols) > 1 else DEFAULT_BENCHMARKS.get(market, DEFAULT_SYMBOLS["US"][0])
            )
            benchmark = _normalize_symbol(benchmark, market) or DEFAULT_BENCHMARKS.get(market, DEFAULT_SYMBOLS["US"][0])
            resample = int(options.get("resample", 5))
            speed_key = options.get("speed_key", "close")
            kl = _fetch_kl(symbol)
            benchmark_kl = _fetch_kl(benchmark)
            if kl is None or benchmark_kl is None:
                raise RuntimeError("Missing kline data for speed comparison")
            speed = calc_kl_speed(kl[speed_key], resample)
            benchmark_speed = calc_kl_speed(benchmark_kl[speed_key], resample)
            corr = ABuCorrcoef.corr_xy(kl.close, benchmark_kl.close, ECoreCorrType.E_CORE_TYPE_SPERM)
            return {
                "tool": tool,
                "symbol": symbol,
                "benchmark": benchmark,
                "speed": speed,
                "benchmark_speed": benchmark_speed,
                "corr": corr,
            }

        if tool in {"shift_distance"}:
            symbol = symbols[0]
            kl = _fetch_kl(symbol)
            if kl is None:
                raise RuntimeError(f"No data for {symbol}")
            step_x = float(options.get("step_x", 1.0))
            mode = options.get("mode", "close")
            mode_map = {
                "close": EShiftDistanceHow.shift_distance_close,
                "maxmin": EShiftDistanceHow.shift_distance_maxmin,
                "summaxmin": EShiftDistanceHow.shift_distance_sum_maxmin,
            }
            how = mode_map.get(mode, EShiftDistanceHow.shift_distance_close)
            tl = AbuTLine(kl.close, symbol)
            segments = tl.show_shift_distance(how=how, step_x=step_x, show=False, show_log=False)
            rows = []
            for idx, item in enumerate(segments or []):
                rows.append(
                    {
                        "segment": idx,
                        "h_distance": float(item[0]),
                        "v_distance": float(item[1]),
                        "distance": float(item[2]),
                        "shift": float(item[3]),
                        "ratio": float(item[4]),
                    }
                )
            return {"tool": tool, "symbol": symbol, "segments": rows}

        if tool in {"regress", "price_channel"}:
            symbol = symbols[0]
            kl = _fetch_kl(symbol)
            if kl is None:
                raise RuntimeError(f"No data for {symbol}")
            mode = options.get("mode", "best")
            tl = AbuTLine(kl.close, symbol)
            payload = {"tool": tool, "symbol": symbol, "mode": mode}
            if mode == "least":
                payload["least_poly"] = tl.show_least_valid_poly(show=False)
            elif mode == "best":
                payload["best_poly"] = tl.show_best_poly(show=False)
            else:
                y_below, y_fit, y_above = regress_trend_channel(np.array(kl.close.values))
                y_fit = _sample_series(y_fit, limit)
                y_below = _sample_series(y_below, limit)
                y_above = _sample_series(y_above, limit)
                payload["channel"] = {
                    "x": list(range(len(y_fit))),
                    "below": list(map(float, y_below)),
                    "fit": list(map(float, y_fit)),
                    "above": list(map(float, y_above)),
                }
            payload["close"] = _series_points(kl.close, limit=limit)
            return payload

        if tool in {"golden_ratio", "golden"}:
            symbol = symbols[0]
            kl = _fetch_kl(symbol)
            if kl is None:
                raise RuntimeError(f"No data for {symbol}")
            x = np.arange(0, len(kl.close))
            y = np.array(kl.close.values)
            sp382, sp50, sp618 = find_golden_point(x, y, show=False)
            sp382_ex, sp50_ex, sp618_ex = find_golden_point_ex(x, y, show=False)
            return {
                "tool": tool,
                "symbol": symbol,
                "golden": {"sp382": sp382, "sp50": sp50, "sp618": sp618},
                "golden_ex": {"sp382": sp382_ex, "sp50": sp50_ex, "sp618": sp618_ex},
            }

        if tool in {"correlation", "distance"}:
            kl_dict = _fetch_kl_dict(symbols)
            if len(kl_dict) < 2:
                raise RuntimeError("Correlation tools require at least two symbols")
            field = options.get("field", "p_change")
            df = pd.concat({sym: kl_dict[sym][field] for sym in kl_dict}, axis=1).fillna(0)
            if tool == "correlation":
                corr_mode = options.get("corr_type", "pears")
                corr = corr_matrix(df, similar_type=ECoreCorrType(corr_mode))
                return {"tool": tool, "field": field, "matrix": _df_to_matrix(corr)}
            dist_mode = options.get("distance_type", "manhattan")
            if dist_mode == "euclidean":
                dist = euclidean_distance_matrix(df, scale_end=True, to_similar=False)
            elif dist_mode == "cosine":
                dist = cosine_distance_matrix(df, scale_end=True, to_similar=False)
            else:
                dist = manhattan_distance_matrix(df, scale_end=True, to_similar=False)
            return {"tool": tool, "field": field, "matrix": _df_to_matrix(dist)}

        if tool in {
            "p_change_stats",
            "date_week_wave",
            "date_week_win",
            "bcut_change_vc",
            "qcut_change_vc",
            "wave_change_rate",
        }:
            kl_dict = _fetch_kl_dict(symbols)
            if not kl_dict:
                raise RuntimeError("No data for requested symbols")
            payload = {"tool": tool, "symbols": list(kl_dict.keys())}
            if tool == "date_week_wave":
                payload["result"] = _df_to_matrix(ABuKLUtil.date_week_wave(kl_dict))
            elif tool == "date_week_win":
                payload["result"] = _df_to_matrix(ABuKLUtil.date_week_win(kl_dict))
            elif tool == "bcut_change_vc":
                payload["result"] = _df_to_matrix(ABuKLUtil.bcut_change_vc(kl_dict))
            elif tool == "qcut_change_vc":
                payload["result"] = _df_to_matrix(ABuKLUtil.qcut_change_vc(kl_dict))
            elif tool == "wave_change_rate":
                wave_map = {}
                for sym, df in kl_dict.items():
                    wave = ((df.high - df.low) / df.pre_close) * 100
                    wave_rate = wave.mean() / np.abs(df["p_change"]).mean()
                    wave_map[sym] = float(wave_rate)
                payload["result"] = wave_map
            else:
                stats_map = {}
                for sym, df in kl_dict.items():
                    p_change_up = df[df["p_change"] > 0]["p_change"]
                    p_change_down = df[df["p_change"] < 0]["p_change"]
                    stats_map[sym] = {
                        "up_mean": float(p_change_up.mean()) if not p_change_up.empty else None,
                        "up_count": int(p_change_up.count()),
                        "down_mean": float(p_change_down.mean()) if not p_change_down.empty else None,
                        "down_count": int(p_change_down.count()),
                        "mean_ratio": float(abs(p_change_up.mean() / p_change_down.mean()))
                        if not p_change_up.empty and not p_change_down.empty
                        else None,
                        "count_ratio": float(p_change_up.count() / p_change_down.count())
                        if p_change_down.count()
                        else None,
                    }
                payload["result"] = stats_map
            return payload

    raise RuntimeError("Unsupported analysis tool")


@quant_router.post("/kl/update", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_kl_update(payload: dict, db: Session = Depends(get_db)):
    job = crud.create_quant_job(db, schemas.QuantJobCreate(type="kl_update", params=payload))
    executor.submit(_run_job, job.id)
    return schemas.APIResponse(message="Job queued", data=schemas.QuantJobRead.from_orm(job))


@quant_router.post("/backtest", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_backtest(payload: dict, db: Session = Depends(get_db)):
    job = crud.create_quant_job(db, schemas.QuantJobCreate(type="backtest", params=payload))
    executor.submit(_run_job, job.id)
    return schemas.APIResponse(message="Job queued", data=schemas.QuantJobRead.from_orm(job))


@quant_router.post("/grid-search", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_grid_search(payload: dict, db: Session = Depends(get_db)):
    job = crud.create_quant_job(db, schemas.QuantJobCreate(type="grid_search", params=payload))
    executor.submit(_run_job, job.id)
    return schemas.APIResponse(message="Job queued", data=schemas.QuantJobRead.from_orm(job))


@quant_router.post("/tools", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def start_quant_tools(payload: dict, db: Session = Depends(get_db)):
    job = crud.create_quant_job(db, schemas.QuantJobCreate(type="analysis", params=payload))
    executor.submit(_run_job, job.id)
    return schemas.APIResponse(message="Job queued", data=schemas.QuantJobRead.from_orm(job))


@quant_router.get("/verify", response_model=schemas.APIResponse)
def verify_quant_env(db: Session = Depends(get_db)):
    job = crud.create_quant_job(db, schemas.QuantJobCreate(type="verify", params={}))
    executor.submit(_run_job, job.id)
    return schemas.APIResponse(message="Job queued", data=schemas.QuantJobRead.from_orm(job))


@jobs_router.get("/", response_model=schemas.APIResponse)
def list_jobs(limit: int = 50, db: Session = Depends(get_db)):
    jobs = crud.list_quant_jobs(db, limit=limit)
    return schemas.APIResponse(data=[schemas.QuantJobRead.from_orm(job) for job in jobs])


@jobs_router.post("/", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(payload: schemas.QuantJobCreate, db: Session = Depends(get_db)):
    job = crud.create_quant_job(db, payload)
    executor.submit(_run_job, job.id)
    return schemas.APIResponse(message="Job queued", data=schemas.QuantJobRead.from_orm(job))


@jobs_router.get("/{job_id}", response_model=schemas.APIResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_quant_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return schemas.APIResponse(data=schemas.QuantJobRead.from_orm(job))


@jobs_router.delete("/{job_id}", response_model=schemas.APIResponse)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_quant_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is running")
    crud.delete_quant_job(db, job)
    return schemas.APIResponse(message="Job deleted", data={"id": job_id})


@jobs_router.get("/{job_id}/export")
def export_job(job_id: int, format: str = "json", section: Optional[str] = None, db: Session = Depends(get_db)):
    job = crud.get_quant_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not job.result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job has no result yet")

    payload = job.result
    section_key = None
    if section and isinstance(payload, dict) and section in payload:
        payload = payload.get(section)
        section_key = section

    fmt = (format or "json").strip().lower()
    file_stem = f"job_{job_id}"
    if section_key:
        file_stem = f"{file_stem}_{section_key}"

    if fmt == "json":
        return JSONResponse(
            content=payload,
            headers={"Content-Disposition": f'attachment; filename="{file_stem}.json"'},
        )

    if fmt != "csv":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported format")

    buf = io.StringIO()
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        keys = []
        for item in payload:
            if isinstance(item, dict):
                for k in item.keys():
                    if k not in keys:
                        keys.append(k)
        writer = csv.DictWriter(buf, fieldnames=keys)
        writer.writeheader()
        for item in payload:
            if isinstance(item, dict):
                writer.writerow({k: item.get(k) for k in keys})
    elif isinstance(payload, dict):
        writer = csv.writer(buf)
        writer.writerow(["key", "value"])
        for k, v in payload.items():
            if isinstance(v, (dict, list)):
                writer.writerow([k, json.dumps(v, ensure_ascii=False)])
            else:
                writer.writerow([k, v])
    else:
        writer = csv.writer(buf)
        writer.writerow(["value"])
        writer.writerow([payload])

    out = io.BytesIO(buf.getvalue().encode("utf-8-sig"))
    return StreamingResponse(
        out,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{file_stem}.csv"'},
    )


router.include_router(quant_router)
router.include_router(jobs_router)
