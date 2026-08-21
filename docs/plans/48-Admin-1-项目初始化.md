> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 48-Admin-1 |
> | 文档版本 | v2.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-21 |
> | 对应功能/内容 | 后台管理前端项目初始化（Vite + Vue 3 + TypeScript + Tailwind CSS） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
> | 2026-08-21 | v2.0.0 | 根据实际代码更新：技术栈升级、部署改为 Cloudflare Workers |
>
> **关联文档**：[Phase Admin 后台管理前端总纲](./47-Admin-后台管理前端.md)

# Phase Admin-1：项目初始化

## 一、目标

创建 admin 目录，初始化 Vite + Vue 3 + TypeScript 项目，配置 Tailwind CSS、Vue Router、Pinia，建立基础目录结构和通用组件。

## 二、前置条件

- Phase B2 已完成（后台管理API全部就绪）
- Node.js ≥ 22.12

## 三、详细执行步骤

### 3.1 创建 admin 目录并初始化项目

```bash
cd /workspace
pnpm create vite admin --template vue-ts
cd admin
pnpm install
```

### 3.2 安装依赖

```bash
# 核心依赖
pnpm add vue-router@4 pinia axios dayjs @heroicons/vue

# 开发依赖
pnpm add -D tailwindcss@3 postcss autoprefixer @tailwindcss/forms @cloudflare/workers-types
npx tailwindcss init -p
```

### 3.3 配置 Tailwind CSS

**tailwind.config.js**：
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        olive: {
          50: '#f8f7f4',
          100: '#f0ede6',
          200: '#e2dccb',
          300: '#cfc5a8',
          400: '#bba985',
          500: '#a8906a',
          600: '#9b7e5e',
          700: '#81664e',
          800: '#6a5443',
          900: '#574639',
          950: '#2e241d',
        },
        lime: {
          50: '#f7fce4',
          100: '#ecf8c5',
          200: '#daf196',
          300: '#c0e55e',
          400: '#a8d634',
          500: '#8bbf16',
          600: '#6b9a0e',
          700: '#51740f',
          800: '#425c13',
          900: '#394e16',
          950: '#1d2b07',
        },
      },
    },
  },
  plugins: [],
}
```

**src/styles/main.css**：
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 3.4 配置 Vue Router

**src/router/index.ts**：
```typescript
import { createRouter, createWebHistory } from 'vue-router'
import routes from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('admin_token')
  
  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  if (to.name === 'Login' && token) {
    next({ name: 'Dashboard' })
    return
  }
  
  next()
})

export default router
```

### 3.5 配置 Pinia

**src/stores/index.ts**：
```typescript
import { createPinia } from 'pinia'

const pinia = createPinia()

export default pinia
```

### 3.6 配置路径别名

**vite.config.ts**：
```typescript
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const base = mode === 'production' ? (env.BUILD_BASE ?? '/') : '/'

  return {
    plugins: [vue()],
    base,
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
```

### 3.7 配置环境变量

**.env**：
```
VITE_APP_TITLE=Tennis Diary Admin
VITE_APP_VERSION=1.0.0
VITE_API_BASE_URL=http://localhost:8000
```

**src/env.d.ts**：
```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_ADMIN_BASE: string
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_VERSION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

### 3.8 配置 Cloudflare Workers 部署

**wrangler.toml**：
```toml
name = "tennis-diary-admin"
compatibility_date = "2024-01-01"

[assets]
directory = "./dist"
not_found_handling = "single-page-application"
```

### 3.9 创建基础目录结构

```
admin/src/
├── api/                  # API接口
│   └── index.ts          # axios实例
├── components/           # 公共组件
│   ├── layout/           # 布局组件
│   │   └── MainLayout.vue
│   └── common/           # 通用组件
├── router/               # 路由配置
│   ├── index.ts
│   └── routes.ts
├── stores/               # Pinia状态
│   ├── index.ts
│   └── auth.ts
├── styles/               # 样式
│   └── main.css
├── types/                # TypeScript类型
│   └── api.ts
├── views/                # 页面视图
│   ├── login/
│   │   └── index.vue
│   └── dashboard/
│       └── index.vue
├── App.vue
└── main.ts
```

## 四、验收标准

| 验收项 | 标准 |
|--------|------|
| 项目初始化 | `pnpm dev` 启动成功 |
| Tailwind CSS | 自定义 olive/lime 颜色可用 |
| Vue Router | 路由跳转正常，未登录重定向到登录页 |
| Pinia | 状态管理正常 |
| 路径别名 | `@/` 别名可用 |
| Cloudflare Workers | `wrangler.toml` 配置正确 |

## 五、提交规范

```bash
feat(admin): 初始化后台管理前端项目

- 创建admin目录结构
- 配置Vite + Vue 3 + TypeScript
- 配置Tailwind CSS（olive/lime主题色）
- 配置Vue Router和Pinia
- 配置Cloudflare Workers部署
```
