> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 20-Phase1-8 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-05 |
> | 对应功能/内容 | 对接 B1 微信登录流程（静默登录） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1：uni-app 小程序前端工程初始化](./12-Phase1-uni-app小程序前端工程初始化.md) · [Phase1-7：网络层封装](./19-Phase1-7-网络层封装.md) · [B1-5：微信登录鉴权](./05-B1-4-基于loguru的日志系统.md)

# Step Phase1-8：对接 B1 登录流程

## 一、目标

实现 `wx.login()` → `/api/auth/login` → 存储 JWT 的完整链路，支持首次启动静默登录。

## 二、前置条件

- Phase1-7 完成（网络层 + 认证 API 已就绪）
- 后台 B1-5 微信登录接口（`POST /api/auth/login`）可用

## 三、技术方案

### 3.1 登录链路

```
App.onLaunch
  → auth.init()            // 从 storage 恢复已有登录态
  → auth.ensureLogin()     // 无 token 时触发静默登录
      → getLoginCode()     // uni.login 取微信 code（H5 mock）
      → loginApi({code})   // POST /api/auth/login 换 JWT
      → getMe()            // GET /api/auth/me 取用户
      → setAuth()          // 写入 store + storage 持久化
```

### 3.2 关键实现

- **`getLoginCode()`**（`services/auth.ts`）：小程序端 `uni.login`（编译为 `wx.login`）取 code；H5 端 mock（用于后端联调）。
- **`login()`**（`stores/auth.ts`）：完整链路，失败时清空登录态并抛错。
- **`ensureLogin()`**（`stores/auth.ts`）：已登录则直接返回，否则自动登录；失败时提示并保持未登录态。
- **`App.vue onLaunch`**：`init()` 恢复登录态后调用 `ensureLogin()` 静默登录。

### 3.3 失败处理

- `wx.login` 失败 → 抛错，`ensureLogin` 捕获并 `showToast` 提示
- token 换取失败（后台 401/502）→ 清空登录态
- code 有效期 5 分钟，静默登录失败不影响页面渲染

## 四、产出物

| 文件 | 说明 |
|---|---|
| `miniapp/src/services/auth.ts` | 新增 `getLoginCode()` |
| `miniapp/src/stores/auth.ts` | 新增 `ensureLogin()`，重构 `login()` |
| `miniapp/src/App.vue` | onLaunch 触发静默登录 |

## 五、验收标准

- [x] 首次启动自动完成登录并取得 JWT
- [x] JWT 持久化，重启无需重复登录（`init()` 恢复）
- [x] `uni.login` 在小程序端编译为 `wx.login`（产物验证）
- [x] 调用受保护接口（如 `/api/auth/me`）自动携带 JWT
- [x] 登录失败有提示且保持未登录态
- [x] `pnpm type-check` 与 `pnpm build:mp-weixin` 通过

## 六、提交拆分

1. `feat(miniapp): 对接 B1 微信登录（静默登录）`
2. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase1-8 完成）`
