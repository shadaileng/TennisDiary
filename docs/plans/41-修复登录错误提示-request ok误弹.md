> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 41 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 修复小程序对后台错误的处理不正确：后端 500 时 toast 误弹无意义「request:ok」，登录 401 误触发登出引导 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
> | 2026-08-08 | v1.0.0 | 实施完成（`parseDetail` 去掉 `errMsg` 兜底 + 登录接口禁止 `handle401`） |
>
> **关联文档**：[Phase1-7：网络层封装](./19-Phase1-7-网络层封装.md) · [Step 38：修复登录时序与用户资料编辑](./38-修复登录时序与用户资料编辑-参考tarot.md)

# 41：修复小程序对登录错误的处理不正确（"request:ok" 误弹）

## 一、背景与根因定位

### 1.1 问题现象

点击「微信一键登录」，后台返回 5xx/4xx 时，小程序 toast 弹出的竟是 **"request ok"**，而非后端真实错误；登录失败（如 `code` 过期返回 401）时还会弹出「请到『我的』页登录后使用」的登出引导，干扰真实错误提示。

### 1.2 根因一：`parseDetail` 错误兜底到 `res.errMsg`

`uni.request` 的 `success` 回调只要**HTTP 有响应**就会触发，此时 `res.errMsg` **恒为 `"request:ok"`**，与 HTTP 状态码无关。而 `request.ts` 的 `parseDetail` 在取不到 `detail`/`message` 时直接回退到 `res.errMsg`：

```ts
// 修复前 miniapp/src/services/request.ts
function parseDetail(res: any): string {
  return (
    (res?.data?.detail) ||
    (res?.data?.message) ||
    (res?.errMsg) ||      // ← 无论成功失败都是 "request:ok"，错误提示失真
    "请求失败"
  );
}
```

于是后端错误响应（尤其是 body 无 `detail` 的场景，如部分兜底错误）都会被渲染成无意义的 `request ok`。

### 1.3 根因二：登录请求被当 401 登出处理

登录接口 `auth:false`，但 `handle401` 沿用默认 `true`。当登录因 code 失效返回 401 时，`request.ts` 会执行 `clearAuth()` + `promptLogin()`，先弹「请到『我的』页登录后使用」，再被页面的 catch 弹真实错误，toast 相互覆盖、语义混乱。

## 二、目标

1. 登录失败时 toast 展示后端真实错误（`detail`/`message`），绝不再出现 "request ok"。
2. 登录接口的 401 不再触发全局登出引导，交由调用方直接展示错误。

## 三、方案设计

### 3.1 `parseDetail` 重构（`miniapp/src/services/request.ts`）

移除 `res.errMsg` 兜底，改为：`detail`/`message` → 非 JSON 文本 → 基于状态码的通用提示：

```ts
function parseDetail(res: any): string {
  const data = res?.data;
  if (data && typeof data === "object") {
    const detail = data.detail ?? data.message;
    if (typeof detail === "string" && detail.trim()) return detail.trim();
    if (Array.isArray(detail) && detail.length) return JSON.stringify(detail);
  }
  if (typeof data === "string" && data.trim()) return data.trim();
  const status = res?.statusCode;
  return status != null && status >= 400 ? `请求失败（HTTP ${status}）` : "请求失败";
}
```

- `data` 为对象 → 取 `detail ?? message`（含数组型校验错误 `JSON.stringify`）
- `data` 为非 JSON 字符串（如后端纯文本错误）→ 原样展示
- 以上都没有 → 基于 `statusCode` 展示通用 `请求失败（HTTP xxx）`，不再出现无意义 errMsg

### 3.2 登录请求禁止 `handle401`（`miniapp/src/services/auth.ts`）

```ts
export function login(data: LoginRequest): Promise<LoginResponse> {
  // 登录接口无需携带 Authorization；401 属登录失败，交由调用方展示，不触发全局登出引导
  return post<LoginResponse>("/auth/login", data, { auth: false, handle401: false });
}
```

## 四、测试方案

前端无单测基建，以 `type-check` 与构建验证为准：

| 校验项 | 命令 | 结果 |
|---|---|---|
| 类型检查 | `pnpm type-check` | ✅ 通过 |
| （小程序端）真机/开发者工具复现 | 登录 5xx → toast 显示后端真实错误；登录 401 → 仅显示错误，无登出引导 | 按实际结果验收 |

## 五、验收标准

1. 后端返回 500 时，toast 展示后端 `detail`（如 `Internal Server Error`）或 `请求失败（HTTP 500）`，不再为 `request ok`。
2. 后端返回 401（code 失效）时，仅展示真实错误，不触发「请到『我的』页登录后使用」。
3. `services/auth.ts` 的 `login` 保持 `auth: false`、`handle401: false`。
4. `pnpm type-check` 通过。

## 六、实施步骤

1. **重构 `parseDetail`**：移除 `errMsg` 兜底，改为对象/文本/状态码三级降级。
2. **登录请求**：`login()` 传 `handle401: false`。
3. **验证**：`pnpm type-check` 通过。
4. **更新状态**：本方案文档标记 ✅ 已完成。