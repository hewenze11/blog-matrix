import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Blog Matrix Platform"
    APP_VERSION: str = "1.0.0"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_SUPER_SECRET_KEY_32CHARS")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://blogmatrix:blogmatrix123@db:5432/blogmatrix"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Feishu Webhook
    FEISHU_WEBHOOK_URL: str = os.getenv(
        "FEISHU_WEBHOOK_URL",
        "https://open.feishu.cn/open-apis/bot/v2/hook/afcb8993-243a-4d11-801c-d879da200f07"
    )

    # Monitor
    MONITOR_INTERVAL_SECONDS: int = 180  # 3 minutes
    MONITOR_FAIL_THRESHOLD: int = 3

    # Admin default credentials
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "BlogMatrix2024!")

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
