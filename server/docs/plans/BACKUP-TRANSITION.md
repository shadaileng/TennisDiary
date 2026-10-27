# 备份管理改造方案（148 阶段二 Step 8）

## 背景

方案 72 的备份管理系统使用独立 SQLite 文件 `backup_meta.db` 存储备
份/恢复记录。该设计存在两个主要问题：

1. **并发锁限制**：SQLite 文件锁机制在高并发写入时会导致锁等待，特别是
   恢复操作需要长时间占用资源时，会阻塞备份列表查询等日常操作。
2. **运维复杂度**：独立元数据库产生额外文件，需要维护两个数据库文件，增
   加备份和迁移的复杂度。

148 阶段二将业务库迁移到 PostgreSQL (Supabase)，**决定将备份元数据也迁入
PG 主库，统一存储、避免锁问题，并支持异步记录**。

## 改造原则

1. **备份元数据 PG 化**：元数据表 `backup_logs` 存入 PG 主库，替代本地
   `backup_meta.db`
2. **保持 Admin 手动操作不变**：不改变后端端点契约（兼容现有前端）
3. **文件存储协议**：仍然使用 Kodo 对象存储（147 阶段）
4. **备份格式**：`pg_dump` 单文件 + Kodo 上传
5. **异步化**：备份/恢复操作通过异步队列执行，前端轮询任务状态

## 改造对比

| 组件 | 旧版 (SQLite 元数据) | 新版 (PG 元数据) |
|------|---------------------|-----------------|
| 元数据存储 | `backup_meta.db` (本地 SQLite 文件) | PG 主库 `backup_logs` 表 |
| 并发锁 | 存在写锁竞争，恢复时阻塞列表查询 | PG 高并发无锁，读写分离 |
| 备份格式 | 本地 SQLite 文件 + 快照 | `pg_dump` 单文件 |
| 备份命令 | `sqlite3.backup()` | `pg_dump -Fc` (blob) |
| 恢复命令 | `sqlite3` 恢复 | `pg_restore` 流 |
| 备份文件 | `data/backups/*.tar.gz` | `data/backups/*.tar.gz` |
| 异步支持 | 不支持 | 原生支持任务队列 |
| 运维复杂度 | 需维护额外 SQLite 文件 | 统一在 PG 主库，自动备份即同步 |

## 技术实现

### 1. 备份元数据模型（PG 版）

```python
# app/models/backup_log.py
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, func, Index
from sqlalchemy.orm import declarative_base
from app.core.database import Base

class BackupLog(Base):
    __tablename__ = "backup_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False, unique=True, index=True)
    size = Column(Integer, nullable=False, default=0)
    type = Column(String(16), nullable=False, default="manual", index=True)
    status = Column(String(16), nullable=False, default="created", index=True)
    note = Column(String(256), default="")
    created_by = Column(Integer, nullable=True)
    restored_by = Column(Integer, nullable=True)
    restored_at = Column(DateTime, nullable=True)
    restored_from_id = Column(Integer, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 复合索引提升查询性能
    __table_args__ = (
        Index('ix_backup_logs_type_status', 'type', 'status'),
    )
```

### 2. 创建 PG 备份

```python
import subprocess
import tempfile
import uuid
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from app.core.database import SessionLocal
from app.models.backup_log import BackupLog
from app.core.storages import storage
from app.core.kodo import KodoBackend
from app.core.config import settings
from app.core.task_queue import task_queue

async def create_backup_async(
    db_url: str,
    backup_name: str,
    note: str = "",
    created_by: int = None,
) -> str:
    """异步执行 pg_dump 备份并上传到 Kodo"""
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    host = parsed.hostname
    port = parsed.port
    dbname = parsed.path[1:]
    user = parsed.username
    password = parsed.password

    temp_dir = Path(tempfile.mkdtemp())
    temp_file = temp_dir / f"{backup_name}.dump"
    
    try:
        # 执行 pg_dump
        result = subprocess.run(
            [
                "pg_dump",
                "-h", host,
                "-p", str(port),
                "-U", user,
                "-d", dbname,
                "-F", "c",
                "-b",
                "-v",
                str(temp_file),
            ],
            env={**os.environ, "PGPASSWORD": password},
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump 失败: {result.stderr}")
        
        # 压缩备份文件
        compressed = temp_dir / f"{backup_name}.tar.gz"
        import tarfile
        with open(temp_file, "rb") as src, tarfile.open(compressed, "w:gz") as tar:
            tar.add(src, arcname=backup_name)
        
        # 上传到 Kodo
        storage_url = KodoBackend.put_object(compressed, bucket="backups")
        
        # 记录备份元数据到 PG
        db = SessionLocal()
        try:
            backup = BackupLog(
                name=backup_name,
                size=compressed.stat().st_size,
                type="backup",
                status="created",
                note=note,
                created_by=created_by,
            )
            db.add(backup)
            db.commit()
        finally:
            db.close()
        
        return str(storage_url)
        
    finally:
        temp_file.unlink()
        compressed.unlink()
        temp_dir.rmdir()

async def create_backup_wrapper(
    note: str = "",
    created_by: int = None,
) -> str:
    """创建备份的异步入口，返回 task_id"""
    backup_name = f"backup_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    # 提交到任务队列
    task_id = f"backup_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    await task_queue.submit(task_id, create_backup_async(
        db_url=settings.DB_DATABASE_URL,
        backup_name=backup_name,
        note=note,
        created_by=created_by,
    ))
    
    return task_id
```

### 3. 恢复数据库

```python
async def restore_backup_async(
    db_url: str,
    backup_id: int,
    admin_id: int,
) -> None:
    """异步执行 pg_restore 恢复"""
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    host = parsed.hostname
    port = parsed.port
    dbname = parsed.path[1:]
    user = parsed.username
    password = parsed.password

    # 查找备份记录（PG 中）
    db = SessionLocal()
    backup = db.query(BackupLog).get(backup_id)
    if not backup:
        db.close()
        raise HTTPException(status_code=404, detail="备份不存在")

    try:
        # 下载备份文件到临时目录
        temp_dir = Path(tempfile.mkdtemp())
        backup_file = temp_dir / backup.name
        
        # 从 Kodo 下载（实现略）
        # download_from_kodo(backup.storage_path, backup_file)

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
                "-v",
                "-j", "auto",
                str(backup_file),
            ],
            env={**os.environ, "PGPASSWORD": password},
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"pg_restore 失败: {result.stderr}")

        # 更新元数据状态
        backup.status = "restored"
        backup.restored_at = datetime.now(datetime.timezone.utc)
        backup.restored_from_id = backup_id
        backup.created_by = admin_id
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

async def restore_backup_wrapper(
    backup_id: int,
    admin_id: int,
) -> str:
    """恢复备份的异步入口，返回 task_id"""
    task_id = f"restore_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    await task_queue.submit(task_id, restore_backup_async(
        db_url=settings.DB_DATABASE_URL,
        backup_id=backup_id,
        admin_id=admin_id,
    ))
    
    return task_id
```

## 后端端点改造

### GET /api/admin/system/backups (无变化)

```python
@router.get("/admin/system/backups")
def get_backups(
    page: int = 1,
    limit: int = 20,
    status: str = None,
    type: str = None,
    admin: Admin = Depends(get_current_admin)
):
    db = SessionLocal()
    query = db.query(BackupLog).filter(BackupLog.deleted_at.is_(None))
    
    if status:
        query = query.filter(BackupLog.status == status)
    if type:
        query = query.filter(BackupLog.type == type)
    
    total = query.count()
    backups = query.order_by(BackupLog.created_at.desc()) \
        .offset((page-1)*limit).limit(limit).all()
    
    return {
        "success": True,
        "data": {
            "backups": backups,
            "total": total,
            "page": page,
            "limit": limit,
        }
    }
```

### POST /api/admin/system/backups (改造为异步)

```python
@router.post("/admin/system/backups")
async def create_backup_endpoint(
    request: Request,
    note: str = Query(default=""),
    admin: Admin = Depends(get_current_admin),
):
    task_id = await create_backup_wrapper(
        note=note,
        created_by=admin.id,
    )
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "备份任务已启动",
    }
```

### POST /api/admin/system/backups/{id}/restore (改造为异步)

```python
@router.post("/admin/system/backups/{backup_id}/restore")
async def restore_backup_endpoint(
    request: Request,
    backup_id: int,
    admin: Admin = Depends(get_current_admin),
):
    task_id = await restore_backup_wrapper(
        backup_id=backup_id,
        admin_id=admin.id,
    )
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "恢复任务已启动",
    }
```

### GET /api/admin/system/backups/tasks/{task_id} (新增)

```python
@router.get("/admin/system/backups/tasks/{task_id}")
async def get_task_status(task_id: str, admin: Admin = Depends(get_current_admin)):
    """查询异步任务状态"""
    status = await task_queue.get_status(task_id)
    
    return {
        "success": True,
        "task_id": task_id,
        "status": status.get("status"),
        "progress": status.get("progress"),
        "error": status.get("error"),
    }
```

## 数据迁移策略

1. **并行运行期**：备份元数据从 SQLite `backup_meta.db` 迁移到 PG `backup_logs` 表
2. **数据同步**：使用数据迁移脚本将历史备份记录导入 PG
3. **切换开关**：通过配置项 `BACKUP_META_SOURCE` 控制备份元数据源（`sqlite` / `pg`）
4. **回滚支持**：保留 SQLite 元数据 30 天，以便快速回滚

### 迁移脚本

```python
# scripts/migrate-backup-meta-to-pg.py
import sys
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.backup_log import BackupLog
from app.core.backup_meta import MetaBase
from app.models.backup_record import BackupRecord

def migrate():
    # 连接 SQLite 元数据库
    src_db = SessionLocal(autocommit=False)
    src_engine = src_db bind
    
    # 连接 PG 主库
    pg_db = SessionLocal(bind=settings.DB_DATABASE_URL)
    pg_engine = pg_db bind
    
    try:
        # 迁移备份记录
        records = src_db.query(BackupRecord).filter(
            BackupRecord.deleted_at.is_(None)
        ).all()
        
        for record in records:
            backup_log = BackupLog(
                name=record.name,
                size=record.size,
                type=record.type,
                status=record.status,
                note=record.note,
                created_by=record.created_by,
                restored_by=record.restored_by,
                restored_at=record.restored_at,
            )
            pg_db.add(backup_log)
        
        pg_db.commit()
        print(f"迁移完成：{len(records)} 条记录")
    finally:
        src_db.close()
        pg_db.close()

if __name__ == "__main__":
    migrate()
```

## 测试策略

1. **本地测试**：使用本地 PG 测试容器
2. **沙盒验证**：在准备环境（非生产）测试完整流程
3. **回滚测试**：验证恢复失败时保持数据状态
4. **并发测试**：验证 PG 高并发下备份/恢复操作稳定性
5. **迁移测试**：验证从 SQLite 到 PG 的元数据迁移
6. **异步任务测试**：验证任务队列正常工作

## 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| `pg_dump` 输出大 | 网络传输慢 | 分块上传 + 断点续传 + 压缩优化 |
| 恢复失败 | 数据丢失 | 备份前快照 + 验证 + 双写策略 |
| 兼容性问题 | 版本差异 | 提前测试 + 版本降级支持 |
| 元数据迁移不一致 | 备份记录丢失 | 双写 + 同步校验 + 回滚机制 |
| 异步任务失败 | 备份/恢复超时 | 任务队列 + 重试机制 + 超时监控 |
| 锁竞争 | 并发操作阻塞 | PG 原生高并发 + 异步执行 |

## 执行计划

- [ ] **Step 8 框架**: 创建代码框架（已完成）
- [ ] **Step 8 实现**: 编写端到点（待生产环境）
- [ ] **Step 8 测试**: 本地 PG 集成测试
- [ ] **Step 8 文档**: 更新 72 文档
- [ ] **Step 8 迁移**: 执行元数据迁移脚本
- [ ] **Step 8 切换**: 切换备份元数据源到 PG

---

## 相关文档

- [方案 72: Admin 备份管理增强](./72-Admin 备份管理增强.md)
- [148: 阶段二 Supabase PostgreSQL 细化方案](./148-阶段二SupabasePG细化方案.md)
