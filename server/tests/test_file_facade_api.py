"""C1 门面 API 契约测试（138 文件管理重构）

`app.services.file_service` 是文件操作的唯一对外入口，必须暴露下列统一工具方法。
内部实现模块（file_store / file_refs / file_ref_service）不得被路由层直接 import。
"""

import importlib

import pytest

pytestmark = pytest.mark.fast

FACADE_API: list[str] = [
    # 登记：写盘 + 落库，MD5 命名，同用户同 MD5 单记录
    "register",
    "register_batch",
    # 引用计数：唯一变更入口
    "bind",
    "unbind",
    "rebind",
    "unbind_record",
    # 路径与元数据
    "build_rel_path",
    "resolve",
    "abs_of",
    "rel_of",
    "exists",
    "size_of",
    "md5_of",
    "mime_of",
    "find_by_md5",
    # 查询 / 扫描
    "owned_by",
    "collect_business_refs",
    "scan",
    # 删除与回收
    "soft_delete",
    "soft_delete_batch",
    "cleanup",
    "cleanup_unbound",
    # 存量迁移
    "migrate_to_md5",
]

INTERNAL_MODULES: list[str] = [
    "app.services.file_store",
    "app.services.file_refs",
    "app.services.file_ref_service",
]


def test_facade_exposes_unified_api():
    """门面必须暴露全部统一工具方法"""
    from app.services import file_service

    missing = [name for name in FACADE_API if not callable(getattr(file_service, name, None))]
    assert missing == [], f"file_service 门面缺少统一工具方法: {missing}"


def test_internal_modules_available():
    """内部实现模块必须可导入（门面委托目标）"""
    for module_name in INTERNAL_MODULES:
        assert importlib.import_module(module_name) is not None


def test_file_draft_available():
    """批量登记的入参结构必须由门面定义"""
    from app.services import file_service

    draft_cls = getattr(file_service, "FileDraft", None)
    assert draft_cls is not None, "file_service 需导出 FileDraft 供批量登记使用"
