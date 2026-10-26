import os
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

# ==================== 引擎工厂（148 阶段二 Step 1） ====================


def make_engine(url: str) -> Engine:
    """按 DSN 方言构造引擎：SQLite 用手动事务连接参数；PG 启用连接池参数。

    - SQLite：`check_same_thread=False` + `timeout=30` + `isolation_level=None`
      （手动管理事务，避免 implicit transaction 冲突）
    - PostgreSQL：`pool_size` / `max_overflow` / `pool_recycle` / `pool_pre_ping`
      （Supabase pgbouncer 并发上限约束；`pool_pre_ping` 断线自愈）
    """
    connect_args: dict = {}
    pool_args: dict = {}
    if "sqlite" in url:
        # 确保数据目录存在
        path_part = url.replace("sqlite:///", "")
        if path_part and not path_part.startswith(":memory:"):
            db_dir = os.path.dirname(os.path.abspath(path_part))
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 30.0
        connect_args["isolation_level"] = None  # 手动管理事务
    else:
        pool_args = {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": settings.DB_POOL_PRE_PING,
        }
    return create_engine(url, connect_args=connect_args, echo=settings.DEBUG, **pool_args)


# 148 阶段二：统一用 DB_DATABASE_URL（本地开发不填时回退到 SQLite 默认）
engine = make_engine(settings.DB_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== 请求级会话上下文（147 Step 7） ====================
#
# 响应层收口改写（storage.urls.rewrite_response_urls）需要在构造响应时拿到
# 当前请求的 DB 会话；FastAPI 的响应序列化不透传 context，故用 ContextVar 绑定。
#
# 绑定必须放在 **async 依赖**（app.main._request_db_context）里：FastAPI 对同步
# 生成器依赖走 `contextmanager_in_threadpool`，在**拷贝的 Context** 中执行，
# `set` 既传不回请求上下文、`reset` 还会因 Token 跨 Context 报错（Step 7 实测）。
# 异步依赖在同一 task 上下文进出 → set/reset 配对，同步端点经线程池执行时
# `copy_context()` 会继承该值（只读场景，足够）。

_request_db: ContextVar[Session | None] = ContextVar("request_db", default=None)


def current_session() -> Session | None:
    """当前请求绑定的 DB 会话；未绑定返回 None（后台/直接构造响应时安全跳过）"""
    return _request_db.get()


@contextmanager
def bind_request_db(db: Session):
    """把会话绑定到当前上下文（退出时还原，允许嵌套）"""
    token = _request_db.set(db)
    try:
        yield db
    finally:
        _request_db.reset(token)


def get_db():
    """FastAPI 依赖：获取数据库会话，请求结束后自动关闭

    会话上下文绑定由应用级异步依赖 `_request_db_context` 负责（见上），
    本生成器在同步线程池中执行，不能在此绑定 ContextVar。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
