> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 43-B2 |
> | 文档版本 | v1.2.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 后台管理系统总纲（API + 前端） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
> | 2026-08-08 | v1.1.0 | 新增角色权限系统、管理员用户管理 |
> | 2026-08-08 | v1.2.0 | 新增后台管理前端方案 |
>
> **关联文档**：[B1-1 FastAPI项目初始化](./02-B1-1-FastAPI项目初始化与目录结构.md)、[B1-2 核心配置模块](./03-B1-2-核心配置模块.md)、[47-Admin 后台管理前端](./47-Admin-后台管理前端.md)

# Phase B2：后台管理系统总纲

## 一、目标

为 Tennis Diary 后台增加运维管理能力，实现管理员独立认证、数据查看、系统监控、日志查询、数据库备份等功能。

## 二、需求概述

| 需求项 | 说明 |
|--------|------|
| 功能范围 | 运维管理（系统监控）+ 角色权限 + 管理员用户管理 |
| 认证方式 | 独立账号密码登录（与普通用户微信登录分离） |
| API组织 | 按功能分组 `/api/admin/users/*`, `/api/admin/diaries/*` 等 |
| 数据查看 | 管理员可查看所有用户数据 |
| 角色权限 | 基于角色的访问控制（RBAC），支持多角色、细粒度权限 |
| 管理员管理 | 超级管理员可管理其他管理员账号 |
| 系统监控 | 健康检查增强、运行时指标、日志查询 |
| 数据备份 | SQLite在线备份/恢复 |
| 日志分离 | admin/user日志分开存储，支持JSON格式 |

## 三、当前项目现状

### 3.1 现有API端点（22个）

| 模块 | 端点 | 说明 |
|------|------|------|
| auth | POST /api/auth/login | 微信登录 |
| auth | GET /api/auth/me | 获取当前用户 |
| auth | PUT /api/auth/me | 更新用户资料 |
| diaries | GET/POST /api/diaries | 日记列表/创建 |
| diaries | GET/PUT/DELETE /api/diaries/{id} | 日记详情/编辑/删除 |
| gears | GET/POST /api/gears | 装备列表/添加 |
| gears | GET/PUT/DELETE /api/gears/{id} | 装备详情/编辑/删除 |
| weights | GET/POST /api/weights | 体重记录列表/添加 |
| weights | DELETE /api/weights/{id} | 删除体重记录 |
| checkin | GET/POST /api/checkin | 打卡记录/签到 |
| stats | GET /api/stats | 统计汇总 |
| files | GET /api/files/{filename} | 文件下载 |
| upload | POST /api/upload/avatar | 上传头像 |
| upload | GET /api/upload/avatar/{user_id}/{filename} | 下载头像 |
| health | GET /health | 健康检查 |

### 3.2 现有鉴权机制

```python
# 当前鉴权流程
wx.login() → POST /api/auth/login {code} → JWT(openid) → 后续请求 Bearer token
                                                         ↓
                                              get_current_user() → User对象
```

**问题**：
- 无角色系统，只有"已登录"和"未登录"
- 无法区分普通用户和管理员
- Token payload仅含openid，无exp声明

### 3.3 现有目录结构

```
server/app/
├── main.py              # FastAPI入口
├── core/                # 配置、安全、日志
├── models/              # SQLAlchemy ORM模型
├── routers/             # API路由（平级组织）
├── schemas/             # Pydantic schemas（单一文件）
└── services/            # 业务逻辑（仅wx_service）
```

## 四、技术方案

### 4.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                    │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │   Public API     │  │       Admin API              │ │
│  │  /api/auth/*     │  │  /api/admin/auth/*           │ │
│  │  /api/diaries/*  │  │  /api/admin/admins/*         │ │
│  │  /api/gears/*    │  │  /api/admin/roles/*          │ │
│  │  /api/weights/*  │  │  /api/admin/users/*          │ │
│  │  /api/checkin/*  │  │  /api/admin/diaries/*        │ │
│  │  /api/stats      │  │  /api/admin/gears/*          │ │
│  │  /api/files/*    │  │  /api/admin/weights/*        │ │
│  │  /api/upload/*   │  │  /api/admin/checkins/*       │ │
│  └──────────────────┘  │  /api/admin/analyses/*       │ │
│                        │  /api/admin/posts/*          │ │
│                        │  /api/admin/system/*         │ │
│                        └──────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                    Application Layer                     │
│              (业务逻辑编排，按需抽取)                    │
├─────────────────────────────────────────────────────────┤
│                     Domain Layer                         │
│           (核心业务规则，稳定不变)                       │
├─────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                    │
│         (数据库、日志、配置、外部服务)                   │
└─────────────────────────────────────────────────────────┘
```

### 4.2 管理员认证流程

```
管理员访问 /api/admin/auth/login
          ↓
    { username, password }
          ↓
    验证账号密码（bcrypt）
          ↓
    签发Admin JWT（独立密钥）
          ↓
    后续请求: Authorization: Bearer <admin_jwt>
          ↓
    get_current_admin() → Admin对象
          ↓
    权限校验（is_active检查 + 角色权限）
          ↓
    require_permission("xxx") → 验证角色权限
```

### 4.3 数据备份方案

```python
# SQLite在线备份（无需停机）
import sqlite3

def backup_database(backup_path: str):
    source = sqlite3.connect("tennis_diary.db")
    dest = sqlite3.connect(backup_path)
    with dest:
        source.backup(dest)
    source.close()
    dest.close()
```

## 五、目录结构设计

### 5.1 新增文件

```
server/app/
├── core/
│   ├── auth.py              # 新增 get_current_admin, require_permission
│   ├── security.py          # 新增 密码哈希工具
│   └── init_data.py         # 新增 初始角色和管理员数据
├── models/
│   ├── admin.py             # 新增 Admin模型（含role_id）
│   ├── role.py              # 新增 Role模型
│   └── __init__.py          # 更新：导出Admin, Role
├── routers/
│   └── admin/               # 新增 admin目录
│       ├── __init__.py
│       ├── auth.py          # 管理员登录
│       ├── admins.py        # 新增：管理员管理
│       ├── roles.py         # 新增：角色管理
│       ├── users.py         # 用户管理
│       ├── diaries.py       # 日记管理
│       ├── gears.py         # 装备管理
│       ├── weights.py       # 体重管理
│       ├── checkins.py      # 打卡管理
│       ├── analyses.py      # 分析管理
│       ├── posts.py         # 发布管理
│       └── system.py        # 系统监控
├── schemas/
│   └── admin.py             # 新增 管理相关schemas
├── middleware/
│   └── logging.py           # 新增 请求日志中间件
└── main.py                  # 更新：注册admin路由
```

### 5.2 目录结构对比

| 变更前 | 变更后 |
|--------|--------|
| `routers/auth.py` | `routers/auth.py`（保持不变） |
| 无 | `routers/admin/__init__.py` |
| 无 | `routers/admin/auth.py` |
| 无 | `routers/admin/admins.py` |
| 无 | `routers/admin/roles.py` |
| 无 | `routers/admin/users.py` |
| 无 | `routers/admin/diaries.py` |
| ... | ... |
| 无 | `core/security.py` |
| 无 | `core/init_data.py` |
| 无 | `models/admin.py` |
| 无 | `models/role.py` |
| 无 | `schemas/admin.py` |
| 无 | `middleware/logging.py` |

## 六、Admin模型设计

### 6.1 数据库表结构

```sql
CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(32) UNIQUE NOT NULL,
    code VARCHAR(32) UNIQUE NOT NULL,
    description VARCHAR(128) DEFAULT '',
    permissions TEXT DEFAULT '[]',  -- JSON: 权限列表
    is_system BOOLEAN DEFAULT 0,    -- 系统内置角色（不可删除）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    nickname VARCHAR(64) DEFAULT '',
    role_id INTEGER NOT NULL,       -- 关联roles表
    is_active BOOLEAN DEFAULT 1,
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
```

### 6.2 SQLAlchemy模型

```python
# app/models/role.py
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from app.core.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), unique=True, nullable=False)
    code = Column(String(32), unique=True, nullable=False, index=True)
    description = Column(String(128), default="")
    permissions = Column(Text, default="[]")  # JSON: 权限列表
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# app/models/admin.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    nickname = Column(String(64), default="")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    role = relationship("Role", backref="admins")
```

### 6.3 预置角色

| 角色名 | 编码 | 权限 | 说明 |
|--------|------|------|------|
| 超级管理员 | superadmin | 全部权限 | 系统内置，不可删除 |
| 普通管理员 | admin | 查看数据、管理系统 | 可管理用户数据 |
| 只读管理员 | viewer | 查看数据 | 只能查看，不能修改 |

### 6.4 权限列表

```python
PERMISSIONS = {
    # 用户管理
    "users:list": "查看用户列表",
    "users:view": "查看用户详情",
    "users:delete": "删除用户",
    
    # 数据管理
    "diaries:list": "查看日记列表",
    "diaries:view": "查看日记详情",
    "diaries:delete": "删除日记",
    
    "gears:list": "查看装备列表",
    "gears:delete": "删除装备",
    
    "weights:list": "查看体重记录",
    "weights:delete": "删除体重记录",
    
    "checkins:list": "查看打卡记录",
    "checkins:delete": "删除打卡记录",
    
    "analyses:list": "查看分析报告",
    "analyses:delete": "删除分析报告",
    
    "posts:list": "查看发布记录",
    "posts:delete": "删除发布记录",
    
    # 系统管理
    "system:health": "查看系统健康",
    "system:stats": "查看运行时指标",
    "system:logs": "查看日志",
    "system:backup": "数据库备份",
    "system:restore": "数据恢复",
    
    # 管理员管理
    "admins:list": "查看管理员列表",
    "admins:create": "创建管理员",
    "admins:edit": "编辑管理员",
    "admins:delete": "删除管理员",
    "admins:reset_password": "重置密码",
    
    # 角色管理
    "roles:list": "查看角色列表",
    "roles:create": "创建角色",
    "roles:edit": "编辑角色",
    "roles:delete": "删除角色",
}
```

## 七、API端点设计

### 7.1 管理员认证 `/api/admin/auth`

| Method | Path | 说明 | 鉴权 |
|--------|------|------|------|
| POST | /api/admin/auth/login | 管理员登录（账号密码） | 无需 |
| GET | /api/admin/auth/me | 获取当前管理员信息 | 需要 |
| PUT | /api/admin/auth/password | 修改密码 | 需要 |

### 7.2 角色管理 `/api/admin/roles`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/roles | 角色列表 | roles:list |
| POST | /api/admin/roles | 创建角色 | roles:create |
| GET | /api/admin/roles/{role_id} | 角色详情 | roles:view |
| PUT | /api/admin/roles/{role_id} | 编辑角色 | roles:edit |
| DELETE | /api/admin/roles/{role_id} | 删除角色 | roles:delete |

### 7.3 管理员管理 `/api/admin/admins`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/admins | 管理员列表（分页） | admins:list |
| POST | /api/admin/admins | 创建管理员 | admins:create |
| GET | /api/admin/admins/{admin_id} | 管理员详情 | admins:view |
| PUT | /api/admin/admins/{admin_id} | 编辑管理员 | admins:edit |
| PUT | /api/admin/admins/{admin_id}/password | 重置密码 | admins:reset_password |
| PUT | /api/admin/admins/{admin_id}/status | 启用/禁用 | admins:edit |
| DELETE | /api/admin/admins/{admin_id} | 删除管理员 | admins:delete |

### 7.4 用户管理 `/api/admin/users`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/users | 用户列表（分页） | users:list |
| GET | /api/admin/users/{user_id} | 用户详情 | users:view |
| DELETE | /api/admin/users/{user_id} | 删除用户 | users:delete |

### 7.5 日记管理 `/api/admin/diaries`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/diaries | 日记列表（分页+用户筛选） | diaries:list |
| GET | /api/admin/diaries/{diary_id} | 日记详情 | diaries:view |
| DELETE | /api/admin/diaries/{diary_id} | 删除日记 | diaries:delete |

### 7.6 装备管理 `/api/admin/gears`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/gears | 装备列表（分页+用户筛选） | gears:list |
| GET | /api/admin/gears/{gear_id} | 装备详情 | gears:view |
| DELETE | /api/admin/gears/{gear_id} | 删除装备 | gears:delete |

### 7.7 体重管理 `/api/admin/weights`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/weights | 体重记录列表（分页+用户筛选） | weights:list |
| DELETE | /api/admin/weights/{weight_id} | 删除体重记录 | weights:delete |

### 7.8 打卡管理 `/api/admin/checkins`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/checkins | 打卡记录列表（分页+用户筛选） | checkins:list |
| DELETE | /api/admin/checkins/{checkin_id} | 删除打卡记录 | checkins:delete |

### 7.9 分析管理 `/api/admin/analyses`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/analyses | 分析报告列表（分页+用户筛选） | analyses:list |
| GET | /api/admin/analyses/{analysis_id} | 分析详情 | analyses:view |
| DELETE | /api/admin/analyses/{analysis_id} | 删除分析报告 | analyses:delete |

### 7.10 发布管理 `/api/admin/posts`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/posts | 发布记录列表（分页+用户筛选） | posts:list |
| GET | /api/admin/posts/{post_id} | 发布详情 | posts:view |
| DELETE | /api/admin/posts/{post_id} | 删除发布记录 | posts:delete |

### 7.11 系统监控 `/api/admin/system`

| Method | Path | 说明 | 权限要求 |
|--------|------|------|---------|
| GET | /api/admin/system/health | 系统健康检查增强 | system:health |
| GET | /api/admin/system/stats | 运行时指标 | system:stats |
| GET | /api/admin/system/logs | 日志查询 | system:logs |
| POST | /api/admin/system/backup | 数据库备份 | system:backup |
| GET | /api/admin/system/backups | 备份列表 | system:backup |
| POST | /api/admin/system/restore/{backup_id} | 数据恢复 | system:restore |

## 八、关键代码实现

### 8.1 密码哈希工具

```python
# app/core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)
```

### 8.2 管理员JWT与权限校验

```python
# app/core/auth.py
ADMIN_JWT_SECRET = "admin-secret-key"  # 独立密钥

def create_admin_access_token(admin_id: int) -> str:
    """签发管理员JWT"""
    to_encode = {"sub": f"admin:{admin_id}", "type": "admin"}
    return jwt.encode(to_encode, ADMIN_JWT_SECRET, algorithm="HS256")

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Admin:
    """获取当前管理员"""
    try:
        payload = jwt.decode(credentials.credentials, ADMIN_JWT_SECRET, algorithms=["HS256"])
        admin_id = int(payload.get("sub").split(":")[1])
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if admin is None or not admin.is_active:
            raise HTTPException(status_code=401, detail="管理员不存在或已禁用")
        return admin
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的token")

def require_permission(permission: str):
    """权限校验依赖"""
    def permission_checker(
        admin: Admin = Depends(get_current_admin),
        db: Session = Depends(get_db),
    ):
        role = db.query(Role).filter(Role.id == admin.role_id).first()
        if role is None:
            raise HTTPException(status_code=403, detail="角色不存在")
        
        permissions = json.loads(role.permissions) if role.permissions else []
        if permission not in permissions and role.code != "superadmin":
            raise HTTPException(status_code=403, detail="权限不足")
        
        return admin
    return permission_checker
```

### 8.3 请求日志中间件

```python
# app/middleware/logging.py
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import get_logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 根据路径判断source
        path = request.url.path
        if path.startswith("/api/admin"):
            source = "admin"
        elif path.startswith("/api"):
            source = "user"
        else:
            source = "app"
        
        log = get_logger(source)
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000

        log.info(
            f"{request.method} {path} "
            f"{response.status_code} {duration:.1f}ms"
        )
        return response
```

### 8.4 数据库备份

```python
# app/routers/admin/system.py
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

@router.post("/backup")
def backup_database(admin: Admin = Depends(require_permission("system:backup"))):
    """数据库备份"""
    backup_dir = Path("data/backups")
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}.db"

    source = sqlite3.connect("data/tennis_diary.db")
    dest = sqlite3.connect(str(backup_path))
    with dest:
        source.backup(dest)
    source.close()
    dest.close()

    return {"backup_id": timestamp, "path": str(backup_path)}
```

## 九、环境变量配置

```bash
# .env.example
# 新增管理员配置
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=changeme
ADMIN_JWT_SECRET=your-admin-jwt-secret-change-in-production
```

## 十、依赖更新

```toml
# pyproject.toml
[project.dependencies]
# 新增
bcrypt = "^4.0.0"
```

## 十一、测试策略

### 11.1 测试文件结构

```
server/tests/
└── routers/
    └── admin/
        ├── __init__.py
        ├── conftest.py        # 管理员测试fixture
        ├── test_auth.py       # 管理员认证测试
        ├── test_roles.py      # 角色管理测试
        ├── test_admins.py     # 管理员管理测试
        ├── test_users.py      # 用户管理测试
        ├── test_diaries.py    # 日记管理测试
        ├── test_system.py     # 系统监控测试
        └── ...
```

### 11.2 关键测试用例

| 模块 | 测试用例 | 验证点 |
|------|---------|--------|
| 认证 | test_admin_login_success | 正确账号密码登录成功 |
| 认证 | test_admin_login_wrong_password | 错误密码返回401 |
| 认证 | test_admin_login_inactive | 禁用账号返回401 |
| 认证 | test_get_current_admin | 有效token返回Admin |
| 角色管理 | test_list_roles | 角色列表正常返回 |
| 角色管理 | test_create_role | 创建角色成功 |
| 角色管理 | test_create_role_duplicate | 重复编码返回400 |
| 角色管理 | test_update_role | 编辑角色信息 |
| 角色管理 | test_delete_role | 删除角色成功 |
| 角色管理 | test_delete_system_role | 系统角色不可删除 |
| 管理员管理 | test_list_admins | 管理员列表正常返回 |
| 管理员管理 | test_create_admin | 创建管理员成功 |
| 管理员管理 | test_create_admin_with_role | 指定角色创建成功 |
| 管理员管理 | test_update_admin | 编辑管理员信息 |
| 管理员管理 | test_change_admin_role | 修改管理员角色 |
| 管理员管理 | test_reset_password | 重置密码成功 |
| 管理员管理 | test_toggle_status | 启用/禁用管理员 |
| 管理员管理 | test_delete_admin | 删除管理员成功 |
| 权限控制 | test_permission_check | 权限校验正确 |
| 权限控制 | test_non_superadmin_create | 非超级管理员不能创建 |
| 用户管理 | test_list_users | 分页查询用户列表 |
| 用户管理 | test_get_user_detail | 获取用户详情 |
| 用户管理 | test_delete_user | 删除用户 |
| 系统监控 | test_health_check | 系统健康检查 |
| 系统监控 | test_system_stats | 运行时指标 |
| 系统监控 | test_backup_database | 数据库备份 |

## 十二、验收标准

### 12.1 功能验收

| 功能 | 验收标准 |
|------|---------|
| 管理员认证 | 管理员可使用账号密码登录，获取独立JWT |
| 角色管理 | 可创建/查看/编辑/删除角色 |
| 系统角色保护 | 系统内置角色不可删除 |
| 管理员管理 | 可创建/查看/编辑/删除管理员 |
| 角色分配 | 可为管理员分配角色 |
| 权限校验 | 无权限时返回403 |
| 超级管理员 | 拥有全部权限，不受限制 |
| 权限隔离 | 普通用户无法访问管理API（返回403） |
| 数据查看 | 管理员可查看所有用户数据，支持分页和筛选 |
| 系统监控 | 可查看系统健康状态、运行时指标 |
| 日志查询 | 可按级别/时间/关键字查询日志 |
| 数据备份 | 可执行数据库备份，查看备份列表，恢复数据 |
| 日志分离 | admin/user日志分开存储 |

### 12.2 代码质量验收

| 检查项 | 标准 |
|--------|------|
| 测试覆盖 | 核心逻辑覆盖率 ≥ 80% |
| ruff检查 | `uv run ruff check .` 无报错 |
| ruff格式 | `uv run ruff format --check .` 无报错 |
| pytest | `uv run pytest -v` 全部通过 |

## 十三、实施步骤

### Phase B2-0: 角色与权限系统（2-3天）

1. 新增Role模型
2. 更新Admin模型（添加role_id）
3. 创建Alembic迁移
4. 实现权限校验依赖
5. 实现初始角色数据
6. 更新初始管理员创建逻辑
7. 编写测试用例

### Phase B2-1: 管理员模型与认证（2-3天）

1. 新增Admin模型
2. 创建Alembic迁移
3. 实现密码哈希工具
4. 实现管理员认证依赖
5. 实现管理员登录接口
6. 编写测试用例

### Phase B2-2: 角色管理API（2-3天）

1. 实现角色CRUD接口
2. 实现权限列表接口
3. 编写测试用例

### Phase B2-3: 管理员用户管理API（2-3天）

1. 实现管理员列表接口
2. 实现创建管理员接口
3. 实现编辑管理员接口
4. 实现重置密码接口
5. 实现启用/禁用接口
6. 实现删除管理员接口
7. 编写测试用例

### Phase B2-4: 数据查看API（3-4天）

1. 实现用户管理接口
2. 实现日记管理接口
3. 实现装备管理接口
4. 实现体重管理接口
5. 实现打卡管理接口
6. 实现分析管理接口
7. 实现发布管理接口
8. 编写测试用例

### Phase B2-5: 系统监控API（3-4天）

1. 实现系统健康检查增强
2. 实现运行时指标
3. 实现日志查询接口
4. 实现数据库备份接口
5. 实现备份列表接口
6. 实现数据恢复接口
7. 编写测试用例

### Phase B2-6: 请求日志中间件（1-2天）

1. 实现请求日志中间件
2. 实现日志分离功能
3. 注册到FastAPI应用
4. 测试验证

### Phase B2-7: 测试与文档（2-3天）

1. 完善所有测试用例
2. 更新OpenAPI文档
3. 更新AGENTS.md
4. 更新README.md

## 十四、时间估算

| 阶段 | 预计时间 | 依赖 |
|------|---------|------|
| Phase B2-0: 角色与权限系统 | 2-3天 | 无 |
| Phase B2-1: 管理员模型与认证 | 2-3天 | Phase B2-0 |
| Phase B2-2: 角色管理API | 2-3天 | Phase B2-1 |
| Phase B2-3: 管理员用户管理API | 2-3天 | Phase B2-1 |
| Phase B2-4: 数据查看API | 3-4天 | Phase B2-1 |
| Phase B2-5: 系统监控API | 3-4天 | Phase B2-1 |
| Phase B2-6: 请求日志中间件 | 1-2天 | 无 |
| Phase B2-7: 测试与文档 | 2-3天 | Phase B2-0~6 |
| **总计** | **17-25天** | - |

## 十五、风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 密码泄露 | 高 | 低 | bcrypt哈希，强制密码复杂度，定期更换 |
| SQL注入 | 高 | 低 | SQLAlchemy ORM，参数化查询 |
| 备份文件安全 | 中 | 中 | 备份文件加密，限制访问权限，定期清理 |
| 日志文件过大 | 低 | 中 | 延用现有轮转策略，增加管理API限制 |
| 性能影响 | 中 | 低 | 分页查询，索引优化，异步备份 |

## 十六、后续优化方向

1. **审计日志**：记录所有管理操作
2. **操作日志**：前端操作日志查看
3. **告警机制**：磁盘空间不足、异常登录等告警
4. **API限流**：防止暴力破解和DDoS攻击
5. **多因素认证**：增加MFA支持
