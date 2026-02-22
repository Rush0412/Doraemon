from fastapi import APIRouter

from .job_routes import jobs_router
from .quant_routes import quant_router

router = APIRouter()
router.include_router(quant_router)
router.include_router(jobs_router)
