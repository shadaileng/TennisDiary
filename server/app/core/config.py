import os
from pathlib import Path

from dotenv import load_dotenv

# 用绝对路径加载 server/.env，无论从哪个目录启动都能正确读取
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    """应用配置，所有值支持环境变量覆盖"""

    # 应用基础
    APP_NAME: str = "Tennis Diary API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 数据目录（数据库 + 上传文件统一在此）
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")

    # 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/tennis_diary.db")

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production-please")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "720"))  # 30 天

    # 微信小程序
    WX_APPID: str = os.getenv("WX_APPID", "")
    WX_SECRET: str = os.getenv("WX_SECRET", "")

    # AI（阿里云百炼 / OpenAI 兼容）
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    AI_MODEL: str = os.getenv("AI_MODEL", "qwen-vl-max")

    # 文件存储
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", f"{DATA_DIR}/uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))

    # 日志
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", f"{DATA_DIR}/logs")
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")
    LOG_ROTATION: str = os.getenv("LOG_ROTATION", "10 MB")
    LOG_RETENTION: str = os.getenv("LOG_RETENTION", "7 days")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
    )


settings = Settings()
