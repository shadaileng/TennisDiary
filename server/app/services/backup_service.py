"""备份服务（148 阶段二：PG 版）

支持 SQLite 本地文件和 PostgreSQL 远程/本地数据库的备份与恢复。

策略：
- SQLite: 直接复制 .db 文件
- PostgreSQL: 使用 pg_dump / pg_restore
"""

import os
import shutil
import subprocess
import tarfile
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("backup")

DATA_DIR = Path(settings.DATA_DIR).resolve()
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_META_DB_NAME = "backup_meta.db"


def is_postgres_url(url: str) -> bool:
    """判断是否为 PostgreSQL DSN"""
    return "postgresql" in url.lower() or "postgres" in url.lower()


class BackupService:
    """备份服务"""

    @staticmethod
    def backup_database(target: Path | None = None, is_pre: bool = False) -> tuple[Path, int]:
        """创建备份（返回备份路径和文件大小）"""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        if is_pre:
            # 兜底备份使用预定义命名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if target is None:
                backup_path = BACKUP_DIR / f"pre_restore_{timestamp}_{uuid.uuid4().hex[:6]}.tar.gz"
            else:
                backup_path = target
        else:
            # 正常备份
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if target is None:
                backup_path = BACKUP_DIR / f"backup_{timestamp}_{uuid.uuid4().hex[:6]}.tar.gz"
            else:
                backup_path = target

        if is_postgres_url(settings.DATABASE_URL):
            return _pg_dump_and_pack(backup_path, timestamp)
        else:
            return _sqlite_pack(backup_path, timestamp)

    @staticmethod
    def restore_backup(backup_path: Path) -> None:
        """恢复备份"""
        if is_postgres_url(settings.DATABASE_URL):
            _pg_restore_unpacked(backup_path)
        else:
            _sqlite_unpack(backup_path)

    @staticmethod
    def delete_backup(backup_path: Path) -> None:
        """删除备份文件"""
        if backup_path.exists():
            backup_path.unlink()
            log.info(f"删除备份: {backup_path.name}")

    @staticmethod
    def verify_backup(backup_path: Path) -> bool:
        """验证备份文件完整性"""
        if backup_path.suffix == ".tar.gz":
            try:
                with tarfile.open(backup_path, "r:gz") as tar:
                    return tar.next() is not None  # 检查是否非空
            except (tarfile.TarError, OSError) as e:
                log.error("验证备份失败: {}", e)
                return False
        return False


def _pg_dump_and_pack(backup_path: Path, timestamp: str) -> tuple[Path, int]:
    """PostgreSQL 备份：pg_dump + 合并 backup_meta.db"""

    # 准备临时工作目录
    work_dir = BACKUP_DIR / f"tmp_{timestamp}"
    work_dir.mkdir(parents=True, exist_ok=True)

    pg_dump_path = work_dir / "dump.dump"
    meta_backup_path = work_dir / BACKUP_META_DB_NAME

    try:
        # 1. pg_dump 导出业务库
        log.info(f"pg_dump 导出数据库: {pg_dump_path.name}")
        ddl = settings.DATABASE_URL
        env = os.environ.copy()
        # 检测 PG 密码（环境变量 PG_PASSWORD），找不到则用默认
        env.get("PG_PASSWORD", env.get("DB_PASSWORD", ""))

        cmd = [
            "pg_dump",
            "--dbname=" + ddl,
            "--file=" + str(pg_dump_path),
            "--no-owner",
            "--no-privileges",
            "--format=custom",  # -Fc 格式
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        if proc.returncode != 0:
            log.error(f"pg_dump 失败: {proc.stderr}")
            raise RuntimeError(f"pg_dump 失败: {proc.stderr[:200]}")

        # 2. 备份 backup_meta.db（用于保留备份记录元数据）
        meta_db_path = DATA_DIR / BACKUP_META_DB_NAME
        if meta_db_path.exists():
            shutil.copy2(meta_db_path, meta_backup_path)
        else:
            # 元数据库没有，创建一个空的文件占位
            meta_backup_path.touch()

        # 3. 打包（仅包含 dump 和 meta 文件，不含其他本地数据）
        log.info(f"打包备份: {backup_path.name}")
        with tarfile.open(backup_path, "w:gz", format=tarfile.GNU_FORMAT) as tar:
            tar.add(pg_dump_path, arcname="dump.dump")
            if meta_backup_path.exists():
                tar.add(meta_backup_path, arcname=BACKUP_META_DB_NAME)

        size = backup_path.stat().st_size
        log.info(f"✅ PostgreSQL 备份完成: {backup_path.name} ({size / 1024 / 1024:.1f} MB)")
        return backup_path, size
    finally:
        # 清理临时目录
        if work_dir.exists():
            shutil.rmtree(work_dir)


def _sqlite_pack(backup_path: Path, timestamp: str) -> tuple[Path, int]:
    """SQLite 备份：复制业务库 + backup_meta.db"""

    # 准备临时工作目录
    work_dir = BACKUP_DIR / f"tmp_{timestamp}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. 复制业务数据库
        db_path = DATA_DIR / "tennis_diary.db"
        if not db_path.exists():
            raise FileNotFoundError("业务数据库不存在")
        shutil.copy2(db_path, work_dir / "tennis_diary.db")

        # 2. 备份 backup_meta.db
        meta_db_path = DATA_DIR / BACKUP_META_DB_NAME
        if meta_db_path.exists():
            shutil.copy2(meta_db_path, work_dir / BACKUP_META_DB_NAME)

        # 3. 打包（仅包含 db 和 meta 文件）
        log.info(f"打包备份: {backup_path.name}")
        with tarfile.open(backup_path, "w:gz", format=tarfile.GNU_FORMAT) as tar:
            for name in ["tennis_diary.db", BACKUP_META_DB_NAME]:
                file_path = work_dir / name
                if file_path.exists():
                    tar.add(file_path, arcname=name)

        size = backup_path.stat().st_size
        log.info(f"✅ SQLite 备份完成: {backup_path.name} ({size / 1024 / 1024:.1f} MB)")
        return backup_path, size
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir)


def _pg_restore_unpacked(backup_path: Path) -> None:
    """PostgreSQL 备份恢复：解压并 pg_restore"""
    # 1. 创建临时工作目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = BACKUP_DIR / f"restore_{timestamp}_{uuid.uuid4().hex[:6]}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 2. 解压备份
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(work_dir)

        # 3. 检查必需文件
        dump_path = work_dir / "dump.dump"
        if not dump_path.exists():
            raise FileNotFoundError("备份文件中缺少 dump.dump")

        # 4. 执行 pg_restore
        log.info(f"pg_restore 恢复数据库: {dump_path.name}")
        env = os.environ.copy()
        env.get("PG_PASSWORD", env.get("DB_PASSWORD", ""))

        ddl = settings.DATABASE_URL
        cmd = [
            "pg_restore",
            "--dbname=" + ddl,
            "--clean",  # 先清理
            "--if-exists",  # 忽略不存在
            "--format=custom",
            str(dump_path),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        if proc.returncode != 0:
            log.error(f"pg_restore 失败: {proc.stderr}")
            raise RuntimeError(f"pg_restore 失败: {proc.stderr[:200]}")

        log.info("✅ PostgreSQL 恢复完成")

        # 5. 清理临时目录
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir)


def _sqlite_unpack(backup_path: Path) -> None:
    """SQLite 备份恢复：解压并替换文件"""
    # 1. 创建临时工作目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = BACKUP_DIR / f"restore_{timestamp}_{uuid.uuid4().hex[:6]}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 解压备份
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(work_dir)

        # 检查必需文件
        db_path = work_dir / "tennis_diary.db"
        if not db_path.exists():
            raise FileNotFoundError("备份文件中缺少 tennis_diary.db")

        # 关闭现有数据库连接（需要一次性替换）
        # 简单做法：先 move 掉旧库，再 copy 新库到 DATA_DIR
        old_db = DATA_DIR / "tennis_diary.db"
        if old_db.exists():
            backup_old = (
                DATA_DIR / f"tennis_diary.db.{datetime.now().strftime('%Y%m%d_%H%M%S')}.old"
            )
            shutil.move(old_db, backup_old)
            log.info(f"已备份旧库: {backup_old.name}")

        shutil.copy2(db_path, DATA_DIR / "tennis_diary.db")

        # 恢复 backup_meta.db（如果有）
        meta_src = work_dir / BACKUP_META_DB_NAME
        meta_dst = DATA_DIR / BACKUP_META_DB_NAME
        if meta_src.exists():
            if meta_dst.exists():
                backup_meta = (
                    DATA_DIR
                    / f"{BACKUP_META_DB_NAME}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.old"
                )
                shutil.move(meta_dst, backup_meta)
            shutil.copy2(meta_src, meta_dst)

        log.info("✅ SQLite 恢复完成")

    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir)
