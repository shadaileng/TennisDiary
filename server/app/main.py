from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.dirs import ensure_dirs
from app.core.logging import logger, setup_logging
from app.routers import auth, checkin, diaries, gears, stats, weights

# 启动时确保所有运行时目录存在
ensure_dirs()

# 初始化日志系统（幂等）
setup_logging()

app = FastAPI(title="Tennis Diary API", version="1.0.0")

logger.info("Tennis Diary API 启动")

# 注册路由
app.include_router(auth.router)
app.include_router(diaries.router)
app.include_router(gears.router)
app.include_router(weights.router)
app.include_router(checkin.router)
app.include_router(stats.router)

# CORS 配置（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
