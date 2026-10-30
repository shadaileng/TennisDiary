# 149 - 魔塔 ModelScope 生产部署方案

> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 149 |
> | 文档版本 | v2.0.0 |
> | 文档状态 | ✅ 已上线生产环境 |
> | 最后更新 | 2026-10-30 |
> | 对应功能/内容 | 魔塔 ModelScope Studio + 外置数据库/存储的生产化部署 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-10-30 | v2.0.0 | **生产就绪**：HF Space 因 PRO 订阅限制，切换至魔塔 ModelScope Studio 部署 |
> | 2026-10-29 | v1.1.0 | **反代调整**：明确使用 Cloudflare Workers 反代 |
> | 2026-10-29 | v1.0.0 | 初版 |
>
> **重要决策**
>
> - ✅ **已下线 HF Space 部署**：需要 $7/月 PRO 订阅，不符合成本效益
> - ✅ **启用魔塔 ModelScope 部署**：免费 Docker 容器支持，生产环境稳定
> - ✅ **外置依赖配置**：数据库适配 Supabase PG，对象存储适配七牛 KODO
>
> **关联文档**：
> - [146：后台三件套改造评估与实施路线](./146-后台三件套改造评估.md)（**总纲**）
> - [63：Server 部署方案 - Docker 与 HF Space](./63-Server部署方案-Docker与HF-Space.md)（已归档）
> - [65：Server 部署方案 - ModelScope 创空间](./65-Server部署方案-ModelScope-创空间.md)（**当前使用**）
> - [67：Cloudflare Workers 代理 ModelScope](./67-Cloudflare-Workers-代理-ModelScope-方案.md)（反代）
> - [147：阶段一 KODO 对象存储细化方案](./147-阶段一KODO对象存储细化方案.md)
> - [148：阶段二 Supabase PG 细化方案](./148-阶段二SupabasePG细化方案.md)
>
> **前置条件**：
> 1. 阶段一 KODO 化稳定运行（文件本体已迁 KODO）
> 2. 阶段二 Supabase PG 生产环境稳定（数据库已迁 PG）
> 3. Cloudflare 账户与已备案域名（用于反向代理）
>
> **架构决策**
>
> - **部署目标**：魔塔 ModelScope Studio（免费 Docker 容器）
> - **数据库**：Supabase PostgreSQL（外置）
> - **对象存储**：七牛 KODO（外置）
> - **反向代理**：Cloudflare Worker（解决 CORS + 鉴权透传）
> - **流程**：GitHub Actions → 魔塔 Docker 构建 → 自动生成部署
>
> **配置策略**
>
> | 配置类别 | 参数 | 状态 | 说明 |
> |---------|------|------|------|
> | **P0 - 必配** | `DATABASE_URL` | ✅ 必须 | PostgreSQL 连接串，格式 `postgresql+psycopg://...` |
> | **P0 - 必配** | `MODEL_SCOPE_TOKEN` / `USERNAME` / `STUDIO_NAME` | ✅ 必须 | 魔塔部署凭据 |
> | **P0 - 必配** | `JWT_SECRET` / `WX_APPID` / `WX_SECRET` | ✅ 必须 | 基础认证 |
> | **P1 - 可选** | 对象存储配置 | ✅ 可选 | 未配置使用 `local` 降级 |
> | **P1 - 可选** | AI 配置 | ✅ 可选 | 未配置使用默认参数 |
> | **P2 - 可选** | 数据库连接池 | ✅ 可选 | **已有默认值**，无需配置 |
>
> **部署步骤**
>
> ### Step 1：配置 GitHub Secrets
>
> 在 GitHub Repository Settings → Secrets and variables → Actions → New repository secret
>
> 配置以下 Secret：
> - `MODEL_SCOPE_TOKEN`（魔塔 Access Token）
> - `MODEL_SCOPE_USERNAME`（魔塔用户名）
> - `MODEL_SCOPE_STUDIO_NAME`（创空间名称）
> - `DATABASE_URL`（PostgreSQL 连接串）
> - `JWT_SECRET`（JWT 签名密钥）
> - `WX_APPID`（微信小程序 AppID）
> - `WX_SECRET`（微信小程序 Secret）
> - `ADMIN_DEFAULT_PASSWORD`（管理员密码）
> - `ADMIN_RESET_KEY`（密码重置密钥）
> - 可选：对象存储/AI 相关配置
>
> ### Step 2：触发 GitHub Actions 部署
>
> ```bash
> # 方式 1：自动触发 - 推送到 master 分支
> git push origin master
>
> # 方式 2：手动触发
> # 访问 GitHub → Actions → Deploy Server to ModelScope Studio → Run workflow
> ```
>
> GitHub Actions 会：
> - 检出 `master` 分支
> - 运行 `server/scripts/deploy-modelscope.sh`
> - 自动创建/更新魔塔创空间
> - 设置 Secrets（密钥不泄露到日志）
> - 部署 Docker 镜像到魔塔 Container Registry
>
> **无本地构建**：所有 Docker 构建在魔塔 Studio 容器内进行。
>
> ### Step 3：Cloudflare 反向代理配置
>
> 1. 登录 Cloudflare Dashboard
> 2. 创建 Worker（使用项目提供的 `td-hf-proxy.js` 或类似脚本）
> 3. 配置路由规则：`api.yourdomain.com/*` → Worker
> 4. 设置 Worker 环境变量：`HF_USERNAME`, `HF_SPACE_NAME` 等
> 5. 测试反代功能：`https://api.yourdomain.com/health`
>
> ### Step 4：灰度切流
>
> 1. **Admin 端灰度**（5% → 50% → 100%）
> 2. **小程序端灰度**（10% → 50% → 100%）
> 3. **监控关键指标**：5xx 错误率、响应时间、数据库连接
>
> ### Step 5：稳定运行 7 天后下线魔塔 CI
>
> 确认 HF Space 稳定运行后，继续观察魔塔部署状态。如需回退 HF 方案（已下线），可移动工作流文件到 `workflows-disabled/`。
>
> **回滚策略**
>
> - **Cloudflare 反代回滚**：修改 Worker 指向旧魔塔空间
> - **数据库回滚**：保留 `backup_inertia` 实现
> - **代码回滚**：准备 `git revert` 快速回退版本
>
> **验收标准**
>
> - [ ] 魔塔部署凭据安全（Settings → Secrets 无明文暴露）
> - [ ] DATABASE_URL 连接正常（PostgreSQL 连接串正确）
> - [ ] 对象存储与 AI 配置（可选）
> - [ ] 反代域名 HTTPS 正常访问
> - [ ] `/health` 健康检查返回 200
> - [ ] Cloudflare Worker 的 `X-Auth-Token` 透传正常
> - [ ] 灰度期间无 5xx 错误率＞0.1%
> - [ ] 冷启动时间＜15 秒
> - [ ] 生产环境数据库连接稳定
>
> **常见问题**
>
> **Q: HF Space 创建失败 (HTTP 402)？**
> A: HF Space Docker Runner 需要 PRO 订阅（$7/月）。已切换至魔塔部署。
>
> **Q: 部署脚本中 `DATABASE_URL` 必须配置？**
> A: 是的，脚本会检查 `DATABASE_URL` 是否设置，未配置则部署失败。
>
> **Q: 对象存储/AI 配置是必选项吗？**
> A: 不是，脚本会将这些配置传递到魔塔 Studio，但不会阻塞部署，不配置时自动降级。
>
> **Q: 数据库连接池参数需要配置吗？**
> A: 不需要，已有合理默认值（`DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10` 等）。
>
> **Q: 依赖的 ModelScope 部署脚本在哪？**
> A: `server/scripts/deploy-modelscope.sh`，支持 `WAIT_FOR_HEALTH=1` 等待健康检查。
>
> **重要提醒**
>
> - 避免使用 `git push`，只执行 `commit`，推送由人工操作
> - 提交前必须运行验证：后端 `ruff check` + `ruff format` + `pytest -m fast`；前端 `type-check` + `build`
> - `feat`/`fix` 提交须同步 bump 根 `package.json` 并更新 `CHANGELOG.md`
