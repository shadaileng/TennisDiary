"""文件 MIME 修复脚本（Step 116）

扫描 File 表，按物理文件真实类型重新探测并修正 mime_type。供离线/CI 运行，
逻辑复用 app.services.file_service.repair_file_mime_types。

用法：
    uv run python scripts/repair-files.py                 # 仅修正 mime_type 为空的记录
    uv run python scripts/repair-files.py --all           # 全量校验所有记录
    uv run python scripts/repair-files.py --source video  # 仅指定来源
    uv run python scripts/repair-files.py --dry-run       # 只统计不写库

退出码：0 成功；1 异常。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.services import file_service


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描并修正 File 表 mime_type")
    parser.add_argument("--all", action="store_true", help="全量校验（默认仅修正空值）")
    parser.add_argument("--source", default=None, help="仅指定 upload_source（如 video/avatar）")
    parser.add_argument("--dry-run", action="store_true", help="只统计与打印明细，不写入数据库")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.dry_run:
            # dry-run：直接读取统计逻辑但不提交
            result = file_service.repair_file_mime_types(
                db, only_empty=not args.all, upload_source=args.source
            )
            # 撤销可能的改动（dry-run 不应落库）
            db.rollback()
        else:
            result = file_service.repair_file_mime_types(
                db, only_empty=not args.all, upload_source=args.source
            )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"修复失败: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("文件 MIME 修复结果：")
    print(f"  扫描: {result['scanned']}")
    print(f"  修正: {result['repaired']}")
    print(f"  未变: {result['unchanged']}")
    print(f"  跳过: {result['skipped']}（物理文件缺失）")
    if result["details"]:
        print("  明细:")
        for d in result["details"]:
            if d.get("action") == "repaired":
                print(f"    #{d['id']} {d['rel_path']}: {d['old'] or '(空)'} -> {d['new']}")
            elif d.get("action") == "skipped":
                print(f"    #{d['id']} {d['rel_path']}: 跳过（{d.get('reason')}）")
    if args.dry_run:
        print("（dry-run，未写入数据库）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
