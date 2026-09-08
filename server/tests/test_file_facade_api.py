"""C1 门面 API 契约测试（138 文件管理重构）

`app.services.file_service` 是文件操作的唯一对外入口，必须暴露下列统一工具方法。
内部实现模块（file_store / file_refs / file_ref_service）不得被路由层直接 import。
"""

import importlib

import pytest

from app.services import file_service

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
    "find_by_id",
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


class TestFindByMd5Category:
    """find_by_md5 的 category 来源隔离（137 阶段一 Step 1）

    不传 category 时行为不变（任意来源均可命中）；传入时仅在该 upload_source
    内匹配，避免装备封面命中头像记录等跨分类误复用。
    """

    @staticmethod
    def _register(db, user_id: int, content: bytes, category: str, ext: str = ".bin"):
        record, reused = file_service.register(
            db=db,
            user_id=user_id,
            content=content,
            category=category,
            original_name=f"sample{ext}",
            ext=ext,
        )
        db.commit()
        return record, reused

    def test_without_category_keeps_legacy_behavior(self, test_db):
        """不传 category：任意来源均可命中（向后兼容）"""
        content = b"137-md5-no-category"
        self._register(test_db, 1, content, "avatar", ".png")
        md5 = file_service.md5_of(content=content)

        assert file_service.find_by_md5(test_db, 1, md5) is not None

    def test_category_hit_same_source(self, test_db):
        """传 category 且来源一致：命中"""
        content = b"137-md5-video-hit"
        record, _ = self._register(test_db, 1, content, "video", ".mp4")
        md5 = file_service.md5_of(content=content)

        found = file_service.find_by_md5(test_db, 1, md5, "video")
        assert found is not None
        assert found.id == record.id

    def test_category_isolates_other_source(self, test_db):
        """相同 MD5 落在 avatar，按 gear_image/video 查询必须 miss"""
        content = b"137-md5-cross-category"
        self._register(test_db, 1, content, "avatar", ".png")
        md5 = file_service.md5_of(content=content)

        assert file_service.find_by_md5(test_db, 1, md5, "gear_image") is None
        assert file_service.find_by_md5(test_db, 1, md5, "video") is None
        assert file_service.find_by_md5(test_db, 1, md5, "avatar") is not None

    def test_category_does_not_leak_across_users(self, test_db):
        """同 MD5 不同用户：互不可见"""
        content = b"137-md5-two-users"
        self._register(test_db, 1, content, "video", ".mp4")
        md5 = file_service.md5_of(content=content)

        assert file_service.find_by_md5(test_db, 2, md5, "video") is None


class TestFindById:
    """find_by_id：按归属用户查询，供 /analyses/start 校验 file_id（137 Step 1）"""

    @staticmethod
    def _register(db, user_id: int, content: bytes, category: str = "video", ext: str = ".mp4"):
        record, _ = file_service.register(
            db=db,
            user_id=user_id,
            content=content,
            category=category,
            original_name=f"clip{ext}",
            ext=ext,
        )
        db.commit()
        return record

    def test_returns_own_file(self, test_db):
        record = self._register(test_db, 1, b"137-find-by-id-own")
        found = file_service.find_by_id(test_db, 1, record.id)
        assert found is not None
        assert found.id == record.id
        assert found.rel_path == record.rel_path

    def test_other_user_returns_none(self, test_db):
        """他人 file_id 越权访问 → None（门面强制带 user_id 条件）"""
        record = self._register(test_db, 1, b"137-find-by-id-other")
        assert file_service.find_by_id(test_db, 2, record.id) is None

    def test_soft_deleted_returns_none(self, test_db):
        record = self._register(test_db, 1, b"137-find-by-id-deleted")
        file_id = record.id
        file_service.soft_delete(test_db, file_id)
        test_db.commit()
        assert file_service.find_by_id(test_db, 1, file_id) is None

    def test_missing_id_returns_none(self, test_db):
        assert file_service.find_by_id(test_db, 1, 999999) is None
