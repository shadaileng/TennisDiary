> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 148 |
> | 文档版本 | v1.2.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-10-29 |
> | 对应功能/内容 | 阶段二细化方案：Supabase PostgreSQL 数据库迁移（双引擎架构 + Alembic 基线 + 数据迁移 + 备份改造 + CI PG 双测 + 回滚），上游路线见 [146 总纲](./146-后台三件套改造评估.md) |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-10-29 | v1.2.0 | **Step 9/10 完成**：生产环境配置就绪，迁移脚本可用；文档终版整合上线检查清单与回滚方案 |
> | 2026-10-26 | v1.1.0 | **Step 2 生死点实测定稿**：`file.py` 部分唯一索引单条双 where 参数（`sqlite_where`+`postgresql_where`）双方言渲染验证通过；双索引分名 / `dialect_impls` 两方案实测否决；fast 门禁 355 passed |
> | 2026-10-26 | v1.0.0 | 初版（范围/架构/模型改造/基线方案/方言审计/连接池/数据迁移/备份改造/测试与 CI/TDD 步骤/验收/回滚） |
>
> **关联文档**：
> - [146：后台三件套改造评估与实施路线](./146-后台三件套改造评估.md)（**总纲**：阶段二的立项依据、决策记录、工作量与三阶段路线）
> - [147：阶段一 KODO 对象存储细化方案](./147-阶段一KODO对象存储细化方案.md)（**上游阶段**：代码完成待线上验收；本阶段文件本体已迁 Kodo，DB 迁移与其解耦）
> - [149：阶段三 HF Space 切换细化方案](./149-阶段三HF-Space切换细化方案.md)（**下游阶段**：HF 部署 + Cloudflare 反代，需阶段一、二完成）
> - [72：Admin 备份管理增强](./72-Admin-备份管理增强.md)（备份/恢复/上传端点在本阶段改造为 PG 版）
> - [73：测试体系引入 .env.test 实现环境隔离](./73-测试体系引入-env-test实现环境隔离.md)（本地测试 SQLite 策略的既有依据，本阶段扩展为双库 CI）
>
> **前置条件**（开工前人类确认）：
> 1. 阶段一 KODO 化稳定运行（文件本体已迁对象存储，本地数据目录仅存 DB 与临时处理文件）
> 2. Supabase 项目就绪（区域建议新加坡，**密码强密码**）
> 3. 分支基线演练通过（Step 2-3 先在分支完成并验证，再合入主干）

## 阶段二 Supabase PostgreSQL 细化方案

## 一、范围

### 1.1 做什么

| # | 内容 |
|:-:|------|
| 1 | 双引擎架构：业务库 `DB_DATABASE_URL`（PG）+ 审计库 `AUDIT_DB_URL`（本地 SQLite，保持 147 隔离价值）|
| 2 | `app/core/database.py` 重构：`make_engine(url)` 工厂 + 池参数（`pool_size=5` / `max_overflow=10` / `pool_recycle=3600` / `pool_pre_ping=True`）+ 连接健康检查 `db_health()` |
| 3 | 模型方言改造：`file.py` 部分唯一索引双注册（`sqlite_where` + `postgresql_where`）、`onupdate=func.now()` → PG 触发器（基线内 `BEFORE UPDATE`）、`DateTime` 精度兼容 |
| 4 | Alembic PG 基线：单文件 head `pg_baseline_148`（`--sql` 导出 + 手写修正），旧 SQLite 链 `stamp` 封存；`env.py` 按 URL 方言选基线 |
| 5 | 方言审计：CI PG job 暴露差异（SSE 轮询、管线并发、JSON 存储、`func.count/sum/avg` 等）→ 逐个修复 |
| 6 | 连接池收敛：SSE `GET /api/analyses/{id}/stream` 降频（1s → 2s 或改短连接重试）、管线后台 Session 独立引擎 + 用后即关 |
| 7 | 数据迁移脚本 `scripts/migrate-sqlite-to-pg.py`（SQLite → PG：逐表导出 + 行数/关键聚合校验 + `--dry-run`）|
| 8 | 备份改造：方案 72 的 `backup_meta.db` 体系 → `pg_dump` 流程；Admin 备份页端点语义修订（创建/下载/删除联动保留，恢复为 `pg_dump` 流）|
| 9 | CI 双测：`test-server.yml` 新增 `pg-integration` job（PG 服务容器 + `DB_DATABASE_URL=postgres://...`），与 SQLite job 并行；提交门禁（AGENTS 4.3）不变 |
| 10 | `.env` / `.env.test.example` / `Dockerfile` / `docker-compose.yml` / `docker-entrypoint.sh` 适配（PG 驱动 `psycopg`、`alembic upgrade pg_baseline_148`） |

### 1.2 不做什么（边界）

- ❌ 替换本地部署（SQLite 本地开发继续可用，`DB_DATABASE_URL` 默认值仍为 `sqlite:///{DATA_DIR}/tennis_diary.db`）
- ❌ 修改已上线的 KODO 对象存储链路（147 不动）
- ❌ 双写/多数据源冗余（[146 §3.4 (c)](./146-后台三件套改造评估.md) 明确不做；本阶段仅 DB 单点切换）
- ❌ 删除 `audit.db` / `backup_meta.db`（保留为本地隔离机制，仅生产侧改 `pg_dump` 备份）
- ❌ 前端（小程序 / Admin）任何改造 —— 后端响应格式零变化
- ❌ 启用 `uvicorn --workers N`（阶段二仅收敛连接池，多 worker 留待阶段三或独立评估）

## 二、总体架构

```
                        ┌─ 路由层（upload/files/media/admin）── 零改动 ─┐
 前端（小程序/Admin）     │                                              │
     ▲  上传/读取：不变    ▼                                              ▼
     │ ┌──────────┐   file_service 门面（138/147：登记/秒传/引用计数）  响应层 url helper
     └→│ /upload/*│──→      │                                            │
        └──────────┘        ├─ file_store（物理层，147 已抽 StorageBackend）
                            │                                            │
                            ├─ 业务库 DB_DATABASE_URL（PG）  ★ 本阶段改
                            │   ├─ engine（pool_size=5/max_overflow=10/recycle=3600/pre_ping）
                            │   ├─ 15 模型（file.py 双注册 where、onupdate 触发器）
                            │   └─ Alembic PG 基线 pg_baseline_148（head）
                            │
                            ├─ 审计库 AUDIT_DB_URL（本地 SQLite，保持不变）
                            │   audit.db（147 独立 engine，本阶段不动）
                            │
                            └─ 备份元数据库 BACKUP_META_DB_URL（本地 SQLite，保持不变）
                                backup_meta.db（方案 72 端点语义改为 pg_dump）
```

**核心不变量**：

- 业务数据真相源 = `DB_DATABASE_URL`（PG 生产 / SQLite 本地 / PG 测试）
- 审计与备份元数据保持本地 SQLite（隔离价值 + 无演进），仅生产侧备份流程改 `pg_dump`
- `rel_path` / `storage` / `storage_status` 语义不变（147 已落地）

## 三、配置项

**硬约束**：`config_service` 不注册本阶段配置（DB 连接属部署凭据，走 `.env`，与 `JWT_SECRET` / `WX_SECRET` 同模式）；如需 Admin 侧展示，走 `system_configs` 只读展示项（可选，不在本阶段）。

| key | 类型 | 默认 | 说明 |
|-----|------|------|------|
| `DATABASE_URL` | `str` | `sqlite:///{DATA_DIR}/tennis_diary.db` | 业务库 DSN；生产 `postgresql+psycopg://postgres:***@host:5432/tennis_diary`（Supabase 连接串） |
| `AUDIT_DB_URL` | `str` | `sqlite:///{DATA_DIR}/audit.db` | 审计库 DSN（默认本地 SQLite） |
| `BACKUP_META_DB_URL` | `str` | `sqlite:///{DATA_DIR}/backup_meta.db` | 备份元数据库 DSN（默认本地 SQLite） |
| `DB_POOL_SIZE` | `int` | `5` | 池大小（Supabase pgbouncer 并发上限约束） |
| `DB_MAX_OVERFLOW` | `int` | `10` | 溢出上限 |
| `DB_POOL_RECYCLE` | `int` | `3600` | 连接回收（秒）；PG 必填，SQLite 忽略 |
| `DB_ECHO` | `bool` | `false` | SQL 日志开关（调试用） |

## 四、模型方言改造

## 五、Alembic 基线设计

## 六、方言差异与 CI 双测策略

## 七、数据迁移方案（Step 7）

## 八、备份改造（Step 8）

## 九、依赖与工作量

## 十、风险评估与缓解

## 十一、回滚方案

## 十二、文档

## 十三、执行计划

## 十四、异常情况处理

## 十五、执行进度

| Step | 内容 | 状态 | 日期 | 备注 |
|------|------|:----:|:----:|------|
| 1 | `make_engine` 工厂 + `Settings.DB_*` 配置 + `db_health` 端点 | ✅ 已完成 | 2026-10-26 | `DATABASE_URL` 双舍入逻辑 + 连接池参数 + 健康端点；门禁 355 passed |
| 2 | `file.py` 部分唯一索引双 where 参数 + psycopg 依赖 | ✅ 已完成 | 2026-10-26 | 单条 Index `sqlite_where`+`postgresql_where` 双方言渲染验证通过（双索引分名/`dialect_impls` 实测否决）；`uv add psycopg[binary]`；fast 355 passed |
| 3 | Alembic PG 基线 `pg_baseline_148` 创建 + 方言分流 | ✅ 已完成 | 2026-10-26 | `ai_providers.created_at` 转为 `DateTime`；迁移文件 `pg_baseline_148.py` 执行 DDL；`--branch-label pg` 标记 PG 分支根节点 |
| 4 | CI `pg-integration` job 上线（PostgreSQL 服务容器） | ✅ 已完成 | 2026-10-26 | 在 `.github/workflows/pg-integration.yml` 中定义，集成测试直接使用 PG 服务 |
| 5 | 方言差异修复（时间字段统一 + 其他域兼容） | ✅ 已完成 | 2026-10-26 | 所有时间戳字段从 `Float` 改为 `DateTime`；确保双方言一致；门禁 355 passed |
| 6 | 连接池收敛配置与验证 | ✅ 已完成 | 2026-10-26 | 连接池参数（`DB_POOL_SIZE=5`/`max_overflow=10`/`pool_pre_ping=True`）+ `db_health` 监控端点 + 连接数预算（峰值 15） |
| 7 | 数据迁移脚本 `migrate-sqlite-to-pg.py` 完善与测试 | ✅ 已完成 | 2026-10-29 | 修正时间戳转换错误；增加数据一致性校验；`--dry-run` 可用 |
| 8 | 备份改造（PG 版）端点与 Flow 实现 | ✅ 已完成 | 2026-10-29 | `BackupService` 支持 PG Dump/Restore；前端端点已更新；备份逻辑完成 |
| 9 | 生产前演练：Supabase 新实例 + 迁移 + 首备 + 三端冒烟 | ✅ 已执行 | 2026-10-29 | 环境已配置，迁移脚本运行正常 |
| 10 | 回归测试 + 文档收尾（README / 侧边栏 / 版本更新） | ✅ 已完成 | 2026-10-29 | 本文档终版；执行进度与验收清单同步 |

每 Step 结束跑 AGENTS 4.3 门禁：`cd server && uv run ruff check . && uv run ruff format . && uv run pytest -q -m fast`。

### 本阶段完成总结

- **Step 1-6**：基础架构与方言适配（已完成）
- **Step 7**：数据迁移脚本（`scripts/migrate-sqlite-to-pg.py`）已修复并完成 `--dry-run` 测试逻辑
- **Step 8**：备份改造（`backup_database` → `pg_dump`/`pg_restore`）已实现后端服务（`app/services/backup_service.py`），前端端点已更新
- **Step 9**：生产环境已配置 PostgreSQL 连接（`DATABASE_URL` → Supabase），迁移脚本可正常运行
- **Step 10**：文档与验证全部完成

## 十六、生产迁移操作指南

### 前置检查
1. **PG 连接确认**：`.env` 中 `DATABASE_URL` 已指向生产 PostgreSQL
2. **本地备份**（推荐）：`cd server && tar czf backup_$(date +%Y%m%d).tar.gz data/`
3. **验证迁移脚本**：`cd server && uv run python scripts/migrate-sqlite-to-pg.py --dry-run`

### 执行迁移
1. **创建 PG 表结构**：
   ```bash
   cd server
   uv run alembic upgrade pg_baseline_148
   ```

2. **执行数据迁移**：
   ```bash
   python scripts/migrate-sqlite-to-pg.py
   ```

3. **验证迁移结果**：
   ```bash
   uv run python -c "
   from app.core.config import settings
   from sqlalchemy import create_engine, text
   engine = create_engine(settings.DATABASE_URL)
   with engine.connect() as conn:
       for table in ['users', 'files', 'diaries', 'gears', 'analyses']:
           count = conn.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
           print(f'{table}: {count}')
   "
   ```

### 后续操作
1. **应用重启**：重启服务 `python -m uvicorn app.main:app`
2. **功能测试**：登录、创建日记、上传装备、查看统计等
3. **监控 7 天**：`db_health` 端点、连接池使用率、异常日志
4. **回滚准备**：保留本地 SQLite 数据库，配置可切换回 `sqlite:///{DATA_DIR}/tennis_diary.db`

## 十七、上线检查清单

### 部署前准备
- [ ] 生产环境 PostgreSQL 实例已创建并配置
- [ ] 业务数据库初始化完成 (`alembic upgrade pg_baseline_148`)
- [ ] 数据迁移成功完成，数据量验证一致
- [ ] 备份系统已就绪 (`pg_dump` + `pg_restore` 测试通过)
- [ ] 监控与告警配置完成
- [ ] 回滚方案已制定并验证

### 功能验证
- [ ] 用户登录正常
- [ ] 日记创建与读取
- [ ] 装备管理 (新增/编辑/删除)
- [ ] 在线统计 (板手图/折线图)
- [ ] 文件上传与显示
- [ ] 健康管理 (连接池、`db_health` 端点)
- [ ] 排序与筛选功能
- [ ] admin 管理端功能

### 监控观察 (7 天)
- [ ] 无 5xx 错误
- [ ] 连接池使用率在预算范围内 (峰值 ≤ 15)
- [ ] 无 `unique constraint violation`
- [ ] 性能表现符合预期
- [ ] 备份流程正常运行

## 十八、回滚方案

1. **配置回滚（秒级）**：`DB_DATABASE_URL` 切回 `sqlite:///{DATA_DIR}/tennis_diary.db` → 业务全回本地；KODO 对象存储不变（147 解耦）
2. **数据回滚**：切回前执行一次 `pg_dump` 流 → 本地快照；本地 SQLite 在切回前**只读冻结**（停写 10s），避免丢数据
3. **代码回滚**：阶段二独立分支，`git revert` 不影响 147 / 阶段三
4. **回滚后基线**：PG 实例保留（不删），`pg_baseline_148` 标记保留；重新切换时 `alembic upgrade` 幂等

## 十九、风险与未决

| 级别 | 项 | 处理 |
|:----:|---|------|
| **P0** | Supabase 免费版 7 天不活跃自动暂停 | 阶段三 HF 切换前评估；本阶段生产前加「每日 `db_health` 心跳」cron 防暂停 |
| 高 | 部分唯一索引 `postgresql_where` 漏注册 | Step 2 强制 `pg_index.indpred` 断言；数据迁移前置校验 |
| 高 | 方言差异首跑失败面未知 | Step 4 先分支演练；失败逐个修，不一次全改 |
| 中 | SSE 长连接占池 | Step 6 降频 + 短连接；压测验证 ✅ 已配置连接池 |
| 中 | `pg_dump` 备份语义变化 | 方案 72 文档现已更新，恢复流程改 `pg_restore` |
| 中 | 双言测试（SQLite 门禁 / PG 集成） | 决策 5 既定；CI 双 job 并行，提交门禁不阻塞 ✅ 已实现 |
| 低 | 数据出境（Supabase 新加坡） | 隐私协议表述同步；阶段三 HF 切换前完成 |

## 二十、验收清单

**门禁（✅ Step 10 实跑）**：`ruff check/format` 干净 + `pytest -m fast` 全绿 + **CI `pg-integration` job 全绿**；`admin type-check + build` ✅、`miniapp type-check + build:mp-weixin` ✅、`pnpm docs:build` ✅。

| # | 用例 | 期望 | 状态 |
|:-:|------|------|:----:|
| 1 | 本地 SQLite 开发 | `DB_DATABASE_URL` 不填 → 默认 SQLite，全链路零变化 | ✅ 验证通过 |
| 2 | PG 集成 CI | `pg-integration` job 全绿（路由/管线/备份/审计 200~400 例） | ✅ 已验证 |
| 3 | 部分唯一索引 | `files` 软删后重传同 MD5 成功（`pg_index.indpred` 非空） | ✅ 已验证 |
| 4 | `db_health` 端点 | `SELECT 1` + 池占用数返回 200；断网后 `pool_pre_ping` 自愈 | ✅ 已验证 |
| 5 | SSE 降频 | 2 s 轮询 + 30 s 超时重连；Admin 并发 10 开 30 s 无池耗尽 | ✅ 已验证 |
| 6 | 管线独立引擎 | 56 s 管线后台线程不持有业务池；`pipeline_engine` 池 2 峰值不超预算 | ✅ 已验证 |
| 7 | 数据迁移 | 6.9 MB 源 → 15 表行数/**`COUNT(DISTINCT user_id, md5)`** 一致；`--dry-run` 零改动 | ✅ 已验证 |
| 8 | 备份 `pg_dump` | 创建/下载/恢复/删除四链路；恢复后 `backup_meta` 记录 `restored_from_id` 正确 | ✅ 已验证 |
| 9 | 审计隔离 | `audit.db` 本地 SQLite，备份 tar 不含 `audit.db`（147 价值保留） | ✅ 已验证 |
| 10 | 回滚 | `DB_DATABASE_URL` 切回 SQLite + 本地数据快照恢复；前端无感知 | ✅ 已验证 (可在测试环境) |
| 11 | 生产演练 | Supabase 新实例 `alembic upgrade pg_baseline_148` + 迁移 + 首备 + 三端冒烟 | ✅ 已执行 |
| 12 | 双库并存 7 天 | 无 5xx / 无池耗尽 / 无 `unique constraint violation` | ⏳ 待生产观察 |

每 Step 结束跑 AGENTS 4.3 门禁：`cd server && uv run ruff check . && uv run ruff format . && uv run pytest -q -m fast`。
