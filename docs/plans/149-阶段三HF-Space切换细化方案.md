> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 149 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | 📋 待执行 |
> | 最后更新 | 2026-10-29 |
> | 对应功能/内容 | 阶段三细化方案：Hugging Face Space Docker 部署 + Cloudflare 反代（摆脱魔搭，生产切流） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-10-29 | v1.1.0 | **反代调整**：明确使用 Cloudflare Workers 反代，无需 Docker 内配置；更新架构与步骤 |
> | 2026-10-29 | v1.0.0 | 初版（基于方案 63 + 当前技术栈 Re-factoring） |
>
> **关联文档**：
> - [146：后台三件套改造评估与实施路线](./146-后台三件套改造评估.md)（**总纲**：阶段三的立项依据与决策记录）
> - [63：Server 部署方案 - Docker 与 HF Space](./63-Server部署方案-Docker与HF-Space.md)（**HF 部署技术来源**，已归档但代码可用）
> - [65：Server 部署方案 - ModelScope 创空间](./65-Server部署方案-ModelScope-创空间.md)（**当前启用**的部署目标，阶段三需下线）
> - [147：阶段一 KODO 对象存储细化方案](./147-阶段一KODO对象存储细化方案.md)（文件存储，需配套）
> - [148：阶段二 Supabase PG 细化方案](./148-阶段二SupabasePG细化方案.md)（数据库，已部署）
> - [67：Cloudflare Workers 代理 ModelScope](./67-Cloudflare-Workers-代理-ModelScope-方案.md)（反代模式，可复用于 HF Space）
>
> **前置条件**：
> 1. 阶段一 KODO 化稳定运行（文件本体已迁 KODO，本地只存临时文件）
> 2. 阶段二 Supabase PG 生产环境稳定（数据库已迁 PG，配置就绪）
> 3. **Cloudflare 反代配置**：已备案域名 + Cloudflare Workers 反代（**Cloudflare 账户，项目外配置**）
> 4. HF 账号与 Space 权限（免费 Docker Runner）
>
> **决策依据**（146 总纲 §七）：
> - **决策 1**：摆脱魔搭创空间
> - **决策 2**：反代配置在**项目外**（仓库仅沉淀契约）→ **本次使用 Cloudflare Workers 反代**
> - **决策 3**：分阶段实施（阶段一 → 二 → 三 串行）
> - **决策 5**：测试 SQLite 生产 PG（不变）

## 阶段三 Hugging Face Space 切换细化方案

## 一、范围

### 1.1 做什么

| # | 内容 |
|:-:|------|
| 1 | 复活方案 63 的 HF Space Docker 部署脚本（`Dockerfile` + `docker-entrypoint.sh` + `deploy-hf.sh`）|
| 2 | 配置 HF Secrets 注入（JWT / WX / AI / 七牛 / Supabase 等凭据）|
| 3 | 适配当前技术栈（Supabase PG + 阶段一 KODO）的 `Dockerfile` 与入口脚本 |
| 4 | 持久化卷配置（`/data` 存数据库与临时文件）|
| 5 | 灰度切流（Admin → 小程序；魔搭保留为回滚目标）|
| 6 | 下线魔搭 CI（`.github/workflows-disabled/`）|
| 7 | 更新部署文档（`docs/plans/65` 状态、方案 63 解封）|

### 1.2 不做什么（边界）

- ❌ 修改前端代码（小程序 / Admin）—— 后端响应格式零变化
- ❌ 修改数据库结构（Supabase 已在阶段二完成）
- ❌ 修改文件存储逻辑（阶段一 KODO 已完成）
- ❌ 新增反代配置（反代在**项目外**配置，见决策 2）
- ❌ 多 Worker 部署（阶段三仅切换到 HF Space CPU，`uvicorn` 单进程）

## 二、技术架构

```
前端（小程序/Admin）
    ▲
    │ HTTPS (已备案域名，如 api.yourdomain.com)
    │ 透传 X-Auth-Token、Range、SSE
    │
    ▼
Cloudflare Workers 反代（**项目外配置，Cloudflare 账户管理**）
    ▲
    │ 转发 to HF Space
    │ - 处理 HTTPS 与 SSL 证书
    │ - 透传 X-Auth-Token
    │ - 设置安全头（CSP、HSTS 等）
    │ - 流量路由与缓存策略
    │ - 隐藏 HF Space 真实域名
    │
    ▼
Hugging Face Space (Docker Runner)
    ├─ FastAPI (uvicorn, 单进程)
    ├─ Supabase PG (外部连接，阶段二)
    └─ KODO S3 (外部存储，阶段一)
```

**关键点**：
- HF Space 仅提供**计算容器**，数据存外部（Supabase + KODO）
- 容器内只保留**临时文件**（视频处理、姿态推理缓存）
- 所有**业务数据**在 PG 和 S3，不依赖容器卷持久化（除非用于加速）
- **Cloudflare 反代**负责：
  - 域名备案与 HTTPS 证书管理
  - 安全头（CSP、HSTS、X-Frame-Options 等）
  - 请求/响应修改（头透传、重定向）
  - 流量监控与防护
  - 隐藏后端真实架构

## 三、详细步骤

### Step 1：在 GitHub Secrets 配置 HF 凭据

在 GitHub 仓库设置中配置 Secrets **（无需本地部署）**：

| Secret Key | 说明 | 来源 |
|------------|------|------|
| `HF_TOKEN` | HF Access Token | HF 个人设置 → Access Tokens |
| `HF_USERNAME` | HF 用户名 | HF 个人主页 |
| `HF_SPACE_NAME` | HF Space 名称 | 自定义（如 `tennis-diary-server`） |
| `JWT_SECRET` | JWT 密钥 | 生成强随机值 |
| `WX_APPID` | 小程序 AppID | 微信公众平台 |
| `WX_SECRET` | 小程序 Secret | 微信公众平台 |
| `ADMIN_DEFAULT_PASSWORD` | 管理员初始密码 | 自定义 |
| `ADMIN_RESET_KEY` | 密码重置密钥 | 自定义 |

### Step 2：触发 GitHub Actions 部署

部署通过 **GitHub Actions 自动完成**，无需本地 Docker 或 HF CLI：

```bash
# 方式 1：自动触发 - 推送到 master 分支
git push origin master

# 方式 2：手动触发
# 在 GitHub → Actions → Deploy Server to HuggingFace Spaces → Run workflow
```

GH Actions 会：
- 检出 `master` 分支
- 运行 `server/scripts/deploy-hf.sh`
- 自动创建/更新 HF Space
- 设置 HF Secrets（密钥不泄露到日志）
- 部署 Docker 镜像到 HF Container Registry

### Step 3：Cloudflare 反代配置（项目外）

配置 Cloudflare 反代到 `https://{HF_USERNAME}-{HF_SPACE_NAME}.hf.space`，参见票据 4.2。

## 三、详细步骤（CI 部署模式）

### Step 1：GitHub Actions 部署流程

**工作流文件**：`.github/workflows/deploy-server-hf.yml`（已启用）

**触发条件**：
- 推送到 `master` 分支且修改 `server/**` 或工作流文件
- 手动触发（GitHub Actions 页面）

**部署流程**：
1. `actions/checkout` 检出代码
2. 运行 `server/scripts/deploy-hf.sh`
3. 脚本自动：
   - 校验 GitHub Secrets
   - 创建 HF Space（如不存在）
   - 设置 HF Secrets（JWT、WX、Admin 等）
   - 复制 `server/` 核心文件到临时目录
   - 初始化 Git 并推送到 HF Space
   - 返回部署链接和健康检查

**无本地构建**：所有 Docker 构建在 HF Space 容器内进行。

### Step 2：Cloudflare 反代配置（项目外）

配置 Cloudflare 反代到 `https://{HF_USERNAME}-{HF_SPACE_NAME}.hf.space`。

### Step 5：灰度切流（Cloudflare 反代）

#### 5.1 Admin 切流

1. **Cloudflare 路由调整**：将 `api.yourdomain.com` 指向 HF Space
2. **验证端点**：`GET https://api.yourdomain.com/api/health`
3. **功能测试**：Admin 登录、创建日记、上传文件

#### 5.2 小程序切流

1. **小程序配置**：更新 `request` 基础 URL 为 `https://api.yourdomain.com`
2. **提审验证**：确保所有 API 调用正常
3. **生产发布**：小流量灰度发布

#### 5.3 监控与观察

- **24 小时监控**：观察错误日志、延迟指标
- **性能对比**：与魔搭 Space 性能对比
- **用户反馈**：收集管理员和用户体验

#### 5.4 魔搭推理保留回滚

- 魔搭 Space 保持运行，作为回滚目标
- 配置 Cloudflare Worker 路由规则，快速切回

### Step 6：下线魔搭 CI

将 `deploy-server-modelscope.yml` 移入 `.github/workflows-disabled/`：

```bash
mv .github/workflows/deploy-server-modelscope.yml .github/workflows-disabled/
```

更新相关文档：

```markdown
# docs/plans/65 末尾添加：
## XX. 状态更新
- **当前状态**：阶段三已启用 HF Space，魔搭 CI 已下线
```

### Step 7：文档与知识沉淀

更新以下文档：

- `docs/plans/63`：解封状态至 ✅ 已完成（HF 部署已启用）
- `docs/plans/65`：状态改为 ⏳ 已下线（阶段三完成）
- `docs/README.md`：更新部署章节，添加 Cloudflare 配置说明
- `docs/plans/146`：更新完成总结
- `docs/plans/149`：本方案终版

## 四、验收清单

### 部署验收

- [ ] HF Space 容器成功创建并启动
- [ ] `GET /api/health` 返回 200 + `{"status": "ok"}`
- [ ] 数据库连接正常（`db_health` 端点 200）
- [ ] KODO 文件上传/读取正常
- [ ] SSE 流式连接正常（Admin 分析轮询）
- [ ] 视频处理管线完整流程通过
- [ ] 文件 Range 下载正常（Admin 预览）

### Cloudflare 验收

- [ ] HTTPS 连接正常，SSL 证书有效
- [ ] Cloudflare Worker 无错误日志
- [ ] X-Auth-Token 正确透传
- [ ] 安全头（CSP、HSTS 等）设置正确
- [ ] 请求/响应压缩正常
- [ ] 防火墙规则正常工作
- [ ] Rate Limiting 测试通过

### 灰度验证

- [ ] Admin 端登录功能正常
- [ ] 创建日记功能正常
- [ ] 上传装备图片正常
- [ ] AI 视频分析功能正常
- [ ] 小程序端登录、创建日记、上传、视频分析正常

### 监控观察（7 天）

- [ ] 无 5xx 错误
- [ ] 无冷启动超时（Space 重启动作）
- [ ] 无连接池耗尽
- [ ] 无文件访问 404
- [ ] 性能表现符合预期
- [ ] Cloudflare 缓存命中率正常

## 五、回滚方案

### Cloudflare 回滚（秒级）

回到魔搭 Involution：

1. **Cloudflare Worker 路由调整**：修改 Worker 路由，将 `api.yourdomain.com` 指向魔搭 Space
2. **数据库恢复**：如 PG 数据有变更，从 backup 恢复
3. **KODO 回滚**：无明显回滚，所有文件已存 KODO

### 数据回滚

1. **数据库**：从 `pg_dump` 备份恢复
2. **文件存储**：无，KODO 数据不变

### 代码回滚

冻结分支后切回：

```bash
git revert <hf-space-commit>
```

## 六、风险与未决

| 级别 | 风险 | 处理 |
|:----:|------|------|
| **P0** | HF Space 免费 Docker 档需 PRO 订阅 | 使用免费 CPU 档，确认无 402 限制 |
| 高 | HF Space 冷启动（**Space 休眠后首次启动需 30-60s**） | 反代前先 ping 激活；考虑托管在持续运行空间（付费档） |
| 高 | HF Space 使用限制（CPU 额度、存储、网络） | 监控使用量，必要时升级到付费档 |
| 中 | 跨境链路无 SLA | 复用 Cloudflare Workers 反代，就近接入 |
| 中 | Cloudflare 配置项目外 | 文档中沉淀契约，配置在外部系统，项目代码只做适配 |
| 低 | HF 账号安全 | 启用 2FA；Secrets 定期轮换 |

## 七、验收总结

**门禁（✅ Step 10 实跑）**：`ruff check/format` 干净 + `pytest -m fast` 全绿 + 真机三端回归。

| # | 用例 | 期望 | 状态 |
|:-:|------|------|:----:|
| 1 | HF Space 创建 | Docker Runner 成功部署 | 🤖 |
| 2 | 健康检查 | `GET /api/health` 200 + 无 5xx | 🤖 |
| 3 | 数据库连接 | `db_health` 200 + 连接池共享 | 🤖 |
| 4 | 文件上传/下载 | KODO S3 上传成功，读取正常 | 🤖 |
| 5 | SSE 流式 | 轮询无积压，数据实时 | 🤖 |
| 6 | 管线处理 | 视频分析流程在 HF 环境完成 | 🤖 |
| 7 | Cloudflare 反代 | HTTPS + X-Auth-Token + Range + SSE 透传 | 🤖 |
| 8 | 灰度切流 | Admin → 小程序，无故障 | 🤖 |
| 9 | 回滚测试 | 切回魔搭成功，业务无感知 | ⏳ 待生产 |

每 Step 结束跑 AGENTS 4.3 门禁：`cd server && uv run ruff check . && uv run ruff format . && uv run pytest -q -m fast`。

## 八、实施计划

| 步骤 | 时间估计 | 前置条件 |
|------|---------|---------|
| 1. 配置 GitHub Secrets | 0.25 人日 | 阶段二完成，HF 账号 |
| 2. 触发 GitHub Actions 部署 | 自动 | 推送到 master 分支 |
| 3. Cloudflare 配置 | 0.5 人日 | 已备案域名 + Cloudflare 账户 |
| 4. 灰度切流 | 1 人日 | 监控就绪 |
| 5. 下线魔搭 | 0.25 人日 | 稳定运行 1 周 |
| **合计** | **2.0 人日** | — |

---

**阶段三 (149 HF Space 切换) 代码与方案就绪，待生产切换。**

**部署流程**：配置 GitHub Secrets → 推送到 master 分支 → 自动触发 GitHub Actions → 完成 HF Space 部署 → Cloudflare 反代配置 → 灰度切流。


