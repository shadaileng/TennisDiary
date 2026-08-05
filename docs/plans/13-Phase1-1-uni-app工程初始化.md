> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 12-Phase1-1 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-05 |
> | 对应功能/内容 | uni-app 工程初始化 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase1：uni-app 小程序前端工程初始化](./12-Phase1-uni-app小程序前端工程初始化.md) · [B1-1：FastAPI 项目初始化与目录结构](./02-B1-1-FastAPI项目初始化与目录结构.md)

# Step Phase1-1：uni-app 工程初始化

## 一、目标

创建 uni-app（Vue 3 + Vite + TypeScript）小程序前端工程骨架，完成基础配置，确保能在微信开发者工具中编译预览。

## 二、前置条件

- Node.js 18+（当前 v22.13.1）已安装
- pnpm 已安装（当前 v10.34.5）
- 微信开发者工具已安装（用于编译预览小程序）

## 三、详细执行步骤

### 3.1 创建 uni-app 工程

使用官方 CLI 的 vite-ts 模板创建 `miniapp` 工程：

```bash
cd /workspace
pnpm create uni@latest miniapp --template vite-ts
# 或使用 degit：
npx degit dcloudio/uni-preset-vue#vite-ts miniapp
```

### 3.2 安装依赖

```bash
cd /workspace/miniapp
pnpm install
```

### 3.3 配置 `src/manifest.json`

- 设置 `name` / `appid`（开发期可用测试号，提审前替换正式 appid）
- 确认 `mp-weixin` 平台配置存在
- `vueVersion: "3"`

### 3.4 加入 pnpm 工作区

在 `/workspace/pnpm-workspace.yaml` 的 `packages` 中追加 `miniapp`：

```yaml
packages:
  - 'docs'
  - 'miniapp'
```

### 3.5 验证编译

```bash
cd /workspace/miniapp
pnpm dev:mp-weixin          # 开发模式编译微信小程序
pnpm build:mp-weixin        # 生产模式构建
```

在微信开发者工具中导入 `dist/dev/mp-weixin` 目录预览。

## 四、产出物

| 文件 | 说明 |
|---|---|
| `miniapp/` 工程目录 | uni-app Vue3+Vite+TS 工程 |
| `miniapp/package.json` | 前端依赖清单 |
| `miniapp/src/manifest.json` | 小程序基础配置 |
| `miniapp/src/pages.json` | 页面与 TabBar 配置（模板默认） |
| `miniapp/src/App.vue` | 应用入口 |
| `miniapp/src/main.ts` | 入口文件 |
| `/workspace/pnpm-workspace.yaml` | 追加 `miniapp` 工作区 |

## 五、验收标准

- [x] `pnpm install` 无报错
- [x] `pnpm dev:mp-weixin` 编译通过
- [x] `pnpm build:mp-weixin` 产出 `dist/build/mp-weixin`
- [ ] 微信开发者工具可正常打开项目并预览默认首页（需人工验证）
- [x] 工程已纳入 pnpm 工作区

## 六、提交拆分

1. `docs: 新增 Phase1-1 uni-app 工程初始化方案`
2. `chore(miniapp): uni-app 工程初始化`
3. `docs: 更新 CHANGELOG 与 AGENTS.md（Phase1-1 完成）`
