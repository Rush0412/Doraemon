from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import csv
import io
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db, SessionLocal

router = APIRouter()
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])
quant_router = APIRouter(prefix="/quant", tags=["quant"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])

executor = ThreadPoolExecutor(max_workers=4)
logger = logging.getLogger("doraemon")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _market_csv_path(market: str) -> Path:
    key = market.upper()
    if key in {"CN", "SH", "SZ"}:
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


@tasks_router.get("/", response_model=schemas.APIResponse)
def list_tasks(db: Session = Depends(get_db)):
    tasks = crud.get_tasks(db)
    return schemas.APIResponse(data=[schemas.TaskRead.from_orm(task) for task in tasks])


@tasks_router.post("/", response_model=schemas.APIResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = crud.create_task(db, payload)
    return schemas.APIResponse(message="Task created", data=schemas.TaskRead.from_orm(task))


@tasks_router.get("/{task_id}", response_model=schemas.APIResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return schemas.APIResponse(data=schemas.TaskRead.from_orm(task))


@tasks_router.put("/{task_id}", response_model=schemas.APIResponse)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    task = crud.update_task(db, task, payload)
    return schemas.APIResponse(message="Task updated", data=schemas.TaskRead.from_orm(task))


@tasks_router.delete("/{task_id}", response_model=schemas.APIResponse)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    crud.delete_task(db, task)
    return schemas.APIResponse(message="Task deleted", data={"id": task_id})


@quant_router.get("/features", response_model=schemas.APIResponse)
def list_feature_map():
    data = {
        "legacy": [
            {"name": "股票基本信息查询", "source": "abupy_ui/widget_stock_info.py", "api": "/api/v1/quant/symbols"},
            {"name": "数据下载界面操作", "source": "abupy_ui/widget_update_ui.py", "api": "/api/v1/quant/kl/update"},
            {"name": "历史回测界面操作", "source": "abupy_ui/widget_loop_back.py", "api": "/api/v1/quant/backtest"},
            {"name": "参数最优交叉验证", "source": "abupy/WidgetBu/ABuWGGridSearch.py", "api": "/api/v1/jobs"},
            {"name": "量化分析工具", "source": "abupy_ui/widget_quant_tool.py", "api": "/api/v1/jobs"},
            {"name": "环境验证工具", "source": "abupy_ui/widget_verify_tool.py", "api": "/api/v1/quant/verify"},
        ],
        "phase_plan": [
            {"phase": 1, "scope": ["symbol search", "kl update", "backtest jobs", "job status sync"]},
            {"phase": 2, "scope": ["grid search jobs", "report export", "result persistence"]},
            {"phase": 3, "scope": ["strategy library", "fine-grained permissions", "audit logs"]},
        ],
    }
    return schemas.APIResponse(data=data)


@quant_router.get("/symbols", response_model=schemas.APIResponse)
def search_symbols(market: str = "CN", q: Optional[str] = None, limit: int = 50):
    limit = max(1, min(limit, 200))
    query = (q or "").strip().lower()
    items: list[schemas.SymbolRead] = []
    for row in _read_stock_rows(market):
        symbol = (row.get("symbol") or "").strip()
        name = (row.get("co_name") or "").strip()
        if not symbol:
            continue
        if query:
            if query not in symbol.lower() and query not in name.lower():
                continue
        items.append(
            schemas.SymbolRead(
                symbol=symbol,
                market=(row.get("market") or market).strip(),
                name=name or None,
                exchange=(row.get("exchange") or row.get("cc") or None),
                industry=(row.get("industry") or None),
            )
        )
        if len(items) >= limit:
            break
    return schemas.APIResponse(data=items)


@quant_router.get("/symbols/{symbol}", response_model=schemas.APIResponse)
def get_symbol(symbol: str, market: str = "CN"):
    want = symbol.strip().lower()
    for row in _read_stock_rows(market):
        sym = (row.get("symbol") or "").strip()
        if sym.lower() == want:
            return schemas.APIResponse(
                data=schemas.SymbolRead(
                    symbol=sym,
                    market=(row.get("market") or market).strip(),
                    name=(row.get("co_name") or "").strip() or None,
                    exchange=(row.get("exchange") or row.get("cc") or None),
                    industry=(row.get("industry") or None),
                )
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")


def _run_job(job_id: int):
    db = SessionLocal()
    try:
        job = crud.get_quant_job(db, job_id)
        if not job:
            return
        crud.set_quant_job_running(db, job)

        if job.type == "kl_update":
            from abupy import abu, EMarketTargetType

            market = (job.params.get("market") or "CN").upper()
            market_map = {
                "CN": EMarketTargetType.E_MARKET_TARGET_CN,
                "US": EMarketTargetType.E_MARKET_TARGET_US,
                "HK": EMarketTargetType.E_MARKET_TARGET_HK,
            }
            abu.run_kl_update(
                n_folds=job.params.get("n_folds", 1),
                start=job.params.get("start"),
                end=job.params.get("end"),
                market=market_map.get(market),
                n_jobs=job.params.get("n_jobs", 8),
                how=job.params.get("how", "thread"),
            )
            crud.set_quant_job_result(db, job, {"message": "kl_update finished"})
            return

        if job.type == "backtest":
            from abupy import abu, EMarketTargetType
            from abupy.FactorBuyBu import AbuFactorBuyBreak
            from abupy.FactorSellBu import AbuFactorAtrNStop

            market = (job.params.get("market") or "CN").upper()
            market_map = {
                "CN": EMarketTargetType.E_MARKET_TARGET_CN,
                "US": EMarketTargetType.E_MARKET_TARGET_US,
                "HK": EMarketTargetType.E_MARKET_TARGET_HK,
            }

            symbols = job.params.get("symbols") or ["usAAPL", "usTSLA"]
            buy_factors = [{"class": AbuFactorBuyBreak, "xd": job.params.get("buy_xd", 42)}]
            sell_factors = [
                {
                    "class": AbuFactorAtrNStop,
                    "stop_loss_n": job.params.get("stop_loss_n", 0.5),
                    "stop_win_n": job.params.get("stop_win_n", 3.0),
                }
            ]
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

            from abupy import abu, EMarketTargetType
            from abupy.FactorBuyBu import AbuFactorBuyBreak
            from abupy.FactorSellBu import AbuFactorAtrNStop

            market = (job.params.get("market") or "CN").upper()
            market_map = {
                "CN": EMarketTargetType.E_MARKET_TARGET_CN,
                "US": EMarketTargetType.E_MARKET_TARGET_US,
                "HK": EMarketTargetType.E_MARKET_TARGET_HK,
            }

            symbols = job.params.get("symbols") or ["usAAPL", "usTSLA"]
            cash = job.params.get("cash", 1000000)
            n_folds = job.params.get("n_folds", 1)
            start = job.params.get("start")
            end = job.params.get("end")

            buy_xd_list = job.params.get("buy_xd_list") or [20, 42, 60]
            stop_loss_n_list = job.params.get("stop_loss_n_list") or [0.5, 1.0]
            stop_win_n_list = job.params.get("stop_win_n_list") or [2.0, 3.0]
            max_runs = int(job.params.get("max_runs", 30))
            max_runs = max(1, min(max_runs, 200))

            runs = []
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


router.include_router(tasks_router)
router.include_router(quant_router)
router.include_router(jobs_router)
