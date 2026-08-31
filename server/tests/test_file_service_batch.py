"""file_service 批量函数测试（TDD Phase 1: RED）"""

import hashlib
import os


class TestComputeMd5AndSize:
    """compute_md5_and_size 测试"""

    def test_normal_file(self, tmp_path):
        """正常文件计算 MD5 和 size"""
        from app.services.file_service import compute_md5_and_size

        # 准备测试文件
        content = b"Hello, World! This is test content."
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(content)

        # 计算预期值
        expected_md5 = hashlib.md5(content).hexdigest()
        expected_size = len(content)

        # 调用函数
        md5, size = compute_md5_and_size(str(file_path))

        # 验证
        assert md5 == expected_md5
        assert size == expected_size

    def test_file_not_exists(self, tmp_path):
        """文件不存在返回 (None, 0)"""
        from app.services.file_service import compute_md5_and_size

        file_path = tmp_path / "nonexistent.txt"

        md5, size = compute_md5_and_size(str(file_path))

        assert md5 is None
        assert size == 0

    def test_empty_file(self, tmp_path):
        """空文件 MD5 和 size"""
        from app.services.file_service import compute_md5_and_size

        content = b""
        file_path = tmp_path / "empty.txt"
        file_path.write_bytes(content)

        expected_md5 = hashlib.md5(content).hexdigest()

        md5, size = compute_md5_and_size(str(file_path))

        assert md5 == expected_md5
        assert size == 0

    def test_large_file(self, tmp_path):
        """大文件流式读取（模拟 1MB）"""
        from app.services.file_service import compute_md5_and_size

        # 创建 1MB 测试文件
        content = os.urandom(1024 * 1024)
        file_path = tmp_path / "large.bin"
        file_path.write_bytes(content)

        expected_md5 = hashlib.md5(content).hexdigest()
        expected_size = len(content)

        md5, size = compute_md5_and_size(str(file_path))

        assert md5 == expected_md5
        assert size == expected_size


class TestBatchGetOrCreateFiles:
    """batch_get_or_create_files 测试"""

    def test_empty_list(self, test_db):
        """空列表返回空"""
        from app.services.file_service import batch_get_or_create_files

        result = batch_get_or_create_files(
            db=test_db,
            user_id=1,
            files=[],
        )

        assert result == []

    def test_single_new_file(self, test_db, tmp_path):
        """单条新文件创建"""
        from app.services.file_service import batch_get_or_create_files

        # 准备测试文件
        content = b"Test file content"
        file_path = tmp_path / "test.jpg"
        file_path.write_bytes(content)

        md5 = hashlib.md5(content).hexdigest()
        size = len(content)
        rel_path = "videos/1/test.jpg"

        # 调用函数
        result = batch_get_or_create_files(
            db=test_db,
            user_id=1,
            files=[
                {
                    "rel_path": rel_path,
                    "md5": md5,
                    "size": size,
                    "upload_source": "skeleton_frame",
                }
            ],
            business_type="analysis",
            business_id=1,
        )

        # 验证
        assert len(result) == 1
        assert result[0].md5 == md5
        assert result[0].size_bytes == size
        assert result[0].upload_source == "skeleton_frame"
        assert result[0].business_type == "analysis"
        assert result[0].business_id == 1

    def test_multiple_new_files(self, test_db, tmp_path):
        """多条批量创建"""
        from app.services.file_service import batch_get_or_create_files

        # 准备多个测试文件
        files_input = []
        for i in range(5):
            content = f"File content {i}".encode()
            file_path = tmp_path / f"file_{i}.jpg"
            file_path.write_bytes(content)

            files_input.append(
                {
                    "rel_path": f"videos/1/file_{i}.jpg",
                    "md5": hashlib.md5(content).hexdigest(),
                    "size": len(content),
                    "upload_source": "skeleton_frame",
                }
            )

        # 调用函数
        result = batch_get_or_create_files(
            db=test_db,
            user_id=1,
            files=files_input,
            business_type="analysis",
            business_id=1,
        )

        # 验证
        assert len(result) == 5
        for i, record in enumerate(result):
            assert record.md5 == files_input[i]["md5"]
            assert record.size_bytes == files_input[i]["size"]

    def test_md5_dedup_reuse(self, test_db, tmp_path):
        """MD5 去重（秒传命中）"""
        from app.services.file_service import batch_get_or_create_files, get_or_create_file

        # 准备测试文件
        content = b"Shared content"
        file_path = tmp_path / "shared.jpg"
        file_path.write_bytes(content)

        md5 = hashlib.md5(content).hexdigest()
        size = len(content)

        # 先创建一个原始记录
        original = get_or_create_file(
            db=test_db,
            user_id=1,
            rel_path="videos/1/original.jpg",
            abs_path=str(file_path),
            upload_source="video",
            original_name="original.jpg",
            business_type="analysis",
            business_id=1,
        )
        assert original is not None

        # 用相同 MD5 批量创建（应该秒传命中）
        result = batch_get_or_create_files(
            db=test_db,
            user_id=1,
            files=[
                {
                    "rel_path": "videos/1/duplicate.jpg",
                    "md5": md5,
                    "size": size,
                    "upload_source": "skeleton_frame",
                }
            ],
            business_type="analysis",
            business_id=2,
        )

        # 验证：新记录复用了原始记录的路径
        assert len(result) == 1
        assert result[0].rel_path == "videos/1/original.jpg"  # 复用路径
        assert result[0].md5 == md5

    def test_original_name_unique(self, test_db, tmp_path):
        """original_name 唯一性（同名文件追加后缀）"""
        from app.services.file_service import batch_get_or_create_files

        # 准备两个同名文件（不同内容）
        content1 = b"Content 1"
        content2 = b"Content 2"
        file_path1 = tmp_path / "same_name.jpg"
        file_path2 = tmp_path / "same_name_2.jpg"
        file_path1.write_bytes(content1)
        file_path2.write_bytes(content2)

        # 批量创建（同名）
        result = batch_get_or_create_files(
            db=test_db,
            user_id=1,
            files=[
                {
                    "rel_path": "videos/1/same_name.jpg",
                    "md5": hashlib.md5(content1).hexdigest(),
                    "size": len(content1),
                    "upload_source": "skeleton_frame",
                },
                {
                    "rel_path": "videos/1/same_name.jpg",
                    "md5": hashlib.md5(content2).hexdigest(),
                    "size": len(content2),
                    "upload_source": "skeleton_frame",
                },
            ],
            business_type="analysis",
            business_id=1,
        )

        # 验证：第二个文件名应该追加后缀
        assert len(result) == 2
        assert result[0].original_name == "same_name.jpg"
        assert result[1].original_name == "same_name_1.jpg"

    def test_mixed_scenario(self, test_db, tmp_path):
        """混合场景（部分秒传 + 部分新文件）"""
        from app.services.file_service import batch_get_or_create_files, get_or_create_file

        # 准备测试文件
        content_shared = b"Shared content"
        content_new = b"New content"
        file_shared = tmp_path / "shared.jpg"
        file_new = tmp_path / "new.jpg"
        file_shared.write_bytes(content_shared)
        file_new.write_bytes(content_new)

        md5_shared = hashlib.md5(content_shared).hexdigest()
        md5_new = hashlib.md5(content_new).hexdigest()

        # 先创建一个原始记录（用于秒传）
        get_or_create_file(
            db=test_db,
            user_id=1,
            rel_path="videos/1/original.jpg",
            abs_path=str(file_shared),
            upload_source="video",
            original_name="original.jpg",
        )

        # 批量创建：一个秒传 + 一个新文件
        result = batch_get_or_create_files(
            db=test_db,
            user_id=1,
            files=[
                {
                    "rel_path": "videos/1/reuse.jpg",
                    "md5": md5_shared,
                    "size": len(content_shared),
                    "upload_source": "skeleton_frame",
                },
                {
                    "rel_path": "videos/1/new.jpg",
                    "md5": md5_new,
                    "size": len(content_new),
                    "upload_source": "skeleton_frame",
                },
            ],
            business_type="analysis",
            business_id=1,
        )

        # 验证
        assert len(result) == 2
        # 秒传的复用原始路径
        reuse_record = next(r for r in result if r.md5 == md5_shared)
        assert reuse_record.rel_path == "videos/1/original.jpg"
        # 新文件使用自己的路径
        new_record = next(r for r in result if r.md5 == md5_new)
        assert new_record.rel_path == "videos/1/new.jpg"
