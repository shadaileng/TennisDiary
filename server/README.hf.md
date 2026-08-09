---
title: Tennis Diary Server
emoji: 🎾
colorFrom: olive
colorTo: lime
sdk: docker
pinned: false
env:
  - name: JWT_SECRET
    value: ""
    required: true
  - name: WX_APPID
    value: ""
    required: true
  - name: WX_SECRET
    value: ""
    required: true
  - name: ADMIN_DEFAULT_PASSWORD
    value: "changeme"
    required: false
  - name: ADMIN_RESET_KEY
    value: ""
    required: false
---

## Tennis Diary Server

网球日记微信小程序 FastAPI 后台服务。

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `GET` | `/docs` | Swagger API 文档 |
| `POST` | `/api/auth/login` | 微信登录（JWT） |
| `GET` | `/api/auth/me` | 获取当前用户 |
| `PUT` | `/api/auth/me` | 更新用户资料 |
| `GET` | `/api/diaries` | 日记列表 |
| `POST` | `/api/diaries` | 创建日记 |
| `GET` | `/api/gears` | 装备列表 |
| `GET` | `/api/weights` | 体重记录 |
| `GET` | `/api/checkin` | 打卡记录 |
| `GET` | `/api/stats` | 统计数据 |
| `POST` | `/api/upload/*` | 文件上传 |
| `GET` | `/api/files/{filename}` | 文件下载 |
| `POST` | `/api/events` | 客户端事件埋点 |

### 环境变量

| 变量 | 用途 | 默认值 | 必填 |
|------|------|--------|:----:|
| `JWT_SECRET` | JWT 签名密钥 | — | **✅** |
| `WX_APPID` | 微信小程序 AppID | — | **✅** |
| `WX_SECRET` | 微信小程序 Secret | — | **✅** |
| `ADMIN_DEFAULT_PASSWORD` | 管理员初始密码 | `changeme` | |
| `ADMIN_RESET_KEY` | 管理员重置密钥 | 空 | |
| `DATA_DIR` | 数据目录（持久化卷） | `/data` | |
| `LOG_LEVEL` | 日志级别 | `INFO` | |

### 数据持久化

容器数据存储在 `/data` 目录（SQLite 数据库 + 上传文件），
需在 HF Space Settings → Storage 挂载 volume 到 `/data` 持久化。

### 技术栈

FastAPI + SQLAlchemy + Alembic + SQLite，Python 3.10。