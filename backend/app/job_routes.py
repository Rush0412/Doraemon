import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db
from .quant_service import _run_job, executor

jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])


@jobs_router.get("/", response_model=schemas.APIResponse)
def list_jobs(limit: int = 50, db: Session = Depends(get_db)):
    jobs = crud.list_quant_jobs(db, limit=limit)
    return schemas.APIResponse(data=[schemas.QuantJobRead.model_validate(job) for job in jobs])


@jobs_router.post("/", response_model=schemas.APIResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(payload: schemas.QuantJobCreate, db: Session = Depends(get_db)):
    job = crud.create_quant_job(db, payload)
    executor.submit(_run_job, job.id)
    return schemas.APIResponse(message="Job queued", data=schemas.QuantJobRead.model_validate(job))


@jobs_router.get("/{job_id}", response_model=schemas.APIResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_quant_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return schemas.APIResponse(data=schemas.QuantJobRead.model_validate(job))


@jobs_router.delete("/{job_id}", response_model=schemas.APIResponse)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_quant_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is running")
    crud.delete_quant_job(db, job)
    return schemas.APIResponse(message="Job deleted", data={"id": job_id})


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
