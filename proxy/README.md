# Tennis Diary Proxy

基于 Cloudflare Workers 的反向代理，解决魔搭 ModelScope 后端跨域（CORS）和自定义鉴权头透传问题。

## 架构

```
浏览器（admin 前端）
   │  CORS 由 Worker 接管，可自由添加 X-Auth-Token
   ▼
Cloudflare Worker（本项目）
   │  服务器端转发，无浏览器 CORS 限制
   ▼
魔搭 .ms.show 后端
```

## 快速开始

### 1. 安装依赖

```bash
pnpm install
```

### 2. 配置上游地址

```bash
cp .dev.vars.example .dev.vars
# 编辑 .dev.vars，填入魔搭创空间域名
```

### 3. 本地开发

```bash
pnpm dev
```

### 4. 部署到 Cloudflare Workers

```bash
# 首次部署需先登录
npx wrangler login

# 注入上游地址 secret 并一步部署
source .dev.vars && echo -n "$UPSTREAM" | npx wrangler secret put UPSTREAM && pnpm run deploy
```

> **注意**：必须用 `pnpm run deploy` 而非 `pnpm deploy`，因为 pnpm 内置 `deploy` 命令与 npm scripts 重名。

### 5. 前端接入

将 admin 前端的 `VITE_API_BASE_URL` 指向 Worker URL：

```bash
# admin/.env
VITE_API_BASE_URL=https://tennis-diary-proxy.{your-account}.workers.dev
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `src/index.ts` | Worker 入口：处理 OPTIONS 预检（返回自定义 CORS 头）+ 反向代理转发 |
| `wrangler.toml` | Wrangler 配置（Worker 名称、入口、vars 占位） |
| `.dev.vars` | 本地开发环境变量（不纳入版本管理） |
| `.dev.vars.example` | 环境变量模板 |
| `tsconfig.json` | TypeScript 配置（ES2022 + bundler 模块） |

## 相关文档

- [Phase 67：Cloudflare Workers 代理 ModelScope 方案](../docs/plans/67-Cloudflare-Workers-%E4%BB%A3%E7%90%86-ModelScope-%E6%96%B9%E6%A1%88.md)
