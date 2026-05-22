from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from itertools import product
import logging
import re
from typing import Optional

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
STRATEGY_CATALOG = {
    "buy": [
        {
            "id": "breakout",
            "name": "突破",
            "desc": "N 日新高突破买入",
            "params": [{"key": "xd", "label": "突破周期", "type": "int", "default": 42, "min": 5}],
        },
        {
            "id": "double_ma",
            "name": "双均线",
            "desc": "快慢均线金叉买入",
            "params": [
                {"key": "fast", "label": "快线周期", "type": "int", "default": 5, "min": 2},
                {"key": "slow", "label": "慢线周期", "type": "int", "default": 60, "min": 5},
                {"key": "resample_min", "label": "最小重采样", "type": "int", "default": 10, "min": 5},
                {"key": "resample_max", "label": "最大重采样", "type": "int", "default": 100, "min": 10},
                {"key": "change_threshold", "label": "波动阈值", "type": "float", "default": 0.12, "step": 0.01},
            ],
        },
        {
            "id": "up_down_trend",
            "name": "趋势回调",
            "desc": "长期上升趋势 + 短期回调买入",
            "params": [
                {"key": "xd", "label": "短期周期", "type": "int", "default": 20, "min": 5},
                {"key": "past_factor", "label": "长期系数", "type": "int", "default": 4, "min": 2},
                {"key": "up_deg_threshold", "label": "趋势阈值", "type": "float", "default": 3, "step": 0.5},
            ],
        },
        {
            "id": "up_down_golden",
            "name": "黄金分割回调",
            "desc": "上升趋势 + 黄金分割回调买入",
            "params": [
                {"key": "xd", "label": "短期周期", "type": "int", "default": 20, "min": 5},
                {"key": "past_factor", "label": "长期系数", "type": "int", "default": 4, "min": 2},
                {"key": "up_deg_threshold", "label": "趋势阈值", "type": "float", "default": 3, "step": 0.5},
            ],
        },
        {
            "id": "down_up_trend",
            "name": "反转趋势",
            "desc": "下跌趋势 + 短期反转买入",
            "params": [
                {"key": "xd", "label": "短期周期", "type": "int", "default": 20, "min": 5},
                {"key": "past_factor", "label": "长期系数", "type": "int", "default": 4, "min": 2},
                {"key": "down_deg_threshold", "label": "趋势阈值", "type": "float", "default": -3, "step": 0.5},
            ],
        },
        {
            "id": "week_win",
            "name": "周胜率",
            "desc": "周胜率回归择时",
            "params": [
                {"key": "buy_dw", "label": "胜率阈值", "type": "float", "default": 0.55, "step": 0.01},
                {"key": "buy_dwm", "label": "涨幅阈值", "type": "float", "default": 0.618, "step": 0.01},
                {"key": "dw_period", "label": "回看周期", "type": "int", "default": 40, "min": 10},
            ],
        },
        {
            "id": "momentum_break",
            "name": "动量突破",
            "desc": "区间新高突破动量买入",
            "params": [{"key": "xd", "label": "突破周期", "type": "int", "default": 20, "min": 5}],
        },
        {
            "id": "put_break",
            "name": "向下突破（做空）",
            "desc": "跌破区间新低触发买入（看空）",
            "params": [{"key": "xd", "label": "突破周期", "type": "int", "default": 20, "min": 5}],
        },
        {
            "id": "put_xdbk",
            "name": "向下突破（区间）",
            "desc": "区间新低突破买入（看空）",
            "params": [{"key": "xd", "label": "突破周期", "type": "int", "default": 20, "min": 5}],
        },
        {
            "id": "macd_cross",
            "name": "MACD 金叉",
            "desc": "DIF 上穿 DEA",
            "params": [
                {"key": "fast_period", "label": "快线周期", "type": "int", "default": 12, "min": 2},
                {"key": "slow_period", "label": "慢线周期", "type": "int", "default": 26, "min": 5},
                {"key": "signal_period", "label": "信号周期", "type": "int", "default": 9, "min": 3},
            ],
        },
    ],
    "sell": [
        {
            "id": "atr_stop",
            "name": "ATR 止损止盈",
            "desc": "ATR 动态止损止盈",
            "params": [
                {"key": "stop_loss_n", "label": "止损倍数", "type": "float", "default": 0.5, "step": 0.1},
                {"key": "stop_win_n", "label": "止盈倍数", "type": "float", "default": 3.0, "step": 0.1},
            ],
        },
        {
            "id": "atr_close",
            "name": "收盘 ATR 止损",
            "desc": "使用收盘价触发 ATR 止损",
            "params": [
                {"key": "stop_loss_n", "label": "止损倍数", "type": "float", "default": 0.5, "step": 0.1},
                {"key": "stop_win_n", "label": "止盈倍数", "type": "float", "default": 3.0, "step": 0.1},
            ],
        },
        {
            "id": "atr_pre",
            "name": "预警 ATR 止损",
            "desc": "使用前一日 ATR 触发止损",
            "params": [
                {"key": "stop_loss_n", "label": "止损倍数", "type": "float", "default": 0.5, "step": 0.1},
                {"key": "stop_win_n", "label": "止盈倍数", "type": "float", "default": 3.0, "step": 0.1},
            ],
        },
        {
            "id": "sell_break",
            "name": "向下突破止盈",
            "desc": "跌破区间低点卖出",
            "params": [{"key": "xd", "label": "突破周期", "type": "int", "default": 20, "min": 5}],
        },
        {
            "id": "sell_xdbk",
            "name": "向下突破（区间）卖出",
            "desc": "区间新低触发卖出",
            "params": [{"key": "xd", "label": "突破周期", "type": "int", "default": 20, "min": 5}],
        },
        {
            "id": "sell_n_day",
            "name": "N 日卖出",
            "desc": "持有 N 日后卖出",
            "params": [
                {"key": "sell_n", "label": "持有天数", "type": "int", "default": 5, "min": 1},
                {"key": "is_sell_today", "label": "当天卖出", "type": "bool", "default": False},
            ],
        },
        {
            "id": "double_ma_sell",
            "name": "均线死叉卖出",
            "desc": "快线下穿慢线卖出",
            "params": [
                {"key": "fast", "label": "快线周期", "type": "int", "default": 5, "min": 2},
                {"key": "slow", "label": "慢线周期", "type": "int", "default": 60, "min": 5},
            ],
        },
        {
            "id": "macd_cross",
            "name": "MACD 死叉",
            "desc": "DIF 下穿 DEA",
            "params": [
                {"key": "fast_period", "label": "快线周期", "type": "int", "default": 12, "min": 2},
                {"key": "slow_period", "label": "慢线周期", "type": "int", "default": 26, "min": 5},
                {"key": "signal_period", "label": "信号周期", "type": "int", "default": 9, "min": 3},
            ],
        },
    ],
}
def _split_symbols(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [item for item in re.split(r"[\s,;\uFF0C\u3001]+", raw) if item]
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


def _normalize_symbols(raw, market: str, fallback_default: bool = True) -> list[str]:
    symbols = [_normalize_symbol(item, market) for item in _split_symbols(raw)]
    symbols = [item for item in symbols if item]
    if symbols:
        return symbols
    if fallback_default:
        return DEFAULT_SYMBOLS.get(market, DEFAULT_SYMBOLS["US"])
    return []


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


def _params_dict(raw):
    if isinstance(raw, dict):
        return raw
    return {}


def _find_strategy_defaults(strategy_id: str, group: str) -> dict:
    for item in STRATEGY_CATALOG.get(group, []):
        if item.get("id") == strategy_id:
            return {param["key"]: param.get("default") for param in item.get("params", [])}
    return {}


def _merge_params(defaults: dict, overrides: dict) -> dict:
    merged = dict(defaults or {})
    for key, value in (overrides or {}).items():
        merged[key] = value
    return merged


def _param_int(config: dict, key: str, fallback: int) -> int:
    value = _safe_int(config.get(key))
    return fallback if value is None else value


def _param_float(config: dict, key: str, fallback: float) -> float:
    value = _safe_float(config.get(key))
    return fallback if value is None else value


def _grid_values(raw):
    if raw is None:
        return []
    if isinstance(raw, str):
        return [item for item in re.split(r"[\s,;\uFF0C\u3001]+", raw) if item]
    if isinstance(raw, (list, tuple, set)):
        return list(raw)
    return [raw]


def _build_param_grid(defaults: dict, grid: dict) -> list[dict]:
    if not grid:
        return [dict(defaults or {})]
    keys = []
    values = []
    for key, raw in grid.items():
        items = _grid_values(raw)
        if not items:
            continue
        keys.append(key)
        values.append(items)
    if not keys:
        return [dict(defaults or {})]
    combos = []
    for combo in product(*values):
        params = dict(defaults or {})
        params.update(dict(zip(keys, combo)))
        combos.append(params)
    return combos


def _normalize_strategy_list(value, fallback: str) -> list[str]:
    if value is None:
        return [fallback]
    if isinstance(value, str):
        items = [item.strip().lower() for item in re.split(r"[\s,;\uFF0C\u3001]+", value) if item.strip()]
        return items or [fallback]
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip().lower() for item in value if str(item).strip()]
        return items or [fallback]
    text = str(value).strip().lower()
    return [text] if text else [fallback]


def _strategy_id_set(group: str) -> set[str]:
    return {item.get("id") for item in STRATEGY_CATALOG.get(group, []) if item.get("id")}


def _validate_strategy_list(strategies: list[str], group: str):
    allowed = _strategy_id_set(group)
    unknown = [item for item in strategies if item not in allowed]
    if unknown:
        raise RuntimeError(f"Unknown {group} strategy: {unknown}. Allowed: {sorted(allowed)}")


def _strategy_param_keys(strategy_id: str, group: str) -> set[str]:
    items = STRATEGY_CATALOG.get(group, [])
    for item in items:
        if item.get("id") == strategy_id:
            return {param.get("key") for param in item.get("params", []) if param.get("key")}
    return set()


def _filter_param_grid(strategy_id: str, group: str, grid: dict) -> dict:
    if not grid:
        return {}
    allowed = _strategy_param_keys(strategy_id, group)
    if not allowed:
        return dict(grid)
    return {key: value for key, value in grid.items() if key in allowed}


__all__ = [name for name in globals().keys() if not name.startswith("__")]
