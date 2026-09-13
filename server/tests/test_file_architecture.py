"""C1 架构守卫测试（138 文件管理重构）

约束：后端所有受管文件的操作必须收口到 `app.services.file_service` 门面。
路由层与其它业务 service 禁止：

- `uuid4(` 之类的自造文件名（文件名必须由 file_store 按 MD5 推导）
- `open(..., "wb")` 直接写上传/派生产物（写盘必须走 file_store）
- `ref_count` 自增自减（引用计数唯一变更入口是 file_ref_service）
- 直接 `from app.models.file import File`（File 模型只允许门面层操作）

PENDING_MIGRATION 是「待改造清单」：名单内文件暂不强制，名单外一律零容忍。
每改造完一个文件就从名单移除，最终名单清空即全量收口。
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

SERVER_ROOT = Path(__file__).resolve().parents[1]

# 受守卫的目录/文件：路由层 + 产生文件产物的业务 service
GUARDED_PATHS = [
    SERVER_ROOT / "app" / "routers",
    SERVER_ROOT / "app" / "services" / "pose_service.py",
    SERVER_ROOT / "app" / "services" / "video_service.py",
    SERVER_ROOT / "app" / "services" / "pipeline.py",
    SERVER_ROOT / "app" / "services" / "analysis_service.py",
]

# 门面层自身允许出现这些写法
FACADE_FILES = {
    "file_service.py",
    "file_store.py",
    "file_ref_service.py",
    "file_refs.py",
}

# 与受管文件无关的豁免（备份压缩包读写走 data/backups，不进 File 表）
GUARD_EXEMPT = {
    "routers/admin/system.py": "备份归档读写（tar.gz/.db），不属于受管文件",
}

FORBIDDEN_PATTERNS: dict[str, re.Pattern[str]] = {
    "自造文件名": re.compile(r"uuid4\s*\("),
    "直接写盘": re.compile(r"open\s*\([^)]{0,120}?[\"']wb[\"']"),
    "自行变更引用计数": re.compile(r"\.ref_count\s*(?:=[^=]|\+=|-=)"),
    "直接操作 File 模型": re.compile(
        r"^\s*(?:from\s+app\.models\.file\s+import|from\s+app\.models\s+import[^\n]*\bFile\b)",
        re.MULTILINE,
    ),
}

# 待改造清单（C7 全量接入后清空）
PENDING_MIGRATION: set[str] = set()


def _rel(file: Path) -> str:
    return file.relative_to(SERVER_ROOT / "app").as_posix()


def _iter_guarded_files() -> list[Path]:
    files: list[Path] = []
    for path in GUARDED_PATHS:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.is_file():
            files.append(path)
    return [f for f in files if f.name not in FACADE_FILES and _rel(f) not in GUARD_EXEMPT]


def _violations_of(file: Path) -> dict[str, int]:
    source = file.read_text(encoding="utf-8")
    return {
        name: len(pattern.findall(source))
        for name, pattern in FORBIDDEN_PATTERNS.items()
        if pattern.search(source)
    }


def test_pending_migration_targets_exist():
    """待改造清单里的文件必须真实存在，防止名单写错后守卫形同虚设"""
    guarded = {_rel(f) for f in _iter_guarded_files()}
    stale = sorted(PENDING_MIGRATION - guarded - GUARD_EXEMPT.keys())
    assert stale == [], f"待改造清单包含不存在的目标: {stale}"


def test_no_violation_outside_pending_migration():
    """名单外文件零容忍：任何新增违规都会立即失败"""
    offenders: dict[str, dict[str, int]] = {}
    for file in _iter_guarded_files():
        if _rel(file) in PENDING_MIGRATION:
            continue
        found = _violations_of(file)
        if found:
            offenders[_rel(file)] = found
    assert offenders == {}, f"文件操作未收口到 file_service 门面: {offenders}"


def test_pending_migration_shrinks_to_zero():
    """终极目标：待改造清单清空（C7 完成后应为空集）"""
    assert PENDING_MIGRATION == set(), f"仍有文件未收口: {sorted(PENDING_MIGRATION)}"


@pytest.mark.parametrize("file", _iter_guarded_files(), ids=_rel)
def test_facade_is_only_entrypoint(file: Path):
    """单个文件维度的守卫，便于定位具体违规"""
    if _rel(file) in PENDING_MIGRATION:
        pytest.skip(f"{_rel(file)} 在待改造清单内")
    assert _violations_of(file) == {}
