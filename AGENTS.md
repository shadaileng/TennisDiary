# AGENTS — AI 协作者指南

本文档面向在此项目中工作的 AI 协作者，提供项目上下文和协作规范。

## 项目概览

- **项目名称**：Tennis Diary（网球日记）
- **目标**：将 Tennis Diary Web 版（React PWA）迁移为微信小程序（uni-app + FastAPI）
- **方案文档**：`docs/plans/` 目录，编号 `{序号}-{标题}.md`
- **参考源码**：`docs/reference/tennis-diary/`（原 Web 版，不纳入版本管理）

## 技术栈

| 端 | 技术 |
|---|---|
| 小程序前端 | uni-app（Vue 3 + Vite + TypeScript）+ Pinia + Tailwind CSS（自定义组件） |
| 后端 | FastAPI（Python 3.10+）+ SQLite + SQLAlchemy |
| 依赖管理 | uv（后端）、pnpm（前端/文档） |
| Node 运行时 | **≥ 22.12（建议 24 LTS）**，根目录 `.nvmrc` 固定 `24` |
| 文档 | VitePress |

## 项目结构

```
workspace/
├── server/            # FastAPI 后台（含部署：Docker/oci/modelscope/spaces）
├── miniapp/           # uni-app 小程序前端
├── admin/             # 后台管理前端（Vite + Vue 3）
├── proxy/             # Cloudflare Workers 反向代理（解决魔搭 CORS + 鉴权头透传）
├── docs/
│   └── plans/         # 方案文档（执行索引）
├── .github/
│   ├── workflows/                 # 启用的 CI（当前仅 modelscope 部署）
│   └── workflows-disabled/        # 停用的 CI（HF/OCI 部署，待启用）
├── package.json       # pnpm workspace 根配置
└── pnpm-workspace.yaml
```

## 工作流程

### TDD 模式

1. **写方案文档**：`docs/plans/{编号}-{标题}.md`
2. **RED**：写测试，确认失败
3. **GREEN**：写最小代码使测试通过
4. **REFACTOR**：优化结构，保持测试通过
5. **完成**：方案状态 `📋` → `✅`

### 常用命令

```bash
# 后端
cd server && uv run pytest -v          # 测试
cd server && uv run ruff check .       # lint
cd server && uv run ruff format .      # 格式化
cd server && bash scripts/verify.sh    # 一键验证

# 前端
cd miniapp && pnpm build:mp-weixin     # 构建小程序
cd admin && pnpm build                 # 构建管理端
```

### 提交规范

```
<type>(<scope>): <中文描述>
```

- `feat`：新功能（自动 bump 次版本号）
- `fix`：修复（自动 bump 修订号）
- `docs` / `chore`：文档 / 依赖配置

禁止 `git add .`，禁止无意义消息（`wip`、`tmp`）。

## 编码规范

### 后端

- ORM：SQLAlchemy 声明式，继承 `app.core.database.Base`
- Schema：Pydantic models，定义在 `app/schemas/`
- 路由：`APIRouter`，统一前缀 `/api/`
- 鉴权：所有数据接口依赖 `get_current_user`
- 启动：`cd server && uv run uvicorn app.main:app --reload`

### 前端

- Vue 3 Composition API + `<script setup>`
- 状态管理：Pinia
- 样式：Tailwind CSS（`weapp-tailwindcss`，`rem2rpx` 转换）
- 组件：Tailwind 自定义组件（`src/components/`）
- 环境变量：运行期 `VITE_*`，构建期非 `VITE_` 前缀（`vite.config.ts` 插件注入）

## API 规范

### 统一响应格式

```json
// 成功
{"code": 0, "message": "ok", "success": true, "data": {...}}

// 失败
{"code": 10001, "message": "未登录", "success": false, "data": null}
```

**错误码**：0=成功 | 10000-19999=认证授权 | 20000-29999=参数校验 | 30000-39999=业务逻辑 | 50000-59999=服务器错误

### 鉴权

- 登录：`POST /api/auth/login`，接收 `wx.login` code，返回 JWT
- 请求头：`X-Auth-Token: <jwt>`（魔搭网关占用 `Authorization`，统一改用自定义头）
- 有效期：30 天

### 端点概览

详见 `docs/plans/` 中各方案文档，或启动服务后访问 `/docs`（Swagger）。

- **用户端**：`/api/auth/*`、`/api/diaries`、`/api/gears`、`/api/weights`、`/api/checkin`、`/api/stats`、`/api/files/*`、`/api/upload/*`、`/api/events`
- **管理端**：`/api/admin/auth/*`、`/api/admin/roles`、`/api/admin/admins`、`/api/admin/users`、`/api/admin/diaries`、`/api/admin/gears`、`/api/admin/weights`、`/api/admin/checkins`、`/api/admin/analyses`、`/api/admin/posts`、`/api/admin/system/*`、`/api/admin/events`

## 项目进度

| 阶段 | 内容 | 状态 |
|------|------|:----:|
| Phase B1 | 后台基础接口（11个） | ✅ |
| Phase B2 | 后台管理API（角色/权限/管理员/数据查看/系统监控） | ✅ |
| Phase Admin | 后台管理前端（Vite+Vue3+Tailwind） | ✅ |
| Phase 1 | 小程序基础能力（工程/Tailwind/store/网络/登录） | ✅ |
| Phase 2 | 小程序业务页面（日记/装备/统计/我的） | ✅ |
| Phase 2.5 | 小程序视觉样式与交互适配 | ✅ |
| Phase 2.6 | 小程序样式方案重构（Tailwind→自定义 CSS） | ✅ |
| Phase 2.7 | 输入框与空状态样式优化 | ✅ |
| Phase 59  | 事件锚点与线上事件日志（小程序埋点 + 后台查询 + 管理端页面） | ✅ |
| Phase 61  | 构建警告修复（Sass @import → additionalData + 循环依赖） | ✅ |
| Server-1  | Server 部署方案（Docker + HF Space，代码已实现；HF 已停用） | ⏳ 已归档 |
| Server-2  | Server 部署方案（Oracle Cloud Always Free 免费 VM，代码已实现；待建 VM 启用 CI） | ✅ |
| Server-3  | Server 部署方案（魔搭创空间 ModelScope Studio，代码已实现；当前启用） | ✅ |
| Phase 66  | ModelScope 部署鉴权头兼容改造（后端统一 `X-Auth-Token`，移除 `Authorization` 回退） | ✅ |
| Phase 67  | Cloudflare Workers 反向代理（解决魔搭网关 CORS 预检 + `X-Auth-Token` 透传） | ✅ |
| Fix 2026-08-10 | 小程序表单保存防重复提交、`safeNavigateBack` 栈底回退、`eventLogger` 移除 `require()` 别名解析 | ✅ |
| Phase 68 | Admin 全局 Loading 遮罩（axios 拦截器请求计数器）与提交类操作防重复提交（`useActionLock`） | ✅ |
| Fix 2026-08-11 | Admin 事件日志表格布局优化（移除"页面"列、表头防换行、表格横向滚动、列宽对齐公共 Table 组件） | ✅ |
| Fix 2026-08-11 | 小程序「我的」页「编辑资料」重复跳转修复（移除整卡点击，收敛到右侧箭头 + 底部按钮 `.stop` 阻止冒泡） | ✅ |
| Step 70 | Admin 日记/装备/体重点击行查看详情（公共 Table 增加可选 `rowClickable`、三个页面接入自定义大弹窗、后端补齐体重单条查询接口） | ✅ |
| Step 72 | Admin 备份管理增强（独立元数据库 `backup_meta.db` + 上传/下载/删除联动 + 恢复状态展示） | ✅ |
| Step 73 | 测试体系引入 `.env.test` 实现环境隔离（pytest-env 注入 `APP_ENV=test`、配置环境感知加载、`data_test/` 隔离、autouse 目录隔离 fixture） | ✅ |
| Step 74 | Admin 日志查看倒序分页优化（尾部倒序读取最新优先 + `offset` 游标分页 + `has_more` + 刷新/加载更早/自动轮询） | ✅ |
| 75-B2-Admin | Admin 同步 AI 网关三件套（分析详情完整六维报告 + ai-status/ai-connect/files 三端点 + 分析页模式/封面列 + 健康页 AI 网关卡片） | ✅ |
| 75-1 | AI 评分代理接口 `/api/ai/analyze`（OpenAI 兼容六维评分，Key 服务端，失败本地降级） | ✅ |
| 75-2 | 视频上传与抽帧 `/api/video/upload`（ffmpeg 抽帧，single 7/full 8 帧，imageio-ffmpeg 兜底） | ✅ |
| 75-3 | MediaPipe 姿态推理 `/api/pose/analyze`（33 关键点 + 肘/膝/躯干角，CPU 推理，模型缺失/无人检测降级） | ✅ |
| 75-4 | 分析报告落库 + 历史查询（`POST/GET/DELETE /api/analyses`，`video_url` 列迁移） | ✅ |
| 75-5 | Phase 4 电子教练小程序页（三页：列表/AI 分析/报告，上传/AI/姿态/落库数据层封装） | ✅ |
| 75-6 | Phase 5 分享工坊（三模板 Canvas 卡片 + 保存相册 + 文案复制） | ✅ |
| 78 | 动态配置系统与 Admin 配置页（配置注册表 7 分类 20 项 + system_configs 覆盖表 + AI 三件套在线配置 + 权限 system:config） | ✅ |
| 79 | AI 服务商管理与配置直选（`ai_providers` 表手动维护 + `ai.provider` 下拉直选引用语义，模型可独立覆盖） | ✅ |
| 80 | AI 服务商多模型支持（`models` JSON 列表，默认模型=首项；配置页服务商→模型二选下拉，`ai.model` 覆盖全局优先） | ✅ |
| 81 | AI 模型可用性校验与调试脚本（`check-models` list/probe 两级端点 + Admin 校验按钮 + `server/scripts/debug-ai.py` 直连生效配置调试） | ✅ |
| 82 | 姿态模型获取与随包打包（`download-pose-model.sh` sha256 幂等下载 + 双 Dockerfile 按文件 COPY 随包 + 魔搭/OCI 部署自动下载；修复 mediapipe 1.0 API 路径 `python.BaseOptions`/`mp.Image`） | ✅ |
| 83 | 姿态可视化与六边形雷达图（每次分析常驻姿态并行推理 + 骨架封面/骨架视频 + 六边形雷达图 + 姿态测量卡 + 用户端媒体服务 `/api/media/{path}?token=` + Admin 姿态详情） | ✅ |
| 84 | 骨架视频多帧修复（修复骨架视频帧数不足，多帧正确编码） | ✅ |
| 85 | 骨骼视频帧率自适应绘制（`probe_frame_rate` 获取视频帧率 + `analyze_frames` 使用 `帧数/时长` 计算骨骼视频帧率，确保播放时长与原视频一致） | ✅ |
| 86 | Admin 静态文件端点移除认证（`/api/admin/system/files/` 无需 `X-Auth-Token`，解决 `<img>` 浏览器原生请求 401 问题） | ✅ |
| 87 | Admin 时间显示统一东八区（后端 isoformat 加 `Z` 后缀 + 前端共享 `utils/date.ts`，`timeZone: 'Asia/Shanghai'`，8 个视图统一导入） | ✅ |
| 88 | 分享工坊技术评分卡片六边形维度点评（`drawRadar` + 维度点评列表 + 大球降级） | ✅ |
| 89 | 分享工坊条件管线模式重构（DrawPipeline → DrawStage → DrawStep 模式 + Playwright 回归测试 8 用例） | ✅ |
| 90 | 小程序 UI 布局视觉回归测试（RadarChart/LineChart 8 用例 + playwright-visual-regression skill 集成） | ✅ |
| 91 | 分享工坊技术评分三区域分离（雷达图/进度条/总结 + 白色卡片包裹 + Playwright 4 用例） | ✅ |
| 92 | 分享工坊视觉优化（雷达图标注偏移+动态对齐 + 进度条文字间距 + footer下移） | ✅ |
| 93 | 分享工坊保存图片默认名称与隐私API适配（USER_DATA_PATH持久路径 + 微信官方隐私弹窗） | 🚧 进行中 |
| 94 | 姿态推理线上503异常排查与修复（slim 镜像安装 libgl1+libglib2.0-0，镜像从 1.1GB 降至 957MB） | ✅ |
| 95 | 分享工坊 AI 文案生成（`POST /api/ai/caption` 后端查库 + 活泼/简洁/专业三风格 + 失败本地模板降级） | ✅ |
| 96 | 小程序大满贯球场主题（四套球场主题 CSS 变量 + page-meta 注入，修复「青柠主题」开关无效；我的页主题选择弹层；网球恒青柠 + 背景/卡片/hero渐变随主题；加强非青柠主题色差） | 🚧 进行中 |
| 97 | 小程序构建 Circular chunk 警告修复（request ↔ auth store 循环依赖解耦：`onSessionExpired` 回调注册替代静态导入） | ✅ |

> 说明：三个 Server 部署方案的脚本/指南/CI/env 模板均已完成。当前唯一启用的部署 CI 为 `deploy-server-modelscope.yml`（魔搭）；HF（需 PRO 订阅）与 OCI（待建 VM）的 workflow 位于 `.github/workflows-disabled/`。详细见 `docs/plans/63/64/65-*`。

详细进度与方案索引见 `docs/plans/` 目录。

## 注意事项

> **⚠️ 第一规则：禁止自动推送（git push）**
>
> AI 协作者**只能提交（commit）**，**不能推送（push）**。所有推送操作必须由人类确认后手动执行。
> - 禁止运行 `git push`、`git push --force` 或任何带网络写操作的命令
> - 禁止使用 `--force` 参数推送
> - 禁止推送到任何远程分支（包括 dev、master、main）
> - 如需部署，应提示人类手动触发 CI/CD 或运行部署脚本
>
> 违反此规则可能导致意外覆盖远程分支、破坏团队协作流程。

- **Node ≥ 22.12**：低于此版本 `@weapp-tailwindcss/postcss` 无法 `require()` ESM 包
- **config.py 路径**：`Path(__file__).resolve().parent.parent.parent / ".env"`（向上三级到 `server/`）
- **数据库迁移**：用 Alembic，禁止 `create_all`；新增模型须在 `app/models/__init__.py` 登记
- **SQLite 数据文件**：不纳入版本管理（已 `.gitignore`）
- **生产环境**：`request` 合法域名必须已备案，需 Nginx 反代
