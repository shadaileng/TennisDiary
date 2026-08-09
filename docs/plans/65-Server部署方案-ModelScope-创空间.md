> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 65 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 📋 待执行 |
> | 最后更新 | 2026-08-09 |
> | 对应功能/内容 | Server 部署方案（魔搭创空间 ModelScope Studio） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-09 | v1.0.0 | 初版 |
>
> **关联文档**：[63-Server 部署方案-Docker 与 HF Space](./63-Server部署方案-Docker与HF-Space.md) · [64-Server 部署方案-Oracle Cloud](./64-Server部署方案-Oracle-Cloud.md)

# Phase Server-3：Server 部署方案（魔搭创空间 ModelScope Studio）

## 一、背景与选型

Hugging Face Space 免费 Docker 档已改为要求 PRO 订阅（HTTP 402），无法免费部署。
魔搭（ModelScope）创空间是阿里的免费 AI 应用托管平台，支持 **Docker 类型部署**，
CPU 免费档（2 vCPU / 16G RAM）可免费托管 FastAPI 后台，且**国内直连，无需科学上网**。

### 1.1 Docker 创空间免费档

| 资源 | 内容 | 说明 |
|------|------|------|
| SDK 类型 | `docker` | 自定义 Docker 镜像运行 |
| CPU 免费档 | `platform/2v-cpu-16g-mem` | 2 vCPU / 16G RAM，免费 |
| 端口 | **固定 7860** | Docker 类型端口必须为 7860，8080 被平台占用 |
| 构建 | 首次构建 3-5 分钟 | push 后平台自动用根目录 Dockerfile 构建 |
| 访问 | `https://{owner}-{name}.ms.show` | 每创空间一个 `.ms.show` 直连域名 |
| 持久化 | `/mnt/workspace` | 重启可持久化，转移/重命名会丢失 |
| 配额 | 免费有时长限制 | CPU 计算时长用完需等待配额恢复 |

### 1.2 方案优势与局限

| 维度 | 说明 |
|------|------|
| ✅ 免费 | CPU 免费档 `platform/2v-cpu-16g-mem`，无需 PRO |
| ✅ 国内直连 | 阿里平台，国内访问快，无需翻墙 |
| ✅ 完整 Docker | 直接用已有 `Dockerfile`，零改动 |
| ❌ 端口固定 | 只能暴露 7860，微信域名仍需自备反代 |
| ❌ 持久化弱 | 重启可保留 `/mnt/workspace`，但转移/重命名会丢数据 |
| ❌ 配额限制 | 免费 CPU 时长有限，不适合高流量生产 |

## 二、产出文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 部署配置 | `server/modelscope/ms_deploy.json` | 魔搭创空间部署配置（sdk/资源/端口） |
| 部署指南 | `server/modelscope/README.md` | 魔搭创空间建仓 + 推送部署完整指南 |
| 部署脚本 | `server/scripts/deploy-modelscope.sh` | 一键镜像 + 推送 + 设置 Secrets |
| 配置模板 | `server/.env.modelscope.example` | 魔搭 SSH 连接参数模板 |
| CI | `.github/workflows/deploy-server-modelscope.yml` | push `server/**` 自动部署到魔搭 |

> 复用已有 `Dockerfile`、`docker-entrypoint.sh`，无需镜像改动。

---

## 三、魔搭创空间部署流程

### 3.1 原理

魔搭创空间 = Git 仓库 + 平台自动构建：

- 创建`创空间`（GitHub 与 HF 不同，魔搭是**仓库型**，无 repo 即由 git repo 反建）
- 在仓库根目录放置 `ms_deploy.json` 与 `Dockerfile`
- `git push` 到魔搭分配的 git remote
- 平台自动用 Dockerfile 构建镜像并启动（监听 7860）

### 3.2 ms_deploy.json 关键配置

`sdk_type` 为 `docker` 时：

```json
{
  "$schema": "https://modelscope.cn/api/v1/studios/deploy_schema.json",
  "sdk_type": "docker",
  "resource_configuration": "platform/2v-cpu-16g-mem",
  "port": 7860
}
```

| 字段 | 值 | 说明 |
|------|-----|------|
| `sdk_type` | `docker` | 使用自定义 Dockerfile 构建应用 |
| `resource_configuration` | `platform/2v-cpu-16g-mem` | 免费 CPU 档（2 vCPU/16G） |
| `port` | **7860** | Docker 类型端口固定 7860 |

> 注意：`environment_variables` 字段**仅对 gradio/streamlit/static 生效**，
> `docker` 类型不生效。Secret 通过部署脚本 RTS-API 设置，非 JSON 注入。

### 3.3 前置步骤（一次性，详见 modelscope/README.md）

1. 注册魔搭账号（阿里账号绑定 + 实名认证，Docker 构建的前置条件）
2. 个人中心生成 Access Token（`modelscope_...`）
3. 确认已有 GitHub 或自建创空间 Git remote 就绪

### 3.4 本地部署步骤

```bash
cp .env.modelscope.example .env.modelscope
# 编辑填入 MODEL_SCOPE_TOKEN / MS_USERNAME / MS_STUDIO_NAME 等
bash scripts/deploy-modelscope.sh
```

脚本自动：
1. 校验必填变量（TOKEN / 用户名 / 空间名）
2. 通过 API 创建或检测创空间（`POST /openapi/v1/studios`，不存在则创建）
3. 将 `server/` 代码 + `ms_deploy.json` + `Dockerfile` 打包到临时目录
4. 通过 API 设置 Secrets（JWT/WX/管理员等敏感项，*非代码文件*）
5. 初始化 git 并推送到魔搭远程
6. 等待构建后轮询 `https://{owner}--{name}.ms.show/health`

### 3.5 健康检查与微信域名

- 创空间域名 `https://{owner}-{studio}.ms.show`（HTTPs）
- 需配置 Nginx 反代才能作为微信合法域名（`.ms.show` 无法备案，需自备已备案域名反代）

反代配置与 HF 方案（`spaces/README.md` 七→八）完全相同，仅 `proxy_pass` 目标改为
`https://{owner}-{studio}.ms.show`。

---

## 四、脚本设计

### 4.1 `deploy-modelscope.sh`

```bash
set -euo pipefail
# 读取 .env.modelscope
# 校验 ML_SCOPE_TOKEN / MS_USERNAME / MS_STUDIO_NAME / JWT_SECRET 等
# API 预检 token 有效性（GET /api/v1/studios/{user}/{name}）
# 不存在则 POST 创建（sdk=docker）
# 构建临时推送目录（app + Dockerfile + ms_deploy.json + pyproject.toml）
# 通过 API 设置 Secrets（POST /secrets）
# git init → remote add → push origin master --force
# 轮询 https://{user}-{studio}.ms.show/health
```

### 4.2 环境变量校验（沿用 HF/OCI 风格）

- 必填：`MODEL_SCOPE_TOKEN`、`MODEL_SCOPE_USERNAME`、`MODEL_SCOPE_STUDIO_NAME`、`JWT_SECRET`、`WX_APPID`、`WX_SECRET`
- 可选：`ADMIN_DEFAULT_PASSWORD`、`ADMIN_RESET_KEY`
- GitHub Actions 模式额外校验 Secrets

---

## 五、目录结构变更（diff）

```
server/
├── .env.modelscope.example        # ← 新建（魔搭部署配置模板）
├── modelscope/
│   ├── ms_deploy.json             # ← 新建（魔搭部署配置）
│   └── README.md                  # ← 新建（魔搭部署指南）
└── scripts/
    └── deploy-modelscope.sh       # ← 新建（本地/CI 部署）

.github/workflows/
└── deploy-server-modelscope.yml   # ← 新建（GitHub Actions）
```

---

## 六、部署验证清单

| 检查项 | 命令/操作 | 预期结果 |
|--------|----------|---------|
| ms_deploy.json 合法 | JSON 可解析 | sdk_type=docker, port=7860 |
| 代码推送成功 | 脚本输出 | `master` 分支已推送 |
| 构建成功 | 日志 `build` 无 ERROR | 首次构建 3-5 分钟 |
| API 文档 | `https://{u}-{s}.ms.show/docs` | Swagger 正常 |
| 健康检查 | `curl https://{u}-{s}.ms.show/health` | `{"code":0,...}` |
| 数据库迁移 | 日志 `Migrations complete.` | alembic 无错误 |
| 数据持久化 | 容器重启后查库 | `/mnt/workspace` 数据不丢 |

---

## 七、成本与风险提示

- 免费档 CPU 时长有限：配额用完会休眠/受限，仅适合演示与低流量场景
- `ms_deploy.json` 不支持 docker 类型注入环境变量（需 API Secrets）
- 数据持久化有限：转移/重命名创空间会丢失 `/mnt/workspace` 数据
- 生产建议：Oracle Cloud（常驻 + 200GB 卷）为正式目标，魔搭适合快速演示
- 域名 `.ms.show` 无法备案：微信小程序仍须自备已备案域名 Nginx 反代

---

## 八、提交规范

```bash
feat(server): 添加魔搭创空间部署方案

- 创建 modelscope/ms_deploy.json（docker sdk / 7860 端口）
- 创建 modelscope/README.md 部署指南
- 创建 deploy-modelscope.sh（打包 + API Secrets + git push）
- 创建 .env.modelscope.example 与 GitHub Actions
```