import os
from pathlib import Path

from dotenv import load_dotenv

# 用绝对路径定位 server/ 目录（config.py 位于 server/app/core/，向上三级）
SERVER_DIR = Path(__file__).resolve().parent.parent.parent

# APP_ENV 必须在 load_dotenv 之前从 os.getenv 读取，
# 否则会被 .env 文件里的 APP_ENV 覆盖，无法切换配置源
APP_ENV = os.getenv("APP_ENV", "dev")

# 测试环境加载 .env.test（override=True 覆盖已存在的环境变量，实现隔离）；
# 开发/生产加载 .env
if APP_ENV == "test":
    load_dotenv(SERVER_DIR / ".env.test", override=True)
else:
    load_dotenv(SERVER_DIR / ".env")


class Settings:
    """应用配置，所有值支持环境变量覆盖"""

    # 应用基础
    APP_NAME: str = "Tennis Diary API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 数据目录（数据库 + 上传文件统一在此）
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")

    # 数据库 URL（业务库）
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/tennis_diary.db")
    # 审计库 / 备份元数据库（默认本地 SQLite，保持 147/72 隔离价值；生产可各自切 PG）
    AUDIT_DB_URL: str = os.getenv("AUDIT_DB_URL", f"sqlite:///{DATA_DIR}/audit.db")
    BACKUP_META_DB_URL: str = os.getenv(
        "BACKUP_META_DB_URL", f"sqlite:///{DATA_DIR}/backup_meta.db"
    )
    # 连接池参数（PG 生效，SQLite 忽略；Supabase pgbouncer 并发上限约束）
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    DB_POOL_PRE_PING: bool = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

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
    # AI 服务商直选（ai_providers 中已维护的服务商名；空 = 自定义独立配置）
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "")

    # 姿态推理模型（MediaPipe pose_landmarker，随包路径 server/models/）
    POSE_MODEL_PATH: str = os.getenv(
        "POSE_MODEL_PATH",
        f"{Path(__file__).resolve().parent.parent.parent}/models/pose_landmarker_lite.task",
    )

    # 骨架视频逐帧生成配置
    POSE_FULL_FRAMES_ENABLED: bool = os.getenv("POSE_FULL_FRAMES_ENABLED", "true").lower() == "true"
    POSE_FULL_FRAMES_THRESHOLD: int = int(os.getenv("POSE_FULL_FRAMES_THRESHOLD", "3"))

    # 文件存储
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", f"{DATA_DIR}/uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))

    # 对象存储（147 阶段一：S3 兼容，七牛 Kodo；backend=local 即回滚开关）
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
    STORAGE_ENDPOINT: str = os.getenv("STORAGE_ENDPOINT", "")
    STORAGE_REGION: str = os.getenv("STORAGE_REGION", "")
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "")
    STORAGE_ACCESS_KEY: str = os.getenv("STORAGE_ACCESS_KEY", "")
    STORAGE_SECRET_KEY: str = os.getenv("STORAGE_SECRET_KEY", "")
    STORAGE_PRESIGN_TTL: int = int(os.getenv("STORAGE_PRESIGN_TTL", "7200"))
    STORAGE_PUBLIC_BASE_URL: str = os.getenv("STORAGE_PUBLIC_BASE_URL", "")
    STORAGE_LOCAL_RETENTION: int = int(os.getenv("STORAGE_LOCAL_RETENTION", "0"))

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

    # 管理员配置
    ADMIN_DEFAULT_USERNAME: str = os.getenv("ADMIN_DEFAULT_USERNAME", "admin")
    ADMIN_DEFAULT_PASSWORD: str = os.getenv("ADMIN_DEFAULT_PASSWORD", "changeme")
    ADMIN_RESET_KEY: str = os.getenv("ADMIN_RESET_KEY", "")

    # 日志分离配置
    LOG_ADMIN_FILE: str = os.getenv("LOG_ADMIN_FILE", "admin.log")
    LOG_USER_FILE: str = os.getenv("LOG_USER_FILE", "user.log")
    LOG_JSON_ENABLED: bool = os.getenv("LOG_JSON_ENABLED", "false").lower() == "true"


settings = Settings()
