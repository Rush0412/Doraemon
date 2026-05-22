from __future__ import annotations

from statistics import fmean
from typing import Any, Optional

from . import schemas


KNOWN_FEATURE_KEYS = {
    "trade_date",
    "close",
    "volume",
    "ma5",
    "ma20",
    "rsi14",
    "macd",
}


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_to_feature_map(row: schemas.TrendFeatureRow) -> dict[str, Any]:
    payload = row.model_dump(exclude_none=True)
    extras = getattr(row, "model_extra", None) or {}
    payload.update(extras)
    return payload


def _numeric_feature_summary(feature_rows: list[schemas.TrendFeatureRow]) -> dict[str, dict[str, float]]:
    numeric_map: dict[str, list[float]] = {}
    for row in feature_rows:
        for key, value in _row_to_feature_map(row).items():
            if key == "trade_date":
                continue
            numeric = _safe_float(value)
            if numeric is None:
                continue
            numeric_map.setdefault(key, []).append(numeric)

    summary = {}
    for key, values in numeric_map.items():
        summary[key] = {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "avg": round(fmean(values), 4),
        }
    return summary


def _infer_direction(feature_rows: list[schemas.TrendFeatureRow]) -> dict[str, Any]:
    if not feature_rows:
        return {
            "direction": "pending_data",
            "confidence": 0.32,
            "score": 0.0,
            "signals": ["未提供结构化特征，当前仅完成上传链路 Demo 校验。"],
        }

    last_row = feature_rows[-1]
    last_close = _safe_float(last_row.close)
    ma5 = _safe_float(last_row.ma5)
    ma20 = _safe_float(last_row.ma20)
    rsi14 = _safe_float(last_row.rsi14)
    macd = _safe_float(last_row.macd)

    score = 0.0
    reasons: list[str] = []
    if last_close is not None and ma5 is not None:
        if last_close >= ma5:
            score += 1.2
            reasons.append("最新收盘价位于 MA5 上方")
        else:
            score -= 1.2
            reasons.append("最新收盘价跌破 MA5")
    if ma5 is not None and ma20 is not None:
        if ma5 >= ma20:
            score += 1.1
            reasons.append("短期均线保持在中期均线之上")
        else:
            score -= 1.1
            reasons.append("短期均线弱于中期均线")
    if rsi14 is not None:
        if 52 <= rsi14 <= 72:
            score += 0.8
            reasons.append("RSI 处于偏强但未过热区间")
        elif rsi14 >= 75:
            score -= 0.5
            reasons.append("RSI 偏高，需警惕回撤")
        elif rsi14 <= 35:
            score -= 0.8
            reasons.append("RSI 偏弱，趋势修复尚未确认")
    if macd is not None:
        if macd >= 0:
            score += 0.7
            reasons.append("MACD 处于零轴上方")
        else:
            score -= 0.7
            reasons.append("MACD 仍位于零轴下方")

    if score >= 1.6:
        direction = "bullish"
    elif score <= -1.2:
        direction = "bearish"
    else:
        direction = "neutral"

    confidence = min(0.92, max(0.38, 0.5 + abs(score) * 0.08))
    return {
        "direction": direction,
        "confidence": round(confidence, 2),
        "score": round(score, 2),
        "signals": reasons or ["特征不足，建议补充均线、动量和量能因子。"],
    }


def build_trend_analysis_demo(payload: schemas.TrendAnalysisDemoPayload) -> dict[str, Any]:
    feature_rows = payload.feature_rows or []
    feature_maps = [_row_to_feature_map(row) for row in feature_rows]
    date_points = [row.get("trade_date") for row in feature_maps if row.get("trade_date")]
    direction = _infer_direction(feature_rows)
    feature_columns = sorted(
        {
            key
            for row in feature_maps
            for key in row.keys()
            if key != "trade_date"
        }
    )

    direction_actions = {
        "bullish": "可进入候选观察池，等待量价确认后执行回测或策略验证。",
        "neutral": "建议补充更多特征或延长观察窗口，再触发正式预测流程。",
        "bearish": "当前偏弱，建议转入风险提示或反向策略观察，不直接给出买入建议。",
        "pending_data": "已完成 Demo 链路校验，需补充结构化特征后再评估。",
    }

    return {
        "demo_mode": True,
        "symbol": payload.symbol,
        "market": payload.market,
        "forecast_horizon_days": payload.horizon_days,
        "chart_upload": {
            "attached": bool(payload.chart_image_name),
            "name": payload.chart_image_name,
            "mime_type": payload.chart_image_type,
            "size_kb": payload.chart_image_size_kb,
        },
        "feature_summary": {
            "rows": len(feature_rows),
            "date_range": {
                "start": date_points[0] if date_points else None,
                "end": date_points[-1] if date_points else None,
            },
            "feature_columns": feature_columns,
            "numeric_overview": _numeric_feature_summary(feature_rows),
        },
        "analysis": direction,
        "recommendation": {
            "action": direction_actions[direction["direction"]],
            "note": payload.note,
        },
        "architecture": {
            "module": "trend-analysis-demo",
            "data_contract_version": "v1",
            "supported_inputs": [
                "chart_image_metadata",
                "feature_rows_json",
                "symbol_market_context",
            ],
            "next_stage_capabilities": [
                "接入真实图片上传与对象存储",
                "衔接特征工程流水线与模型推理服务",
                "输出可解释的未来走势评分、置信度和风险标签",
            ],
        },
        "quality_checks": [
            "前端已预留图片上传、特征录入和结果面板。",
            "后端接口已形成标准契约，可平滑替换为真实模型推理。",
            "当前 Demo 不做投资建议，仅用于架构联调与流程验证。",
        ],
    }


def run_trend_analysis_demo(payload: schemas.TrendAnalysisDemoPayload) -> schemas.APIResponse:
    return schemas.APIResponse(message="Trend analysis demo ready", data=build_trend_analysis_demo(payload))
