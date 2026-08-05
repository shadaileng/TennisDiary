from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.dirs import ensure_dirs

# 启动时确保所有运行时目录存在
ensure_dirs()

app = FastAPI(title="Tennis Diary API", version="1.0.0")

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
