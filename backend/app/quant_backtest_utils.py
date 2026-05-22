from datetime import date, timedelta
import re
import math
from typing import Optional

from sqlalchemy.orm import Session

from . import crud
from .quant_core_utils import *
from .quant_data_utils import *
from .strategies import MacdCrossBuy, MacdCrossSell
def _summarize_orders(orders_pd):
    if orders_pd is None or getattr(orders_pd, "empty", True):
        return {
            "closed_orders": 0,
            "open_orders": 0,
            "wins": 0,
            "losses": 0,
            "profit_sum": 0.0,
            "profit_mean": 0.0,
            "win_rate": 0.0,
        }
    import pandas as pd

    closed = orders_pd[orders_pd["sell_type"].isin(["win", "loss"])]
    closed_count = int(getattr(closed, "shape", [0])[0])
    open_count = int(getattr(orders_pd, "shape", [0])[0]) - closed_count
    wins = int((closed.get("result") == 1).sum()) if closed_count else 0
    losses = max(0, closed_count - wins)
    profit_series = pd.to_numeric(closed.get("profit"), errors="coerce").fillna(0)
    profit_sum = float(profit_series.sum()) if closed_count else 0.0
    profit_mean = float(profit_series.mean()) if closed_count else 0.0
    win_rate = float((wins / closed_count) * 100) if closed_count else 0.0
    return {
        "closed_orders": closed_count,
        "open_orders": max(0, open_count),
        "wins": wins,
        "losses": losses,
        "profit_sum": profit_sum,
        "profit_mean": profit_mean,
        "win_rate": win_rate,
    }


def _summarize_capital(capital):
    if capital is None or not hasattr(capital, "capital_pd"):
        return {}
    import pandas as pd
    import numpy as np
    from abupy.CoreBu import ABuEnv

    raw_series = pd.to_numeric(capital.capital_pd.get("capital_blance"), errors="coerce")
    if not hasattr(raw_series, "dropna"):
        raw_series = pd.Series([raw_series])
    series = raw_series.dropna()
    if series is None or len(series) < 2:
        return {}
    returns = series.pct_change().dropna()
    if returns.empty:
        return {}
    trade_year = getattr(ABuEnv, "g_market_trade_year", 252)
    total_return = float(series.iloc[-1] / series.iloc[0] - 1)
    annual_return = (1 + total_return) ** (trade_year / len(returns)) - 1 if len(returns) else total_return
    volatility = float(returns.std() * np.sqrt(trade_year)) if returns.std() else 0.0
    sharpe = float((returns.mean() / returns.std()) * np.sqrt(trade_year)) if returns.std() else 0.0
    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    drawdown = (peak - cum) / peak
    max_drawdown = float(drawdown.max()) if not drawdown.empty else 0.0
    downside = returns[returns < 0]
    downside_volatility = float(downside.std() * np.sqrt(trade_year)) if not downside.empty and downside.std() else 0.0
    sortino = float((returns.mean() / downside.std()) * np.sqrt(trade_year)) if not downside.empty and downside.std() else 0.0
    calmar = float(annual_return / max_drawdown) if max_drawdown > 0 else 0.0
    var_95 = float(returns.quantile(0.05)) if not returns.empty else 0.0
    tail = returns[returns <= var_95]
    cvar_95 = float(tail.mean()) if not tail.empty else var_95
    drawdown_flags = (drawdown > 0).tolist()
    max_drawdown_duration = 0
    current_duration = 0
    for flag in drawdown_flags:
        if flag:
            current_duration += 1
            if current_duration > max_drawdown_duration:
                max_drawdown_duration = current_duration
        else:
            current_duration = 0
    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "volatility": volatility,
        "downside_volatility": downside_volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_drawdown,
        "max_drawdown_duration": int(max_drawdown_duration),
        "var_95": var_95,
        "cvar_95": cvar_95,
    }


def _build_commission_dict(params: Optional[dict]):
    params = params or {}
    commission_rate = float(_safe_float(params.get("commission_rate")) or 0.00025)
    min_commission = float(_safe_float(params.get("min_commission")) or 5.0)
    stamp_tax_rate = float(_safe_float(params.get("stamp_tax_rate")) or 0.0005)

    def _resolve_trade_args(*args, price_attr: str):
        if len(args) >= 2:
            trade_cnt = abs(_safe_float(args[0]) or 0.0)
            price = abs(_safe_float(args[1]) or 0.0)
            return trade_cnt, price
        a_order = args[0] if args else None
        trade_cnt = abs(_safe_float(getattr(a_order, "buy_cnt", 0)) or 0.0)
        price = abs(_safe_float(getattr(a_order, price_attr, 0)) or 0.0)
        return trade_cnt, price

    def buy_commission(*args):
        trade_cnt, price = _resolve_trade_args(*args, price_attr="buy_price")
        notional = trade_cnt * price
        if notional <= 0:
            return 0.0
        return max(min_commission, notional * commission_rate)

    def sell_commission(*args):
        trade_cnt, price = _resolve_trade_args(*args, price_attr="sell_price")
        notional = trade_cnt * price
        if notional <= 0:
            return 0.0
        return max(min_commission, notional * commission_rate) + notional * stamp_tax_rate

    return {
        "buy_commission_func": buy_commission,
        "sell_commission_func": sell_commission,
    }


def _trade_cost_config(params: Optional[dict]) -> dict:
    params = params or {}
    return {
        "commission_rate": float(_safe_float(params.get("commission_rate")) or 0.00025),
        "min_commission": float(_safe_float(params.get("min_commission")) or 5.0),
        "stamp_tax_rate": float(_safe_float(params.get("stamp_tax_rate")) or 0.0005),
        "slippage_bp": float(_safe_float(params.get("slippage_bp")) or 0.0),
    }


def _slippage_classes_from_bp(slippage_bp: float):
    bp = float(max(0.0, slippage_bp or 0.0))
    if bp <= 0:
        return None, None

    from abupy.SlippageBu.ABuSlippageBuyMean import AbuSlippageBuyMean
    from abupy.SlippageBu.ABuSlippageSellMean import AbuSlippageSellMean

    class AbuSlippageBuyBp(AbuSlippageBuyMean):
        def fit_price(self):
            price = super().fit_price()
            if price == float("inf"):
                return price
            adjusted = float(price) * (1.0 + bp / 10000.0)
            self.buy_price = adjusted
            return adjusted

    class AbuSlippageSellBp(AbuSlippageSellMean):
        def fit_price(self):
            price = super().fit_price()
            if price == float("-inf"):
                return price
            adjusted = float(price) * max(0.0, 1.0 - bp / 10000.0)
            self.sell_price = adjusted
            return adjusted

    return AbuSlippageBuyBp, AbuSlippageSellBp


def _summarize_execution_costs(capital, orders_pd, params: Optional[dict] = None) -> dict:
    import pandas as pd

    cost_config = _trade_cost_config(params)
    commission_total = 0.0
    commission_records = 0
    commission_df = getattr(getattr(capital, "commission", None), "commission_df", None)
    if commission_df is not None and not getattr(commission_df, "empty", True):
        commission_series = pd.to_numeric(commission_df.get("commission"), errors="coerce").fillna(0.0)
        commission_total = float(commission_series.sum())
        commission_records = int(commission_series.shape[0])

    estimated_slippage_cost = 0.0
    turnover_ratio_est = 0.0
    if orders_pd is not None and not getattr(orders_pd, "empty", True):
        buy_cnt = pd.to_numeric(orders_pd.get("buy_cnt"), errors="coerce").fillna(0.0).abs()
        buy_price = pd.to_numeric(orders_pd.get("buy_price"), errors="coerce").fillna(0.0).abs()
        sell_price = pd.to_numeric(orders_pd.get("sell_price"), errors="coerce").fillna(0.0).abs()
        traded_notional = float((buy_cnt * buy_price).sum() + (buy_cnt * sell_price).sum())
        estimated_slippage_cost = traded_notional * float(cost_config["slippage_bp"]) / 10000.0
        init_cash = float(getattr(capital, "read_cash", 0.0) or 0.0)
        turnover_ratio_est = traded_notional / init_cash if init_cash > 0 else 0.0

    estimated_total_cost = float(commission_total + estimated_slippage_cost)
    return {
        "trade_costs": {
            **cost_config,
            "commission_total": float(commission_total),
            "estimated_slippage_cost": float(estimated_slippage_cost),
            "estimated_total_cost": estimated_total_cost,
            "commission_records": commission_records,
            "turnover_ratio_est": float(turnover_ratio_est),
        },
        "commission_total": float(commission_total),
        "estimated_slippage_cost": float(estimated_slippage_cost),
        "estimated_total_cost": estimated_total_cost,
        "turnover_ratio_est": float(turnover_ratio_est),
    }


def _summarize_run(abu_result, params: Optional[dict] = None):
    summary = _summarize_orders(getattr(abu_result, "orders_pd", None))
    summary.update(_summarize_capital(getattr(abu_result, "capital", None)))
    summary.update(
        _summarize_execution_costs(
            getattr(abu_result, "capital", None),
            getattr(abu_result, "orders_pd", None),
            params=params,
        )
    )
    summary["estimated_gross_profit_sum"] = float(summary.get("profit_sum", 0.0) or 0.0) + float(
        summary.get("estimated_total_cost", 0.0) or 0.0
    )
    return summary


def _aggregate_summaries(items: list[dict]) -> dict:
    if not items:
        return {}
    closed_orders = 0
    open_orders = 0
    wins = 0
    losses = 0
    profit_sum = 0.0
    total_returns = []
    annual_returns = []
    volatilities = []
    downside_volatilities = []
    sharpes = []
    sortinos = []
    calmars = []
    max_drawdowns = []
    max_drawdown_durations = []
    var_95_values = []
    cvar_95_values = []
    turnover_ratios = []
    commission_total = 0.0
    estimated_slippage_cost = 0.0
    estimated_total_cost = 0.0
    for item in items:
        if not item:
            continue
        closed_orders += int(item.get("closed_orders", 0) or 0)
        open_orders += int(item.get("open_orders", 0) or 0)
        wins += int(item.get("wins", 0) or 0)
        losses += int(item.get("losses", 0) or 0)
        profit_sum += float(item.get("profit_sum", 0.0) or 0.0)
        commission_total += float(item.get("commission_total", 0.0) or 0.0)
        estimated_slippage_cost += float(item.get("estimated_slippage_cost", 0.0) or 0.0)
        estimated_total_cost += float(item.get("estimated_total_cost", 0.0) or 0.0)
        for key, bucket in (
            ("total_return", total_returns),
            ("annual_return", annual_returns),
            ("volatility", volatilities),
            ("downside_volatility", downside_volatilities),
            ("sharpe", sharpes),
            ("sortino", sortinos),
            ("calmar", calmars),
            ("max_drawdown", max_drawdowns),
            ("var_95", var_95_values),
            ("cvar_95", cvar_95_values),
            ("turnover_ratio_est", turnover_ratios),
        ):
            value = item.get(key)
            if value is None:
                continue
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            if value != value:
                continue
            bucket.append(value)
        duration = item.get("max_drawdown_duration")
        if duration is not None:
            try:
                max_drawdown_durations.append(int(duration))
            except (TypeError, ValueError):
                pass
    profit_mean = profit_sum / closed_orders if closed_orders else 0.0
    win_rate = (wins / closed_orders) * 100 if closed_orders else 0.0
    avg_total_return = sum(total_returns) / len(total_returns) if total_returns else 0.0
    avg_return = sum(annual_returns) / len(annual_returns) if annual_returns else 0.0
    avg_volatility = sum(volatilities) / len(volatilities) if volatilities else 0.0
    avg_downside_volatility = sum(downside_volatilities) / len(downside_volatilities) if downside_volatilities else 0.0
    avg_sharpe = sum(sharpes) / len(sharpes) if sharpes else 0.0
    avg_sortino = sum(sortinos) / len(sortinos) if sortinos else 0.0
    avg_calmar = sum(calmars) / len(calmars) if calmars else 0.0
    max_drawdown = max(max_drawdowns) if max_drawdowns else 0.0
    return {
        "closed_orders": closed_orders,
        "open_orders": open_orders,
        "wins": wins,
        "losses": losses,
        "profit_sum": profit_sum,
        "estimated_gross_profit_sum": profit_sum + estimated_total_cost,
        "profit_mean": profit_mean,
        "win_rate": win_rate,
        "total_return": avg_total_return,
        "annual_return": avg_return,
        "volatility": avg_volatility,
        "downside_volatility": avg_downside_volatility,
        "sharpe": avg_sharpe,
        "sortino": avg_sortino,
        "calmar": avg_calmar,
        "max_drawdown": max_drawdown,
        "max_drawdown_duration": max(max_drawdown_durations) if max_drawdown_durations else 0,
        "var_95": sum(var_95_values) / len(var_95_values) if var_95_values else 0.0,
        "cvar_95": sum(cvar_95_values) / len(cvar_95_values) if cvar_95_values else 0.0,
        "commission_total": commission_total,
        "estimated_slippage_cost": estimated_slippage_cost,
        "estimated_total_cost": estimated_total_cost,
        "turnover_ratio_est": sum(turnover_ratios) / len(turnover_ratios) if turnover_ratios else 0.0,
    }


def _prefix_summary(summary: dict, prefix: str) -> dict:
    return {f"{prefix}{key}": value for key, value in summary.items()} if summary else {}


def _run_metric(item: dict, key: str, default: float = 0.0) -> float:
    value = item.get(f"validation_{key}")
    if value is None:
        value = item.get(key, default)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return float(default)
    if value != value:
        return float(default)
    return value


def _run_metric_int(item: dict, key: str, default: int = 0) -> int:
    value = item.get(f"validation_{key}")
    if value is None:
        value = item.get(key, default)
    try:
        value = int(value)
    except (TypeError, ValueError):
        return int(default)
    return value


def _grid_sort_key(item: dict):
    profit = _run_metric(item, "profit_sum", 0.0)
    sharpe = _run_metric(item, "sharpe", 0.0)
    win_rate = _run_metric(item, "win_rate", 0.0)
    annual_return = _run_metric(item, "annual_return", 0.0)
    drawdown = _run_metric(item, "max_drawdown", 0.0)
    closed_orders = _run_metric_int(item, "closed_orders", 0)
    return (profit, sharpe, win_rate, annual_return, -drawdown, closed_orders)


def _grid_win_key(item: dict):
    win_rate = _run_metric(item, "win_rate", 0.0)
    profit = _run_metric(item, "profit_sum", 0.0)
    sharpe = _run_metric(item, "sharpe", 0.0)
    annual_return = _run_metric(item, "annual_return", 0.0)
    drawdown = _run_metric(item, "max_drawdown", 0.0)
    closed_orders = _run_metric_int(item, "closed_orders", 0)
    return (win_rate, profit, sharpe, annual_return, -drawdown, closed_orders)


def _summarize_orders_by_symbol(orders_pd, top_n: int = 10) -> list[dict]:
    if orders_pd is None or getattr(orders_pd, "empty", True):
        return []
    if "symbol" not in orders_pd.columns:
        return []
    import pandas as pd

    closed = orders_pd[orders_pd["sell_type"].isin(["win", "loss"])] if "sell_type" in orders_pd.columns else orders_pd
    if closed is None or getattr(closed, "empty", True):
        return []
    scoped = closed.copy()
    scoped["profit_num"] = pd.to_numeric(scoped.get("profit"), errors="coerce").fillna(0.0)
    scoped["is_win"] = (scoped.get("result") == 1).astype(int)
    grouped = (
        scoped.groupby("symbol", dropna=True)
        .agg(
            closed_orders=("is_win", "size"),
            wins=("is_win", "sum"),
            profit_sum=("profit_num", "sum"),
            profit_mean=("profit_num", "mean"),
        )
        .reset_index()
    )
    if grouped.empty:
        return []
    grouped["win_rate"] = grouped["wins"] / grouped["closed_orders"] * 100.0
    grouped = grouped.sort_values(
        by=["win_rate", "profit_sum", "closed_orders", "profit_mean"],
        ascending=[False, False, False, False],
    )
    result = []
    for idx, row in grouped.head(max(1, int(top_n))).iterrows():
        result.append(
            {
                "rank": len(result) + 1,
                "symbol": row["symbol"],
                "closed_orders": int(row["closed_orders"]),
                "wins": int(row["wins"]),
                "win_rate": float(row["win_rate"]),
                "profit_sum": float(row["profit_sum"]),
                "profit_mean": float(row["profit_mean"]),
            }
        )
    return result


def _build_strategy_recommendation(run_summary: Optional[dict], top_symbols: list[dict]) -> dict:
    if not run_summary:
        return {}
    win_rate = _run_metric(run_summary, "win_rate", 0.0)
    drawdown = _run_metric(run_summary, "max_drawdown", 0.0)
    sharpe = _run_metric(run_summary, "sharpe", 0.0)
    profit = _run_metric(run_summary, "profit_sum", 0.0)
    closed_orders = _run_metric_int(run_summary, "closed_orders", 0)
    if drawdown >= 0.2 or win_rate < 50:
        mode = "稳健"
        position = "30%~45%"
    elif win_rate >= 62 and drawdown <= 0.12 and sharpe >= 1.0:
        mode = "激进"
        position = "60%~75%"
    else:
        mode = "平衡"
        position = "45%~60%"

    notes = [
        f"当前组合胜率 {win_rate:.1f}%，回撤 {drawdown:.3f}，夏普 {sharpe:.2f}。",
        f"建议初始仓位区间：{position}。",
    ]
    if closed_orders < 20:
        notes.append("样本交易笔数偏少，建议扩大回测区间后再确认。")
    if top_symbols:
        names = ", ".join([str(item.get("symbol")) for item in top_symbols[:5] if item.get("symbol")])
        if names:
            notes.append(f"优先跟踪 Top 标的：{names}。")
    if profit <= 0:
        notes.append("收益尚未转正，建议先使用稳健模式并收紧止损。")

    return {
        "mode": mode,
        "position_range": position,
        "buy_strategy": run_summary.get("buy_strategy"),
        "sell_strategy": run_summary.get("sell_strategy"),
        "buy_params": run_summary.get("buy_params") or {},
        "sell_params": run_summary.get("sell_params") or {},
        "notes": notes,
    }


def _summary_from_ranked_symbols(top_symbols: list[dict], template: Optional[dict] = None) -> dict:
    base = dict(template or {})
    if not top_symbols:
        base.setdefault("win_rate", 0.0)
        base.setdefault("max_drawdown", 0.0)
        base.setdefault("sharpe", 0.0)
        base.setdefault("sortino", 0.0)
        base.setdefault("calmar", 0.0)
        base.setdefault("profit_sum", 0.0)
        base.setdefault("estimated_gross_profit_sum", 0.0)
        base.setdefault("annual_return", 0.0)
        base.setdefault("commission_total", 0.0)
        base.setdefault("estimated_slippage_cost", 0.0)
        base.setdefault("estimated_total_cost", 0.0)
        base.setdefault("closed_orders", 0)
        return base

    count = max(1, len(top_symbols))
    win_rate = sum(float(item.get("win_rate", 0.0) or 0.0) for item in top_symbols) / count
    sharpe = sum(float(item.get("sharpe", 0.0) or 0.0) for item in top_symbols) / count
    sortino = sum(float(item.get("sortino", 0.0) or 0.0) for item in top_symbols) / count
    calmar = sum(float(item.get("calmar", 0.0) or 0.0) for item in top_symbols) / count
    max_drawdown = sum(float(item.get("max_drawdown", 0.0) or 0.0) for item in top_symbols) / count
    annual_return = sum(float(item.get("annual_return", 0.0) or 0.0) for item in top_symbols) / count
    profit_sum = sum(float(item.get("profit_sum", 0.0) or 0.0) for item in top_symbols)
    commission_total = sum(float(item.get("commission_total", 0.0) or 0.0) for item in top_symbols)
    estimated_slippage_cost = sum(float(item.get("estimated_slippage_cost", 0.0) or 0.0) for item in top_symbols)
    estimated_total_cost = sum(float(item.get("estimated_total_cost", 0.0) or 0.0) for item in top_symbols)
    closed_orders = sum(int(item.get("closed_orders", 0) or 0) for item in top_symbols)
    base.update(
        {
            "win_rate": float(win_rate),
            "max_drawdown": float(max_drawdown),
            "sharpe": float(sharpe),
            "sortino": float(sortino),
            "calmar": float(calmar),
            "profit_sum": float(profit_sum),
            "estimated_gross_profit_sum": float(profit_sum + estimated_total_cost),
            "annual_return": float(annual_return),
            "commission_total": float(commission_total),
            "estimated_slippage_cost": float(estimated_slippage_cost),
            "estimated_total_cost": float(estimated_total_cost),
            "closed_orders": int(closed_orders),
        }
    )
    return base


def _load_candidate_symbols_from_db(db: Session, market: str, limit: int = 500) -> list[str]:
    market_keys = _market_scope(market)
    rows = crud.list_stock_symbols_by_markets(db, market_keys)
    normalized = []
    for item in rows:
        symbol = _normalize_symbol(item.symbol, item.market)
        if symbol:
            lower = str(symbol).lower()
            if lower.startswith("sh000") or lower.startswith("sz399"):
                continue
            normalized.append(symbol)
    deduped = list(dict.fromkeys(normalized))
    cap = max(20, min(int(limit or 500), 50000))
    return deduped[:cap]


def _evaluate_symbols_for_run(
    abu,
    symbols: list[str],
    cash,
    buy_factors: list[dict],
    sell_factors: list[dict],
    n_folds,
    start,
    end,
    top_n: int = 10,
    eval_limit: Optional[int] = 120,
    progress_cb=None,
    run_kwargs: Optional[dict] = None,
    summary_params: Optional[dict] = None,
) -> dict:
    top_n = max(1, min(int(top_n), 200))
    max_eval_cap = 50000
    if not symbols:
        return {
            "evaluated": 0,
            "available": 0,
            "truncated": False,
            "top": [],
        }
    if eval_limit is None:
        effective_eval_limit = len(symbols)
    else:
        try:
            requested_limit = int(eval_limit)
        except (TypeError, ValueError):
            requested_limit = len(symbols)
        if requested_limit <= 0:
            effective_eval_limit = len(symbols)
        else:
            effective_eval_limit = max(5, min(requested_limit, max_eval_cap, len(symbols)))
    candidates = symbols[:effective_eval_limit]
    rows = []
    for idx, symbol in enumerate(candidates, start=1):
        try:
            abu_result, _ = abu.run_loop_back(
                read_cash=cash,
                buy_factors=buy_factors,
                sell_factors=sell_factors,
                choice_symbols=[symbol],
                n_folds=n_folds,
                start=start,
                end=end,
                n_process_kl=1,
                n_process_pick=1,
                **(run_kwargs or {}),
            )
            if abu_result is None:
                continue
            summary = _summarize_run(abu_result, params=summary_params)
            if not summary:
                continue
            row = {
                "symbol": symbol,
                "closed_orders": int(summary.get("closed_orders", 0) or 0),
                "win_rate": float(summary.get("win_rate", 0.0) or 0.0),
                "profit_sum": float(summary.get("profit_sum", 0.0) or 0.0),
                "profit_mean": float(summary.get("profit_mean", 0.0) or 0.0),
                "annual_return": float(summary.get("annual_return", 0.0) or 0.0),
                "sharpe": float(summary.get("sharpe", 0.0) or 0.0),
                "sortino": float(summary.get("sortino", 0.0) or 0.0),
                "calmar": float(summary.get("calmar", 0.0) or 0.0),
                "max_drawdown": float(summary.get("max_drawdown", 0.0) or 0.0),
                "commission_total": float(summary.get("commission_total", 0.0) or 0.0),
                "estimated_slippage_cost": float(summary.get("estimated_slippage_cost", 0.0) or 0.0),
                "estimated_total_cost": float(summary.get("estimated_total_cost", 0.0) or 0.0),
            }
            rows.append(row)
        except Exception:
            continue
        finally:
            if callable(progress_cb) and (idx == len(candidates) or idx % 5 == 0):
                try:
                    progress_cb(idx, len(candidates))
                except Exception:
                    pass

    rows_sorted = sorted(
        rows,
        key=lambda item: (
            item.get("win_rate", 0.0),
            item.get("profit_sum", 0.0),
            item.get("sharpe", 0.0),
            -item.get("max_drawdown", 0.0),
            item.get("closed_orders", 0),
        ),
        reverse=True,
    )
    top_rows = []
    for idx, row in enumerate(rows_sorted[:top_n], start=1):
        top_rows.append({**row, "rank": idx})
    return {
        "evaluated": len(candidates),
        "available": len(symbols),
        "truncated": len(symbols) > len(candidates),
        "top": top_rows,
    }


def _capital_curve_points(capital, limit: int = 3000) -> list[dict]:
    if capital is None or not hasattr(capital, "capital_pd"):
        return []
    try:
        import pandas as pd

        raw_series = pd.to_numeric(capital.capital_pd.get("capital_blance"), errors="coerce")
        if raw_series is None:
            return []
        series = raw_series.dropna()
        if series is None or len(series) < 1:
            return []
        base = float(series.iloc[0])
        pnl_series = series - base
        if limit and len(pnl_series) > limit:
            total = len(pnl_series)
            if limit <= 1:
                pnl_series = pnl_series.tail(1)
            else:
                # Keep the full timeline shape by evenly sampling indices
                # instead of dropping all early history with tail(limit).
                step = (total - 1) / float(limit - 1)
                positions = sorted(
                    {
                        min(total - 1, max(0, int(round(i * step))))
                        for i in range(int(limit))
                    }
                )
                pnl_series = pnl_series.iloc[positions]
        points = []
        for idx, val in pnl_series.items():
            try:
                value = float(val)
            except (TypeError, ValueError):
                continue
            if hasattr(idx, "strftime"):
                time_str = idx.strftime("%Y-%m-%d")
            else:
                raw = str(idx)
                if re.match(r"^\d{8}$", raw):
                    time_str = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
                else:
                    time_str = raw[:10]
            points.append({"time": time_str, "value": value})
        return points
    except Exception:
        return []


def _build_actionable_candidates(
    db: Session,
    top_symbols: list[dict],
    market: str,
    mode: str = "平衡",
    limit: int = 10,
) -> list[dict]:
    if not top_symbols:
        return []
    import pandas as pd

    position_map = {
        "稳健": "30%~45%",
        "平衡": "45%~60%",
        "激进": "60%~75%",
    }
    action_weight = {
        "breakout_buy": 4.0,
        "pullback_buy": 3.0,
        "hold_watch": 2.0,
        "wait": 1.0,
        "reduce_defense": 0.5,
    }

    candidates = []
    for item in top_symbols[: max(limit * 3, 12)]:
        symbol = str(item.get("symbol") or "").strip()
        if not symbol:
            continue
        try:
            symbol_market = _market_from_symbol(symbol) or market
            rows = crud.load_klines(db, symbol_market, symbol)
            if not rows:
                continue
            rows = rows[-220:]
            kl = _kl_df_from_rows(rows)
            if kl is None or len(kl) < 60:
                continue

            close = pd.to_numeric(kl.get("close"), errors="coerce").dropna()
            if len(close) < 60:
                continue
            last_close = float(close.iloc[-1])
            ma20 = float(close.rolling(20).mean().iloc[-1])
            ma60 = float(close.rolling(60).mean().iloc[-1])
            resistance = float(close.tail(20).max())
            support = float(close.tail(20).min())
            atr = None
            if "atr14" in kl.columns:
                atr = _safe_float(kl["atr14"].iloc[-1])
            if (atr is None or atr <= 0) and "atr21" in kl.columns:
                atr = _safe_float(kl["atr21"].iloc[-1])
            if atr is None or atr <= 0:
                atr = _safe_float((kl["high"] - kl["low"]).tail(14).mean()) if {"high", "low"}.issubset(kl.columns) else None

            if last_close >= resistance * 0.995 and last_close > ma20 > ma60:
                action = "突破买入"
                action_code = "breakout_buy"
                reason = "价格接近或突破 20 日新高，且均线多头。"
            elif last_close > ma60 and abs(last_close - ma20) / max(ma20, 1e-9) <= 0.012:
                action = "回踩观察买入"
                action_code = "pullback_buy"
                reason = "价格贴近 20 日均线且中期趋势仍偏强。"
            elif last_close >= ma20 and ma20 >= ma60:
                action = "持有观察"
                action_code = "hold_watch"
                reason = "趋势仍在，但未出现强突破点。"
            elif last_close < ma60 * 0.985:
                action = "减仓防守"
                action_code = "reduce_defense"
                reason = "价格明显弱于中期均线，优先防守。"
            else:
                action = "观望"
                action_code = "wait"
                reason = "趋势信号不明确。"

            if atr and atr > 0:
                stop_loss = last_close - 1.5 * atr
                take_profit = last_close + 3.0 * atr
            else:
                stop_loss = last_close * 0.95
                take_profit = last_close * 1.1

            win_rate = float(item.get("win_rate") or 0.0)
            profit_sum = float(item.get("profit_sum") or 0.0)
            sharpe = float(item.get("sharpe") or 0.0)
            annual_return = float(item.get("annual_return") or 0.0)
            max_drawdown = float(item.get("max_drawdown") or 0.0)
            profit_component = math.log1p(max(0.0, profit_sum)) * 8.0
            score = (
                action_weight.get(action_code, 0.0) * 30.0
                + win_rate * 0.6
                + sharpe * 25.0
                + annual_return * 120.0
                - max_drawdown * 120.0
                + profit_component
            )
            candidates.append(
                {
                    "symbol": symbol,
                    "action": action,
                    "action_code": action_code,
                    "reason": reason,
                    "position_range": position_map.get(mode, position_map["平衡"]),
                    "win_rate": win_rate,
                    "profit_sum": profit_sum,
                    "sharpe": sharpe,
                    "annual_return": annual_return,
                    "max_drawdown": max_drawdown,
                    "last_close": last_close,
                    "support": support,
                    "resistance": resistance,
                    "stop_loss": float(stop_loss),
                    "take_profit": float(take_profit),
                    "score": float(score),
                }
            )
        except Exception:
            continue

    candidates = sorted(
        candidates,
        key=lambda x: (
            float(x.get("score", 0.0)),
            float(x.get("win_rate", 0.0)),
            float(x.get("profit_sum", 0.0)),
        ),
        reverse=True,
    )
    return candidates[: max(1, min(limit, 30))]


def _calc_custom_score(
    run: dict,
    weights: Optional[dict] = None,
) -> float:
    weights = weights or {}

    def _weight(name: str, default: float = 1.0) -> float:
        value = weights.get(name, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    w_profit = _weight("profit", 1.0)
    w_win = _weight("win_rate", 1.0)
    w_sharpe = _weight("sharpe", 1.0)
    w_return = _weight("annual_return", 1.0)
    w_drawdown = _weight("drawdown", 1.0)
    profit = _run_metric(run, "profit_sum", 0.0)
    win_rate = _run_metric(run, "win_rate", 0.0)
    sharpe = _run_metric(run, "sharpe", 0.0)
    annual_return = _run_metric(run, "annual_return", 0.0)
    drawdown = _run_metric(run, "max_drawdown", 0.0)
    return (
        profit * w_profit
        + win_rate * w_win
        + sharpe * 100.0 * w_sharpe
        + annual_return * 100.0 * w_return
        - drawdown * 100.0 * w_drawdown
    )


def _choose_grid_sort_key(metric: str, weights: Optional[dict] = None):
    metric = (metric or "profit").strip().lower()
    if metric == "win_rate":
        return _grid_win_key
    if metric == "sharpe":
        return lambda item: (
            _run_metric(item, "sharpe", 0.0),
            _run_metric(item, "win_rate", 0.0),
            _run_metric(item, "profit_sum", 0.0),
            -_run_metric(item, "max_drawdown", 0.0),
            _run_metric_int(item, "closed_orders", 0),
        )
    if metric == "annual_return":
        return lambda item: (
            _run_metric(item, "annual_return", 0.0),
            _run_metric(item, "sharpe", 0.0),
            _run_metric(item, "win_rate", 0.0),
            -_run_metric(item, "max_drawdown", 0.0),
            _run_metric_int(item, "closed_orders", 0),
        )
    if metric == "custom":
        return lambda item: (
            float(item.get("custom_score") or _calc_custom_score(item, weights)),
            _run_metric(item, "win_rate", 0.0),
            _run_metric(item, "profit_sum", 0.0),
            _run_metric(item, "sharpe", 0.0),
            -_run_metric(item, "max_drawdown", 0.0),
        )
    return _grid_sort_key


def _build_next_param_suggestions(best_run: Optional[dict]) -> dict:
    if not best_run:
        return {}

    def _expand(value):
        number = _safe_float(value)
        if number is None:
            return [value]
        if number == 0:
            return [0, 0.1, 0.2]
        return sorted(
            set(
                [
                    round(number * 0.8, 4),
                    round(number * 0.9, 4),
                    round(number, 4),
                    round(number * 1.1, 4),
                    round(number * 1.2, 4),
                ]
            )
        )

    buy = best_run.get("buy_params") or {}
    sell = best_run.get("sell_params") or {}
    buy_grid = {k: _expand(v) for k, v in buy.items()}
    sell_grid = {k: _expand(v) for k, v in sell.items()}
    return {
        "buy_params_grid": buy_grid,
        "sell_params_grid": sell_grid,
    }


def _resolve_date_bounds(
    db: Session, symbols: list[str], start: Optional[str], end: Optional[str], n_folds: int
) -> tuple[Optional[date], Optional[date]]:
    start_date = _parse_date_str(start)
    end_date = _parse_date_str(end)
    if start_date and end_date:
        return start_date, end_date
    if symbols:
        rows = crud.load_klines(db, _market_from_symbol(symbols[0]), symbols[0])
        if rows:
            first = rows[0].trade_date
            last = rows[-1].trade_date
            if not start_date:
                start_date = first
            if not end_date:
                end_date = last
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=365 * max(1, int(n_folds)))
    return start_date, end_date


def _split_holdout(start_date: date, end_date: date, train_ratio: float):
    total_days = (end_date - start_date).days
    if total_days <= 1:
        return None
    ratio = max(0.5, min(0.9, train_ratio))
    train_days = max(1, int(total_days * ratio))
    train_end = start_date + timedelta(days=train_days)
    val_start = train_end + timedelta(days=1)
    if val_start >= end_date:
        return None
    return (start_date, train_end, val_start, end_date)


def _walk_forward_slices(
    start_date: date, end_date: date, train_ratio: float, window_days: int, step_days: int
):
    ratio = max(0.5, min(0.9, train_ratio))
    window = max(60, int(window_days))
    step = max(30, int(step_days))
    slices = []
    cursor = start_date
    while cursor + timedelta(days=window) < end_date:
        window_start = cursor
        window_end = min(end_date, cursor + timedelta(days=window))
        split = _split_holdout(window_start, window_end, ratio)
        if split:
            slices.append(split)
        cursor += timedelta(days=step)
    return slices


def _build_buy_factors(params: dict) -> list[dict]:
    from abupy.FactorBuyBu import AbuFactorBuyBreak
    from abupy.FactorBuyBu.ABuFactorBuyBreak import (
        AbuFactorBuyXDBK,
        AbuFactorBuyPutBreak,
        AbuFactorBuyPutXDBK,
    )
    from abupy.FactorBuyBu.ABuFactorBuyDM import AbuDoubleMaBuy
    from abupy.FactorBuyBu.ABuFactorBuyTrend import AbuDownUpTrend, AbuUpDownGolden, AbuUpDownTrend
    from abupy.FactorBuyBu.ABuFactorBuyWD import AbuFactorBuyWD

    strategy_id = (params.get("buy_strategy") or "breakout").strip().lower()
    defaults = _find_strategy_defaults(strategy_id, "buy")
    config = _merge_params(defaults, _params_dict(params.get("buy_params")))
    slippage_bp = float(_safe_float(params.get("slippage_bp")) or 0.0)
    buy_slippage_class, _ = _slippage_classes_from_bp(slippage_bp)

    def _apply_buy_slippage(payload: dict) -> dict:
        if buy_slippage_class is not None:
            payload["slippage"] = buy_slippage_class
        return payload

    if strategy_id in {"breakout", "break"}:
        xd = _param_int(config, "xd", _param_int(params, "buy_xd", 42))
        return [_apply_buy_slippage({"class": AbuFactorBuyBreak, "xd": xd})]
    if strategy_id == "momentum_break":
        xd = _param_int(config, "xd", 20)
        return [{"class": AbuFactorBuyXDBK, "xd": xd}]
    if strategy_id == "double_ma":
        return [
            _apply_buy_slippage(
                {
                "class": AbuDoubleMaBuy,
                "fast": _param_int(config, "fast", 5),
                "slow": _param_int(config, "slow", 60),
                "resample_min": _param_int(config, "resample_min", 10),
                "resample_max": _param_int(config, "resample_max", 100),
                "change_threshold": _param_float(config, "change_threshold", 0.12),
                }
            )
        ]
    if strategy_id == "up_down_trend":
        return [
            _apply_buy_slippage(
                {
                "class": AbuUpDownTrend,
                "xd": _param_int(config, "xd", 20),
                "past_factor": _param_int(config, "past_factor", 4),
                "up_deg_threshold": _param_float(config, "up_deg_threshold", 3),
                }
            )
        ]
    if strategy_id == "up_down_golden":
        return [
            _apply_buy_slippage(
                {
                "class": AbuUpDownGolden,
                "xd": _param_int(config, "xd", 20),
                "past_factor": _param_int(config, "past_factor", 4),
                "up_deg_threshold": _param_float(config, "up_deg_threshold", 3),
                }
            )
        ]
    if strategy_id == "down_up_trend":
        return [
            _apply_buy_slippage(
                {
                "class": AbuDownUpTrend,
                "xd": _param_int(config, "xd", 20),
                "past_factor": _param_int(config, "past_factor", 4),
                "down_deg_threshold": _param_float(config, "down_deg_threshold", -3),
                }
            )
        ]
    if strategy_id == "week_win":
        return [
            _apply_buy_slippage(
                {
                "class": AbuFactorBuyWD,
                "buy_dw": _param_float(config, "buy_dw", 0.55),
                "buy_dwm": _param_float(config, "buy_dwm", 0.618),
                "dw_period": _param_int(config, "dw_period", 40),
                }
            )
        ]
    if strategy_id == "macd_cross":
        return [
            _apply_buy_slippage(
                {
                "class": MacdCrossBuy,
                "fast_period": _param_int(config, "fast_period", 12),
                "slow_period": _param_int(config, "slow_period", 26),
                "signal_period": _param_int(config, "signal_period", 9),
                }
            )
        ]
    if strategy_id == "put_break":
        xd = _param_int(config, "xd", 20)
        return [_apply_buy_slippage({"class": AbuFactorBuyPutBreak, "xd": xd})]
    if strategy_id == "put_xdbk":
        xd = _param_int(config, "xd", 20)
        return [_apply_buy_slippage({"class": AbuFactorBuyPutXDBK, "xd": xd})]

    raise ValueError(f"Unknown buy strategy: {strategy_id}")


def _build_sell_factors(params: dict) -> list[dict]:
    from abupy.FactorSellBu import AbuFactorAtrNStop
    from abupy.FactorSellBu.ABuFactorCloseAtrNStop import AbuFactorCloseAtrNStop
    from abupy.FactorSellBu.ABuFactorPreAtrNStop import AbuFactorPreAtrNStop
    from abupy.FactorSellBu.ABuFactorSellBreak import AbuFactorSellBreak
    from abupy.FactorSellBu.ABuFactorSellBreak import AbuFactorSellXDBK
    from abupy.FactorSellBu.ABuFactorSellNDay import AbuFactorSellNDay
    from abupy.FactorSellBu.ABuFactorSellDM import AbuDoubleMaSell

    strategy_id = (params.get("sell_strategy") or "atr_stop").strip().lower()
    defaults = _find_strategy_defaults(strategy_id, "sell")
    config = _merge_params(defaults, _params_dict(params.get("sell_params")))
    slippage_bp = float(_safe_float(params.get("slippage_bp")) or 0.0)
    _, sell_slippage_class = _slippage_classes_from_bp(slippage_bp)

    def _apply_sell_slippage(payload: dict) -> dict:
        if sell_slippage_class is not None:
            payload["slippage"] = sell_slippage_class
        return payload

    if strategy_id == "atr_stop":
        return [
            _apply_sell_slippage(
                {
                "class": AbuFactorAtrNStop,
                "stop_loss_n": _param_float(config, "stop_loss_n", _param_float(params, "stop_loss_n", 0.5)),
                "stop_win_n": _param_float(config, "stop_win_n", _param_float(params, "stop_win_n", 3.0)),
                }
            )
        ]
    if strategy_id == "atr_close":
        return [
            _apply_sell_slippage(
                {
                "class": AbuFactorCloseAtrNStop,
                "stop_loss_n": _param_float(config, "stop_loss_n", 0.5),
                "stop_win_n": _param_float(config, "stop_win_n", 3.0),
                }
            )
        ]
    if strategy_id == "atr_pre":
        return [
            _apply_sell_slippage(
                {
                "class": AbuFactorPreAtrNStop,
                "stop_loss_n": _param_float(config, "stop_loss_n", 0.5),
                "stop_win_n": _param_float(config, "stop_win_n", 3.0),
                }
            )
        ]
    if strategy_id == "sell_break":
        return [_apply_sell_slippage({"class": AbuFactorSellBreak, "xd": _param_int(config, "xd", 20)})]
    if strategy_id == "sell_xdbk":
        return [_apply_sell_slippage({"class": AbuFactorSellXDBK, "xd": _param_int(config, "xd", 20)})]
    if strategy_id == "sell_n_day":
        return [
            _apply_sell_slippage(
                {
                "class": AbuFactorSellNDay,
                "sell_n": _param_int(config, "sell_n", 5),
                "is_sell_today": bool(config.get("is_sell_today", False)),
                }
            )
        ]
    if strategy_id == "double_ma_sell":
        return [
            _apply_sell_slippage(
                {
                "class": AbuDoubleMaSell,
                "fast": _param_int(config, "fast", 5),
                "slow": _param_int(config, "slow", 60),
                }
            )
        ]
    if strategy_id == "macd_cross":
        return [
            _apply_sell_slippage(
                {
                "class": MacdCrossSell,
                "fast_period": _param_int(config, "fast_period", 12),
                "slow_period": _param_int(config, "slow_period", 26),
                "signal_period": _param_int(config, "signal_period", 9),
                }
            )
        ]

    raise ValueError(f"Unknown sell strategy: {strategy_id}")


__all__ = [name for name in globals().keys() if not name.startswith("__")]

