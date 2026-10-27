# 148 阶段二 Supabase PostgreSQL 迁移总结

## 核心成果

### 1. 数据库架构升级
- ✅ 将业务库从 SQLite 迁移到 PostgreSQL (Supabase)
- ✅ **统一 PG 存储**：业务库 PG (Supabase) + 审计库 PG (可选，未来) + **备份元数据 PG**（消除 SQLite 锁问题）
- ✅ 隔离价值保留：审计库/备份元数据最终都迁入 PG，实现统一存储

### 2. 方言兼容性改造
- ✅ **部分唯一索引双注册**：`uq_files_user_md5_active` 在 PG/SQLite 上均正确渲染带 WHERE 的索引
- ✅ **时间字段统一**：所有时间戳从 `Float` 改为 `DateTime`，确保双方言行为一致
- ✅ **主线稳定**：SQLite 门禁 355 passed；PG 集成 CI 作业就绪

### 3. 基础设施完善
- ✅ `make_engine` 工厂 + 连接池配置
- ✅ `db_health` 健康检查端点
- ✅ Alembic PG 基线 `pg_baseline_148`
- ✅ CI `pg-integration` 作业（PostgreSQL 服务容器）
- ✅ 数据迁移脚本框架 + 备份改造方案（PG 化）

### 4. 文档体系
- ✅ 148 细化方案文档（完整设计 + 执行进度）
- ✅ `BACKUP-TRANSITION.md` 备份改造方案（PG 元数据 + 异步化）
- ✅ 148 总结文档（本文）

## 执行进度总览

| Step | 内容 | 状态 | 备注 |
|------|------|:----:|------|
| 1 | 引擎工厂 + 配置 + 健康端点 | ✅ | 连接池参数、双舍入逻辑 |
| 2 | 索引双方言改造 + psycopg | ✅ | 单条 Index 双 where 参数 |
| 3 | PG 基线 + 方言分流 | ✅ | `pg_baseline_148.py` + 迁移 |
| 4 | CI PG 集成作业 | ✅ | `pg-integration.yml` |
| 5 | 方言差异修复 | ✅ | 时间字段统一 + 其他兼容 |
| 6 | 连接池收敛 | ✅ | 池参数 + 预算 + `db_health` |
| 7 | 数据迁移脚本框架 | ✅ | `migrate-sqlite-to-pg.py` |
| 8 | 备份改造方案 | ✅ | `BACKUP-TRANSITION.md` |
| 9 | ⏳ 生产前演练 | - | 待执行 |
| 10 | ⏳ 回归 + 收尾 | - | 待执行 |

## 技术亮点

### 1. 部分唯一索引的双方言渲染
```python
Index(
    "uq_files_user_md5_active",
    "user_id", "md5", unique=True,
    sqlite_where=text("deleted_at IS NULL"),
    postgresql_where=text("deleted_at IS NULL"),
)
```
实测表明：同一条 Index 同时传双方言 where 参数，在各自方言下均正确渲染带 WHERE 的索引，无需分名方案。

### 2. 时间字段统一改造
所有 `created_at`、`business_time`、`deleted_at` 从 `Float` 改为 `DateTime`，确保 PG 和 SQLite 行为一致。

### 3. 连接池配置与后端改造
- `pool_size=5`、`max_overflow=10`、`pool_recycle=3600`、`pool_pre_ping=True`
- 峰值连接数 ≤ 15（业务池）+ 2（管线）= 17
- 预留 Admin 查询缓冲：3~8 连接
- **备份元数据 PG 化：消除 SQLite 锁竞争，支持异步操作**

### 4. 统一 PG 存储架构
- 业务库 PG (Supabase) - 主数据库
- 审计库未来可迁入 PG (当前仍保持 SQLite 独立，值)
- **备份元数据 PG** - 存储在 PG `backup_logs` 表，避免 SQLite 锁
- 对象存储 Kodo (147 阶段)
- **异步任务队列：备份/恢复操作通过异步队列执行，前端轮询状态**

## 门禁状态

```bash
cd server
uv run ruff check .  # ✅ 通过
uv run ruff format . # ✅ 通过
uv run pytest -m fast 355 passed # ✅ 通过
```

## 待办事项

### Step 9：生产前演练
1. 创建新的 Supabase 实例（测试数据库）
2. 执行 `pg_baseline_148` 迁移
3. 运行数据迁移脚本 `--dry-run`
4. 正式迁移验证（如有必要）
5. 备份 `pg_dump` 首备
6. 三端冒烟测试（小程序 / Admin / 管线）

### Step 10：回归 + 收尾
1. 运行全量测试 `pytest -m "not fast"` (PG 环境)
2. 更新 README / 侧边栏 / 146 文档
3. 版本 bump (package.json + CHANGELOG)
4. 合并到主分支

## 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| PG 连接超时 | 服务不可用 | `pool_pre_ping=True` 断线自愈 |
| 数据迁移失败 | 数据丢失 | 迁移前备份 + `--dry-run` 检查 |
| 备份恢复失败 | 无法回滚 | 测试恢复流程 + 验证 + 双写策略 |
| 表单冲突 | 唯一约束失败 | `WHERE deleted_at IS NULL` 索引保护 |
| 异步任务失败 | 备份/恢复超时 | 任务队列 + 重试机制 + 超时监控 |

## 代码变更统计

- **模型文件修改**：10+ 个（所有时间戳字段）
- **PG 基线 DDL**：15 表 + 索引
- **CI 作业**：1 个
- **文档**：3 份
- **脚本**：2 个（迁移 + 备份）

## 相关文档

- [148-阶段二SupabasePG细化方案.md](./148-阶段二SupabasePG细化方案.md) （主文档）
- [BACKUP-TRANSITION.md](./BACKUP-TRANSITION.md) （备份改造）
- [146-后台三件套改造评估.md](./146-后台三件套改造评估.md) （总纲）

---

*本文档由 AI 协作者自动生成，最后更新：2026-10-26*
