# 备份管理改造方案（148 阶段二 Step 8）

## 背景

方案 72 的备份管理系统基于本地 SQLite，使用 `backup_meta.db` + 压缩包。  
148 阶段二将业务库迁移到 PostgreSQL (Supabase)，备份流程需要适配 PG 的 `pg_dump` / `pg_restore`。

## 改造原则

1. **保持 Admin 手动操作不变**：不改变后端端点契约
2. **文件存储协议**：仍然使用 Kodo 对象存储（147）
3. **元数据隔离**：`backup_meta.db` 保持本地 SQLite（147 价值）
4. **备份格式**：`tar.gz` → `pg_dump 单文件 + 压缩包`

## 改造对比

| 组件 | 旧版 (SQLite) | 新版 (PG) |
|------|---------------|-----------|
| 备份格式 | SQLite `.db` + sqlite3 备份 | `pg_dump` 单文件 |
| 备份命令 | `sqlite3.backup()` | `pg_dump -Fc` (blob) |
| 恢复命令 | `sqlite3` 恢复 | `pg_restore` 流 |
| 备份文件 | `data/backups/*.tar.gz` | `data/backups/*.tar.gz` + `pg_dump` 数据 |
| 数据范围 | 仅业务库 | 业务库 + `backup_meta` |
| 压缩格式 | `.tar.gz` | `.tar.gz` (多层) |

## 实现步骤

### 1. 创建临时 PG 备份文件

```python
import subprocess
from pathlib import Path

def dump_pg_database(
    db_url: str,
    backup_file: Path,
) -> Path:
    """执行 pg_dump 备份"""
    # 解析连接串
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    host = parsed.hostname
    port = parsed.port
    dbname = parsed.path[1:]
    user = parsed.username
    password = parsed.password

    # 使用 pg_dump 命令
    result = subprocess.run(
        [
            "pg_dump",
            "-h", host,
            "-p", str(port),
            "-U", user,
            "-d", dbname,
            "-F", "c",  # custom format
            "-b",        # include large objects
            "-t", "public",  # only public schema
            backup_file,
        ],
        env={**os.environ, "PGPASSWORD": password},
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"pg_dump 失败: {result.stderr}")

    return backup_file
```

### 2. 恢复数据库

```python
def restore_pg_database(
    db_url: str,
    backup_file: Path,
) -> None:
    """执行 pg_restore 恢复"""
    # 解析连接串
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    host = parsed.hostname
    port = parsed.port
    dbname = parsed.path[1:]
    user = parsed.username
    password = parsed.password

    # 新建数据库（重置数据）
    conn_string = f"postgresql+psycopg://{user}:{password}@{host}:{port}/postgres"
    with create_engine(conn_string).connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {dbname}"))
        conn.execute(text(f"CREATE DATABASE {dbname}"))

    # 恢复
    result = subprocess.run(
        [
            "pg_restore",
            "-h", host,
            "-p", str(port),
            "-U", user,
            "-d", dbname,
            "-v",  # verbose
            "-j", "auto",  # parallel restore
            backup_file,
        ],
        env={**os.environ, "PGPASSWORD": password},
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"pg_restore 失败: {result.stderr}")
```

## 后端端点改造

### GET /api/admin/system/backups/{id}/download (无变化)

- 从 `backup_meta.db` 获取备份记录
- 返回 Kodo 下载链接
- 用户下载到本地

### POST /api/admin/system/backups/{id}/restore (改造)

```python
@router.post("/admin/system/backups/{backup_id}/restore")
def restore_backup(backup_id: int, admin: Admin = Depends(get_current_admin)):
    # 1. 查找备份记录
    backup = db.query(BackupRecord).get(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="备份不存在")

    # 2. 标记恢复状态
    backup.status = "restoring"
    db.commit()

    # 3. 下载备份文件到临时目录
    temp_dir = Path(tempfile.mkdtemp())
    try:
        backup_file = download_from_kodo(backup.storage_path, temp_dir)

        # 4. 恢复数据库
        restore_pg_database(settings.DB_DATABASE_URL, backup_file)

        # 5. 更新记录
        backup.status = "restored"
        backup.restored_at = time.time()
        backup.restored_from_id = backup_id
        db.commit()

        return {"success": True, "message": "恢复成功"}

    except Exception as e:
        backup.status = "failed"
        backup.error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"恢复失败: {e}")
    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)
```

## 测试策略

1. **本地测试**：使用本地 PG 测试容器
2. **沙盒验证**：在准备环境（非生产）测试完整流程
3. **回滚测试**：验证恢复失败时保持数据状态

## 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| `pg_dump` 输出大 | 网络传输慢 | 分块上传 + 断点续传 |
| 恢复失败 | 数据丢失 | 备份前快照 + 验证 |
| 兼容性问题 | 版本差异 | 提前测试 |

## 执行计划

- [ ] **Step 8 框架**: 创建代码框架（已完成）
- [ ] **Step 8 实现**: 编写端到点（待生产环境）
- [ ] **Step 8 测试**: 本地 PG 集成测试
- [ ] **Step 8 文档**: 更新 72 文档

---

## 相关文档

- [方案 72: Admin 备份管理增强](./72-Admin 备份管理增强.md)
- [148: 阶段二 Supabase PostgreSQL 细化方案](./148-阶段二SupabasePG细化方案.md)
