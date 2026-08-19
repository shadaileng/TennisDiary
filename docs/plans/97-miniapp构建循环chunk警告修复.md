> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 97 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-19 |
> | 对应功能/内容 | miniapp 构建 Circular chunk 警告修复（request ↔ auth store 循环依赖解耦） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-19 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1-7：网络层封装](./19-Phase1-7-网络层封装.md)、[76：小程序 401 响应清除 token 内存态并引导登录](./76-小程序401响应清除token内存态并引导登录.md)、[61：miniapp 构建警告修复 — Sass 与循环依赖](./61-miniapp构建警告修复-Sass与循环依赖.md)

## 问题描述

执行 `pnpm build:mp-weixin` 时，构建输出如下警告：

```
Circular chunk: stores/auth -> services/auth -> services/request -> stores/auth.
Please adjust the manual chunk logic for these chunks.
```

该警告自 [76 号方案](./76-小程序401响应清除token内存态并引导登录.md) 引入后一直存在（README 曾标注「循环分块警告（不影响功能）」）。本次彻底解耦循环依赖，消除构建警告。

## 根因分析

真实的模块循环引用：

```
stores/auth.ts:4     import { getLoginCode, login } from "@/services/auth";
services/auth.ts:2   import { get, post, put } from "./request";
services/request.ts:4 import { useAuthStore } from "@/stores/auth";
```

- `stores/auth` 通过 `services/auth → services/request` 间接依赖网络层；
- 而 `services/request` 又静态导入 `stores/auth`（`clearAuth()` 中调用 `useAuthStore().logout()`），形成闭环：
  **`stores/auth → services/auth → services/request → stores/auth`**。

`request.ts` 中读取 token 已按注释「直接读 storage 而非导入 auth store」解耦（`getToken()` 走 `uni.getStorageSync`），但 `clearAuth()` 仍保留了静态导入的 store 引用，未完全解耦。`stores/app`（`useAppStore`）不参与该环，不受影响。

## 修复方案

用「会话失效回调注册」替代 `request.ts → stores/auth` 的静态依赖，打破循环：网络层保持零 store 依赖，auth store 主动向网络层注册到期清理回调。

### 修改文件

1. `miniapp/src/services/request.ts`
2. `miniapp/src/stores/auth.ts`

### 具体变更

**1. `services/request.ts`**

删除 `import { useAuthStore } from "@/stores/auth";`，新增回调注册入口，`clearAuth()` 改为通知回调：

```ts
type SessionExpiredHandler = () => void;
let sessionExpiredHandler: SessionExpiredHandler | null = null;

/** 注册会话失效回调（由 auth store 注册，用于同步重置内存态） */
export function onSessionExpired(handler: SessionExpiredHandler) {
  sessionExpiredHandler = handler;
}

/** 清理登录态：清 storage + 通知 auth store 重置内存态 */
function clearAuth() {
  uni.removeStorageSync(TOKEN_KEY);
  uni.removeStorageSync(USER_KEY);
  sessionExpiredHandler?.();
}
```

**2. `stores/auth.ts`**

静态导入 `onSessionExpired`，并在模块顶层注册（回调延迟到 401 触发时才 `useAuthStore()`，此时 pinia 必然已初始化）：

```ts
import { onSessionExpired } from "@/services/request";

onSessionExpired(() => {
  useAuthStore().logout();
});
```

依赖方向变为单向：`stores/auth → services/request`，`services/request` 不再引用任何 store，循环被打破。

### 备选方案（不采用）

`clearAuth()` 内改为 `await import("@/stores/auth")` 动态加载。小程序端 `import()` 支持性不确定，且 `clearAuth` 需变异步，故不采用。

## 修复后效果

| 项 | 修复前 | 修复后 |
|----|--------|--------|
| `Circular chunk` 构建警告 | 存在 | 消失 |
| 401 后 auth store 内存态 | 由 `useAuthStore().logout()` 重置 | 由回调 `onSessionExpired → logout()` 重置（行为一致） |
| 网络层对 store 依赖 | `stores/auth` + `stores/app` | 仅 `stores/app`（不参与环） |

## 测试要点

1. `pnpm build:mp-weixin` 无 `Circular chunk` 警告
2. token 过期触发 401 → 页面仍切换到游客引导（回调链路生效）
3. 登录功能正常（auth store 内登录链路不受影响）