import json
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from . import crud
from .quant_base import *
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

    with _suppress_numeric_warnings(), _with_market_env(market):
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
            index_values = list(kl.close.index)

            def _index_to_date_str(idx: int) -> Optional[str]:
                if idx < 0 or idx >= len(index_values):
                    return None
                value = index_values[idx]
                if hasattr(value, "strftime"):
                    return value.strftime("%Y-%m-%d")
                return str(value)

            x_start_idx = 0
            x_end_idx = len(tl.tl) - 1
            x_start = _index_to_date_str(x_start_idx) or x_start_idx
            x_end = _index_to_date_str(x_end_idx) or x_end_idx
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
                            "x_start_idx": x_start_idx,
                            "x_end_idx": x_end_idx,
                            "y_start": y_start,
                            "y_end": y_end,
                        }
                    )
            signal = None
            try:
                last_close = float(kl.close.iloc[-1])
                last_idx = len(kl.close) - 1

                def _line_value_at(line_item, idx):
                    x0 = int(line_item.get("x_start_idx", 0))
                    x1 = int(line_item.get("x_end_idx", 0))
                    y0 = float(line_item.get("y_start", 0))
                    y1 = float(line_item.get("y_end", 0))
                    if x1 == x0:
                        return y1
                    slope = (y1 - y0) / (x1 - x0)
                    return y0 + slope * (idx - x0)

                supports = []
                resistances = []
                for item in trend_lines:
                    value = _line_value_at(item, last_idx)
                    if item.get("type") == "support":
                        supports.append(value)
                    elif item.get("type") == "resistance":
                        resistances.append(value)
                support = max([v for v in supports if v <= last_close], default=None)
                resistance = min([v for v in resistances if v >= last_close], default=None)

                near_threshold = 0.01
                breakout_threshold = 0.015
                action = "hold"
                reason = "No strong signal"
                if resistance and last_close > resistance * (1 + breakout_threshold):
                    action = "breakout"
                    reason = "Price breaks above resistance"
                elif support and last_close < support * (1 - breakout_threshold):
                    action = "breakdown"
                    reason = "Price breaks below support"
                elif support and (last_close - support) / support <= near_threshold:
                    action = "near_support"
                    reason = "Price is near support"
                elif resistance and (resistance - last_close) / resistance <= near_threshold:
                    action = "near_resistance"
                    reason = "Price is near resistance"

                atr = None
                for col in ("atr14", "atr21"):
                    if col in kl.columns:
                        value = kl[col].iloc[-1]
                        if value is not None:
                            atr = float(value)
                            if atr > 0:
                                break
                if atr is None or atr <= 0:
                    if {"high", "low"}.issubset(kl.columns):
                        atr = float((kl.high - kl.low).tail(14).mean())
                stop_loss = None
                take_profit = None
                if atr and atr > 0:
                    stop_loss = last_close - 1.5 * atr
                    take_profit = last_close + 3.0 * atr

                signal = {
                    "action": action,
                    "reason": reason,
                    "last_close": last_close,
                    "support": support,
                    "resistance": resistance,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                }
            except Exception:
                signal = None
            return {
                "tool": tool,
                "symbol": symbol,
                "trend_lines": trend_lines,
                "signal": signal,
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





