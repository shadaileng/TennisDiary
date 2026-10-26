"""SQLite → PostgreSQL 数据迁移脚本（148 阶段二 Step 7）

使用方式：
  1. 设置 DB_DATABASE_URL (SQLite 源) 和 PG_URL (环境隔离)
  2. 运行 --dry-run 检查目标和源数据库
  3. 确认无误后去掉 --dry-run 执行正式迁移
"""

import sys
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'app'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 需要迁移的表清单
MIGRATION_TABLES = [
    'admins', 'ai_providers', 'analyses', 'analysis_video_info',
    'checkins', 'diaries', 'event_logs', 'file_bindings', 'files',
    'gears', 'posts', 'roles', 'system_configs', 'users', 'weight_records'
]

# 源数据库 URL (SQLite)
SOURCE_DB = settings.DATABASE_URL  # 默认是本地 SQLite

# 目标数据库 URL (PostgreSQL) - 从环境变量读取
TARGET_DB_URL = os.getenv('PG_MIGRATION_URL', os.getenv('DB_DATABASE_URL', ''))


def get_engines() -> Tuple[create_engine, create_engine, sessionmaker, sessionmaker]:
    """获得源和目标数据库引擎"""
    if not TARGET_DB_URL:
        print("❌ 目标 PG 数据库 URL 未设置，请设置 PG_MIGRATION_URL 环境变量")
        sys.exit(1)

    src_engine = create_engine(SOURCE_DB, echo=False)
    dst_engine = create_engine(TARGET_DB_URL, echo=False)

    return src_engine, dst_engine, sessionmaker(bind=src_engine), sessionmaker(bind=dst_engine)


def check_table_exists(engine: create_engine, table_name: str) -> bool:
    """检查表是否存在"""
    with engine.connect() as conn:
        result = conn.execute(text(
            f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')"
        ))
        return result.fetchone()[0]


def get_table_column_info(engine: create_engine, table_name: str) -> Dict[str, str]:
    """获取表列信息"""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position;
        """))
        return {row[0]: (row[1], row[2]) for row in result.fetchall()}


def validate_schema(src_engine: create_engine, dst_engine: create_engine) -> List[str]:
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

        # 检查位置顺序（仅用于警告）
        src_order = list(src_cols.keys())
        dst_order = list(dst_cols.keys())
        if src_order != dst_order:
            errors.append(f"{table}: 列顺序不一致 - 源: {src_order} 目标: {dst_order}")

    return errors


def count_rows(engine: create_engine, table_name: str) -> int:
    """统计表中记录数"""
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.fetchone()[0]


def migrate_table(
    src_db: sessionmaker,
    dst_db: sessionmaker,
    table_name: str,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """迁移单表数据（从源到目标）"""
    src_session = src_db()
    dst_session = dst_db()

    try:
        # 从源表读取
        src_session.execution_options(stream_results=True).streambar()
        query = src_session.query()

        # 获取模型
        from app.models import get_all_models
        from app.core.database import Base

        # 通过反射来获取模型定义不太方便，我们使用 SQLAlchemy ORM
        # 直接使用 query()
        models = get_all_models()
        model = next((m for m in models if m.__tablename__ == table_name), None)
        if not model:
            # 找不到 ORM 模型，跳过
            print(f"⚠️ {table_name}: 找不到 ORM 模型，跳过迁移")
            return 0, 0

        if dry_run:
            count = query.from_statement(query.statement.text).count()
            print(f"💾 {table_name}: PRIME 模式 - 预计迁移 {count} 行")
            return 0, 0

        # 复制记录
        count = 0
        for obj in query:
            dst_obj = model()
            for field_name in obj.__table__.columns.keys():
                value = getattr(obj, field_name)
                # 软删除字段特殊处理：deleted_at 为 time.sleep() 时保持
                if field_name == 'deleted_at':
                    if value is not None:
                        # 将时间戳转为 datetime
                        if isinstance(value, float):
                            from datetime import datetime
                            value = datetime.fromtimestamp(value, tz=datetime.now().astimezone().tzinfo)
                    else:
                        continue
                setattr(dst_obj, field_name, value)
            dst_session.add(dst_obj)
            count += 1
            if count % 1000 == 0:
                dst_session.commit()
                print(f"💾 {table_name}: {count} 行")

        dst_session.commit()
        print(f"✅ {table_name}: 迁移完成 {count} 行")
        return count, len(dtype.get_new_obj.keys())  # type: ignore  # type: ignore
    except Exception as e:
        dst_session.rollback()
        print(f"❌ {table_name}: 迁移失败 - {e}")
        raise
    finally:
        src_session.close()
        dst_session.close()


def run_migrate(dry_run: bool = True):
    """执行迁移"""
    print("🚀 SQLite → PostgreSQL 数据迁移脚本")
    print(f"📍 源数据库: {SOURCE_DB}")
    print(f"🎯 目标数据库: {TARGET_DB_URL}")

    try:
        src_engine, dst_engine, src_session, dst_session = get_engines()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        sys.exit(1)

    # 校验目标表结构
    print("\n📊 验证表结构...")
    errors = validate_schema(src_engine, dst_engine)
    if errors:
        print("❌ 表结构验证失败:")
        for e in errors:
            print(f"  - {e}")
        print("\n请检查目标数据库是否已初始化到最新状态")
        sys.exit(1)
    else:
        print("✅ 表结构验证通过")

    # 统计源表数据量
    print("\n📊 源表数据量:")
    for table in MIGRATION_TABLES:
        if check_table_exists(src_engine, table):
            count = count_rows(src_engine, table)
            print(f"  {table}: {count} 行")

    # 执行迁移
    print("\n🚀 开始迁移...")
    total_migrated = 0
    for table in MIGRATION_TABLES:
        print(f"\n📄 处理表: {table}")
        try:
            migrated, new = migrate_table(src_session, dst_session, table, dry_run)
            total_migrated += migrated
            if migrated == 0:
                print(f"⚠️ {table}: 无迁移 (表不存在或无数据)")
        except Exception as e:
            print(f"❌ {table}: 迁移异常 - {e}")
            sys.exit(1)

    print(f"\n🎉 迁移完成: 共迁移 {total_migrated} 行数据")
    if not dry_run:
        print("\n⚠️ 注意: 不能立即重建所有索引（可能消耗大量内存）")
    print("\n✅ 迁移脚本执行完毕")


if __name__ == "__main__":
    dry_run = '--dry-run' in sys.argv
    run_migrate(dry_run=dry_run)
