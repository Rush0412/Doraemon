from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Doraemon API"
    api_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql://postgres:123456@localhost:5432/doraemon"
    )
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
