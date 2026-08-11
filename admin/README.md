# Tennis Diary Admin 管理端

Vue 3 + TypeScript + Vite 构建的管理后台 SPA。支持 **Cloudflare Workers** 与 **Docker/Nginx** 两种部署方式。

## 环境准备

```bash
pnpm install
```

Node 运行时建议 ≥ 22.12（参考仓库根 `.nvmrc` 固定 `24`）。

## 开发

```bash
pnpm dev
# 或 cd admin && pnpm dev
```

本地开发 `vite.config.ts` 已配置 `/api` 代理到 `http://localhost:8000`。

## 环境变量

复制 `.env.example` 为 `.env` 并按需修改：

| 变量 | 说明 |
|------|------|
| `VITE_APP_TITLE` | 应用标题 |
| `VITE_APP_VERSION` | 应用版本 |
| `VITE_API_BASE_URL` | 后端 API 地址（**构建期内联**，改后需重新构建） |
| `BUILD_BASE` | （构建期）前端资源 base，默认 `/`；Nginx 挂 `/admin/` 时设为 `/admin/` |

## 构建

### 默认构建（Cloudflare Workers，`base=/`）

```bash
pnpm build
```

### Nginx 构建（`base=/admin/` 特例）

```bash
pnpm build:nginx
```

> 两套构建产物互不影响，发布前必须用**对应脚本**，勿混用，否则静态资源 404。

## 部署方式

### 方式一：Cloudflare Workers（纯 Workers 静态托管）

API 网关由独立 Worker `tennis-diary-proxy`（见仓库 `proxy/`）承担，本 Worker 仅托管静态资源，无 API 转发逻辑。

```bash
cd admin
npx wrangler login          # 授权 Cloudflare 账号
pnpm build                  # base=/，供 Workers
npx wrangler deploy         # 读取 wrangler.toml（assets.directory=./dist）
```

- Worker 入口 `admin/worker/index.ts`：经 `ASSETS` 绑定伺服 `dist/`，处理 SPA history 路由 fallback 与静态资源长缓存。
- `wrangler.toml`：`main = "worker/index.ts"` + `assets = { directory = "./dist", binding = "ASSETS" }`。
- 部署后输出形如 `https://tennis-diary-admin.{account}.workers.dev`。
- 生产建议绑定已备案自定义域名（`*.workers.dev` 大陆不稳定）。

### 方式二：Docker + Nginx（挂 `/admin/` 子路径）

```bash
cd admin
docker build -t tennis-diary-admin .
docker run -p 8080:80 tennis-diary-admin
```

`Dockerfile` 使用 `npm run build:nginx` 构建（`base=/admin/`），`nginx.conf` 已配置 history 路由 fallback、静态资源缓存与 `/api` 反向代理。

## CI（可选）

仓库 `.github/workflows/deploy-admin-workers.yml` 提供了基于 `cloudflare/wrangler-action@v3` 的自动部署，需配置：

- **Secrets**：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`
- **Variables**：`VITE_API_BASE_URL`
