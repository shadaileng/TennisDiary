"""140 视频分片上传与断点续传（方案 C+）

- 存储层（`file_store`）：`data.bin` 按 offset 定位写、`manifest.json` 原子写、会话清理与过期回收
- 门面层（`file_service`）：会话管理、片级校验（`length` + `crc32`）、写成功才入账 `ok`、
  失败入 `failed`、complete 免合并直接校验登记
"""

import hashlib
import json
import os
import time
import zlib
from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.services import file_service, file_store

pytestmark = pytest.mark.fast

MD5 = "a" * 32
OTHER_MD5 = "b" * 32


def _iso(ts: float) -> str:
    """时间戳 → ISO8601 UTC（`Z` 后缀，与 87 时区规范一致）"""
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")


def _session_dir(user_id: int, md5: str) -> str:
    return os.path.join(str(settings.UPLOAD_DIR), "tmp", "chunks", str(user_id), md5)


def _read_data(user_id: int, md5: str) -> bytes:
    with open(file_store.chunk_data_abs(user_id, md5), "rb") as f:
        return f.read()


# ==================== 会话目录 ====================


def test_chunk_dir_abs_creates_session_dir():
    """会话目录为 UPLOAD_DIR/tmp/chunks/<user_id>/<md5>/，自动创建"""
    path = file_store.chunk_dir_abs(1, MD5)
    assert os.path.isdir(path)
    assert path.endswith(os.path.join("tmp", "chunks", "1", MD5))


def test_chunk_dir_abs_rejects_unsafe_md5():
    """非法 md5（可能路径穿越）直接拒绝"""
    with pytest.raises(ValueError):
        file_store.chunk_dir_abs(1, "../evil")


def test_chunk_dir_abs_isolates_users():
    """不同用户的同名 md5 会话相互隔离"""
    assert file_store.chunk_dir_abs(1, MD5) != file_store.chunk_dir_abs(2, MD5)


# ==================== data.bin 定位写 ====================


def test_pwrite_chunk_writes_at_offset():
    """乱序写入各区段，最终内容按 offset 正确拼合（空洞补零由 OS 保证）"""
    file_store.pwrite_chunk(1, MD5, 0, b"AAA")
    file_store.pwrite_chunk(1, MD5, 6, b"CCC")
    file_store.pwrite_chunk(1, MD5, 3, b"BBB")
    assert _read_data(1, MD5) == b"AAABBBCCC"


def test_pwrite_chunk_overwrites_same_offset():
    """重复写同一区段为覆盖语义，文件不会增长"""
    file_store.pwrite_chunk(1, MD5, 0, b"AAABBB")
    file_store.pwrite_chunk(1, MD5, 3, b"XXX")
    assert _read_data(1, MD5) == b"AAAXXX"
    assert file_store.data_size(1, MD5) == 6


def test_data_size_zero_without_session():
    assert file_store.data_size(99, OTHER_MD5) == 0


def test_pwrite_chunk_returns_written_bytes():
    assert file_store.pwrite_chunk(1, MD5, 0, b"12345") == 5


# ==================== manifest 原子写 ====================


def test_manifest_roundtrip():
    """无会话读回 None；写入后可原样读回"""
    assert file_store.read_manifest(1, MD5) is None
    manifest = {"v": 1, "md5": MD5, "segments": {}}
    file_store.write_manifest(1, MD5, manifest)
    assert file_store.read_manifest(1, MD5) == manifest


def test_write_manifest_is_atomic_without_tmp_residue():
    """连续写入后无 manifest.json.tmp 残留，内容为最后一次写入"""
    file_store.write_manifest(1, MD5, {"v": 1, "n": 1})
    file_store.write_manifest(1, MD5, {"v": 1, "n": 2})
    session = _session_dir(1, MD5)
    assert sorted(os.listdir(session)) == ["manifest.json"]
    with open(os.path.join(session, "manifest.json"), encoding="utf-8") as f:
        assert json.load(f)["n"] == 2


def test_read_manifest_returns_none_on_corrupted_file():
    """manifest 损坏时返回 None（由门面按「无会话」处理）"""
    session = file_store.chunk_dir_abs(1, MD5)
    with open(os.path.join(session, "manifest.json"), "w", encoding="utf-8") as f:
        f.write("{broken")
    assert file_store.read_manifest(1, MD5) is None


# ==================== 清理与过期回收 ====================


def test_clear_chunks_removes_session():
    file_store.pwrite_chunk(1, MD5, 0, b"AAA")
    file_store.write_manifest(1, MD5, {"v": 1})
    assert file_store.clear_chunks(1, MD5) >= 1
    assert not os.path.exists(_session_dir(1, MD5))


def test_clear_chunks_missing_returns_zero():
    assert file_store.clear_chunks(1, MD5) == 0


def test_cleanup_expired_chunks_by_manifest_updated_at():
    """按 manifest.updated_at 判过期：只回收超时会话"""
    file_store.write_manifest(1, MD5, {"v": 1, "updated_at": _iso(time.time() - 48 * 3600)})
    file_store.write_manifest(2, OTHER_MD5, {"v": 1, "updated_at": _iso(time.time())})

    cleaned = file_store.cleanup_expired_chunks(max_age_hours=24)

    assert cleaned == 1
    assert not os.path.exists(_session_dir(1, MD5))
    assert os.path.isdir(_session_dir(2, OTHER_MD5))


def test_cleanup_expired_chunks_falls_back_to_dir_mtime():
    """无 manifest（或时间戳缺失/非法）时回退目录 mtime"""
    session = file_store.chunk_dir_abs(1, MD5)
    stale = time.time() - 48 * 3600
    os.utime(session, (stale, stale))
    assert file_store.cleanup_expired_chunks(max_age_hours=24) == 1
    assert not os.path.exists(session)


def test_cleanup_expired_chunks_keeps_fresh_sessions():
    file_store.pwrite_chunk(1, MD5, 0, b"AAA")
    file_store.write_manifest(1, MD5, {"v": 1, "updated_at": _iso(time.time())})
    assert file_store.cleanup_expired_chunks(max_age_hours=24) == 0
    assert os.path.isdir(_session_dir(1, MD5))


# ==================== 门面层：会话与片级校验 ====================

CONTENT = b"0123456789AB"  # 12 字节 / 单片 4 字节 → 3 片
CHUNK_LEN = 4
CHUNK_PARTS = [CONTENT[0:4], CONTENT[4:8], CONTENT[8:12]]
CONTENT_MD5 = hashlib.md5(CONTENT).hexdigest()


def _crc(data: bytes) -> str:
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"


def _open(user_id: int = 1, **kwargs) -> dict:
    md5 = kwargs.pop("md5", CONTENT_MD5)
    return file_service.open_chunk_session(
        user_id,
        md5,
        total_size=kwargs.pop("total_size", len(CONTENT)),
        chunk_size=kwargs.pop("chunk_size", CHUNK_LEN),
        original_name=kwargs.pop("original_name", "clip.mp4"),
        ext=kwargs.pop("ext", ".mp4"),
        **kwargs,
    )


def _put(index: int, user_id: int = 1, *, data: bytes | None = None, **kwargs) -> dict:
    payload = CHUNK_PARTS[index] if data is None else data
    return file_service.register_chunk(user_id, CONTENT_MD5, index, payload, **kwargs)


def _put_all(user_id: int = 1, *, with_crc: bool = True) -> None:
    for i in range(len(CHUNK_PARTS)):
        _put(
            i,
            user_id,
            crc32=_crc(CHUNK_PARTS[i]) if with_crc else "",
        )


def test_chunk_policy_defaults():
    policy = file_service.chunk_policy()
    assert policy["enabled"] is True
    assert policy["size_bytes"] == file_service.CHUNK_SIZE_BYTES
    assert policy["threshold_bytes"] == file_service.CHUNK_THRESHOLD_BYTES
    assert policy["max_count"] == file_service.MAX_CHUNK_COUNT
    assert policy["crc32"] is True


def test_open_chunk_session_creates_manifest():
    _open()
    manifest = file_store.read_manifest(1, CONTENT_MD5)
    assert manifest["v"] == file_service.CHUNK_MANIFEST_VERSION
    assert manifest["md5"] == CONTENT_MD5
    assert manifest["total_size"] == len(CONTENT)
    assert manifest["chunk_size"] == CHUNK_LEN
    assert manifest["total"] == 3
    assert manifest["ext"] == ".mp4"
    assert manifest["original_name"] == "clip.mp4"
    assert manifest["segments"] == {}


def test_open_chunk_session_is_idempotent():
    _open()
    _put(0)
    _open()  # 重复开会话不应清空已入账的段
    assert file_service.list_chunks(1, CONTENT_MD5)["ok"] == [0]


def test_open_chunk_session_rejects_conflicting_params():
    _open()
    with pytest.raises(file_service.ChunkParamError):
        _open(total_size=999)


def test_open_chunk_session_rejects_oversized_total():
    with pytest.raises(file_service.ChunkParamError):
        _open(total_size=file_service.CHUNK_SIZE_BYTES * (file_service.MAX_CHUNK_COUNT + 1))


def test_validate_chunk_params_rejects_bad_md5():
    with pytest.raises(file_service.ChunkParamError):
        file_service.validate_chunk_params("not-md5", 0, 3)


def test_register_chunk_without_session_raises():
    with pytest.raises(file_service.ChunkSessionError):
        _put(0)


def test_register_chunk_rejects_index_out_of_range():
    _open()
    with pytest.raises(file_service.ChunkParamError):
        _put(3, data=b"0123")


def test_register_chunk_enters_ok():
    _open()
    result = _put(1)
    assert result["index"] == 1
    assert result["ok"] == [1]
    manifest = file_store.read_manifest(1, CONTENT_MD5)
    assert manifest["segments"]["1"]["state"] == "ok"


def test_register_chunk_is_idempotent():
    _open()
    _put(0)
    _put(0)
    assert file_service.list_chunks(1, CONTENT_MD5)["ok"] == [0]
    assert file_store.data_size(1, CONTENT_MD5) == CHUNK_LEN


def test_register_chunk_length_mismatch_goes_failed():
    _open()
    with pytest.raises(file_service.ChunkVerifyError):
        _put(0, data=b"short", length=len(b"short"))
    summary = file_service.list_chunks(1, CONTENT_MD5)
    assert summary["ok"] == []
    assert summary["failed"] == [0]
    assert summary["missing"] == [0, 1, 2]


def test_register_chunk_crc_mismatch_goes_failed():
    _open()
    with pytest.raises(file_service.ChunkVerifyError):
        _put(0, crc32="deadbeef")
    assert file_service.list_chunks(1, CONTENT_MD5)["failed"] == [0]


def test_register_chunk_accepts_valid_crc32():
    _open()
    _put(0, crc32=_crc(CHUNK_PARTS[0]))
    manifest = file_store.read_manifest(1, CONTENT_MD5)
    assert manifest["segments"]["0"]["crc32"] == _crc(CHUNK_PARTS[0])


def test_list_chunks_derives_missing():
    _open()
    _put(0)
    summary = file_service.list_chunks(1, CONTENT_MD5)
    assert summary["ok"] == [0]
    assert summary["failed"] == []
    assert summary["missing"] == [1, 2]
    assert summary["total"] == 3
    assert summary["chunk_size"] == CHUNK_LEN


def test_failed_segment_recovered_by_reupload():
    """失败段重传正确内容后转 ok，可继续 complete"""
    _open()
    with pytest.raises(file_service.ChunkVerifyError):
        _put(0, crc32="deadbeef")
    _put(0, crc32=_crc(CHUNK_PARTS[0]))
    summary = file_service.list_chunks(1, CONTENT_MD5)
    assert summary["ok"] == [0]
    assert summary["failed"] == []


# ==================== 门面层：complete ====================


def test_complete_missing_chunks_raises(test_db):
    _open()
    _put(0)
    with pytest.raises(file_service.ChunkIncompleteError):
        file_service.complete_chunk_upload(test_db, 1, md5=CONTENT_MD5)


def test_complete_without_session_raises(test_db):
    with pytest.raises(file_service.ChunkSessionError):
        file_service.complete_chunk_upload(test_db, 1, md5=CONTENT_MD5)


def test_complete_registers_video(test_db):
    """乱序传片后 complete：免合并直接登记为受管文件"""
    _open()
    _put(2)
    _put(0)
    _put(1)
    record, reused = file_service.complete_chunk_upload(test_db, 1, md5=CONTENT_MD5)
    test_db.commit()
    assert reused is False
    assert record.rel_path == f"videos/1/{CONTENT_MD5}.mp4"
    assert record.security_checked == 1
    assert record.upload_source == "video"
    with open(file_service.abs_of(record.rel_path), "rb") as f:
        assert f.read() == CONTENT
    # 会话目录已清理，data.bin 已迁走
    assert not os.path.exists(_session_dir(1, CONTENT_MD5))


def test_complete_is_idempotent(test_db):
    _open()
    _put_all()
    first, _ = file_service.complete_chunk_upload(test_db, 1, md5=CONTENT_MD5)
    test_db.commit()
    _open()
    _put_all()
    second, reused = file_service.complete_chunk_upload(test_db, 1, md5=CONTENT_MD5)
    test_db.commit()
    assert second.id == first.id
    assert reused is True


def test_complete_mismatch_clears_unverified_segments(test_db):
    """无 crc32 的段无法定位坏片 → 整会话清空要求重传"""
    _open()
    _put_all(with_crc=False)
    file_store.pwrite_chunk(1, CONTENT_MD5, 0, b"XXXX")  # 模拟写后损坏
    with pytest.raises(file_service.ChunkMismatchError):
        file_service.complete_chunk_upload(test_db, 1, md5=CONTENT_MD5)
    assert file_service.list_chunks(1, CONTENT_MD5)["ok"] == []


def test_complete_mismatch_keeps_crc_verified_segments(test_db):
    """带 crc32 且校验通过的段视为可信，仅清未校验段"""
    _open()
    _put_all(with_crc=True)
    file_store.pwrite_chunk(1, CONTENT_MD5, 0, b"XXXX")
    with pytest.raises(file_service.ChunkMismatchError):
        file_service.complete_chunk_upload(test_db, 1, md5=CONTENT_MD5)
    assert file_service.list_chunks(1, CONTENT_MD5)["ok"] == [0, 1, 2]


def test_complete_rejects_oversize(test_db, monkeypatch):
    _open()
    _put_all()
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)
    with pytest.raises(file_service.ChunkTooLargeError):
        file_service.complete_chunk_upload(test_db, 1, md5=CONTENT_MD5)


def test_cleanup_expired_chunks_via_facade():
    _open()
    _put(0)
    assert file_service.cleanup_expired_chunks(max_age_hours=24) == 0
    assert file_service.cleanup_expired_chunks(max_age_hours=0) == 1
