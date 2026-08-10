> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 67 |
> | 文档版本 | v1.3.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-10 |
> | 对应功能/内容 | 用 Cloudflare Workers 反向代理魔搭 ModelScope 后端，解决跨域/鉴权头/CORS 问题 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-10 | v1.3.0 | 部署命令优化：从 `.dev.vars` 一步注入 UPSTREAM secret + 部署；新增 `proxy/README.md` |
> | 2026-08-10 | v1.2.0 | 代码已实现：`proxy/` 目录（package.json / tsconfig / wrangler.toml / src/index.ts / .dev.vars.example / .gitignore） |
> | 2026-08-10 | v1.1.0 | 脱敏：UPSTREAM 使用 `env.UPSTREAM` 环境变量（wrangler secret / .dev.vars），移除硬编码域名 |
> | 2026-08-10 | v1.0.0 | 初版（方案分析 + 代码设计，暂不实施） |
>
> **关联文档**：[65-Server 部署方案-ModelScope 创空间](./65-Server部署方案-ModelScope-创空间.md) · [66-ModelScope部署鉴权头兼容改造](./66-ModelScope部署鉴权头兼容改造.md)

# Phase 67：Cloudflare Workers 代理 ModelScope 方案

## 一、背景与问题

### 1.1 现象

admin 前端（CloudStudio dev server，`5173` 端口）调用魔搭线上后端
`https://{owner}-{studio}.ms.show` 时，浏览器报 CORS 预检失败：

```
Request header field x-auth-token is not allowed by
Access-Control-Allow-Headers in preflight response.
```

即 `OPTIONS /api/admin/auth/me` 预检响应的 `Access-Control-Allow-Headers`
中不包含 `X-Auth-Token`，浏览器因此拒绝后续真实请求。

### 1.2 根因

- 后端 FastAPI 本身 CORS 已配置 `allow_headers=["*"]`（`server/app/main.py:150`），**无误**。
- 但 `.ms.show` 域名背后是**魔搭平台网关**（反向代理），网关很可能**自行处理 `OPTIONS` 预检**并返回固定白名单 CORS 头，未透传到 FastAPI，白名单里没有 `X-Auth-Token`。
- 这与 Phase 66 确认的「网关占用 `Authorization`」是**同一类问题**：魔搭网关对请求头/跨域有自己的一套规则，后端 `allow_headers=["*"]` 无法影响网关层。

### 1.3 目标

引入一层**可完全自定义 CORS 头的代理**，使浏览器只与该代理通信，绕开魔搭网关对预检与自定义头的限制。本方案评估 **Cloudflare Workers** 作为该代理的可行性、实现方式与限制，并给出落地文档（**暂不实施**）。

## 二、方案可行性结论

**技术可行，但需按用途区分。** Cloudflare Workers 作为 API 反向代理 + CORS 网关，能解决当前 admin 联调跨域问题，但对生产小程序（大陆访问 + 已备案域名）存在明显局限。

### 2.1 为什么能解决当前 CORS 问题

```
admin 前端 (5173)
   │  (浏览器只与 Worker 通信，CORS 由 Worker 返回)
   ▼
Cloudflare Worker  ← 唯一被浏览器访问的源
   │  (服务器端转发，无浏览器 CORS 限制)
   ▼
魔搭 .ms.show 后端
```

- 浏览器**只和 Worker 通信**，CORS 头由 Worker 自定义，可自由加入 `x-auth-token`、`Content-Type` 等。
- Worker → 魔搭的转发是**服务器端请求**，不存在浏览器 CORS 限制，`X-Auth-Token` 原样透传即可（Phase 66 已确认后端用它鉴权）。

### 2.2 能力对比

| 维度 | Cloudflare Workers | Nginx 反代 | CloudStudio 直连 |
|------|:--:|:--:|:--:|
| 成本 | 免费（`workers.dev`） | 需自备服务器/域名 | 免费 |
| 部署速度 | 分钟级 | 需建站配置 | 分钟级 |
| CORS 头自定义 | ✅ 完全可控 | ✅ 完全可控 | 依赖平台 |
| 绕过魔搭网关占用 | ✅（服务器端转发） | ✅ | 不适用（同平台） |
| 大陆访问稳定性 | ❌ `workers.dev` 被墙 | ✅（需已备案） | ✅ |
| 小程序合法域名 | 需已备案自定义域名 | 需已备案自定义域名 | 需已备案 |

### 2.3 关键限制（易踩坑）

| 注意点 | 说明 |
|--------|------|
| **免费版无大陆节点** | `workers.dev` 子域名在大陆被墙/不稳定；免费版大陆访问走境外节点，延迟高。对 admin 开发期联调无碍，对生产小程序不理想。 |
| **自定义域名需过 CF 代理** | 绑定自定义域名（如 `api.yourdomain.com`）必须通过 Cloudflare 代理才生效，且免费版已不再支持自定义域名路由到 Worker（2025 起免费版需绑定 CF 托管域名）。 |
| **免费版请求头透传** | 默认会剥离部分 `CF-*` / 受保护头，但 `x-auth-token` 是普通自定义头，默认透传，一般无碍。 |
| **魔搭对服务端请求的限制未知** | 需先 curl 验证魔搭后端对 `X-Auth-Token` 的服务端透传是否正常（见第六节）。若网关连服务端请求也拦截（如同 `Authorization`），则 Workers 也救不了。 |

## 三、架构设计

### 3.1 目标架构

```
浏览器（admin 前端 / 小程序）
   │  Worker URL（免费 `xxx.workers.dev` 或自备已备案域名）
   ▼
Cloudflare Worker
   ├── 处理 OPTIONS 预检 → 返回自定义 CORS 头（204）
   └── 转发 GET/POST/... → 原样透传 `X-Auth-Token` 等请求头
          │
          ▼
   魔搭 .ms.show（服务器端转发，无 CORS 限制）
```

### 3.2 需要透传的头部

| 头部 | 处理方式 |
|------|---------|
| `X-Auth-Token` | 原样透传（后端鉴权用，Phase 66） |
| `Content-Type` | 原样透传（POST body 必需） |
| `Origin` | 由 Worker 覆盖为魔搭域或透传（转发时按需） |
| `Cookie` / 其他 | 按需透传，鉴权链路不需要 |

## 四、核心代码设计（参考实现）

> 以下为**已实现代码**的说明。Worker 核心是一个带自定义 CORS 头的反向代理。

### 4.0 产出文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 包配置 | `proxy/package.json` | pnpm 包（已加入 workspace） |
| TypeScript 配置 | `proxy/tsconfig.json` | ES2022 + bundler 模块 |
| Wrangler 配置 | `proxy/wrangler.toml` | Worker 名称、入口、vars 占位 |
| Worker 入口 | `proxy/src/index.ts` | CORS 预检处理 + 反向代理转发 |
| 本地变量模板 | `proxy/.dev.vars.example` | UPSTREAM 注入模板 |
| Git 忽略 | `proxy/.gitignore` | 忽略 node_modules / .dev.vars / .wrangler |

### 4.1 `wrangler.toml`

```toml
name = "tennis-diary-proxy"
main = "src/index.ts"
compatibility_date = "2024-01-01"

# 目标上游（魔搭创空间域名），通过 wrangler secret 设置或 .dev.vars 注入
[vars]
# UPSTREAM  = "https://{owner}-{studio}.ms.show"

# 免费档 0 请求限制；生产建议绑定自定义域名后调整用量
```

### 4.2 `src/index.ts`

```ts
// 从 wrangler.toml [vars] 或 .dev.vars 注入（生产建议用 wrangler secret）
// 用法：wrangler secret put UPSTREAM

interface Env {
  UPSTREAM: string
}

const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token, Authorization",
  "Access-Control-Max-Age": "86400",
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // 处理预检请求：网关由 Worker 接管，返回自定义 CORS 头
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS })
    }

    // 构造上游请求：保留路径 + 全部请求头（含 X-Auth-Token）
    const url = new URL(request.url)
    const upstreamUrl = env.UPSTREAM + url.pathname + url.search
    const upstreamReq = new Request(upstreamUrl, {
      method: request.method,
      headers: request.headers,          // 原样透传
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
    })

    // 转发并原样透传响应体，仅附加 CORS 头
    const resp = await fetch(upstreamReq)
    const newResp = new Response(resp.body, resp)
    Object.entries(CORS_HEADERS).forEach(([k, v]) => newResp.headers.set(k, v))
    return newResp
  },
}
```

### 4.3 部署命令（参考）

```bash
cd proxy && pnpm init -y
cd proxy && pnpm add -D wrangler @cloudflare/workers-types

# 本地开发：创建 .dev.vars 注入上游地址
echo 'UPSTREAM=https://{owner}-{studio}.ms.show' > .dev.vars

npx wrangler login                              # 授权 Cloudflare 账号

# 生产部署：从 .dev.vars 注入 UPSTREAM secret 并一步部署
source .dev.vars && echo -n "$UPSTREAM" | npx wrangler secret put UPSTREAM && pnpm run deploy
# 输出形如 https://tennis-diary-proxy.xxx.workers.dev

# 注意：pnpm 内置 deploy 命令与 npm scripts deploy 重名，须用 pnpm run deploy
```

### 4.4 前端接入方式（参考）

将 `admin/.env` 与 `miniapp` 对应环境变量的 `VITE_API_BASE_URL` 指向 Worker URL：

```bash
# admin/.env
VITE_API_BASE_URL=https://tennis-diary-proxy.{your-account}.workers.dev
```

## 五、方案对比与选型建议

| 方案 | 适用场景 | 建议 |
|------|---------|------|
| **Workers（workers.dev 免费）** | admin 开发期联调、临时 API 网关 | ✅ 当前首选，轻量免费 |
| **Workers（绑定已备案自定义域名）** | 需要稳定 API 域名 + 已备案 | 可作生产网关，但需过 CF 代理 |
| **Nginx 反代（自备已备案域名）** | 小程序生产（大陆直连） | ✅ 生产首选，一劳永逸 |
| **CloudStudio 后端直连** | 开发期最快联调 | ✅ 最快，文档 6「备选方案（二）」已验证 |

**优先级建议**：
1. **立即**：admin 联调若嫌 CORS 烦，先切回 CloudStudio 后端（最快）。
2. **短期**：用 Workers 免费版做 CORS 网关，验证魔搭线上接口。
3. **中长期**：微信小程序生产仍需自备已备案域名 + Nginx 反代（Workers 免费版无大陆节点、`workers.dev` 被墙）。

## 六、前置验证（决定是否落地）

在实施前，先用 curl 模拟 Worker 的服务器端转发，确认魔搭后端对 `X-Auth-Token` 的服务端透传正常：

```bash
# 1. 模拟预检（观察网关是否拦截 OPTIONS 及 CORS 头）
curl -i -X OPTIONS https://{owner}-{studio}.ms.show/api/admin/auth/me \
  -H "Origin: https://tennis-diary-proxy.xxx.workers.dev" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: x-auth-token"

# 2. 模拟服务端转发（带 X-Auth-Token 的 GET，先登录拿 token）
curl -i https://{owner}-{studio}.ms.show/api/admin/auth/me \
  -H "X-Auth-Token: <你的token>"
```

- 若第 2 步返回 **200** → Workers 方案可完整落地。
- 若被网关拦截（如同 `Authorization`）→ Workers 也救不了，需彻底绕开 `.ms.show`（自建后端或 Nginx 反代）。

## 七、风险与注意事项

1. **免费版 `workers.dev` 大陆不可达**：微信小程序用户访问会受影响，仅适合 admin/开发联调。
2. **免费版自定义域名路由限制**：生产建议使用已备案域名 + Nginx 反代而非 Workers 免费版。
3. **魔搭网关服务端转发行为未验证**：需先执行第六节验证，再决定是否实施。
4. **`X-Auth-Token` 透传**：Workers 默认透传普通自定义头，若被 CF 剥离可显式在 `fetch` 时用 `request.headers` 重建。
5. **不纳入后端代码改动**：本方案纯前端/边缘层，后端 `allow_headers=["*"]` 已足够，无需改动。

## 八、提交规范（实施时参考）

```bash
docs(server): 添加 Cloudflare Workers 代理 ModelScope 方案
```

## 九、当前状态说明（2026-08-10）

- **状态**：✅ 已完成（代码已实现，`proxy/` 目录包含所有文件，类型检查通过）。
- **结论**：Workers 技术可行，适合 admin 开发期 CORS 网关；生产小程序仍建议自备已备案域名反代。
- **待办**：按第六节先 curl 验证魔搭对 `X-Auth-Token` 的服务端透传，确认后 `source .dev.vars && echo -n "$UPSTREAM" | npx wrangler secret put UPSTREAM && pnpm run deploy` 即可上线。
