from pathlib import Path
import sys
import logging

repo_root = Path(__file__).resolve().parents[2]
repo_root_str = str(repo_root)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import get_settings
from .database import ensure_database_schema
from .job_runtime import cleanup_stale_jobs
from .routes import router
from .schemas import APIResponse

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("doraemon")


def _safe_validation_errors(exc: RequestValidationError | ValidationError):
    safe_errors = []
    for item in exc.errors():
        normalized = dict(item)
        ctx = normalized.get("ctx")
        if isinstance(ctx, dict):
            normalized["ctx"] = {
                key: (str(value) if isinstance(value, Exception) else value)
                for key, value in ctx.items()
            }
        safe_errors.append(normalized)
    return safe_errors

if settings.auto_create_tables:
    ensure_database_schema()
    try:
        expired = cleanup_stale_jobs()
        if expired:
            logger.info("expired %s stale running jobs on startup", expired)
    except Exception:
        logger.exception("stale job cleanup failed during startup")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("%s %s failed", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=APIResponse(message="Internal Server Error", data={"error": "internal_error"}).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.info("%s %s %s", request.method, request.url.path, exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(message=str(exc.detail), data={"error": str(exc.detail)}).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info("%s %s 422", request.method, request.url.path)
    return JSONResponse(
        status_code=422,
        content=APIResponse(message="Validation Error", data={"error": _safe_validation_errors(exc)}).model_dump(),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    logger.info("%s %s 422", request.method, request.url.path)
    return JSONResponse(
        status_code=422,
        content=APIResponse(message="Validation Error", data={"error": _safe_validation_errors(exc)}).model_dump(),
    )


@app.get("/health", tags=["health"])
async def health_check():
    return APIResponse(message="ok", data={"service": settings.app_name})


app.include_router(router, prefix=settings.api_prefix)
