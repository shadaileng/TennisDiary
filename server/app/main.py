from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.dirs import ensure_dirs
from app.core.logging import logger, setup_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import auth, checkin, diaries, files, gears, stats, upload, weights
from app.routers.admin import admins as admin_admins
from app.routers.admin import analyses as admin_analyses
from app.routers.admin import auth as admin_auth
from app.routers.admin import checkins as admin_checkins
from app.routers.admin import diaries as admin_diaries
from app.routers.admin import gears as admin_gears
from app.routers.admin import posts as admin_posts
from app.routers.admin import roles as admin_roles
from app.routers.admin import system as admin_system
from app.routers.admin import users as admin_users
from app.routers.admin import weights as admin_weights

# 启动时确保所有运行时目录存在
ensure_dirs()

# 初始化日志系统（幂等）
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
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

# 注册路由
app.include_router(auth.router)
app.include_router(diaries.router)
app.include_router(gears.router)
app.include_router(weights.router)
app.include_router(checkin.router)
app.include_router(stats.router)
app.include_router(files.router)
app.include_router(upload.router)

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
    return {"status": "ok", "version": "1.0.0"}
