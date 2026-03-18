from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, Union

from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_, func, not_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from . import models, schemas


def _dedupe_rows(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for row in rows:
        key = tuple(row.get(k) for k in keys)
        if any(item in (None, "") for item in key):
            continue
        seen[key] = row
    return list(seen.values())


def _market_filter(model, markets: Optional[list[str]]):
    if not markets:
        return None
    pred = model.market.in_(markets)
    if "300" in markets:
        pred = and_(
            pred,
            or_(
                model.market != "300",
                model.symbol.ilike("sz30%"),
            ),
        )
    if "300" in markets and "SZ" not in markets:
        pred = or_(pred, and_(model.market == "SZ", model.symbol.ilike("sz30%")))
    return pred


def _ml_market_scope(market: Optional[str]) -> list[str]:
    key = str(market or "CN").upper()
    if key in {"CN", "ALL", "A"}:
        return ["SH", "SZ", "300"]
    return [key]


def _non_index_symbol_pred(model):
    return not_(
        or_(
            model.symbol.ilike("sh000%"),
            model.symbol.ilike("sz399%"),
        )
    )


def _json_safe_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe_value(item) for item in value]
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return _json_safe_value(value.item())
        except Exception:
            pass
    if hasattr(value, "isoformat") and callable(getattr(value, "isoformat")):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def create_quant_job(db: Session, payload: schemas.QuantJobCreate) -> models.QuantJob:
    job = models.QuantJob(type=payload.type, params=payload.params, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _quant_job_id(job: Union[models.QuantJob, int]) -> int:
    return int(job.id if hasattr(job, "id") else job)


def _current_quant_job(db: Session, job: Union[models.QuantJob, int]) -> Optional[models.QuantJob]:
    return db.get(models.QuantJob, _quant_job_id(job))


def get_quant_job(db: Session, job_id: int) -> Optional[models.QuantJob]:
    return db.get(models.QuantJob, job_id)


def list_quant_jobs(db: Session, limit: int = 50) -> list[models.QuantJob]:
    result = db.execute(select(models.QuantJob).order_by(models.QuantJob.id.desc()).limit(limit))
    return result.scalars().all()


def set_quant_job_running(db: Session, job: Union[models.QuantJob, int]) -> Optional[models.QuantJob]:
    current = _current_quant_job(db, job)
    if not current or current.status not in {"queued", "running"}:
        return current
    current.status = "running"
    db.add(current)
    db.commit()
    db.refresh(current)
    return current


def set_quant_job_result(db: Session, job: Union[models.QuantJob, int], result: dict) -> Optional[models.QuantJob]:
    current = _current_quant_job(db, job)
    if not current or current.status in {"failed", "cancelled"}:
        return current
    current.status = "succeeded"
    current.result = _json_safe_value(result)
    current.error = None
    db.add(current)
    db.commit()
    db.refresh(current)
    return current


def touch_quant_job(
    db: Session,
    job: Union[models.QuantJob, int],
    *,
    status: Optional[str] = None,
) -> Optional[models.QuantJob]:
    current = _current_quant_job(db, job)
    if not current or current.status in {"failed", "cancelled", "succeeded"}:
        return current
    if status:
        current.status = status
    current.updated_at = datetime.now(timezone.utc)
    db.add(current)
    db.commit()
    db.refresh(current)
    return current


def set_quant_job_error(
    db: Session,
    job: Union[models.QuantJob, int],
    error: str,
    *,
    overwrite_terminal: bool = False,
    terminal_status: str = "failed",
) -> Optional[models.QuantJob]:
    current = _current_quant_job(db, job)
    if not current:
        return None
    if not overwrite_terminal and current.status in {"succeeded", "failed", "cancelled"}:
        return current
    current.status = terminal_status
    current.error = error
    if terminal_status != "succeeded":
        current.result = None
    db.add(current)
    db.commit()
    db.refresh(current)
    return current


def cancel_quant_job(db: Session, job: Union[models.QuantJob, int], error: str = "Job cancelled") -> Optional[models.QuantJob]:
    return set_quant_job_error(
        db,
        job,
        error,
        overwrite_terminal=False,
        terminal_status="cancelled",
    )


def delete_quant_job(db: Session, job: Union[models.QuantJob, int]) -> None:
    current = _current_quant_job(db, job)
    if not current:
        return
    db.delete(current)
    db.commit()


def search_stock_symbols(
    db: Session,
    markets: Optional[list[str]],
    query: Optional[str],
    kind: Optional[str],
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[models.StockSymbol], int]:
    filters = []
    stmt = select(models.StockSymbol)
    if markets:
        market_pred = _market_filter(models.StockSymbol, markets)
        if market_pred is not None:
            filters.append(market_pred)
        prefix_filters = []
        if "SH" in markets:
            prefix_filters.append(models.StockSymbol.symbol.ilike("sh%"))
        if "SZ" in markets:
            if "300" in markets:
                prefix_filters.append(models.StockSymbol.symbol.ilike("sz%"))
            else:
                prefix_filters.append(
                    and_(
                        models.StockSymbol.symbol.ilike("sz%"),
                        not_(models.StockSymbol.symbol.ilike("sz30%")),
                    )
                )
        if "300" in markets:
            prefix_filters.append(models.StockSymbol.symbol.ilike("sz30%"))
        if prefix_filters:
            filters.append(or_(*prefix_filters))
    if query:
        cleaned = query.strip()
        if cleaned.isdigit():
            filters.append(models.StockSymbol.symbol.ilike(f"%{cleaned}%"))
        else:
            like = f"%{cleaned}%"
            filters.append(
                (models.StockSymbol.symbol.ilike(like))
                | (models.StockSymbol.name.ilike(like))
            )
    if kind and kind != "all":
        name = func.coalesce(models.StockSymbol.name, "")
        industry = func.coalesce(models.StockSymbol.industry, "")
        index_pred = or_(
            name.ilike("%指数%"),
            industry.ilike("%指数%"),
            models.StockSymbol.symbol.ilike("sh000%"),
            models.StockSymbol.symbol.ilike("sz399%"),
        )
        if kind == "index":
            filters.append(index_pred)
        elif kind == "stock":
            filters.append(not_(index_pred))
            if markets:
                if "SH" in markets:
                    filters.append(
                        or_(
                            models.StockSymbol.symbol.ilike("sh6%"),
                            models.StockSymbol.symbol.ilike("sh9%"),
                        )
                    )
                if "SZ" in markets:
                    filters.append(
                        or_(
                            models.StockSymbol.symbol.ilike("sz0%"),
                            models.StockSymbol.symbol.ilike("sz2%"),
                        )
                    )
                if "300" in markets and "SZ" not in markets:
                    filters.append(models.StockSymbol.symbol.ilike("sz30%"))
    if filters:
        stmt = stmt.where(*filters)
    total_stmt = select(func.count()).select_from(models.StockSymbol)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = db.execute(total_stmt).scalar_one()
    offset = max(0, (page - 1) * page_size)
    stmt = stmt.order_by(models.StockSymbol.symbol).offset(offset).limit(page_size)
    result = db.execute(stmt)
    return result.scalars().all(), int(total)


def search_stock_symbols_from_klines(
    db: Session,
    markets: Optional[list[str]],
    query: Optional[str],
    kind: Optional[str],
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[tuple[str, str]], int]:
    filters = []
    stmt = select(models.StockKline.market, models.StockKline.symbol).distinct()
    if markets:
        market_pred = _market_filter(models.StockKline, markets)
        if market_pred is not None:
            filters.append(market_pred)
        prefix_filters = []
        if "SH" in markets:
            prefix_filters.append(models.StockKline.symbol.ilike("sh%"))
        if "SZ" in markets:
            if "300" in markets:
                prefix_filters.append(models.StockKline.symbol.ilike("sz%"))
            else:
                prefix_filters.append(
                    and_(
                        models.StockKline.symbol.ilike("sz%"),
                        not_(models.StockKline.symbol.ilike("sz30%")),
                    )
                )
        if "300" in markets:
            prefix_filters.append(models.StockKline.symbol.ilike("sz30%"))
        if prefix_filters:
            filters.append(or_(*prefix_filters))
    if query:
        cleaned = query.strip()
        if cleaned:
            like = f"%{cleaned}%"
            filters.append(models.StockKline.symbol.ilike(like))
    if kind and kind != "all":
        index_pred = or_(
            models.StockKline.symbol.ilike("sh000%"),
            models.StockKline.symbol.ilike("sz399%"),
        )
        if kind == "index":
            filters.append(index_pred)
        elif kind == "stock":
            filters.append(not_(index_pred))
            if markets:
                if "SH" in markets:
                    filters.append(
                        or_(
                            models.StockKline.symbol.ilike("sh6%"),
                            models.StockKline.symbol.ilike("sh9%"),
                        )
                    )
                if "SZ" in markets:
                    filters.append(
                        or_(
                            models.StockKline.symbol.ilike("sz0%"),
                            models.StockKline.symbol.ilike("sz2%"),
                        )
                    )
                if "300" in markets and "SZ" not in markets:
                    filters.append(models.StockKline.symbol.ilike("sz30%"))
    if filters:
        stmt = stmt.where(*filters)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(total_stmt).scalar_one()
    offset = max(0, (page - 1) * page_size)
    stmt = stmt.order_by(models.StockKline.symbol).offset(offset).limit(page_size)
    result = db.execute(stmt)
    return result.all(), int(total)


def get_stock_symbol(db: Session, market: str, symbol: str) -> Optional[models.StockSymbol]:
    stmt = select(models.StockSymbol).where(
        models.StockSymbol.market == market, models.StockSymbol.symbol == symbol
    )
    result = db.execute(stmt)
    return result.scalars().first()


def list_stock_symbols(db: Session, market: str) -> list[models.StockSymbol]:
    stmt = select(models.StockSymbol).where(models.StockSymbol.market == market).order_by(models.StockSymbol.symbol)
    result = db.execute(stmt)
    return result.scalars().all()


def list_stock_symbols_by_markets(
    db: Session,
    markets: list[str],
    *,
    include_indices: bool = False,
) -> list[models.StockSymbol]:
    if not markets:
        return []
    stmt = select(models.StockSymbol).where(models.StockSymbol.market.in_(markets))
    if not include_indices:
        stmt = stmt.where(
            not_(
                or_(
                    models.StockSymbol.symbol.ilike("sh000%"),
                    models.StockSymbol.symbol.ilike("sz399%"),
                )
            )
        )
    stmt = stmt.order_by(models.StockSymbol.symbol)
    result = db.execute(stmt)
    return result.scalars().all()


def list_kline_symbols_by_markets(
    db: Session,
    markets: list[str],
    *,
    min_rows: int = 120,
    limit: int = 300,
    include_indices: bool = False,
) -> list[str]:
    market_pred = _market_filter(models.StockKline, markets)
    if market_pred is None:
        return []
    stmt = select(
        models.StockKline.symbol,
        func.count(models.StockKline.id).label("row_count"),
        func.max(models.StockKline.trade_date).label("latest_trade_date"),
    ).where(market_pred)
    if not include_indices:
        stmt = stmt.where(
            not_(
                or_(
                    models.StockKline.symbol.ilike("sh000%"),
                    models.StockKline.symbol.ilike("sz399%"),
                )
            )
        )
    stmt = (
        stmt
        .group_by(models.StockKline.symbol)
        .having(func.count(models.StockKline.id) >= max(1, int(min_rows)))
        .order_by(
            func.max(models.StockKline.trade_date).desc(),
            func.count(models.StockKline.id).desc(),
            models.StockKline.symbol.asc(),
        )
        .limit(max(1, int(limit)))
    )
    result = db.execute(stmt)
    return [str(row.symbol).strip() for row in result.all() if str(row.symbol or "").strip()]


def has_stock_symbols(db: Session, market: str) -> bool:
    stmt = select(models.StockSymbol.id).where(models.StockSymbol.market == market).limit(1)
    result = db.execute(stmt).scalar_one_or_none()
    return result is not None


def has_stock_symbols_any(db: Session, markets: list[str]) -> bool:
    if not markets:
        return False
    stmt = select(models.StockSymbol.id).where(models.StockSymbol.market.in_(markets)).limit(1)
    result = db.execute(stmt).scalar_one_or_none()
    return result is not None


def repair_cn_market_mislabels(db: Session) -> dict:
    # Legacy compatibility repair:
    # older rules classified all `sz3xxxxx` symbols as market=300,
    # which accidentally moved Shenzhen index symbols like sz399xxx
    # into the 300 market. We normalize them back to SZ.
    repaired = {}
    table_specs = [
        ("stock_symbols", models.StockSymbol),
        ("stock_klines", models.StockKline),
        ("ml_feature_snapshots", models.MLFeatureSnapshot),
        ("ml_predictions", models.MLPrediction),
    ]
    for name, table in table_specs:
        stmt = (
            update(table)
            .where(
                table.market == "300",
                table.symbol.ilike("sz399%"),
            )
            .values(market="SZ")
        )
        result = db.execute(stmt)
        repaired[name] = int(result.rowcount or 0)
    db.commit()
    repaired["total"] = int(sum(repaired.values()))
    return repaired


def upsert_stock_symbols(db: Session, rows: list[dict]) -> int:
    rows = _dedupe_rows(rows, ("market", "symbol"))
    if not rows:
        return 0
    stmt = pg_insert(models.StockSymbol).values(rows)
    update_cols = {
        col.name: getattr(stmt.excluded, col.name)
        for col in models.StockSymbol.__table__.columns
        if col.name not in {"id", "created_at"}
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["market", "symbol"],
        set_=update_cols,
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


def upsert_stock_klines(db: Session, rows: list[dict]) -> int:
    rows = _dedupe_rows(rows, ("market", "symbol", "trade_date"))
    if not rows:
        return 0
    stmt = pg_insert(models.StockKline).values(rows)
    update_cols = {
        col.name: getattr(stmt.excluded, col.name)
        for col in models.StockKline.__table__.columns
        if col.name not in {"id", "created_at"}
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["market", "symbol", "trade_date"],
        set_=update_cols,
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


def load_klines(
    db: Session,
    market: str,
    symbol: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> list[models.StockKline]:
    stmt = select(models.StockKline).where(
        models.StockKline.market == market,
        models.StockKline.symbol == symbol,
    )
    if start:
        stmt = stmt.where(models.StockKline.trade_date >= start)
    if end:
        stmt = stmt.where(models.StockKline.trade_date <= end)
    stmt = stmt.order_by(models.StockKline.trade_date)
    result = db.execute(stmt)
    return result.scalars().all()


def upsert_ml_feature_rows(db: Session, rows: list[dict]) -> int:
    rows = _dedupe_rows(rows, ("market", "symbol", "trade_date", "feature_version"))
    if not rows:
        return 0
    stmt = pg_insert(models.MLFeatureSnapshot).values(rows)
    update_cols = {
        col.name: getattr(stmt.excluded, col.name)
        for col in models.MLFeatureSnapshot.__table__.columns
        if col.name not in {"id", "created_at"}
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["market", "symbol", "trade_date", "feature_version"],
        set_=update_cols,
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


def list_ml_feature_snapshots(
    db: Session,
    market: str,
    feature_version: str = "v1",
    symbols: Optional[list[str]] = None,
    limit: int = 200000,
    include_indices: bool = False,
) -> list[models.MLFeatureSnapshot]:
    markets = _ml_market_scope(market)
    stmt = select(models.MLFeatureSnapshot).where(
        models.MLFeatureSnapshot.market.in_(markets),
        models.MLFeatureSnapshot.feature_version == feature_version,
    )
    if not include_indices:
        stmt = stmt.where(_non_index_symbol_pred(models.MLFeatureSnapshot))
    if symbols:
        stmt = stmt.where(models.MLFeatureSnapshot.symbol.in_(symbols))
    stmt = stmt.order_by(models.MLFeatureSnapshot.trade_date.desc()).limit(max(1, limit))
    result = db.execute(stmt)
    return result.scalars().all()


def list_latest_ml_feature_snapshots(
    db: Session,
    market: str,
    feature_version: str = "v1",
    symbols: Optional[list[str]] = None,
    limit: int = 500,
    include_indices: bool = False,
) -> list[models.MLFeatureSnapshot]:
    markets = _ml_market_scope(market)
    base_filters = [
        models.MLFeatureSnapshot.market.in_(markets),
        models.MLFeatureSnapshot.feature_version == feature_version,
    ]
    if not include_indices:
        base_filters.append(_non_index_symbol_pred(models.MLFeatureSnapshot))
    if symbols:
        base_filters.append(models.MLFeatureSnapshot.symbol.in_(symbols))

    subq = (
        select(
            models.MLFeatureSnapshot.symbol.label("symbol"),
            func.max(models.MLFeatureSnapshot.trade_date).label("trade_date"),
        )
        .where(*base_filters)
        .group_by(models.MLFeatureSnapshot.symbol)
        .subquery()
    )

    stmt = (
        select(models.MLFeatureSnapshot)
        .join(
            subq,
            and_(
                models.MLFeatureSnapshot.symbol == subq.c.symbol,
                models.MLFeatureSnapshot.trade_date == subq.c.trade_date,
            ),
        )
        .where(*base_filters)
        .order_by(models.MLFeatureSnapshot.trade_date.desc(), models.MLFeatureSnapshot.symbol.asc())
        .limit(max(1, limit))
    )
    result = db.execute(stmt)
    return result.scalars().all()


def create_ml_model(db: Session, payload: dict) -> models.MLModel:
    model = models.MLModel(**payload)
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def list_ml_models(
    db: Session,
    market: Optional[str] = None,
    target: Optional[str] = None,
    limit: int = 100,
) -> list[models.MLModel]:
    stmt = select(models.MLModel)
    if market:
        stmt = stmt.where(models.MLModel.market == market)
    if target:
        stmt = stmt.where(models.MLModel.target == target)
    stmt = stmt.order_by(models.MLModel.id.desc()).limit(max(1, limit))
    result = db.execute(stmt)
    return result.scalars().all()


def get_ml_model(db: Session, model_id: int) -> Optional[models.MLModel]:
    return db.get(models.MLModel, model_id)


def get_active_ml_model(db: Session, market: str, target: str = "y_up_5d") -> Optional[models.MLModel]:
    stmt = (
        select(models.MLModel)
        .where(
            models.MLModel.market == market,
            models.MLModel.target == target,
            models.MLModel.is_active.is_(True),
        )
        .order_by(models.MLModel.id.desc())
        .limit(1)
    )
    result = db.execute(stmt)
    return result.scalars().first()


def set_ml_model_active(db: Session, model: models.MLModel) -> models.MLModel:
    # deactivate same market+target active models first
    stmt = select(models.MLModel).where(
        models.MLModel.market == model.market,
        models.MLModel.target == model.target,
        models.MLModel.is_active.is_(True),
    )
    for item in db.execute(stmt).scalars().all():
        item.is_active = False
        db.add(item)

    model.is_active = True
    model.status = "active"
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def upsert_ml_predictions(db: Session, rows: list[dict]) -> int:
    rows = _dedupe_rows(rows, ("model_id", "symbol", "trade_date"))
    if not rows:
        return 0
    stmt = pg_insert(models.MLPrediction).values(rows)
    update_cols = {
        col.name: getattr(stmt.excluded, col.name)
        for col in models.MLPrediction.__table__.columns
        if col.name not in {"id", "created_at"}
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["model_id", "symbol", "trade_date"],
        set_=update_cols,
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


def list_latest_ml_predictions(
    db: Session,
    market: str,
    model_id: Optional[int] = None,
    limit: int = 100,
    include_indices: bool = False,
) -> list[models.MLPrediction]:
    markets = _ml_market_scope(market)
    stmt = select(models.MLPrediction).where(models.MLPrediction.market.in_(markets))
    if not include_indices:
        stmt = stmt.where(_non_index_symbol_pred(models.MLPrediction))
    if model_id:
        stmt = stmt.where(models.MLPrediction.model_id == model_id)
    stmt = stmt.order_by(models.MLPrediction.trade_date.desc(), models.MLPrediction.score_up_5d.desc()).limit(max(1, limit))
    result = db.execute(stmt)
    return result.scalars().all()
