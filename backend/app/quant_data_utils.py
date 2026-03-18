from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
import csv
import re
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from . import crud
from .database import SessionLocal
from .quant_core_utils import *
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
    try:
        df.name = rows[0].symbol
    except Exception:
        pass
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


def _load_symbol_kl_df(symbol: str, start: Optional[str], end: Optional[str], n_folds: int):
    from abupy.MarketBu import ABuSymbolPd

    try:
        folds = max(1, int(n_folds or 1))
    except Exception:
        folds = 1
    attempts = [(start, end, folds)]
    if start or end:
        attempts.append((None, None, max(2, folds)))

    errors = []
    for start_value, end_value, folds_value in attempts:
        try:
            df = ABuSymbolPd.make_kl_df(symbol, n_folds=folds_value, start=start_value, end=end_value)
        except Exception as exc:
            errors.append(f"abupy(start={start_value},end={end_value}): {exc}")
            continue
        if df is not None and not getattr(df, "empty", False):
            return df

    market = _market_from_symbol(symbol)
    if market in CN_MARKETS or market == "CN":
        try:
            df = _fetch_akshare_df(symbol, start, end, folds)
            if df is not None and not getattr(df, "empty", False):
                if errors:
                    logger.warning("abupy fetch failed for %s, fallback to akshare succeeded", symbol)
                return df
        except Exception as exc:
            errors.append(f"akshare: {exc}")

    if errors:
        logger.warning("kline fetch failed for %s: %s", symbol, errors[-1])
    return None


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

    with _with_pg_data_env(market):
        df = _load_symbol_kl_df(symbol, start=start, end=end, n_folds=n_folds)
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
                try:
                    df.name = fallback_symbol
                except Exception:
                    pass
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
                    try:
                        df = source_cls(self._symbol).kline(n_folds=n_folds, start=start, end=end)
                    except Exception as exc:
                        logger.debug(
                            "market source fetch failed symbol=%s source=%s err=%s",
                            symbol_value,
                            source_value,
                            exc,
                        )
                        continue
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


@contextmanager
def _suppress_numeric_warnings():
    import warnings
    import numpy as np

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"numpy\\.polynomial")
        warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"scipy\\.optimize")
        prev = np.seterr(over="ignore", invalid="ignore")
        try:
            yield
        finally:
            np.seterr(**prev)


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


def _extract_cn_symbol_code(query: Optional[str]) -> Optional[str]:
    if not query:
        return None
    raw = str(query).strip()
    if not raw:
        return None
    lower = raw.lower()
    if lower.startswith(("sh", "sz")):
        code = lower[2:]
    else:
        code = raw
    code = code.strip()
    if not code.isdigit():
        return None
    if len(code) < 6:
        code = code.zfill(6)
    return code


def _select_akshare_row(df, code: str, code_index: int):
    try:
        series = df.iloc[:, code_index].astype(str)
        matches = df[series == code]
        if matches.empty:
            return None
        return matches.iloc[0]
    except Exception:
        return None


def _akshare_symbol_row(code: str) -> Optional[dict]:
    try:
        import akshare as ak
    except Exception:
        return None
    if not code or not code.isdigit():
        return None
    if len(code) < 6:
        code = code.zfill(6)
    if code.startswith(("6", "9")):
        df = ak.stock_info_sh_name_code()
        row = _select_akshare_row(df, code, 0)
        if row is None:
            return None
        name = row.iloc[1] if len(row) > 1 else None
        if isinstance(name, str):
            name = name.strip() or None
        return {
            "market": "SH",
            "symbol": f"sh{code}",
            "name": name,
            "exchange": "SH",
            "industry": None,
        }
    df = ak.stock_info_sz_name_code()
    row = _select_akshare_row(df, code, 1)
    if row is None:
        return None
    name = row.iloc[2] if len(row) > 2 else None
    industry = row.iloc[6] if len(row) > 6 else None
    if isinstance(name, str):
        name = name.strip() or None
    if isinstance(industry, str):
        industry = industry.strip() or None
    market_value = "300" if code.startswith("3") else "SZ"
    return {
        "market": market_value,
        "symbol": f"sz{code}",
        "name": name,
        "exchange": "SZ",
        "industry": industry,
    }


def _ensure_symbol_from_akshare(db: Session, market: str, query: Optional[str]) -> int:
    code = _extract_cn_symbol_code(query)
    if not code:
        return 0
    row = _akshare_symbol_row(code)
    if not row:
        return 0
    market_keys = _market_scope(market)
    if market_keys and row.get("market") not in market_keys:
        return 0
    return crud.upsert_stock_symbols(db, [row])


def _coerce_symbol_items(raw):
    if raw is None:
        return []
    if isinstance(raw, str):
        return _split_symbols(raw)
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, (list, tuple, set)):
        return list(raw)
    return [raw]


def _build_manual_symbol_rows(payload: dict) -> tuple[list[dict], list[str]]:
    market_hint = (payload.get("market") or "CN").upper()
    raw_items = payload.get("items")
    if raw_items is None:
        raw_items = payload.get("symbols")
    if raw_items is None:
        raw_items = payload.get("symbol")
    items = _coerce_symbol_items(raw_items)
    rows = []
    skipped = []
    for item in items:
        if isinstance(item, dict):
            symbol = item.get("symbol") or item.get("code") or item.get("ticker")
            item_market = item.get("market") or market_hint
            name = item.get("name") or item.get("co_name")
            exchange = item.get("exchange") or item.get("cc")
            industry = item.get("industry")
        else:
            symbol = item
            item_market = market_hint
            name = None
            exchange = None
            industry = None
        if not symbol:
            skipped.append(str(item))
            continue
        normalized = _normalize_symbol(str(symbol), str(item_market).upper())
        if not normalized:
            skipped.append(str(item))
            continue
        market_value = _market_from_symbol(normalized)
        if exchange is None and market_value in {"CN", "SH", "SZ", "300"}:
            exchange = market_value
        if isinstance(exchange, str):
            exchange = exchange.strip() or None
        if isinstance(name, str):
            name = name.strip() or None
        if isinstance(industry, str):
            industry = industry.strip() or None
        rows.append(
            {
                "market": market_value,
                "symbol": normalized,
                "name": name,
                "exchange": exchange,
                "industry": industry,
            }
        )
    return rows, skipped


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


__all__ = [name for name in globals().keys() if not name.startswith("__")]

