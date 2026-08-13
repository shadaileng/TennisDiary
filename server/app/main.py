import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.dirs import ensure_dirs
from app.core.logging import logger, setup_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import (
    ai,
    analyses,
    auth,
    checkin,
    diaries,
    files,
    gears,
    pose,
    stats,
    upload,
    video,
    weights,
)
from app.routers import events as user_events
from app.routers.admin import admins as admin_admins
from app.routers.admin import analyses as admin_analyses
from app.routers.admin import auth as admin_auth
from app.routers.admin import checkins as admin_checkins
from app.routers.admin import diaries as admin_diaries
from app.routers.admin import events as admin_events
from app.routers.admin import gears as admin_gears
from app.routers.admin import posts as admin_posts
from app.routers.admin import roles as admin_roles
from app.routers.admin import system as admin_system
from app.routers.admin import users as admin_users
from app.routers.admin import weights as admin_weights
from app.schemas.common import ApiResponse, ErrorCode

# 启动时确保所有运行时目录存在
ensure_dirs()

# 初始化日志系统（幂等）
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 记录启动时间
    app.state.start_time = time.time()

    # 启动时初始化默认角色和管理员
    from app.core.database import SessionLocal
    from app.core.init_data import init_default_admin, init_default_roles

    db = SessionLocal()
    try:
        init_default_roles(db)
        init_default_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Tennis Diary API", version="1.0.0", lifespan=lifespan)

logger.info("Tennis Diary API 启动")


# ==================== 全局异常处理器 ====================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理（401/403/404等）"""
    code = ErrorCode.UNAUTHORIZED
    if exc.status_code == 403:
        code = ErrorCode.FORBIDDEN
    elif exc.status_code == 404:
        code = ErrorCode.NOT_FOUND
    elif exc.status_code == 422:
        code = ErrorCode.VALIDATION_ERROR
    elif exc.status_code >= 500:
        code = ErrorCode.INTERNAL_ERROR

    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            code=code,
            message=str(exc.detail),
            success=False,
            data=None,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验异常处理"""
    errors = []
    for error in exc.errors():
        loc = " → ".join(str(item) for item in error["loc"])
        errors.append(f"{loc}: {error['msg']}")

    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            code=ErrorCode.VALIDATION_ERROR,
            message="参数校验失败",
            success=False,
            data=errors,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """未知异常处理（最外层 ServerErrorMiddleware 生成响应，绕过 CORSMiddleware，需补 CORS 头）"""
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="服务器内部错误",
            success=False,
            data=None,
        ).model_dump(),
        headers={"Access-Control-Allow-Origin": "*"},
    )


# 注册路由
app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(analyses.router)
app.include_router(pose.router)
app.include_router(video.router)
app.include_router(diaries.router)
app.include_router(gears.router)
app.include_router(weights.router)
app.include_router(checkin.router)
app.include_router(stats.router)
app.include_router(files.router)
app.include_router(upload.router)
app.include_router(user_events.router)

# 注册管理路由
app.include_router(admin_auth.router)
app.include_router(admin_roles.router)
app.include_router(admin_admins.router)
app.include_router(admin_users.router)
app.include_router(admin_diaries.router)
app.include_router(admin_gears.router)
app.include_router(admin_weights.router)
app.include_router(admin_checkins.router)
app.include_router(admin_analyses.router)
app.include_router(admin_posts.router)
app.include_router(admin_system.router)
app.include_router(admin_events.router)

# CORS 配置（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件（实现日志分离）
app.add_middleware(RequestLoggingMiddleware)


@app.get("/health")
def health():
    return ApiResponse(data={"status": "ok", "version": "1.0.0"})
