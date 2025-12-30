from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import Base, engine
from .routes import router
from .schemas import APIResponse

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="1.0.0", openapi_url=f"{settings.api_prefix}/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=APIResponse(message="Internal Server Error", data={"error": str(exc)}).model_dump(),
    )


@app.get("/health", tags=["health"])
async def health_check():
    return APIResponse(message="ok", data={"service": settings.app_name})


app.include_router(router, prefix=settings.api_prefix)
