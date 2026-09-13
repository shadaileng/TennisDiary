"""Pipeline _process_video FileDraft 修复测试（id=18 IntegrityError 复现）

复现场景：抽帧中间产物的 md5 在 register_batch 中实时计算（未传入），
但 register_batch 内部 existing_map 查询只校验传入的 md5（md5s 为空时跳过），
导致与同 user_id 下已存在的 (user_id, md5) 唯一索引冲突。
"""

import os

import pytest

from app.services import file_service

pytestmark = pytest.mark.fast


def test_video_frame_draft_carries_md5_and_size(test_db, tmp_path):
    """_process_video 的 FileDraft 应携带 md5/size，让 register_batch 走 existing 复用

    修复前：FileDraft 仅传 src_path/ext/upload_source/original_name，
    内部 `md5s = [item.md5 for item in items if item.md5]` 为空，跳过 existing_map 查询，
    后续实时算 md5 后 INSERT 触发 UNIQUE 冲突（id=18/17 实际现场）。

    修复后：把预先计算好的 md5/size 传给 draft，确保走复用分支。
    """
    f1 = tmp_path / "seg0_f0.jpg"
    f1.write_bytes(b"\xff\xd8\xff\xd9")
    f2 = tmp_path / "seg0_f1.jpg"
    f2.write_bytes(b"\xff\xd8\xff\xd8" * 2 + b"\xff\xd9")

    md5_1 = file_service.file_store.md5_of(path=str(f1))
    md5_2 = file_service.file_store.md5_of(path=str(f2))
    size_1 = os.path.getsize(f1)
    size_2 = os.path.getsize(f2)

    drafts = [
        file_service.FileDraft(
            src_path=str(f1),
            ext=".jpg",
            upload_source="video_frame",
            original_name=f1.name,
            md5=md5_1,
            size=size_1,
        ),
        file_service.FileDraft(
            src_path=str(f2),
            ext=".jpg",
            upload_source="video_frame",
            original_name=f2.name,
            md5=md5_2,
            size=size_2,
        ),
    ]

    # 第一次成功登记
    recs1 = file_service.register_batch(test_db, 2, drafts, business=("analysis", 1))
    test_db.commit()
    assert len(recs1) == 2

    # 第二次同 md5 —— 走 existing 复用，不抛 IntegrityError
    f1b = tmp_path / "seg0_f0.jpg"
    f1b.write_bytes(b"\xff\xd8\xff\xd9")
    f2b = tmp_path / "seg0_f1.jpg"
    f2b.write_bytes(b"\xff\xd8\xff\xd8" * 2 + b"\xff\xd9")
    drafts_again = [
        file_service.FileDraft(
            src_path=str(f1b),
            ext=".jpg",
            upload_source="video_frame",
            original_name=f1b.name,
            md5=md5_1,
            size=size_1,
        ),
        file_service.FileDraft(
            src_path=str(f2b),
            ext=".jpg",
            upload_source="video_frame",
            original_name=f2b.name,
            md5=md5_2,
            size=size_2,
        ),
    ]
    recs2 = file_service.register_batch(test_db, 2, drafts_again, business=("analysis", 2))
    test_db.commit()
    assert {r.md5 for r in recs2} == {md5_1, md5_2}
