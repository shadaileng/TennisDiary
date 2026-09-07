"""批量登记测试（Step 121 性能基线 / 138 门面化）

覆盖：
- `md5_and_size_of` 一次读盘同时得到 MD5 与大小
- `register_batch` 幂等 / 复用 / 新记录语义（对齐 121 的零额外 I/O 目标）
"""

import hashlib

import pytest

from app.models.file import File
from app.services import file_service

pytestmark = pytest.mark.fast


class TestMd5AndSizeOf:
    """md5_and_size_of：一次读盘同时得到 MD5 与大小"""

    def test_consistent(self, tmp_path):
        """与单独计算 md5 + os.path.getsize 结果一致"""
        path = tmp_path / "sample.mp4"
        content = b"0" * 1000
        path.write_bytes(content)

        md5, size = file_service.md5_and_size_of(str(path))

        assert md5 == hashlib.md5(content).hexdigest()
        assert size == 1000

    def test_missing_file(self, tmp_path):
        """文件不存在时返回 (None, 0)"""
        md5, size = file_service.md5_and_size_of(str(tmp_path / "not-exist.mp4"))

        assert md5 is None
        assert size == 0


class TestRegisterBatch:
    """register_batch：一次查询 + 单批 flush"""

    def test_creates_records(self, test_db):
        """新 MD5 全部新建记录，返回与入参对齐"""
        records = file_service.register_batch(
            db=test_db,
            user_id=1,
            items=[
                file_service.FileDraft(
                    md5=hashlib.md5(b"a").hexdigest(),
                    size=1,
                    ext=".jpg",
                    upload_source="skeleton_frame",
                    original_name="a.jpg",
                ),
                file_service.FileDraft(
                    md5=hashlib.md5(b"b").hexdigest(),
                    size=2,
                    ext=".jpg",
                    upload_source="skeleton_frame",
                    original_name="b.jpg",
                ),
            ],
        )
        test_db.flush()

        assert len(records) == 2
        assert all(r.id is not None for r in records)
        assert {r.md5 for r in records} == {
            hashlib.md5(b"a").hexdigest(),
            hashlib.md5(b"b").hexdigest(),
        }

    def test_reuses_existing_records(self, test_db):
        """已存在的 MD5 复用同一记录，不重复插入"""
        md5 = hashlib.md5(b"reuse").hexdigest()
        existing = File(
            user_id=1,
            md5=md5,
            original_name="old.jpg",
            rel_path="videos/1/old.jpg",
            size_bytes=5,
            mime_type="image/jpeg",
            upload_source="skeleton_frame",
            business_type="analysis",
            business_id=1,
            ref_count=1,
            created_at=0,
        )
        test_db.add(existing)
        test_db.commit()

        records = file_service.register_batch(
            db=test_db,
            user_id=1,
            items=[
                file_service.FileDraft(
                    md5=md5,
                    size=5,
                    ext=".jpg",
                    upload_source="skeleton_frame",
                    original_name="new.jpg",
                )
            ],
        )
        test_db.flush()

        assert len(records) == 1
        assert records[0].id == existing.id
        assert records[0].rel_path == "videos/1/old.jpg"
        assert test_db.query(File).filter(File.md5 == md5).count() == 1

    def test_dedupes_within_batch(self, test_db):
        """同一批内重复 MD5 只落一条记录"""
        md5 = hashlib.md5(b"dup").hexdigest()
        items = [
            file_service.FileDraft(
                md5=md5,
                size=3,
                ext=".jpg",
                upload_source="skeleton_frame",
                original_name=f"d{i}.jpg",
            )
            for i in range(3)
        ]
        records = file_service.register_batch(db=test_db, user_id=1, items=items)
        test_db.flush()

        assert len(records) == 3
        assert len({r.id for r in records}) == 1
        assert test_db.query(File).filter(File.md5 == md5).count() == 1

    def test_business_binds_once_per_record(self, test_db):
        """批量登记带 business 时，每条记录只 +1（去重项不重复计数）"""
        md5 = hashlib.md5(b"bind").hexdigest()
        file_service.register_batch(
            db=test_db,
            user_id=1,
            items=[
                file_service.FileDraft(
                    md5=md5,
                    size=3,
                    ext=".jpg",
                    upload_source="skeleton_frame",
                    original_name="x.jpg",
                )
            ]
            * 2,
            business=("analysis", 7),
        )
        test_db.flush()

        record = test_db.query(File).filter(File.md5 == md5).first()
        assert record.ref_count == 1
        assert record.business_type == "analysis"
        assert record.business_id == 7

    def test_empty_items(self, test_db):
        """空入参返回空列表，不报错"""
        assert file_service.register_batch(db=test_db, user_id=1, items=[]) == []
