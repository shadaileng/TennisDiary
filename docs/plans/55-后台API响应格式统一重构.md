> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 55 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 后台API响应格式统一重构 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
>
> **关联文档**：[43-B2 后台管理API总纲](./43-B2-后台管理API总纲.md)

# 后台API响应格式统一重构

## 一、目标

统一后台所有API接口的响应格式，返回 `code`、`message`、`success`、`data` 四个字段，使前端可用统一拦截器处理业务逻辑。

## 二、响应格式定义

### 2.1 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "success": true,
  "data": { ... }
}
```

### 2.2 失败响应

```json
{
  "code": 40001,
  "message": "参数错误",
  "success": false,
  "data": null
}
```

### 2.3 分页响应

```json
{
  "code": 0,
  "message": "ok",
  "success": true,
  "data": {
    "items": [...],
    "total": 100,
    "offset": 0,
    "limit": 20
  }
}
```

### 2.4 错误码规范

| 错误码范围 | 说明 | 示例 |
|-----------|------|------|
| 0 | 成功 | - |
| 10000-19999 | 认证/授权错误 | 10001 未登录, 10002 token过期, 10003 无权限 |
| 20000-29999 | 参数校验错误 | 20001 参数缺失, 20002 参数格式错误 |
| 30000-39999 | 业务逻辑错误 | 30001 日记不存在, 30002 装备不存在 |
| 40000-49999 | 数据库错误 | 40001 插入失败, 40002 唯一约束冲突 |
| 50000-59999 | 服务器内部错误 | 50001 未知异常 |

## 三、当前现状

### 3.1 现有响应格式（5种）

| 格式 | 适用场景 | 示例 |
|------|---------|------|
| 裸对象/数组 | 查询成功 | `{ "id": 1, "date": "..." }` |
| 裸 dict | 删除成功 | `{ "message": "删除成功" }` |
| PaginatedResponse | admin 分页 | `{ "items": [...], "total": 100 }` |
| 无 Schema | system 接口 | `{ "status": "ok", "version": "..." }` |
| LoginResponse | 登录 | `{ "access_token": "...", "user": {...} }` |

### 3.2 问题清单

| 问题 | 影响 |
|------|------|
| 无统一响应包装 | 前端错误处理分散 |
| `MessageResponse` 重复定义 | schemas.py 和 admin.py 各一份 |
| delete 接口裸 dict | 无 response_model 声明 |
| system 接口无 Schema | 类型不安全 |

## 四、涉及文件

### 4.1 后端文件

| 文件路径 | 操作 |
|----------|------|
| `server/app/schemas/common.py` | 新建：ApiResponse、ErrorResponse |
| `server/app/main.py` | 修改：注册全局异常处理器 |
| `server/app/routers/auth.py` | 修改：包裹响应 |
| `server/app/routers/diaries.py` | 修改：包裹响应 |
| `server/app/routers/gears.py` | 修改：包裹响应 |
| `server/app/routers/weights.py` | 修改：包裹响应 |
| `server/app/routers/checkin.py` | 修改：包裹响应 |
| `server/app/routers/stats.py` | 修改：包裹响应 |
| `server/app/routers/upload.py` | 修改：包裹响应 |
| `server/app/routers/files.py` | 不改：二进制流 |
| `server/app/routers/admin/auth.py` | 修改：包裹响应 |
| `server/app/routers/admin/users.py` | 修改：包裹响应 |
| `server/app/routers/admin/diaries.py` | 修改：包裹响应 |
| `server/app/routers/admin/gears.py` | 修改：包裹响应 |
| `server/app/routers/admin/weights.py` | 修改：包裹响应 |
| `server/app/routers/admin/checkins.py` | 修改：包裹响应 |
| `server/app/routers/admin/analyses.py` | 修改：包裹响应 |
| `server/app/routers/admin/posts.py` | 修改：包裹响应 |
| `server/app/routers/admin/roles.py` | 修改：包裹响应 |
| `server/app/routers/admin/admins.py` | 修改：包裹响应 |
| `server/app/routers/admin/system.py` | 修改：包裹响应 |

### 4.2 Admin 前端文件

| 文件路径 | 操作 |
|----------|------|
| `admin/src/api/index.ts` | 修改：拦截器判断 code===0 |
| `admin/src/types/api.ts` | 新建：ApiResponse 类型定义 |
| `admin/src/api/auth.ts` | 修改：适配新格式 |
| `admin/src/api/users.ts` | 修改：适配新格式 |
| `admin/src/api/diaries.ts` | 修改：适配新格式 |
| `admin/src/api/gears.ts` | 修改：适配新格式 |
| `admin/src/api/weights.ts` | 修改：适配新格式 |
| `admin/src/api/roles.ts` | 修改：适配新格式 |
| `admin/src/api/admins.ts` | 修改：适配新格式 |
| `admin/src/api/system.ts` | 修改：适配新格式 |

### 4.3 Miniapp 前端文件

| 文件路径 | 操作 |
|----------|------|
| `miniapp/src/services/request.ts` | 修改：拦截器判断 code===0 |
| `miniapp/src/types/api.ts` | 新建：ApiResponse 类型定义 |
| `miniapp/src/services/data.ts` | 修改：适配新格式 |
| `miniapp/src/services/auth.ts` | 修改：适配新格式 |

## 五、实施步骤

### Step 1：新建通用 Schema

创建 `server/app/schemas/common.py`：

```python
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    code: int = 0
    message: str = "ok"
    success: bool = True
    data: T | None = None

class PaginatedData(BaseModel, Generic[T]):
    """分页数据"""
    items: list[T]
    total: int
    offset: int
    limit: int

class ErrorCode:
    """错误码定义"""
    SUCCESS = 0
    # 认证/授权 10000-19999
    UNAUTHORIZED = 10001
    TOKEN_EXPIRED = 10002
    FORBIDDEN = 10003
    # 参数校验 20000-29999
    VALIDATION_ERROR = 20001
    # 业务逻辑 30000-39999
    NOT_FOUND = 30001
    ALREADY_EXISTS = 30002
    # 数据库 40000-49999
    DB_ERROR = 40001
    DUPLICATE_KEY = 40002
    # 服务器 50000-59999
    INTERNAL_ERROR = 50001
```

### Step 2：注册全局异常处理器

修改 `server/app/main.py`，添加异常处理器将 HTTPException 转换为统一格式：

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from app.schemas.common import ApiResponse, ErrorCode

app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            code=exc.status_code if exc.status_code < 600 else ErrorCode.INTERNAL_ERROR,
            message=str(exc.detail),
            success=False,
            data=None,
        ).model_dump(),
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="服务器内部错误",
            success=False,
            data=None,
        ).model_dump(),
    )
```

### Step 3：改造用户端路由

所有路由函数返回值包裹为 `ApiResponse(data=...)`：

```python
# 改造前
@router.get("/diaries", response_model=list[DiaryResponse])
def list_diaries(...):
    return diaries

# 改造后
@router.get("/diaries", response_model=ApiResponse[list[DiaryResponse]])
def list_diaries(...):
    return ApiResponse(data=diaries)
```

### Step 4：改造 Admin 路由

分页接口使用 `ApiResponse[PaginatedData[T]]`：

```python
# 改造前
@router.get("/users", response_model=PaginatedResponse[UserAdminResponse])
def list_users(...):
    return {"items": users, "total": total, "offset": offset, "limit": limit}

# 改造后
@router.get("/users", response_model=ApiResponse[PaginatedData[UserAdminResponse]])
def list_users(...):
    return ApiResponse(data=PaginatedData(items=users, total=total, offset=offset, limit=limit))
```

### Step 5：改造前端拦截器

#### Admin 前端

```typescript
// admin/src/api/index.ts
api.interceptors.response.use(
  (response) => {
    const res = response.data as ApiResponse<any>;
    if (res.code !== 0) {
      // 业务错误，抛出异常
      return Promise.reject(new Error(res.message));
    }
    return res.data; // 直接返回 data
  },
  (error) => {
    // HTTP 错误
    return Promise.reject(error);
  }
);
```

#### Miniapp 前端

```typescript
// miniapp/src/services/request.ts
export function request<T>(options: RequestOptions): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      ...options,
      success: (res) => {
        const data = res.data as ApiResponse<T>;
        if (data.code === 0) {
          resolve(data.data as T);
        } else {
          uni.showToast({ title: data.message, icon: 'none' });
          reject(new Error(data.message));
        }
      },
      fail: (err) => {
        reject(err);
      },
    });
  });
}
```

### Step 6：修复 Admin 前端类型错误

| 文件 | 修复内容 |
|------|---------|
| `admin/src/api/roles.ts` | 返回类型改为 `Role[]` → `ApiResponse<RoleListResponse>` |
| `admin/src/api/gears.ts` | 字段名 `feelings`→`feeling`, `photos`→`photo` |
| `admin/src/api/weights.ts` | 字段名 `body_fat`→`bust/waist/hip` |
| `admin/src/api/analyses.ts` | 字段名 `type`→`kind`, `report`→`score/summary` |
| `admin/src/api/auth.ts` | 补充 `admin` 字段类型 |

## 六、验收标准

| 序号 | 验收项 | 标准 |
|:----:|--------|------|
| 1 | 响应格式 | 所有接口返回 `{code, message, success, data}` 四个字段 |
| 2 | 错误码 | 成功返回 code=0，错误返回对应错误码 |
| 3 | HTTP 状态码 | 业务错误仍使用 HTTP 4xx/5xx，body 中 code 为业务码 |
| 4 | Admin 拦截器 | code!==0 时自动弹出错误提示 |
| 5 | Miniapp 拦截器 | code!==0 时自动显示 toast |
| 6 | 分页接口 | 返回 `{items, total, offset, limit}` 在 data 内 |
| 7 | ruff 检查 | `cd server && uv run ruff check .` 无报错 |
| 8 | ruff 格式 | `cd server && uv run ruff format --check .` 无报错 |
| 9 | pytest | `cd server && uv run pytest -v` 全部通过 |
| 10 | Admin 构建 | `cd admin && pnpm build` 无报错 |
| 11 | Miniapp 构建 | `cd miniapp && pnpm build:mp-weixin` 无报错 |

## 七、时间估算

| 步骤 | 预计时间 |
|------|---------|
| Step 1：新建通用 Schema | 0.5h |
| Step 2：注册全局异常处理器 | 0.5h |
| Step 3：改造用户端路由（6个文件） | 2h |
| Step 4：改造 Admin 路由（11个文件） | 3h |
| Step 5：改造前端拦截器（2个） | 1h |
| Step 6：修复 Admin 前端类型错误 | 1h |
| 测试与联调 | 2h |
| **总计** | **~10h** |

## 八、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 回归风险 | 改动面广，可能引入新 bug | 先跑通测试，再逐个改造路由 |
| 前端适配遗漏 | 某些页面未处理新格式 | 拦截器统一处理，无需逐页修改 |
| HTTP 状态码混乱 | 前端同时判断 status 和 code | 明确规范：HTTP 状态码表示网络层，code 表示业务层 |
