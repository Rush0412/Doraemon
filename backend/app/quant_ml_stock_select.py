from typing import Optional

from sqlalchemy.orm import Session

from . import crud
from .quant_backtest_utils import (
    _build_actionable_candidates,
    _build_buy_factors,
    _build_sell_factors,
    _build_strategy_recommendation,
    _evaluate_symbols_for_run,
    _summary_from_ranked_symbols,
)
from .quant_core_utils import _params_dict, _validate_strategy_list
from .quant_data_utils import _market_from_symbol, _parse_date_str, _with_benchmark_fallback, _with_pg_data_env
from .quant_ml_model_utils import (
    is_composite_market_request,
    ml_model_scope,
    ml_model_symbol_count,
    market_symbol_universe_count,
    recommended_market_model_min_symbol_count,
    resolve_best_ml_model,
    resolve_market_model_bundle,
    score_latest_features_for_model,
    score_latest_features_for_model_bundle,
)


def _normalize_action_set(raw_actions) -> set[str]:
    if not raw_actions:
        return {"buy", "light_buy"}
    if isinstance(raw_actions, str):
        raw_actions = [part.strip() for part in raw_actions.split(",")]
    return {str(item).strip().lower() for item in raw_actions if str(item).strip()}


def _sort_prediction_dicts(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda item: (
            float(item.get("score_up_5d", 0.0) or 0.0),
            float(item.get("expected_ret_5d", 0.0) or 0.0),
        ),
        reverse=True,
    )


def _is_index_symbol(symbol: str) -> bool:
    lower = str(symbol or "").strip().lower()
    if not lower:
        return False
    return lower.startswith("sh000") or lower.startswith("sz399")


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _effective_quant_eval_limit(*, symbol_eval_limit: int, candidate_count: int, full_market_scan: bool) -> int:
    if candidate_count <= 0:
        return 0
    if full_market_scan:
        if int(symbol_eval_limit or 0) <= 0:
            return int(candidate_count)
        return max(10, min(int(symbol_eval_limit), int(candidate_count)))
    return max(10, min(int(symbol_eval_limit), int(candidate_count)))


def _empty_select_result(
    *,
    model_summary: dict,
    market: str,
    target: str,
    prediction_limit: int,
    candidate_limit: int,
    n_folds: int,
    start,
    end,
    diagnostics: dict,
    ml_candidates: Optional[list[dict]] = None,
    missing_symbols: Optional[list[str]] = None,
    warning: Optional[str] = None,
):
    summary = {
        **(model_summary or {}),
        "market": market,
        "target": target,
        "prediction_limit": prediction_limit,
        "candidate_limit": candidate_limit,
        "ml_candidates": len(ml_candidates or []),
        "available_symbols": 0,
        "missing_symbols": len(missing_symbols or []),
        "evaluated_symbols": 0,
        "buy_candidates": 0,
        "symbol_top_n": 0,
        "start": start,
        "end": end,
        "n_folds": n_folds,
        "warning": warning,
    }
    recommendation = {
        "mode": "wait",
        "action": "wait",
        "reason": warning or "No actionable ML + quant candidates found.",
    }
    return {
        "summary": summary,
        "diagnostics": diagnostics,
        "recommendation": recommendation,
        "ml_candidates": ml_candidates or [],
        "top_symbols": [],
        "actionable_candidates": [],
        "buy_candidates": [],
        "missing_symbols": (missing_symbols or [])[:200],
    }


def _model_summary_from_single(model_row) -> dict:
    market_key = str(model_row.market or "").strip().upper()
    symbol_count = ml_model_symbol_count(model_row)
    return {
        "model_id": model_row.id,
        "model_name": model_row.name,
        "model_scope": ml_model_scope(model_row),
        "model_symbol_count": symbol_count,
        "model_ids": {market_key: int(model_row.id)} if market_key else {},
        "model_names": {market_key: model_row.name} if market_key else {},
        "model_symbol_counts": {market_key: symbol_count} if market_key else {},
    }


def _model_summary_from_bundle(model_rows_by_market: dict[str, object]) -> dict:
    model_ids = {}
    model_names = {}
    model_symbol_counts = {}
    total_symbol_count = 0
    for market_key, model_row in (model_rows_by_market or {}).items():
        count = int(ml_model_symbol_count(model_row) or 0)
        model_ids[market_key] = int(model_row.id)
        model_names[market_key] = model_row.name
        model_symbol_counts[market_key] = count
        total_symbol_count += count
    return {
        "model_id": None,
        "model_name": "composite_market_bundle",
        "model_scope": "composite_market",
        "model_symbol_count": total_symbol_count or None,
        "model_ids": model_ids,
        "model_names": model_names,
        "model_symbol_counts": model_symbol_counts,
    }


def run_ml_stock_select_job(job_params: dict, db: Session, *, job_id: Optional[int] = None) -> dict:
    from abupy import abu

    market = (job_params.get("market") or "CN").upper()
    target = str(job_params.get("target") or "y_up_5d")
    min_kline_rows = max(60, min(int(job_params.get("min_kline_rows", 120)), 2000))
    raw_symbols = job_params.get("symbols")
    requested_model_id = job_params.get("model_id")
    requested_symbols = set()
    if raw_symbols:
        from .quant_base import _normalize_symbols

        requested_symbols = set(_normalize_symbols(raw_symbols, market, fallback_default=False))
    market_wide_mode = not requested_symbols

    request_markets = crud.ml_market_scope(market)
    universe_count = market_symbol_universe_count(db, market, min_rows=min_kline_rows)
    min_market_model_symbols_by_market = {
        market_key: (
            recommended_market_model_min_symbol_count(db, market_key, min_rows=min_kline_rows)
            if market_wide_mode
            else 0
        )
        for market_key in request_markets
    }
    min_market_model_symbols = sum(min_market_model_symbols_by_market.values())

    full_market_scan = _as_bool(job_params.get("full_market_scan"), default=market_wide_mode)
    include_indices = _as_bool(job_params.get("include_indices"), default=False)
    allowed_actions = _normalize_action_set(job_params.get("allowed_actions"))
    min_score = max(0.0, min(float(job_params.get("min_score", 0.55)), 1.0))
    min_expected_ret = job_params.get("min_expected_ret_5d")
    min_expected_ret = None if min_expected_ret is None else float(min_expected_ret)
    max_limit_cap = 50000
    prediction_limit = max(20, min(int(job_params.get("prediction_limit", 300)), max_limit_cap))
    candidate_limit = max(10, min(int(job_params.get("candidate_limit", 120)), max_limit_cap))
    symbol_top_n = max(1, min(int(job_params.get("symbol_top_n", 20)), 100))
    symbol_eval_limit = max(10, min(int(job_params.get("symbol_eval_limit", candidate_limit)), max_limit_cap))
    if market_wide_mode and full_market_scan:
        prediction_limit = min(max_limit_cap, max(prediction_limit, universe_count, 2000))
        candidate_limit = min(max_limit_cap, max(candidate_limit, universe_count, 2000))
        symbol_eval_limit = min(max_limit_cap, max(symbol_eval_limit, candidate_limit))
    cash = job_params.get("cash", 1000000)
    n_folds = job_params.get("n_folds", 1)
    start = job_params.get("start")
    end = job_params.get("end")

    buy_strategy = (job_params.get("buy_strategy") or "breakout").strip().lower()
    sell_strategy = (job_params.get("sell_strategy") or "atr_stop").strip().lower()
    _validate_strategy_list([buy_strategy], "buy")
    _validate_strategy_list([sell_strategy], "sell")

    scoring_limit = max(prediction_limit, candidate_limit, symbol_eval_limit)
    if market_wide_mode and full_market_scan:
        scoring_limit = max(scoring_limit, universe_count)

    model_warning = None
    model_errors = {}
    bundle_mode = bool(is_composite_market_request(market) and not requested_model_id)
    if is_composite_market_request(market) and requested_model_id:
        raise RuntimeError(
            f"Composite market request {market} cannot pin a single model_id={requested_model_id}. "
            "Clear model_id to use the default SH/SZ/300 market models, or choose a concrete market."
        )
    if bundle_mode:
        model_rows_by_market, model_errors = resolve_market_model_bundle(
            db,
            market=market,
            target=target,
            require_market_scope=market_wide_mode,
            min_rows=min_kline_rows,
            attempt_repair=True,
        )
        model_summary = _model_summary_from_bundle(model_rows_by_market)
        scoring = score_latest_features_for_model_bundle(
            db,
            model_rows_by_market=model_rows_by_market,
            market=market,
            target=target,
            symbols=raw_symbols,
            limit=scoring_limit,
            persist=True,
        )
        if model_errors:
            model_warning = (
                "Skipped markets without a qualified model: "
                + ", ".join(f"{key} ({value})" for key, value in sorted(model_errors.items()))
            )
    else:
        model_row = resolve_best_ml_model(
            db,
            market=market,
            target=target,
            model_id=requested_model_id,
            require_market_scope=market_wide_mode,
            min_symbol_count=(
                min_market_model_symbols_by_market.get(market, 0)
                if market_wide_mode
                else 0
            ),
            allow_fallback_to_best=bool(market_wide_mode and not requested_model_id),
            attempt_repair=True,
        )
        model_summary = _model_summary_from_single(model_row)
        scoring = score_latest_features_for_model(
            db,
            model_row=model_row,
            market=market,
            target=target,
            symbols=raw_symbols,
            limit=scoring_limit,
            persist=True,
        )
        if requested_model_id and int(requested_model_id) != int(model_row.id):
            model_warning = (
                f"Requested model {requested_model_id} is not suitable for market-wide selection; "
                f"automatically switched to best available market model {model_row.id}."
            )

    prediction_dicts = _sort_prediction_dicts(scoring["predictions"])
    if not prediction_dicts:
        raise RuntimeError("No ML predictions found. Run ml_feature/ml_train first.")

    filtered_predictions = []
    for item in prediction_dicts:
        symbol = str(item.get("symbol") or "").strip()
        if requested_symbols and symbol not in requested_symbols:
            continue
        if not include_indices and _is_index_symbol(symbol):
            continue
        action = str(item.get("action") or "").strip().lower()
        score = float(item.get("score_up_5d") or 0.0)
        expected_ret = float(item.get("expected_ret_5d") or 0.0)
        if allowed_actions and action not in allowed_actions:
            continue
        if score < min_score:
            continue
        if min_expected_ret is not None and expected_ret < min_expected_ret:
            continue
        filtered_predictions.append(dict(item))

    filter_mode = "strict"
    filter_warning = None
    if not filtered_predictions:
        filter_mode = "fallback_relaxed_score"
        filter_warning = "No rows met the strict ML score filter; falling back to the highest-score buy/light_buy candidates."
        for item in prediction_dicts:
            symbol = str(item.get("symbol") or "").strip()
            if requested_symbols and symbol not in requested_symbols:
                continue
            if not include_indices and _is_index_symbol(symbol):
                continue
            action = str(item.get("action") or "").strip().lower()
            if allowed_actions and action not in allowed_actions:
                continue
            expected_ret = float(item.get("expected_ret_5d") or 0.0)
            if min_expected_ret is not None and expected_ret < min_expected_ret:
                continue
            filtered_predictions.append(dict(item))

    sorted_predictions = _sort_prediction_dicts(filtered_predictions)
    if market_wide_mode and full_market_scan:
        ml_candidates = sorted_predictions
    else:
        ml_candidates = sorted_predictions[:candidate_limit]
    effective_eval_limit = _effective_quant_eval_limit(
        symbol_eval_limit=symbol_eval_limit,
        candidate_count=len(ml_candidates),
        full_market_scan=bool(market_wide_mode and full_market_scan),
    )
    diagnostics = {
        "allowed_actions": sorted(allowed_actions),
        "min_score": min_score,
        "min_expected_ret_5d": min_expected_ret,
        "prediction_limit": prediction_limit,
        "candidate_limit": candidate_limit,
        "scoring_limit": scoring_limit,
        "effective_candidate_count": len(ml_candidates),
        "eval_limit": symbol_eval_limit,
        "effective_eval_limit": effective_eval_limit,
        "min_kline_rows": min_kline_rows,
        "filter_mode": filter_mode,
        "filter_warning": filter_warning,
        "rows_scored": scoring["rows_scored"],
        "rows_upserted": scoring["rows_upserted"],
        "feature_version": scoring.get("feature_version"),
        "feature_versions": scoring.get("feature_versions") or {},
        "model_scope": model_summary.get("model_scope"),
        "model_symbol_count": model_summary.get("model_symbol_count"),
        "market_model_ready": bool(model_summary.get("model_ids")) and not bool(model_errors),
        "min_market_model_symbols": min_market_model_symbols,
        "min_market_model_symbols_by_market": min_market_model_symbols_by_market,
        "market_universe_symbols": universe_count,
        "market_wide_mode": market_wide_mode,
        "full_market_scan": bool(market_wide_mode and full_market_scan),
        "include_indices": include_indices,
        "requested_model_id": requested_model_id,
        "selected_model_id": model_summary.get("model_id"),
        "selected_model_ids": model_summary.get("model_ids", {}),
        "models_by_market": scoring.get("models_by_market") or {},
        "missing_model_markets": sorted(model_errors),
    }
    if model_warning:
        diagnostics["model_warning"] = model_warning
    if not ml_candidates:
        return _empty_select_result(
            model_summary=model_summary,
            market=market,
            target=target,
            prediction_limit=prediction_limit,
            candidate_limit=candidate_limit,
            n_folds=n_folds,
            start=start,
            end=end,
            diagnostics=diagnostics,
            warning="No buy/light_buy ML candidates are available for the current market/model.",
        )

    candidate_symbols = [row["symbol"] for row in ml_candidates[:effective_eval_limit]]
    available_symbols = []
    missing_symbols = []
    start_date = _parse_date_str(start)
    end_date = _parse_date_str(end)
    for symbol in candidate_symbols:
        rows = crud.load_klines(db, _market_from_symbol(symbol), symbol, start=start_date, end=end_date)
        if len(rows) >= min_kline_rows:
            available_symbols.append(symbol)
        else:
            missing_symbols.append(symbol)

    if not available_symbols:
        return _empty_select_result(
            model_summary=model_summary,
            market=market,
            target=target,
            prediction_limit=prediction_limit,
            candidate_limit=candidate_limit,
            n_folds=n_folds,
            start=start,
            end=end,
            diagnostics=diagnostics,
            ml_candidates=ml_candidates,
            missing_symbols=missing_symbols,
            warning="ML candidates do not have sufficient kline data. Run kl_update or widen the date range.",
        )

    params_with_strategy = dict(job_params)
    params_with_strategy["buy_strategy"] = buy_strategy
    params_with_strategy["sell_strategy"] = sell_strategy
    buy_factors = _build_buy_factors(params_with_strategy)
    sell_factors = _build_sell_factors(params_with_strategy)

    def progress_cb(done: int, total: int):
        diagnostics["progress"] = {"done": int(done), "total": int(total)}
        if job_id:
            crud.touch_quant_job(db, job_id, status="running")

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
            eval_limit=effective_eval_limit,
            progress_cb=progress_cb,
            run_kwargs={"commission_dict": _build_commission_dict(params_with_strategy)},
            summary_params=params_with_strategy,
        )

    prediction_map = {row["symbol"]: row for row in ml_candidates}
    top_symbols = []
    for item in symbol_eval.get("top") or []:
        merged = dict(item)
        prediction = prediction_map.get(str(item.get("symbol") or "").strip(), {})
        if prediction:
            merged.update(prediction)
            merged["trade_date"] = (
                prediction.get("trade_date").isoformat()
                if hasattr(prediction.get("trade_date"), "isoformat")
                else prediction.get("trade_date")
            )
        top_symbols.append(merged)

    base_summary = {
        "market": market,
        "buy_strategy": buy_strategy,
        "sell_strategy": sell_strategy,
        "buy_params": _params_dict(job_params.get("buy_params")),
        "sell_params": _params_dict(job_params.get("sell_params")),
        "trade_costs": _trade_cost_config(params_with_strategy),
    }
    summary_metrics = _summary_from_ranked_symbols(top_symbols, base_summary)
    recommendation = _build_strategy_recommendation(summary_metrics, top_symbols)
    actionable_candidates = _build_actionable_candidates(
        db=db,
        top_symbols=top_symbols,
        market=market,
        mode=recommendation.get("mode", "balanced"),
        limit=symbol_top_n,
    )

    buy_candidates = []
    for item in actionable_candidates:
        symbol = str(item.get("symbol") or "").strip()
        prediction = prediction_map.get(symbol, {})
        quant_action_code = str(item.get("action_code") or "").strip().lower()
        ml_action = str(prediction.get("action") or "").strip().lower()
        if allowed_actions and ml_action not in allowed_actions:
            continue
        if quant_action_code not in {"breakout_buy", "pullback_buy"}:
            continue
        combined = dict(item)
        combined["ml_action"] = prediction.get("action")
        combined["score_up_5d"] = prediction.get("score_up_5d")
        combined["expected_ret_5d"] = prediction.get("expected_ret_5d")
        combined["risk_mdd_10d"] = prediction.get("risk_mdd_10d")
        combined["trade_date"] = (
            prediction.get("trade_date").isoformat()
            if hasattr(prediction.get("trade_date"), "isoformat")
            else prediction.get("trade_date")
        )
        combined["combined_score"] = float(item.get("score", 0.0) or 0.0) + float(
            prediction.get("score_up_5d", 0.0) or 0.0
        ) * 1000.0
        buy_candidates.append(combined)
    buy_candidates = sorted(
        buy_candidates,
        key=lambda item: (
            float(item.get("score_up_5d", 0.0) or 0.0),
            float(item.get("combined_score", 0.0) or 0.0),
            float(item.get("win_rate", 0.0) or 0.0),
            float(item.get("profit_sum", 0.0) or 0.0),
        ),
        reverse=True,
    )
    buy_candidate_symbols = {str(item.get("symbol") or "").strip() for item in buy_candidates}
    candidate_symbols_set = set(candidate_symbols)
    available_symbols_set = set(available_symbols)
    missing_symbols_set = set(missing_symbols)
    top_symbols_map = {str(item.get("symbol") or "").strip(): item for item in top_symbols}
    actionable_map = {str(item.get("symbol") or "").strip(): item for item in actionable_candidates}
    excluded_ml_candidates = []
    for prediction in sorted_predictions[: min(max(candidate_limit, symbol_top_n), 20)]:
        symbol = str(prediction.get("symbol") or "").strip()
        if not symbol or symbol in buy_candidate_symbols:
            continue
        reason_code = "not_selected"
        reason_text = "未进入当前联动选股结果。"
        quant_action = None
        if symbol not in candidate_symbols_set:
            reason_code = "outside_eval_scope"
            reason_text = "ML 排名靠前，但未进入本次量化评估范围。可提高候选池或评估上限。"
        elif symbol in missing_symbols_set:
            reason_code = "insufficient_kline"
            reason_text = "ML 信号较强，但K线不足，未进入量化评估。"
        elif symbol not in available_symbols_set:
            reason_code = "quant_data_unavailable"
            reason_text = "未获得可用量化评估数据。"
        elif symbol not in top_symbols_map:
            reason_code = "not_in_quant_top"
            reason_text = "已通过ML筛选并完成量化评估，但在当前策略下未进入量化 TopN。"
        elif symbol in actionable_map:
            quant_action = str(actionable_map[symbol].get("action_code") or "").strip().lower() or None
            reason_code = f"quant_gate:{quant_action or 'unknown'}"
            reason_text = str(actionable_map[symbol].get("reason") or "量化动作未达到买入条件。").strip()
        excluded_ml_candidates.append(
            {
                "symbol": symbol,
                "ml_action": prediction.get("action"),
                "score_up_5d": prediction.get("score_up_5d"),
                "expected_ret_5d": prediction.get("expected_ret_5d"),
                "reason_code": reason_code,
                "reason": reason_text,
                "quant_action": actionable_map.get(symbol, {}).get("action") if symbol in actionable_map else None,
                "quant_action_code": quant_action,
            }
        )

    summary = {
        **summary_metrics,
        **model_summary,
        "target": target,
        "prediction_limit": prediction_limit,
        "candidate_limit": candidate_limit,
        "ml_candidates": len(ml_candidates),
        "available_symbols": len(available_symbols),
        "missing_symbols": len(missing_symbols),
        "evaluated_symbols": int(symbol_eval.get("evaluated", 0) or 0),
        "buy_candidates": len(buy_candidates),
        "symbol_top_n": len(top_symbols),
        "full_market_scan": bool(market_wide_mode and full_market_scan),
        "start": start,
        "end": end,
        "n_folds": n_folds,
        "warning": diagnostics.get("model_warning"),
    }
    diagnostics["truncated"] = bool(symbol_eval.get("truncated"))
    ml_candidates_preview_limit = min(max(candidate_limit, symbol_top_n), 2000)
    return {
        "summary": summary,
        "diagnostics": diagnostics,
        "recommendation": recommendation,
        "ml_candidates": ml_candidates[:ml_candidates_preview_limit],
        "top_symbols": top_symbols,
        "actionable_candidates": actionable_candidates,
        "buy_candidates": buy_candidates[:symbol_top_n],
        "excluded_ml_candidates": excluded_ml_candidates,
        "missing_symbols": missing_symbols[:200],
    }
