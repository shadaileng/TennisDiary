> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 71 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-11 |
> | 对应功能/内容 | Admin 管理端新增 Cloudflare Workers 部署方式 |
> | 关联文档 | [67-Cloudflare-Workers-代理-ModelScope-方案](./67-Cloudflare-Workers-代理-ModelScope-方案.md)、[47-Admin-后台管理前端](./47-Admin-后台管理前端.md)、[54-Admin-7-测试与部署](./54-Admin-7-测试与部署.md) |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-11 | v1.2.0 | 由 Pages 改为**纯 Workers**：`worker/index.ts` + `assets` 绑定 + `wrangler deploy`，移除 `_redirects`/`_headers` |
> | 2026-08-11 | v1.1.0 | 代码已实现：vite.config/package.json/Dockerfile/public/wrangler.toml/CI/文档，构建验证通过 |
> | 2026-08-11 | v1.0.0 | 初版（方案设计，待确认后执行） |

# Step 71：Admin 部署方式 — Cloudflare Workers

## 一、背景与问题

Admin 管理端（Vite + Vue3 + TS SPA）目前**仅支持 Docker/Nginx 部署**（`admin/Dockerfile` + `admin/nginx.conf`），且生产构建 `base` 硬编码为 `/admin/`，前端资源路径固定挂 `/admin/` 前缀。

用户需求：为 admin **新增 Cloudflare Workers 部署方式**。经多次澄清，最终确立关键约束：

| 部署方式 | 前端构建 `base` | 说明 |
|----------|:--:|------|
| **Cloudflare Workers** | `/`（默认） | 独立根路径构建，无需 `/admin/` 前缀 |
| **Nginx** | `/admin/`（显式特例） | 挂 `/admin/` 子路径，仅此方式用该前缀 |

**核心结论**：默认构建（含 Cloudflare Workers）应为根路径 `/`，`/admin/` 是 Nginx 的**特例**，必须通过显式环境变量触发，而非硬编码进默认构建。

## 二、现状问题

`admin/vite.config.ts` 当前生产 `base` 硬编码为 `/admin/`，与 Vue Router 的 `createWebHistory()`（无 base，默认 `/`）存在**静态资源路径与路由 base 不一致**的隐患：

- 静态资源：`/admin/assets/xxx.js`（由 vite `base` 决定）
- 路由：`/login`、`/dashboard` 等（由 router `base` 决定，默认为 `/`）

这在 Nginx 挂 `/admin/` 时恰好能工作（因为 router 实际也在 `/admin/` 下被访问，资源路径对齐）。但对 Cloudflare Workers 根路径部署则不适用——资源会带上 `/admin/` 前缀导致 404。

## 三、设计方案

### 3.1 `vite.config.ts`：默认 `/`，Nginx 特例时显式 `/admin/`

```ts
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  // 非 VITE_ 前缀，仅构建期读取，不注入 import.meta.env 产物
  const env = loadEnv(mode, process.cwd(), '')
  // 默认 /（含 Cloudflare Workers 部署）；Nginx 挂 /admin/ 时用 BUILD_BASE=/admin/
  const base = mode === 'production' ? (env.BUILD_BASE ?? '/') : '/'

  return {
    plugins: [vue()],
    base,
    resolve: {
      alias: { '@': resolve(__dirname, 'src') },
    },
    server: {
      proxy: {
        '/api': { target: 'http://localhost:8000', changeOrigin: true },
      },
    },
  }
})
```

- 默认 `pnpm build`（含 Cloudflare Workers）→ `base='/'`
- Nginx 特例：`BUILD_BASE=/admin/ pnpm build` → `/admin/`

> 关键点：`loadEnv(mode, process.cwd(), '')` 第三参数传 `''`，使 **`BUILD_BASE`（非 `VITE_` 前缀）在构建期可读，但不注入 `import.meta.env` 产物**，避免暴露构建配置到前端包。

### 3.2 `package.json`：新增 `build:nginx` 脚本

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "build:nginx": "export BUILD_BASE=/admin/ && vue-tsc -b && vite build",
    "preview": "vite preview"
  }
}
```

- `pnpm build` → Cloudflare Workers（`/`）
- `pnpm build:nginx` → Nginx（`/admin/`）

### 3.3 Worker 入口：SPA fallback 与静态缓存（`admin/worker/index.ts`）

纯 Workers 方案需一个 Worker 脚本在运行时伺服 `dist/` 产物，并处理 SPA history fallback 与静态资源缓存（这些在 Pages 下由 `_redirects`/`_headers` 自动处理，Workers 下由 Worker 逻辑承担）。

```ts
interface Env {
  ASSETS: Fetcher // Vite 构建产物 dist/（wrangler.toml assets.directory）
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url)

    // 静态资源（带 hash 的构建产物）交给 assets 绑定，附加长缓存头
    if (url.pathname.startsWith("/assets/")) {
      const resp = await env.ASSETS.fetch(request)
      const headers = new Headers(resp.headers)
      if (!headers.has("Cache-Control")) headers.set("Cache-Control", "public, max-age=31536000, immutable")
      return new Response(resp.body, { ...resp, headers })
    }

    // 其余路径：先尝试原样伺服（/favicon.svg 等 public 资源），命中则带 no-cache
    const asset = await env.ASSETS.fetch(request)
    if (asset.status === 200) {
      const headers = new Headers(asset.headers)
      if (!headers.has("Cache-Control")) headers.set("Cache-Control", "public, max-age=0, must-revalidate")
      return new Response(asset.body, { ...asset, headers })
    }

    // SPA history 路由 fallback：所有未命中的路径返回 index.html
    const index = await env.ASSETS.fetch(new Request(new URL("/index.html", url), request))
    const headers = new Headers(index.headers)
    headers.set("Content-Type", "text/html;charset=UTF-8")
    if (!headers.has("Cache-Control")) headers.set("Cache-Control", "public, max-age=0, must-revalidate")
    return new Response(index.body, { ...index, headers })
  },
}
```

> 该文件放 `admin/worker/`（独立于前端 `src/`），避免被 `tsconfig.app.json`（`include: src/**`）纳入 `vue-tsc -b` 检查，与 `proxy/` 的 Worker 写法保持一致。

### 3.4 `wrangler.toml`：纯 Workers 静态资源配置

在 `admin/` 下新建 `wrangler.toml`，使用 Workers Static Assets（`assets` 绑定 + Worker 入口）：

```toml
name = "tennis-diary-admin"
main = "worker/index.ts"
compatibility_date = "2024-01-01"

# Vite 构建产物静态托管：worker/index.ts 经 ASSETS 绑定伺服 dist/
# SPA fallback 与静态资源长缓存由 worker/index.ts 内的 fetch handler 处理
assets = { directory = "./dist", binding = "ASSETS" }
```

> 说明：当前 API 已由独立的 `proxy/` Worker（`tennis-diary-proxy`）承担。admin 静态资源 Worker 只需托管 `dist/` 产物即可，两者相互独立，**无 API 转发逻辑**。

## 四、部署步骤

### 4.1 前置准备

```bash
# 1. 安装 wrangler（admin 目录）
cd admin && npx wrangler login

# 2. 配置 API 地址（构建期内联）
# admin/.env 中设置 VITE_API_BASE_URL，指向已有 proxy Worker 或线上后端
VITE_API_BASE_URL=https://tennis-diary-proxy.{your-account}.workers.dev
```

### 4.2 构建并部署（纯 Workers）

```bash
cd admin
pnpm build                                  # base=/，供 Cloudflare Workers
npx wrangler deploy                         # 读取 wrangler.toml（assets.directory=./dist）
# 输出形如 https://tennis-diary-admin.{account}.workers.dev
```

### 4.3 Nginx 部署（保持不变，特例）

```bash
cd admin
pnpm build:nginx                            # BUILD_BASE=/admin/
docker build -t tennis-diary-admin .
docker run -p 8080:80 tennis-diary-admin
```

## 五、CI 集成（可选）

新增 `.github/workflows/deploy-admin-workers.yml`，用官方 `cloudflare/wrangler-action@v3` 自动构建部署（pnpm workspace，install 在根目录，build 走 `pnpm --filter admin`）：

```yaml
name: Deploy Admin to Cloudflare Workers

on:
  push:
    branches: [master]
    paths:
      - 'admin/**'
      - '.github/workflows/deploy-admin-workers.yml'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 24
          cache: pnpm
          cache-dependency-path: pnpm-lock.yaml
      - name: Install dependencies
        run: pnpm install --frozen-lockfile
      - name: Build
        run: pnpm --filter admin build
        env:
          VITE_API_BASE_URL: ${{ vars.VITE_API_BASE_URL }}
      - name: Deploy to Cloudflare Workers
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: deploy --config admin/wrangler.toml
```

需要配置：
- **Secrets**：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`
- **Variables**：`VITE_API_BASE_URL`

## 六、修改文件清单

| 文件 | 变更 |
|------|------|
| `admin/vite.config.ts` | 生产 `base` 从硬编码 `/admin/` 改为默认 `/`（读 `BUILD_BASE`），Nginx 特例显式 `BUILD_BASE=/admin/` |
| `admin/package.json` | 新增 `build:nginx` 脚本（`export BUILD_BASE=/admin/`）；`cf:deploy` 改为 `wrangler deploy` |
| `admin/Dockerfile` | 构建命令 `npm run build` → `npm run build:nginx`（保持 Nginx `/admin/` 行为） |
| `admin/worker/index.ts` | **新增**：纯 Workers 入口（assets 伺服 + SPA fallback + 静态缓存） |
| `admin/wrangler.toml` | **新增**：`main = "worker/index.ts"` + `assets = { directory = "./dist", binding = "ASSETS" }` |
| `admin/public/_redirects` | **删除**（原 Pages fallback，逻辑并入 worker/index.ts） |
| `admin/public/_headers` | **删除**（原 Pages 缓存头，逻辑并入 worker/index.ts） |
| `admin/.env.example` | 补充 `BUILD_BASE` 说明 |
| `admin/README.md` | 补充 Cloudflare Workers 部署章节 |
| `.github/workflows/deploy-admin-workers.yml` | **新增**：CI 自动构建部署（`deploy --config admin/wrangler.toml`） |

## 七、风险与注意事项

1. **两套构建并存**：`pnpm build`（`/`）与 `pnpm build:nginx`（`/admin/`）互不影响，但**发布前必须用对应脚本**，勿混用产物，否则资源 404。
2. **`VITE_API_BASE_URL` 构建期内联**：更换 API 地址需重新构建，不能运行期改。
3. **大陆访问**：`*.workers.dev` 大陆不稳定（与 Phase 67 结论一致），生产建议绑定已备案自定义域名。
4. **Worker 入口在 `admin/worker/`**：独立于前端 `src/`，避免被 `vue-tsc -b` 纳入 DOM 类型检查。
5. **router base**：根路径部署时 `createWebHistory()` 无需传 base（保持 `/`），与 vite `base='/'` 对齐，无需改动 router。
6. **Nginx 构建用 `export`**：`build:nginx` 用 `export BUILD_BASE=/admin/ &&` 而非内联 `VAR=cmd`，否则 `&&` 后 vite 读不到 env（shell 语义）。
7. **CI 用 `--config admin/wrangler.toml`**：wrangler-action 在仓库根运行，需显式指定 config 路径，其内 `assets.directory`/`main` 均相对该文件解析。

## 八、Nginx Dockerfile 联动（已实施）

`admin/Dockerfile` 构建命令已从 `RUN npm run build` 改为 `RUN npm run build:nginx`，保持 Nginx 挂 `/admin/` 前缀行为不变。Docker 部署流程无需其它改动。

## 九、文档计划（已实施）

- ✅ 本方案文档（`docs/plans/71-*`）
- ✅ `admin/README.md` 新增「Cloudflare Workers 部署」章节
- ✅ `admin/.env.example` 补充 `BUILD_BASE` 说明

## 十、提交规范

```bash
feat(admin): 新增 Cloudflare Workers 部署方式（base 默认 /，Nginx 特例 /admin/）
```
