> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 66 |
> | 文档版本 | v1.2.0 |
> | 文档状态 | 📋 待实施 |
> | 最后更新 | 2026-08-10 |
> | 对应功能/内容 | ModelScope 部署鉴权头被网关占用，改用自定义头 `X-Auth-Token` |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-10 | v1.2.0 | 4.1 后端实现定为「仅 `APIKeyHeader`」写法甲，移除 `Request` 与 `Authorization` 回退（三端已统一改发 `X-Auth-Token`，回退无场景） |
> | 2026-08-10 | v1.1.0 | 4.1 后端实现由「裸 `Header` 注入」升级为「`APIKeyHeader` 为主 + `Request` 回退」（方案 C），使 `X-Auth-Token` 进入 OpenAPI security scheme，Swagger 可一键 Authorize |
> | 2026-08-10 | v1.0.1 | 修正 4.1 代码块残留的 `HTTPAuthorizationCredentials, HTTPBearer` 导入（与「移除」说明自相矛盾） |
> | 2026-08-10 | v1.0.0 | 初版（定位根因 + 完整改动清单） |
>
> **关联文档**：[65-Server 部署方案-ModelScope 创空间](./65-Server部署方案-ModelScope-创空间.md) · [44-B2-1-管理员模型与认证](./44-B2-1-管理员模型与认证.md)

# Phase 66：ModelScope 部署鉴权头兼容改造（X-Auth-Token）

## 一、背景与问题根因

### 1.1 现象

admin 系统部署到魔搭（ModelScope）Docker 创空间（域名 `https://{owner}-{studio}.ms.show`）后，
**登录成功**（`POST /api/admin/auth/login` 能签发 token），但登录成功后前端自动调用
`GET /api/admin/auth/me` 触发 **401**。

### 1.2 诊断过程与结论

执行 `server/scripts/diag-admin-auth.sh` 的输出证实：

```
==> 1) POST .../api/admin/auth/login  → 成功签发 token（147 字符）
==> 2) GET /me（携带 Authorization: Bearer <token>）  → 401 {"code":10001,"message":"Not authenticated"}
==> 3) GET /me（不带任何 header）                     → 401 {"code":10001,"message":"Not authenticated"}
```

第 2、3 步返回**完全相同**的响应，说明请求根本没有到达 FastAPI 后端：

- 后端 `HTTPBearer` 在**无 header** 时返回 **403**（`Not authenticated`），不是 401；
- 后端 `decode` 失败（token 无效）时返回 **401** 但 message 为 `"无效的 token"`；
- 而实际返回的 401 + `"Not authenticated"` 与后端两种行为都不符 → 是**网关层拦截**。

作为对照，CloudStudio（未配 `JWT_SECRET`）上 login → /me 全流程正常，证明后端 JWT 逻辑本身无问题。

### 1.3 根因（官方文档铁证）

魔搭 Docker 创空间官方文档明确规定：

> **HTTP Header `Authorization`、`X-modelscope-*`、`X-studio-*` 已被魔搭平台占用，请勿在后端接口中使用。**

魔搭 `.ms.show` 网关会拦截并占用 `Authorization` 头，不透传给 FastAPI 后端。
因此前端发的 `Authorization: Bearer <JWT>` 在网关层被吃掉，后端拿不到 token，所有鉴权接口返回 401。

## 二、目标

让鉴权 JWT 传输绕开被魔搭占用/拦截的 `Authorization` 头，同时保证**非魔搭环境**（本地、CloudStudio、自有服务器）不受影响：

1. 后端鉴权统一读取自定义头 `X-Auth-Token`，**不再兼容 `Authorization`**。
2. 前端（admin / miniapp）所有携带 token 的请求改用 `X-Auth-Token`。
3. 测试与诊断脚本同步更新。
4. 函数名与 `Depends` 用法不变 → **88+ 处路由零改动**。

## 三、核心设计

### 3.1 鉴权头策略

| 环境 | 使用的头 | 说明 |
|------|---------|------|
| 魔搭 `.ms.show` | `X-Auth-Token` | `Authorization` 被网关占用，必须绕开 |
| 本地 / CloudStudio / 自有服务器 | `X-Auth-Token` | 三端统一，无回退 |

> `X-Auth-Token` 不在魔搭保留名单（`Authorization` / `X-modelscope-*` / `X-studio-*`）内，理论上可透传。
> 所有环境统一使用 `X-Auth-Token`，不再保留 `Authorization` 回退。

## 四、改动清单

### 4.1 后端核心：`server/app/core/auth.py`

将 `HTTPBearer` 替换为 `APIKeyHeader` 读取自定义头（**写法甲**，无 `Request`、无回退）：

```python
"""JWT签发与鉴权核心"""

import json
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

# 自定义鉴权头（魔搭网关占用 Authorization，需绕开）
AUTH_HEADER = "X-Auth-Token"
auth_scheme = APIKeyHeader(name=AUTH_HEADER, auto_error=False)


def get_token_from_header(
    x_auth_token: str | None = Depends(auth_scheme),
) -> str:
    """从请求头读取 JWT，统一使用 X-Auth-Token"""
    if not x_auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return x_auth_token


def create_access_token(openid: str) -> str:
    """签发普通用户JWT"""
    to_encode = {"sub": openid, "type": "user"}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """解码普通用户JWT，返回openid"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "user":
            raise HTTPException(status_code=401, detail="无效的 token")
        openid = payload.get("sub")
        if openid is None:
            raise HTTPException(status_code=401, detail="无效的 token")
        return openid
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的 token") from None


def create_admin_access_token(admin_id: int) -> str:
    """签发管理员JWT"""
    expire = datetime.utcnow() + timedelta(hours=ADMIN_JWT_EXPIRATION_HOURS)
    to_encode = {
        "sub": f"admin:{admin_id}",
        "type": "admin",
        "exp": expire,
    }
    return jwt.encode(to_encode, ADMIN_JWT_SECRET, algorithm=ADMIN_JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db),
):
    """从JWT获取当前用户"""
    from app.models.user import User

    openid = decode_access_token(token)
    user = db.query(User).filter(User.openid == openid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def get_current_admin(
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db),
):
    """从JWT获取当前管理员"""
    from app.models.admin import Admin

    try:
        payload = jwt.decode(token, ADMIN_JWT_SECRET, algorithms=[ADMIN_JWT_ALGORITHM])
        if payload.get("type") != "admin":
            raise HTTPException(status_code=403, detail="需要管理员权限")
        sub = payload.get("sub")
        if sub is None or not sub.startswith("admin:"):
            raise HTTPException(status_code=401, detail="无效的token")
        admin_id = int(sub.split(":")[1])
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if admin is None or not admin.is_active:
            raise HTTPException(status_code=401, detail="管理员不存在或已禁用")
        return admin
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的token") from None


def require_permission(permission: str):
    """权限校验依赖

    用法：
        @router.get("/users")
        def list_users(admin: Admin = Depends(require_permission("users:list"))):
            ...
    """

    def permission_checker(
        admin=Depends(get_current_admin),
        db: Session = Depends(get_db),
    ):
        from app.models.role import Role

        role = db.query(Role).filter(Role.id == admin.role_id).first()
        if role is None:
            raise HTTPException(status_code=403, detail="角色不存在")

        permissions = json.loads(role.permissions) if role.permissions else []
        if permission not in permissions and role.code != "superadmin":
            raise HTTPException(status_code=403, detail="权限不足")

        return admin

    return permission_checker
```

**关键点**：
- `get_current_user` / `get_current_admin` / `require_permission` 函数名与 `Depends` 用法**完全不变** → 88+ 处路由无需改动。
- 移除 `HTTPBearer`、`HTTPAuthorizationCredentials`、`security`、`Header`、`Request`；新增 `APIKeyHeader` 导入。
- 采用官方 `APIKeyHeader`（标准自定义头能力），`X-Auth-Token` **自动进入 OpenAPI security scheme**，Swagger 的 `Authorize` 按钮可一键注入 token（此为本方案相比裸 `Header` 的增量收益）。
- 不做 `Authorization` 回退：三端已统一改发 `X-Auth-Token`，旧场景不存在，`Request` 无需注入。
- `get_token_from_header` 未命中任何 token 时抛 401 `Not authenticated`，与原先 `HTTPBearer` 无 header 的 403 语义略有差异（网关兜底 401），无碍。

### 4.2 admin 前端：`admin/src/api/index.ts`（约第 14 行）

```ts
request.interceptors.request.use(config => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers['X-Auth-Token'] = authStore.token   // 原: Authorization = `Bearer ${authStore.token}`
  }
  return config
})
```

### 4.3 miniapp 小程序：三处

1. **`miniapp/src/services/request.ts`（约第 126 行）**
   ```ts
   if (token) {
     finalHeaders['X-Auth-Token'] = token   // 原: finalHeaders.Authorization = `Bearer ${token}`
   }
   ```

2. **`miniapp/src/services/auth.ts`（约第 60 行，头像上传）**
   ```ts
   header: token ? { 'X-Auth-Token': token } : {},   // 原: { Authorization: `Bearer ${token}` }
   ```

3. **`miniapp/src/utils/eventLogger.ts`（约第 132 行，事件上报）**
   ```ts
   ...(token ? { 'X-Auth-Token': token } : {}),   // 原: { Authorization: `Bearer ${token}` }
   ```

### 4.4 后端测试：两处

1. **`server/tests/routers/test_auth.py:104`**
   ```python
   headers={"X-Auth-Token": "invalid.token.here"},   # 原: {"Authorization": "Bearer invalid.token.here"}
   ```

2. **`server/tests/routers/admin/conftest.py:105`**
   ```python
   client.headers["X-Auth-Token"] = admin_token   # 原: client.headers["Authorization"] = f"Bearer {admin_token}"
   ```

### 4.5 诊断脚本（可选）：`server/scripts/diag-admin-auth.sh`

将第 36-37 行 curl 改为：

```bash
HTTP=$(curl -s -o /tmp/_diag_me.json -w "%{http_code}" "${BASE}/api/admin/auth/me" \
  -H "X-Auth-Token: ${TOKEN}")
```

（同步更新第 49-52 行的判断说明注释。）

### 4.6 CORS

`server/app/main.py` 的 CORS 已是 `allow_headers=["*"]`，**无需额外配置**，
`X-Auth-Token` 自定义头跨域预检（OPTIONS）可正常通过。

## 五、验证流程

```bash
# 1. 后端 lint + 测试（本地验证 X-Auth-Token 可用）
cd server && uv run ruff check app
cd server && uv run pytest -v

# 2. admin 前端构建
cd admin && pnpm build

# 3. 重新部署到魔搭
bash server/scripts/deploy-modelscope.sh

# 4. 线上诊断（期望第 2 步 = 200）
bash server/scripts/diag-admin-auth.sh https://{owner}-{studio}.ms.show admin 你的密码
```

## 六、风险与备选

1. **`X-Auth-Token` 是否 100% 可透传未获魔搭保证**：文档仅明确 `Authorization`/`X-modelscope-*`/`X-studio-*` 被占用。三端已统一改用 `X-Auth-Token`，若上线后被拦，可在后续版本恢复 `Authorization` 回退。
2. **备选方案（一）**：魔搭官方建议 Nginx 反代 + 自备已备案域名，可彻底绕开网关头占用问题，但需额外服务器与域名备案。
3. **备选方案（二）**：直接换回 CloudStudio（已验证 login → /me 全流程正常），魔搭仅作展示用途。

## 七、提交规范

```bash
fix(server): 魔搭部署下鉴权头被网关占用，改用 X-Auth-Token

- 后端 auth.py 新增 get_token_from_header，统一读取 X-Auth-Token（移除 Authorization 回退）
- admin/src/api/index.ts 请求头改用 X-Auth-Token
- miniapp request.ts / auth.ts / eventLogger.ts 三处改用 X-Auth-Token
- 测试 test_auth.py / admin/conftest.py 同步改用 X-Auth-Token
- diag-admin-auth.sh 诊断脚本同步更新
```

---

## 八、当前状态说明（2026-08-10）

- **状态**：📋 待实施（本方案文档仅用于记录方案，尚未改动任何代码）。
- **根因已确认**：魔搭 `.ms.show` 网关占用 `Authorization` 头，不透传给后端，导致所有鉴权接口返回 401。
- **待办**：按第四节改动清单逐一落地，并执行第五节验证流程。
