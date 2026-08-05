> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 19-Phase1-7 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-05 |
> | 对应功能/内容 | 网络层封装（`uni.request` + JWT 注入 + 401 处理） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1：uni-app 小程序前端工程初始化](./12-Phase1-uni-app小程序前端工程初始化.md) · [Phase1-6：Pinia store 搭建](./18-Phase1-6-PiniaStore搭建.md) · [Phase1-8：对接 B1 登录流程](./20-Phase1-8-对接B1登录流程.md)

# Step Phase1-7：网络层封装

## 一、目标

封装 `uni.request`，统一 baseURL、JWT 注入、错误处理与 401 登录失效处理，并封装认证相关 API（`services/auth.ts`）。

## 二、前置条件

- Phase1-5（types）/ Phase1-6（Pinia store）完成
- 后台 B1 接口就绪（`/api/auth`、`/api/diaries` 等）

## 三、技术方案

### 3.1 目录结构

```
miniapp/src/
├── config/index.ts        # baseURL 配置（按平台编译）
└── services/
    ├── request.ts         # 网络请求封装
    └── auth.ts            # 认证 API
```

### 3.2 核心机制

- **baseURL**：`config/index.ts` 用 `process.env.UNI_PLATFORM` 判断平台。
  - 小程序端（`mp-weixin`）→ `http://127.0.0.1:8000`（开发者工具勾选「不校验合法域名」）
  - H5 端 → `http://localhost:8000`
  - 生产环境须替换为备案 HTTPS 域名
- **请求封装**（`request.ts`）：
  - Promise 化 `get/post/put/delete`
  - 自动拼接 `BASE_URL + /api` 前缀
  - 自动注入 `Authorization: Bearer <token>`（从 storage 读取，避免与 store 循环依赖）
  - 统一错误为 `ApiError`（含 HTTP 状态码与后端 detail）
  - 401 时清空登录态并提示重新登录
- **认证 API**（`auth.ts`）：
  - `login(data)` → `POST /api/auth/login`（不带 Authorization）
  - `getMe()` → `GET /api/auth/me`（带 Authorization）

### 3.3 auth store 对接

`stores/auth.ts` 的 `login(code)` 对接网络层：先用 code 换 token，再调 `getMe` 获取用户，写入持久化。`App.vue onLaunch` 调用 `init()` 恢复登录态与偏好。

## 四、产出物

| 文件 | 说明 |
|---|---|
| `miniapp/src/config/index.ts` | baseURL 平台配置 |
| `miniapp/src/services/request.ts` | 请求封装 + ApiError |
| `miniapp/src/services/auth.ts` | 认证 API |
| `miniapp/src/stores/auth.ts` | login 对接网络层 |
| `miniapp/src/App.vue` | onLaunch 初始化 store |

## 五、验收标准

- [x] `get/post/put/delete` 可用，自动注入 JWT
- [x] 401 统一处理（清登录态 + 提示）
- [x] H5 与小程序双端 baseURL 正确（编译产物验证：小程序端 `127.0.0.1`，无 `process.env` 残留）
- [x] `services/auth.ts` 提供登录/获取用户 API
- [x] `pnpm type-check` 通过
- [x] `pnpm build:mp-weixin` 编译通过

## 六、提交拆分

1. `feat(miniapp): 封装网络层（request + 认证 API）`
2. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase1-7 完成）`
