> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 54-Admin-7 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-21 |
> | 对应功能/内容 | 后台管理前端测试与部署 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
> | 2026-08-21 | v1.1.0 | 部署方案改为 Cloudflare Workers Pages/Assets 托管，修复 SPA 子路径白屏问题 |
>
> **关联文档**：[Phase Admin 后台管理前端总纲](./47-Admin-后台管理前端.md)

# Phase Admin-7：测试与部署

## 一、目标

配置 Cloudflare Workers Pages/Assets 部署方案，编写部署文档。

## 二、已完成内容

- 创建 Cloudflare Workers 配置（wrangler.toml）
- 创建 CI/CD 工作流（.github/workflows/deploy-admin-workers.yml）
- 创建 Dockerfile（Nginx 备用方案）
- 创建 .env.example 环境变量模板
- 修复 SPA 子路径白屏问题（改用 Pages/Assets 托管）

## 三、部署方式

### 3.1 本地开发

```bash
cd admin
pnpm install
pnpm dev
```

访问 `http://localhost:5173`

### 3.2 构建生产版本

```bash
pnpm build
```

构建产物在 `dist/` 目录。

### 3.3 Cloudflare Workers 部署（推荐）

```bash
cd admin
pnpm build
pnpm cf:deploy
```

或手动部署：
```bash
pnpm build && npx wrangler deploy
```

**wrangler.toml 配置**：
```toml
name = "tennis-diary-admin"
compatibility_date = "2024-01-01"

[assets]
directory = "./dist"
not_found_handling = "single-page-application"
```

`not_found_handling = "single-page-application"` 会自动处理 SPA 路由 fallback，所有未匹配的请求返回 `index.html`。

### 3.4 GitHub Actions CI/CD

push 到 master 分支自动触发部署：
```yaml
# .github/workflows/deploy-admin-workers.yml
name: Deploy Admin to Cloudflare Workers
on:
  push:
    branches: [master]
    paths: ['admin/**', '.github/workflows/deploy-admin-workers.yml']
  workflow_dispatch:
# ...
```

### 3.5 Nginx 部署（备用）

1. 将 `dist/` 目录内容复制到 Nginx 的 html 目录
2. 配置 Nginx（参考 `nginx.conf`）
3. 重启 Nginx

### 3.6 Docker 部署（备用）

```bash
cd admin
docker build -t tennis-diary-admin .
docker run -p 80:80 tennis-diary-admin
```

## 四、环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| VITE_APP_TITLE | 应用标题 | Tennis Diary Admin |
| VITE_APP_VERSION | 应用版本 | 1.0.0 |
| VITE_API_BASE_URL | API地址 | `http://localhost:8000` |

## 五、提交规范

```bash
chore(admin): 配置 Cloudflare Workers 部署方案

- 创建wrangler.toml配置
- 创建CI/CD工作流
- 创建Dockerfile（备用）
- 修复SPA子路径白屏问题
```