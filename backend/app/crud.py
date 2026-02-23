from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_, func, not_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import date

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
    if "300" in markets and "SZ" not in markets:
        pred = or_(pred, and_(model.market == "SZ", model.symbol.ilike("sz3%")))
    return pred


def create_quant_job(db: Session, payload: schemas.QuantJobCreate) -> models.QuantJob:
    job = models.QuantJob(type=payload.type, params=payload.params, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_quant_job(db: Session, job_id: int) -> Optional[models.QuantJob]:
    return db.get(models.QuantJob, job_id)


def list_quant_jobs(db: Session, limit: int = 50) -> list[models.QuantJob]:
    result = db.execute(select(models.QuantJob).order_by(models.QuantJob.id.desc()).limit(limit))
    return result.scalars().all()


def set_quant_job_running(db: Session, job: models.QuantJob) -> models.QuantJob:
    job.status = "running"
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def set_quant_job_result(db: Session, job: models.QuantJob, result: dict) -> models.QuantJob:
    job.status = "succeeded"
    job.result = result
    job.error = None
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def set_quant_job_error(db: Session, job: models.QuantJob, error: str) -> models.QuantJob:
    job.status = "failed"
    job.error = error
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def delete_quant_job(db: Session, job: models.QuantJob) -> None:
    db.delete(job)
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
                        not_(models.StockSymbol.symbol.ilike("sz3%")),
                    )
                )
        if "300" in markets:
            prefix_filters.append(models.StockSymbol.symbol.ilike("sz3%"))
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
                    filters.append(models.StockSymbol.symbol.ilike("sz3%"))
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
                        not_(models.StockKline.symbol.ilike("sz3%")),
                    )
                )
        if "300" in markets:
            prefix_filters.append(models.StockKline.symbol.ilike("sz3%"))
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
                    filters.append(models.StockKline.symbol.ilike("sz3%"))
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


def list_stock_symbols_by_markets(db: Session, markets: list[str]) -> list[models.StockSymbol]:
    if not markets:
        return []
    stmt = select(models.StockSymbol).where(models.StockSymbol.market.in_(markets)).order_by(models.StockSymbol.symbol)
    result = db.execute(stmt)
    return result.scalars().all()


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
) -> list[models.MLFeatureSnapshot]:
    stmt = select(models.MLFeatureSnapshot).where(
        models.MLFeatureSnapshot.market == market,
        models.MLFeatureSnapshot.feature_version == feature_version,
    )
    if symbols:
        stmt = stmt.where(models.MLFeatureSnapshot.symbol.in_(symbols))
    stmt = stmt.order_by(models.MLFeatureSnapshot.trade_date.asc()).limit(max(1, limit))
    result = db.execute(stmt)
    return result.scalars().all()


def list_latest_ml_feature_snapshots(
    db: Session,
    market: str,
    feature_version: str = "v1",
    symbols: Optional[list[str]] = None,
    limit: int = 500,
) -> list[models.MLFeatureSnapshot]:
    base_filters = [
        models.MLFeatureSnapshot.market == market,
        models.MLFeatureSnapshot.feature_version == feature_version,
    ]
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
) -> list[models.MLPrediction]:
    stmt = select(models.MLPrediction).where(models.MLPrediction.market == market)
    if model_id:
        stmt = stmt.where(models.MLPrediction.model_id == model_id)
    stmt = stmt.order_by(models.MLPrediction.trade_date.desc(), models.MLPrediction.score_up_5d.desc()).limit(max(1, limit))
    result = db.execute(stmt)
    return result.scalars().all()
