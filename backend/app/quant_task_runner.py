from . import crud
from .database import SessionLocal
from .quant_analysis_service import _run_analysis_job
from .quant_ml_pipeline import run_ml_feature_job, run_ml_predict_job, run_ml_train_job
from .quant_ml_stock_select import run_ml_stock_select_job
import json
from datetime import datetime

from .quant_base import *
def _run_job(job_id: int):
    db = SessionLocal()
    try:
        job = crud.get_quant_job(db, job_id)
        if not job:
            return
        job = crud.set_quant_job_running(db, job)
        if not job:
            return

        if job.type == "kl_update":
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
                    kl = _load_symbol_kl_df(symbol, start=start, end=end, n_folds=n_folds)
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

            market = (job.params.get("market") or "CN").upper()
            symbols = _normalize_symbols(job.params.get("symbols"), market, fallback_default=False)
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
            buy_strategy = (job.params.get("buy_strategy") or "breakout").strip().lower()
            sell_strategy = (job.params.get("sell_strategy") or "atr_stop").strip().lower()
            _validate_strategy_list([buy_strategy], "buy")
            _validate_strategy_list([sell_strategy], "sell")
            buy_factors = _build_buy_factors(job.params)
            sell_factors = _build_sell_factors(job.params)
            fallback_symbol = benchmark_symbol
            with _with_pg_data_env(market), _with_benchmark_fallback(fallback_symbol):
                abu_result, _ = abu.run_loop_back(
                    read_cash=job.params.get("cash", 1000000),
                    buy_factors=buy_factors,
                    sell_factors=sell_factors,
                    choice_symbols=available_symbols,
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
                "buy_strategy": buy_strategy,
                "sell_strategy": sell_strategy,
                "buy_params": _params_dict(job.params.get("buy_params")),
                "sell_params": _params_dict(job.params.get("sell_params")),
                "orders_rows": int(getattr(abu_result.orders_pd, "shape", [0])[0]),
                "actions_rows": int(getattr(abu_result.action_pd, "shape", [0])[0]),
                "benchmark": getattr(getattr(abu_result, "benchmark", None), "symbol", None),
            }
            orders_pd = getattr(abu_result, "orders_pd", None)
            summary.update(_summarize_orders(orders_pd))
            summary.update(_summarize_capital(getattr(abu_result, "capital", None)))
            top_symbols = _summarize_orders_by_symbol(orders_pd, top_n=10)
            equity_curve = _capital_curve_points(getattr(abu_result, "capital", None), limit=3000)
            orders_preview = None
            actions_preview = None
            if orders_pd is not None and hasattr(orders_pd, "head") and hasattr(orders_pd, "to_json"):
                import pandas as pd

                orders_safe = orders_pd.copy()
                orders_safe["buy_date_int"] = pd.to_numeric(orders_safe.get("buy_date"), errors="coerce").fillna(0).astype(int)
                orders_safe["sell_date_int"] = pd.to_numeric(orders_safe.get("sell_date"), errors="coerce").fillna(0).astype(int)
                try:
                    sell_params = _params_dict(job.params.get("sell_params"))
                    stop_loss_n = _safe_float(sell_params.get("stop_loss_n"))
                    if stop_loss_n is None:
                        stop_loss_n = _safe_float(job.params.get("stop_loss_n"))
                    if stop_loss_n is None:
                        stop_loss_n = 0.5
                    stop_win_n = _safe_float(sell_params.get("stop_win_n"))
                    if stop_win_n is None:
                        stop_win_n = _safe_float(job.params.get("stop_win_n"))
                    if stop_win_n is None:
                        stop_win_n = 3.0
                    symbols_orders = orders_safe["symbol"].dropna().unique().tolist() if "symbol" in orders_safe else []
                    for sym in symbols_orders:
                        sym_orders = orders_safe[orders_safe["symbol"] == sym]
                        if sym_orders.empty:
                            continue
                        min_date = int(sym_orders["buy_date_int"].min())
                        max_date = int(sym_orders["buy_date_int"].max())
                        if min_date <= 0 or max_date <= 0:
                            continue
                        start_date = datetime.strptime(str(min_date), "%Y%m%d").date()
                        end_date = datetime.strptime(str(max_date), "%Y%m%d").date()
                        rows = crud.load_klines(db, _market_from_symbol(sym), sym, start=start_date, end=end_date)
                        atr_map = {
                            int(row.trade_date.strftime("%Y%m%d")): (row.atr14, row.atr21)
                            for row in rows
                        }
                        for idx in sym_orders.index:
                            buy_date = int(orders_safe.at[idx, "buy_date_int"] or 0)
                            if buy_date <= 0:
                                continue
                            atr14, atr21 = atr_map.get(buy_date, (None, None))
                            if atr14 is None and atr21 is None:
                                continue
                            atr_base = 0.0
                            if atr14 is not None:
                                atr_base += float(atr14)
                            if atr21 is not None:
                                atr_base += float(atr21)
                            if atr_base <= 0:
                                continue
                            buy_price = float(orders_safe.at[idx, "buy_price"] or 0)
                            expect_direction = orders_safe.at[idx, "expect_direction"] or 1
                            direction = 1 if float(expect_direction) >= 0 else -1
                            if direction >= 0:
                                orders_safe.at[idx, "stop_loss_price"] = buy_price - stop_loss_n * atr_base
                                orders_safe.at[idx, "stop_win_price"] = buy_price + stop_win_n * atr_base
                            else:
                                orders_safe.at[idx, "stop_loss_price"] = buy_price + stop_loss_n * atr_base
                                orders_safe.at[idx, "stop_win_price"] = buy_price - stop_win_n * atr_base
                            orders_safe.at[idx, "atr_base"] = atr_base
                except Exception:
                    # keep raw orders if enrichment failed
                    pass
                try:
                    preview_limit = int(job.params.get("orders_preview_limit", 2000))
                except Exception:
                    preview_limit = 2000
                preview_limit = max(200, min(preview_limit, 10000))
                if "buy_date_int" in orders_safe.columns:
                    orders_safe = orders_safe.sort_values("buy_date_int")
                if len(orders_safe) > preview_limit:
                    # Preserve both early and recent trades for chart marker/history checks.
                    head_size = max(100, int(preview_limit * 0.35))
                    tail_size = max(100, preview_limit - head_size)
                    orders_safe = pd.concat(
                        [orders_safe.head(head_size), orders_safe.tail(tail_size)],
                        axis=0,
                    )
                    if "buy_date_int" in orders_safe.columns:
                        orders_safe = orders_safe.sort_values("buy_date_int")
                orders_json = orders_safe.to_json(orient="records", date_format="iso")
                orders_preview = json.loads(orders_json)
            try:
                action_pd = getattr(abu_result, "action_pd", None)
                if action_pd is not None and hasattr(action_pd, "head") and hasattr(action_pd, "to_json"):
                    try:
                        action_limit = int(job.params.get("actions_preview_limit", 2000))
                    except Exception:
                        action_limit = 2000
                    action_limit = max(200, min(action_limit, 10000))
                    actions_json = action_pd.tail(action_limit).to_json(orient="records", date_format="iso")
                    actions_preview = json.loads(actions_json)
            except Exception:
                actions_preview = None

            result = {"summary": summary}
            if top_symbols:
                result["top_symbols"] = top_symbols
                result["actionable_candidates"] = _build_actionable_candidates(
                    db=db,
                    top_symbols=top_symbols,
                    market=market,
                    mode="平衡",
                    limit=min(10, len(top_symbols)),
                )
            if equity_curve:
                result["equity_curve"] = equity_curve
            if orders_preview is not None:
                result["orders"] = orders_preview
            if actions_preview is not None:
                result["actions"] = actions_preview
            crud.set_quant_job_result(db, job, result)
            return

        if job.type == "grid_search":
            from abupy import abu

            market = (job.params.get("market") or "CN").upper()
            symbols = _normalize_symbols(job.params.get("symbols"), market, fallback_default=False)
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

            buy_strategy = (job.params.get("buy_strategy") or "breakout").strip().lower()
            sell_strategy = (job.params.get("sell_strategy") or "atr_stop").strip().lower()
            buy_strategy_list = _normalize_strategy_list(job.params.get("buy_strategies"), buy_strategy)
            sell_strategy_list = _normalize_strategy_list(job.params.get("sell_strategies"), sell_strategy)
            buy_strategy_list = list(dict.fromkeys(buy_strategy_list))
            sell_strategy_list = list(dict.fromkeys(sell_strategy_list))
            _validate_strategy_list(buy_strategy_list, "buy")
            _validate_strategy_list(sell_strategy_list, "sell")

            buy_params_grid = job.params.get("buy_params_grid") or {}
            sell_params_grid = job.params.get("sell_params_grid") or {}

            if "xd" not in buy_params_grid and job.params.get("buy_xd_list"):
                buy_params_grid["xd"] = job.params.get("buy_xd_list")
            if "stop_loss_n" not in sell_params_grid and job.params.get("stop_loss_n_list"):
                sell_params_grid["stop_loss_n"] = job.params.get("stop_loss_n_list")
            if "stop_win_n" not in sell_params_grid and job.params.get("stop_win_n_list"):
                sell_params_grid["stop_win_n"] = job.params.get("stop_win_n_list")
            max_runs = int(job.params.get("max_runs", 50))
            max_runs = max(1, min(max_runs, 5000))
            ranking_metric = (job.params.get("ranking_metric") or "profit").strip().lower()
            ranking_weights = job.params.get("ranking_weights") or {}

            runs = []
            run_errors = []
            validation_mode = (job.params.get("validation_mode") or "none").strip().lower()
            train_ratio = float(job.params.get("train_ratio", 0.7))
            walk_forward_days = int(job.params.get("walk_forward_days", 365))
            walk_forward_step_days = int(job.params.get("walk_forward_step_days", 180))
            validation_slices = []
            if validation_mode in {"holdout", "walk_forward"}:
                start_date, end_date = _resolve_date_bounds(db, symbols, start, end, n_folds)
                if start_date and end_date:
                    if validation_mode == "holdout":
                        split = _split_holdout(start_date, end_date, train_ratio)
                        if split:
                            validation_slices = [split]
                    else:
                        validation_slices = _walk_forward_slices(
                            start_date, end_date, train_ratio, walk_forward_days, walk_forward_step_days
                        )
            fallback_symbol = benchmark_symbol
            total_candidates = 0
            tested_runs = 0
            with _with_pg_data_env(market), _with_benchmark_fallback(fallback_symbol):
                pairs = [(bs, ss) for bs in buy_strategy_list for ss in sell_strategy_list]
                if not pairs:
                    pairs = [(buy_strategy, sell_strategy)]
                run_index = 0
                for buy_strategy, sell_strategy in pairs:
                    buy_defaults = _find_strategy_defaults(buy_strategy, "buy")
                    buy_grid_filtered = _filter_param_grid(buy_strategy, "buy", buy_params_grid)
                    buy_param_sets = _build_param_grid(buy_defaults, buy_grid_filtered)
                    sell_defaults = _find_strategy_defaults(sell_strategy, "sell")
                    sell_grid_filtered = _filter_param_grid(sell_strategy, "sell", sell_params_grid)
                    sell_param_sets = _build_param_grid(sell_defaults, sell_grid_filtered)
                    total_candidates += len(buy_param_sets) * len(sell_param_sets)
                    for buy_params in buy_param_sets:
                        for sell_params in sell_param_sets:
                            if run_index >= max_runs:
                                break
                            combo_params = dict(job.params)
                            combo_params["buy_strategy"] = buy_strategy
                            combo_params["sell_strategy"] = sell_strategy
                            combo_params["buy_params"] = buy_params
                            combo_params["sell_params"] = sell_params
                            run_index += 1
                            tested_runs += 1
                            try:
                                buy_factors = _build_buy_factors(combo_params)
                                sell_factors = _build_sell_factors(combo_params)
                                summary = {
                                    "buy_strategy": buy_strategy,
                                    "sell_strategy": sell_strategy,
                                    "buy_params": buy_params,
                                    "sell_params": sell_params,
                                    "buy_xd": buy_params.get("xd"),
                                    "stop_loss_n": sell_params.get("stop_loss_n"),
                                    "stop_win_n": sell_params.get("stop_win_n"),
                                    "benchmark": benchmark_symbol,
                                    "validation_mode": validation_mode if validation_slices else "none",
                                }
                                if validation_slices:
                                    train_summaries = []
                                    validation_summaries = []
                                    for train_start, train_end, val_start, val_end in validation_slices:
                                        try:
                                            train_result, _ = abu.run_loop_back(
                                                read_cash=cash,
                                                buy_factors=buy_factors,
                                                sell_factors=sell_factors,
                                                choice_symbols=symbols,
                                                n_folds=n_folds,
                                                start=train_start.isoformat(),
                                                end=train_end.isoformat(),
                                                n_process_kl=1,
                                                n_process_pick=1,
                                            )
                                            if train_result is not None:
                                                train_summaries.append(_summarize_run(train_result))
                                            val_result, _ = abu.run_loop_back(
                                                read_cash=cash,
                                                buy_factors=buy_factors,
                                                sell_factors=sell_factors,
                                                choice_symbols=symbols,
                                                n_folds=n_folds,
                                                start=val_start.isoformat(),
                                                end=val_end.isoformat(),
                                                n_process_kl=1,
                                                n_process_pick=1,
                                            )
                                            if val_result is not None:
                                                validation_summaries.append(_summarize_run(val_result))
                                        except Exception as slice_exc:
                                            if len(run_errors) < 30:
                                                run_errors.append(
                                                    {
                                                        "stage": "validation_slice",
                                                        "buy_strategy": buy_strategy,
                                                        "sell_strategy": sell_strategy,
                                                        "buy_params": buy_params,
                                                        "sell_params": sell_params,
                                                        "message": str(slice_exc),
                                                    }
                                                )
                                            continue
                                    if not train_summaries and not validation_summaries:
                                        continue
                                    train_summary = _aggregate_summaries(train_summaries)
                                    validation_summary = _aggregate_summaries(validation_summaries)
                                    summary.update(_prefix_summary(train_summary, "train_"))
                                    summary.update(_prefix_summary(validation_summary, "validation_"))
                                    summary["train_runs"] = len(train_summaries)
                                    summary["validation_runs"] = len(validation_summaries)
                                    summary["orders_rows"] = int(
                                        summary.get("validation_closed_orders", 0) + summary.get("validation_open_orders", 0)
                                    )
                                    summary["actions_rows"] = 0
                                else:
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
                                    summary["benchmark"] = getattr(getattr(abu_result, "benchmark", None), "symbol", None)
                                    summary.update(_summarize_run(abu_result))
                                    summary["orders_rows"] = int(
                                        summary.get("closed_orders", 0) + summary.get("open_orders", 0)
                                    )
                                    summary["actions_rows"] = int(getattr(abu_result.action_pd, "shape", [0])[0])
                                summary["custom_score"] = _calc_custom_score(summary, ranking_weights)
                                runs.append(summary)
                            except Exception as combo_exc:
                                if len(run_errors) < 30:
                                    run_errors.append(
                                        {
                                            "stage": "combo",
                                            "buy_strategy": buy_strategy,
                                            "sell_strategy": sell_strategy,
                                            "buy_params": buy_params,
                                            "sell_params": sell_params,
                                            "message": str(combo_exc),
                                        }
                                    )
                                continue
                        if run_index >= max_runs:
                            break
                    if run_index >= max_runs:
                        break

            sort_key = _choose_grid_sort_key(ranking_metric, ranking_weights)
            runs_sorted = sorted(runs, key=sort_key, reverse=True)
            best = runs_sorted[0] if runs_sorted else None
            runs_by_win = sorted(runs, key=_grid_win_key, reverse=True)
            best_win = runs_by_win[0] if runs_by_win else None
            symbol_top_n = max(1, min(int(job.params.get("symbol_top_n", 10)), 50))
            symbol_eval_limit = max(5, min(int(job.params.get("symbol_eval_limit", 120)), 500))
            top_symbols = []
            symbol_eval_meta = {}
            recommendation = {}
            actionable_candidates = []
            best_for_symbol = best_win or best
            if best_for_symbol:
                best_params = dict(job.params)
                best_params["buy_strategy"] = best_for_symbol.get("buy_strategy")
                best_params["sell_strategy"] = best_for_symbol.get("sell_strategy")
                best_params["buy_params"] = best_for_symbol.get("buy_params") or {}
                best_params["sell_params"] = best_for_symbol.get("sell_params") or {}
                try:
                    best_buy_factors = _build_buy_factors(best_params)
                    best_sell_factors = _build_sell_factors(best_params)
                    symbol_eval = _evaluate_symbols_for_run(
                        abu=abu,
                        symbols=symbols,
                        cash=cash,
                        buy_factors=best_buy_factors,
                        sell_factors=best_sell_factors,
                        n_folds=n_folds,
                        start=start,
                        end=end,
                        top_n=symbol_top_n,
                        eval_limit=symbol_eval_limit,
                    )
                    top_symbols = symbol_eval.get("top") or []
                    symbol_eval_meta = {
                        "evaluated": symbol_eval.get("evaluated", 0),
                        "available": symbol_eval.get("available", 0),
                        "truncated": bool(symbol_eval.get("truncated")),
                    }
                except Exception:
                    top_symbols = []
                    symbol_eval_meta = {}
                recommendation = _build_strategy_recommendation(best_for_symbol, top_symbols)
                try:
                    actionable_candidates = _build_actionable_candidates(
                        db=db,
                        top_symbols=top_symbols,
                        market=market,
                        mode=recommendation.get("mode", "平衡"),
                        limit=symbol_top_n,
                    )
                except Exception:
                    actionable_candidates = []

            diagnostics = {
                "candidate_runs": int(total_candidates),
                "tested_runs": int(tested_runs),
                "max_runs": int(max_runs),
                "fully_tested": bool(total_candidates <= max_runs and tested_runs >= total_candidates),
                "truncated": bool(total_candidates > max_runs),
                "pair_count": int(len(pairs)),
                "error_count": int(len(run_errors)),
            }
            next_param_suggestions = _build_next_param_suggestions(best_win or best)
            crud.set_quant_job_result(
                db,
                job,
                {
                    "market": market,
                    "symbols": symbols,
                    "buy_strategy": buy_strategy,
                    "sell_strategy": sell_strategy,
                    "buy_strategies": buy_strategy_list,
                    "sell_strategies": sell_strategy_list,
                    "validation_mode": validation_mode if validation_slices else "none",
                    "validation_slices": len(validation_slices),
                    "train_ratio": train_ratio,
                    "walk_forward_days": walk_forward_days,
                    "walk_forward_step_days": walk_forward_step_days,
                    "max_runs": max_runs,
                    "ranking_metric": ranking_metric,
                    "ranking_weights": ranking_weights,
                    "diagnostics": diagnostics,
                    "best": best,
                    "best_by_win_rate": best_win,
                    "recommendation": recommendation,
                    "symbol_eval": symbol_eval_meta,
                    "top_symbols": top_symbols,
                    "actionable_candidates": actionable_candidates,
                    "next_param_suggestions": next_param_suggestions,
                    "errors": run_errors,
                    "runs": runs_sorted[:200],
                },
            )
            return

        if job.type == "stock_select":
            from abupy import abu

            market = (job.params.get("market") or "CN").upper()
            cash = job.params.get("cash", 1000000)
            n_folds = job.params.get("n_folds", 1)
            start = job.params.get("start")
            end = job.params.get("end")
            buy_strategy = (job.params.get("buy_strategy") or "breakout").strip().lower()
            sell_strategy = (job.params.get("sell_strategy") or "atr_stop").strip().lower()
            _validate_strategy_list([buy_strategy], "buy")
            _validate_strategy_list([sell_strategy], "sell")

            requested_symbols = _normalize_symbols(job.params.get("symbols"), market, fallback_default=False)
            all_symbols_raw = job.params.get("all_symbols", False)
            if isinstance(all_symbols_raw, str):
                all_symbols = all_symbols_raw.strip().lower() in {"1", "true", "yes", "y"}
            else:
                all_symbols = bool(all_symbols_raw)
            candidate_limit = max(20, min(int(job.params.get("candidate_limit", 300)), 5000))
            symbol_top_n = max(1, min(int(job.params.get("symbol_top_n", 10)), 50))
            symbol_eval_limit = max(10, min(int(job.params.get("symbol_eval_limit", candidate_limit)), 500))
            min_kline_rows = max(60, min(int(job.params.get("min_kline_rows", 120)), 2000))

            symbols = list(dict.fromkeys(requested_symbols))
            used_all_symbols = False
            if all_symbols:
                symbols = _load_candidate_symbols_from_db(db, market, limit=max(candidate_limit, symbol_eval_limit))
                used_all_symbols = True
            if not symbols:
                raise RuntimeError("No symbols specified for stock select.")
            symbols = symbols[: max(candidate_limit, symbol_eval_limit)]

            available_symbols = []
            missing_symbols = []
            start_date = _parse_date_str(start)
            end_date = _parse_date_str(end)
            for symbol in symbols:
                rows = crud.load_klines(db, _market_from_symbol(symbol), symbol, start=start_date, end=end_date)
                if len(rows) >= min_kline_rows:
                    available_symbols.append(symbol)
                else:
                    missing_symbols.append(symbol)
            if not available_symbols:
                raise RuntimeError(
                    "No kline data available for stock select symbols; try kl_update first or widen date range."
                )

            params_with_strategy = dict(job.params)
            params_with_strategy["buy_strategy"] = buy_strategy
            params_with_strategy["sell_strategy"] = sell_strategy
            buy_factors = _build_buy_factors(params_with_strategy)
            sell_factors = _build_sell_factors(params_with_strategy)

            fallback_symbol = available_symbols[0]
            with _with_pg_data_env(market), _with_benchmark_fallback(fallback_symbol):
                symbol_eval = _evaluate_symbols_for_run(
                    abu=abu,
                    symbols=available_symbols,
                    cash=cash,
                    buy_factors=buy_factors,
                    sell_factors=sell_factors,
                    n_folds=n_folds,
                    start=start,
                    end=end,
                    top_n=symbol_top_n,
                    eval_limit=symbol_eval_limit,
                )

            top_symbols = symbol_eval.get("top") or []
            base_summary = {
                "market": market,
                "buy_strategy": buy_strategy,
                "sell_strategy": sell_strategy,
                "buy_params": _params_dict(job.params.get("buy_params")),
                "sell_params": _params_dict(job.params.get("sell_params")),
            }
            summary_metrics = _summary_from_ranked_symbols(top_symbols, base_summary)
            recommendation = _build_strategy_recommendation(summary_metrics, top_symbols)
            actionable_candidates = _build_actionable_candidates(
                db=db,
                top_symbols=top_symbols,
                market=market,
                mode=recommendation.get("mode", "平衡"),
                limit=symbol_top_n,
            )

            summary = {
                **summary_metrics,
                "requested_symbols": len(symbols),
                "available_symbols": len(available_symbols),
                "missing_symbols": len(missing_symbols),
                "evaluated_symbols": int(symbol_eval.get("evaluated", 0) or 0),
                "top_n": len(top_symbols),
                "all_symbols_mode": used_all_symbols,
                "candidate_limit": candidate_limit,
                "eval_limit": symbol_eval_limit,
                "start": start,
                "end": end,
                "n_folds": n_folds,
            }
            diagnostics = {
                "requested_symbols": len(symbols),
                "available_symbols": len(available_symbols),
                "missing_symbols": len(missing_symbols),
                "evaluated_symbols": int(symbol_eval.get("evaluated", 0) or 0),
                "truncated": bool(symbol_eval.get("truncated")),
                "all_symbols_mode": used_all_symbols,
                "candidate_limit": candidate_limit,
                "eval_limit": symbol_eval_limit,
                "min_kline_rows": min_kline_rows,
            }
            crud.set_quant_job_result(
                db,
                job,
                {
                    "summary": summary,
                    "diagnostics": diagnostics,
                    "recommendation": recommendation,
                    "top_symbols": top_symbols,
                    "actionable_candidates": actionable_candidates,
                    "missing_symbols": missing_symbols[:200],
                },
            )
            return

        if job.type == "analysis":
            result = _run_analysis_job(job.params, db)
            crud.set_quant_job_result(db, job, result)
            return

        if job.type == "ml_feature":
            result = run_ml_feature_job(job.params or {}, db)
            crud.set_quant_job_result(db, job, result)
            return

        if job.type == "ml_train":
            result = run_ml_train_job(job.params or {}, db)
            crud.set_quant_job_result(db, job, result)
            return

        if job.type == "ml_predict":
            result = run_ml_predict_job(job.params or {}, db)
            crud.set_quant_job_result(db, job, result)
            return

        if job.type == "ml_stock_select":
            result = run_ml_stock_select_job(job.params or {}, db, job_id=job.id)
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

