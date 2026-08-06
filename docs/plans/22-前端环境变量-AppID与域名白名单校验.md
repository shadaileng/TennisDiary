> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 22 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-06 |
> | 对应功能/内容 | 前端环境变量：微信小程序 appid 注入 + 域名白名单校验开关 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-06 | v1.0.0 | 初版 |
>
> **关联文档**：[Step 21：前后端 `.env` 配置模板](./21-环境变量配置模板.md) · [Phase1-7：网络层封装](./19-Phase1-7-网络层封装.md) · 参考实现：[shadaileng/tarot](https://github.com/shadaileng/tarot)

# Step 22：前端环境变量 — AppID 注入与域名白名单校验

## 一、目标

1. 微信小程序 `appid` 从环境变量读取，构建期自动写入 `project.config.json`
2. 域名白名单校验开关（`setting.urlCheck`）随环境切换（开发 `false` / 生产 `true`）
3. 构建期变量采用**非 `VITE_` 前缀**（`TD_*`），避免打入 `import.meta.env` / 打包产物
4. 全部 `.env*` 文件不提交，仅保留 `.env.example` 模板

## 二、决策记录

| 决策点 | 结论 |
|---|---|
| appid 注入方式 | 参照 [tarot](https://github.com/shadaileng/tarot)：Vite 内联插件 `closeBundle` 改写**构建产物** `dist/{dev\|build}/mp-weixin/project.config.json`，不改 `src/manifest.json`（零依赖，无 git 污染） |
| 变量前缀 | 构建期变量用 `TD_APPID` / `TD_URL_CHECK`（非 `VITE_`，插件经 `loadEnv(..., '', '')` 读取） |
| 域名白名单校验 | 即微信开发者工具 `setting.urlCheck` 布尔开关，随环境注入 `project.config.json` |
| `.env*` 是否提交 | 全部忽略，仅 `.env.example` 可提交（补齐根 `.gitignore` 未覆盖的 `.env.development` / `.env.production`） |

## 三、技术方案

### 3.1 环境变量

新增构建期变量（非 `VITE_` 前缀）：

| 变量 | 说明 | 示例 |
|---|---|---|
| `TD_APPID` | 微信小程序 AppID（登录 https://mp.weixin.qq.com 获取） | `wxxxxxxxxxxxxxxx` |
| `TD_URL_CHECK` | 域名白名单校验开关（`false` 开发 / `true` 生产） | `false` |

- 运行时变量 `VITE_API_BASE_URL` / `VITE_REQUEST_TIMEOUT` 保持不变
- 支持 `.env` + `.env.development` / `.env.production` 覆盖（Vite 按 mode 加载）

### 3.2 Vite 内联插件（参照 tarot）

在 `miniapp/vite.config.ts` 新增 `injectAppidPlugin()`：

- `closeBundle()` 钩子：`loadEnv(process.env.NODE_ENV || 'development', process.cwd(), '')` 读取 `TD_APPID` / `TD_URL_CHECK`
- 按 `NODE_ENV` 定位产物目录：`production` → `dist/build/mp-weixin`，否则 → `dist/dev/mp-weixin`
- 读取该目录下 `project.config.json`，写入 `appid` 与 `setting.urlCheck`
- `TD_APPID` 为空则跳过；文件不存在 / 解析失败静默忽略（H5 构建不受影响）

### 3.3 依赖

新增 devDependency `@types/node`（`vite.config.ts` 使用 `node:path` / `node:fs` / `process` 类型）。

## 四、产出物

### 修改文件（5 个）

| 文件 | 改动 |
|---|---|
| `miniapp/.env.example` | 新增 `TD_APPID` / `TD_URL_CHECK` 说明与示例 |
| `miniapp/vite.config.ts` | 新增 `injectAppidPlugin`（构建期注入 appid + urlCheck） |
| `miniapp/.gitignore` | 忽略 `.env` / `.env.*`，保留 `!.env.example` |
| `miniapp/package.json` | 新增 devDependency `@types/node` |
| `README.md` | 环境变量表补 `TD_APPID` / `TD_URL_CHECK` + 微信后台 request 合法域名提醒 |
| `AGENTS.md` | 编码规范补前端构建期环境变量约定 |

## 五、验收标准

- [ ] 配置 `TD_APPID=wx...` 后 `pnpm build:mp-weixin`，产物 `dist/build/mp-weixin/project.config.json` 的 `appid` 正确
- [ ] `TD_URL_CHECK=true` 时产物 `setting.urlCheck` 为 `true`；默认 / `false` 时为 `false`
- [ ] 不配置 `TD_APPID` 构建不报错（插件静默跳过）
- [ ] `pnpm build:h5` 构建正常（无 `project.config.json`，插件跳过）
- [ ] `pnpm type-check` 通过
- [ ] `git check-ignore .env.development` 命中（不再跟踪）

## 六、提交拆分

1. `feat(miniapp): 构建期注入微信 appid 与 urlCheck 开关`
2. `docs: 更新 CHANGELOG 与 AGENTS.md（AppID 注入完成）`
