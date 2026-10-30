"""SQLite → PostgreSQL 数据迁移脚本（148 阶段二 Step 5）

使用方式：
  1. 设置 PG_MIGRATION_URL（PostgreSQL 目标）
  2. 运行 --dry-run 检查目标和源数据库
  3. 确认无误后去掉 --dry-run 执行正式迁移

特性：
  - 时间戳日期转换（Float → datetime）
  - 软删除字段特殊处理（deleted_at）
  - 唯一约束预检（files.md5）
  - 聚合校验（行数、DISTINCT count）
"""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

# 确保 APP 可以被导入
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "app"))

from app.core.config import settings  # noqa: E402
from app.models import get_all_models  # noqa: E402

# 需要迁移的表清单
MIGRATION_TABLES = [
    "admins",
    "ai_providers",
    "analyses",
    "analysis_video_info",
    "checkins",
    "diaries",
    "event_logs",
    "file_bindings",
    "files",
    "gears",
    "posts",
    "roles",
    "system_configs",
    "users",
    "weight_records",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 源数据库 URL (SQLite)
SOURCE_DB = settings.DATABASE_URL  # 默认是本地 SQLite

# 目标数据库 URL (PostgreSQL) - 从环境变量读取
TARGET_DB_URL = os.getenv("PG_MIGRATION_URL", os.getenv("DB_DATABASE_URL", ""))


def get_engines() -> tuple[Any, Any, Any, Any]:
    """获得源和目标数据库引擎"""
    if not TARGET_DB_URL:
        logger.error("❌ 目标 PG 数据库 URL 未设置，请设置 PG_MIGRATION_URL 环境变量")
        sys.exit(1)

    src_engine = create_engine(SOURCE_DB, echo=False)
    dst_engine = create_engine(TARGET_DB_URL, echo=False)

    return (
        src_engine,
        dst_engine,
        create_engine(SOURCE_DB, echo=False),
        create_engine(TARGET_DB_URL, echo=False),
    )


def check_table_exists(engine: Any, table_name: str) -> bool:
    """检查表是否存在"""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                f"SELECT EXISTS (SELECT FROM information_schema.tables "
                f"WHERE table_name = '{table_name}')"
            )
        )
        return result.fetchone()[0]


def get_table_column_info(engine: Any, table_name: str) -> dict[str, tuple[str, str]]:
    """获取表列信息"""
    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position;
        """)
        )
        return {row[0]: (row[1], row[2]) for row in result.fetchall()}


def validate_schema(src_engine: Any, dst_engine: Any) -> list[str]:
    """验证目标表结构是否与源表一致"""
    errors = []

    for table in MIGRATION_TABLES:
        src_cols = get_table_column_info(src_engine, table)
        dst_cols = get_table_column_info(dst_engine, table)

        # 检查列名是否一致
        if set(src_cols.keys()) != set(dst_cols.keys()):
            errors.append(
                f"{table}: 列不一致 - 源: {set(src_cols.keys())} 目标: {set(dst_cols.keys())}"
            )
            continue

        # 检查类型兼容性（用于警告但不强制）
        for col in src_cols:
            src_type = src_cols[col][0]
            dst_type = dst_cols[col][0]
            # 忽略 minor 差异
            if src_type != dst_type and not _is_type_compatible(src_type, dst_type):
                errors.append(f"{table}.{col}: 类型不兼容 - 源: {src_type} 目标: {dst_type}")

    return errors


def _is_type_compatible(src_type: str, dst_type: str) -> bool:
    """简单的类型兼容性检查"""
    # FLOAT → FLOAT (PostgreSQL)
    # FLOAT → DOUBLE PRECISION (PostgreSQL)
    # DATETIME → TIMESTAMP
    return (
        src_type.upper() == dst_type.upper()
        or (
            src_type.upper() in ["FLOAT"]
            and dst_type.upper() in ["FLOAT", "DOUBLE PRECISION", "NUMERIC"]
        )
        or (
            src_type.upper() in ["DATETIME", "TIMESTAMP"]
            and dst_type.upper() in ["TIMESTAMP", "DATE"]
        )
    )


def count_rows(engine: Any, table_name: str) -> int:
    """统计表中记录数"""
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.fetchone()[0]


def migrate_table(
    src_session: Any,
    dst_session: Any,
    table_name: str,
    dry_run: bool = False,
) -> int:
    """迁移单表数据（从源到目标）"""
    try:
        query = src_session.query()

        # 获取模型
        models = get_all_models()
        model = next((m for m in models if m.__tablename__ == table_name), None)
        if not model:
            logger.warning(f"⚠️ {table_name}: 找不到 ORM 模型，跳过迁移")
            return 0

        if dry_run:
            count = query.from_statement(query.statement.text).count()
            logger.info(f"💾 {table_name}: PRIME 模式 - 预计迁移 {count} 行")
            return 0

        # 复制记录
        count = 0
        for src_obj in query:
            dst_obj = model()
            for field_name in src_obj.__table__.columns.keys():
                value = getattr(src_obj, field_name)
                # 软删除字段特殊处理（时间戳转 datetime）
                if field_name in ["deleted_at", "business_time", "created_at", "updated_at"]:
                    if value is not None:
                        # 如果是 float 时间戳，转为 datetime
                        if isinstance(value, (int, float)):
                            dst_value = datetime.fromtimestamp(value, tz=timezone.utc)
                        else:
                            dst_value = value
                    else:
                        dst_value = None
                else:
                    dst_value = value

                setattr(dst_obj, field_name, dst_value)
            dst_session.add(dst_obj)
            count += 1
            if count % 1000 == 0:
                dst_session.commit()
                logger.info(f"💾 {table_name}: {count} 行")

        dst_session.commit()
        logger.info(f"✅ {table_name}: 迁移完成 {count} 行")
        return count
    except Exception as e:
        dst_session.rollback()
        logger.error(f"❌ {table_name}: 迁移失败 - {e}")
        raise
    finally:
        src_session.close()
        dst_session.close()


def validate_lineage(src_engine: Any, dst_engine: Any) -> list[str]:
    """数据一致性校验"""
    diffs = []

    # 总分表
    for table in MIGRATION_TABLES:
        src_count = count_rows(src_engine, table)
        dst_count = count_rows(dst_engine, table)
        if src_count != dst_count:
            diffs.append(f"{table}: 行数不一致 - 源: {src_count} 目标: {dst_count}")

    # files 表唯一约束
    diff_files_md5 = check_files_unique(dst_engine)
    if diff_files_md5:
        diffs.append(f"files: 唯一约束冲突 - {diff_files_md5}")

    return diffs


def check_files_unique(engine: Any) -> str | None:
    """检查 files 表是否满足唯一约束 (user_id, md5, deleted_at IS NULL)"""
    with engine.connect() as conn:
        # 查询软删记录数量大于1 的唯一 user_id 和md5
        result = conn.execute(
            text("""
            SELECT user_id, md5, COUNT(*) as cnt
            FROM files
            WHERE deleted_at IS NULL
            GROUP BY user_id, md5
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        )
        rows = result.fetchall()
        if rows:
            return f"重复记录: {len(rows)} 条 (user_id, md5)."
    return None


def run_migrate(dry_run: bool = True) -> None:
    """执行迁移"""
    logger.info("🚀 SQLite → PostgreSQL 数据迁移脚本")
    logger.info(f"📍 源数据库: {SOURCE_DB}")
    logger.info(f"🎯 目标数据库: {TARGET_DB_URL}")

    try:
        src_engine, dst_engine, src_session0, dst_session0 = get_engines()
    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ 数据库连接失败: {e}")
        sys.exit(1)

    src_session = src_session0()
    dst_session = dst_session0()

    try:
        # 校验目标表结构
        logger.info("\n📊 验证表结构...")
        errors = validate_schema(src_engine, dst_engine)
        if errors:
            logger.error("❌ 表结构验证失败:")
            for e in errors:
                logger.error(f"  - {e}")
            logger.error("\n请检查目标数据库是否已初始化到最新状态")
            sys.exit(1)
        else:
            logger.info("✅ 表结构验证通过")

        # 统计源表数据量
        logger.info("\n📊 源表数据量:")
        for table in MIGRATION_TABLES:
            if check_table_exists(src_engine, table):
                count = count_rows(src_engine, table)
                logger.info(f"  {table}: {count} 行")

        # 执行迁移
        logger.info("\n🚀 开始迁移...")
        total_migrated = 0
        for table in MIGRATION_TABLES:
            logger.info(f"\n📄 处理表: {table}")
            try:
                migrated = migrate_table(src_session, dst_session, table, dry_run)
                total_migrated += migrated
                if migrated == 0:
                    logger.warning(f"⚠️ {table}: 无迁移 (表不存在或无数据)")
            except Exception as e:  # noqa: BLE001
                logger.error(f"❌ {table}: 迁移异常 - {e}")
                logger.error(f"   错误详情: {e}")
                sys.exit(1)

        logger.info(f"\n🎉 迁移完成: 共迁移 {total_migrated} 行数据")

        # 数据一致性校验
        if not dry_run:
            logger.info("\n🔍 数据一致性校验...")
            lineage_diffs = validate_lineage(src_engine, dst_engine)
            if lineage_diffs:
                logger.error("❌ 数据一致性校验失败:")
                for diff in lineage_diffs:
                    logger.error(f"  - {diff}")
                sys.exit(1)
            else:
                logger.info("✅ 数据一致性校验通过")

            logger.info("\n⚠️ 注意：索引重建建议 POSTGRESQL 自动完成 (ANALYZE)")
        logger.info("\n✅ 迁移脚本执行完毕")
    finally:
        src_session.close()
        dst_session.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "--validate" in sys.argv
    run_migrate(dry_run=dry_run)
