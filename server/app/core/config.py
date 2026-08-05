import os


class Settings:
    """应用配置，所有值支持环境变量覆盖"""

    # 应用基础
    APP_NAME: str = "Tennis Diary API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/tennis_diary.db")

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
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))


settings = Settings()
