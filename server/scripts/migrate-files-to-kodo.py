"""存量文件搬迁到七牛 Kodo（147 §9.2，Step 10）

`storage_sync_service` 的命令行入口 —— 与 Admin 文件页「S3 同步」中心**共用一套逻辑**
（scope / dry_run / force 语义完全一致），只是把后台跑批换成同步执行并打印结果。

用法：
    uv run python scripts/migrate-files-to-kodo.py --scope local            # 存量搬迁
    uv run python scripts/migrate-files-to-kodo.py --scope failed           # 失败补偿
    uv run python scripts/migrate-files-to-kodo.py --scope pending          # 待同步
    uv run python scripts/migrate-files-to-kodo.py --scope local --dry-run  # 只统计不改动
    uv run python scripts/migrate-files-to-kodo.py --scope local --force    # 已 SYNCED 也重传

退出码：0 成功；1 异常（含 backend=local 未启用对象存储、未知 scope）。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import storage_sync_service as svc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="存量文件搬迁到对象存储（与同步中心共用逻辑）")
    parser.add_argument(
        "--scope",
        default="local",
        help="同步范围：local=存量搬迁 / failed=失败补偿 / pending=待同步 / selected=按 --file-ids",
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计条数/字节，不改动")
    parser.add_argument("--force", action="store_true", help="对已 SYNCED 也重传（HEAD 核对用）")
    parser.add_argument(
        "--file-ids",
        default="",
        help="scope=selected 时必填，逗号分隔的文件 ID 列表",
    )
    return parser


def run(args: argparse.Namespace, session_factory=None) -> dict:
    """执行 CLI（可注入会话工厂供测试）

    Returns:
        `{"exit_code": int, ...}`，dry_run 额外带 `queued/skipped/estimate_bytes`
    """
    if session_factory is None:
        from app.core.database import SessionLocal

        session_factory = SessionLocal

    file_ids = [int(x) for x in args.file_ids.split(",") if x.strip()] if args.file_ids else None
    if args.scope == "selected" and not file_ids:
        print("错误: scope=selected 需要 --file-ids", file=sys.stderr)
        return {"exit_code": 1}

    db = session_factory()
    try:
        if args.dry_run:
            to_sync, skipped, estimate_bytes = svc.plan(db, args.scope, file_ids, force=args.force)
            print(
                f"[预览] 待同步 {len(to_sync)} 个（{estimate_bytes} 字节），"
                f"跳过 {skipped} 个已同步 —— 未做任何改动"
            )
            return {
                "exit_code": 0,
                "dry_run": True,
                "queued": len(to_sync),
                "skipped": skipped,
                "estimate_bytes": estimate_bytes,
            }

        result = svc.run_sync(db, args.scope, file_ids, force=args.force)
        print(
            f"[完成] 同步 {result['synced']} 个成功、{result['failed']} 个失败"
            f"（扫描 {result['total']} 条）"
        )
        if result["failed"]:
            print("  失败记录已标记 FAILED，可稍后用 --scope failed 重试", file=sys.stderr)
        return {"exit_code": 0, "dry_run": False, **result}
    except (svc.SyncDisabledError, svc.SyncValidationError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return {"exit_code": 1}
    except Exception as exc:  # noqa: BLE001 - CLI 兜底
        db.rollback()
        print(f"同步失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        return {"exit_code": 1}
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
