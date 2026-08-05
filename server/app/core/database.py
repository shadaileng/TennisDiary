import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 确保 SQLite 数据目录存在
db_path = settings.DATABASE_URL.replace("sqlite:///", "")
db_dir = os.path.dirname(os.path.abspath(db_path))
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

# SQLite 需要 check_same_thread=False 以支持多线程
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：获取数据库会话，请求结束后自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
