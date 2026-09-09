"""140 分片上传端点测试

- `POST /api/upload/video/chunk`：单片上传（首片建会话）、片级校验入账
- `GET /api/upload/video/chunks`：续传进度查询（`ok` / `failed` / `missing`）
- `POST /api/upload/video/complete`：免合并校验并登记，返回 `file_id`
"""

import hashlib
import io
import zlib

import pytest

from app.services import file_service

CONTENT = b"0123456789AB"  # 12 字节 / 单片 4 字节 → 3 片
CHUNK_LEN = 4
PARTS = [CONTENT[0:4], CONTENT[4:8], CONTENT[8:12]]
CONTENT_MD5 = hashlib.md5(CONTENT).hexdigest()


@pytest.fixture(autouse=True)
def _small_chunk_size(monkeypatch):
    """把服务端默认单片大小降到 4B，避免测试构造 5MB 级数据"""
    monkeypatch.setattr(file_service, "CHUNK_SIZE_BYTES", CHUNK_LEN)


def _crc(data: bytes) -> str:
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"


def _post_chunk(
    client,
    index: int,
    *,
    md5: str = CONTENT_MD5,
    data: bytes | None = None,
    crc32: str | None = None,
    with_session: bool = True,
):
    payload = PARTS[index] if data is None else data
    form = {"md5": md5, "index": str(index)}
    if with_session:
        form["total"] = str(len(PARTS))
        form["size_bytes"] = str(len(CONTENT))
        form["original_name"] = "clip.mp4"
    if crc32 is not None:
        form["crc32"] = crc32
    return client.post(
        "/api/upload/video/chunk",
        files={"file": ("chunk.bin", io.BytesIO(payload), "application/octet-stream")},
        data=form,
    )


def _post_all(client, *, with_crc: bool = True) -> None:
    for i in range(len(PARTS)):
        response = _post_chunk(client, i, crc32=_crc(PARTS[i]) if with_crc else None)
        assert response.status_code == 200, response.text


# ==================== POST /video/chunk ====================


def test_upload_chunk_ok(auth_client):
    response = _post_chunk(auth_client, 0)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["index"] == 0
    assert data["ok"] == [0]
    assert data["missing"] == [1, 2]


def test_upload_chunk_accumulates(auth_client):
    _post_chunk(auth_client, 0)
    response = _post_chunk(auth_client, 1)
    assert response.json()["data"]["ok"] == [0, 1]


def test_upload_chunk_is_idempotent(auth_client):
    _post_chunk(auth_client, 0)
    response = _post_chunk(auth_client, 0)
    assert response.status_code == 200
    assert response.json()["data"]["ok"] == [0]


def test_upload_chunk_rejects_bad_md5(auth_client):
    response = _post_chunk(auth_client, 0, md5="not-a-md5")
    assert response.status_code == 400


def test_upload_chunk_without_session(auth_client):
    """非首片且会话不存在 → 400（需从 index=0 重开会话）"""
    response = _post_chunk(auth_client, 1, with_session=False)
    assert response.status_code == 400


def test_upload_chunk_rejects_crc_mismatch_and_marks_failed(auth_client):
    response = _post_chunk(auth_client, 0, crc32="deadbeef")
    assert response.status_code == 400
    summary = auth_client.get(f"/api/upload/video/chunks?md5={CONTENT_MD5}").json()["data"]
    assert summary["failed"] == [0]
    assert summary["ok"] == []


def test_upload_chunk_rejects_length_mismatch(auth_client):
    response = _post_chunk(auth_client, 0, data=b"too-long-payload")
    assert response.status_code == 400


def test_upload_chunk_requires_auth(client):
    response = _post_chunk(client, 0)
    assert response.status_code in (401, 403)


# ==================== GET /video/chunks ====================


def test_chunks_query_returns_progress(auth_client):
    _post_chunk(auth_client, 0)
    response = auth_client.get(f"/api/upload/video/chunks?md5={CONTENT_MD5}")
    assert response.status_code == 200
    summary = response.json()["data"]
    assert summary["ok"] == [0]
    assert summary["missing"] == [1, 2]
    assert summary["total"] == 3
    assert summary["total_size"] == len(CONTENT)


def test_chunks_query_empty_without_session(auth_client):
    response = auth_client.get(f"/api/upload/video/chunks?md5={CONTENT_MD5}")
    assert response.status_code == 200
    summary = response.json()["data"]
    assert summary == {
        "ok": [],
        "failed": [],
        "missing": [],
        "chunk_size": 0,
        "total": 0,
        "total_size": 0,
        "crc32": True,
    }


def test_chunks_isolated_between_users(auth_client, mock_user):
    _post_chunk(auth_client, 0)
    assert auth_client.get(f"/api/upload/video/chunks?md5={CONTENT_MD5}").json()["data"]["ok"] == [
        0
    ]
    mock_user.id = 2
    assert auth_client.get(f"/api/upload/video/chunks?md5={CONTENT_MD5}").json()["data"]["ok"] == []


# ==================== POST /video/complete ====================


def test_complete_returns_file_id(auth_client, test_db):
    _post_all(auth_client)
    response = auth_client.post("/api/upload/video/complete", json={"md5": CONTENT_MD5})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["url"] == f"videos/1/{CONTENT_MD5}.mp4"
    assert data["mirage"] is False
    assert data["file_id"] > 0

    record = file_service.find_by_id(test_db, 1, data["file_id"])
    assert record is not None
    assert record.security_checked == 1
    assert record.upload_source == "video"


def test_complete_missing_chunks(auth_client):
    _post_chunk(auth_client, 0)
    response = auth_client.post("/api/upload/video/complete", json={"md5": CONTENT_MD5})
    assert response.status_code == 400


def test_complete_without_session(auth_client):
    response = auth_client.post("/api/upload/video/complete", json={"md5": CONTENT_MD5})
    assert response.status_code == 400


def test_complete_is_idempotent(auth_client):
    _post_all(auth_client)
    first = auth_client.post("/api/upload/video/complete", json={"md5": CONTENT_MD5})
    _post_all(auth_client)
    second = auth_client.post("/api/upload/video/complete", json={"md5": CONTENT_MD5})
    assert first.json()["data"]["file_id"] == second.json()["data"]["file_id"]
    assert second.json()["data"]["mirage"] is True


def test_complete_mismatch_returns_409(auth_client):
    """整文件 MD5 与客户端声明不符 → 409（段已清账，需重传）"""
    _post_all(auth_client)
    file_service.register_chunk(1, CONTENT_MD5, 0, b"XXXX")  # 模拟内容被改写
    response = auth_client.post("/api/upload/video/complete", json={"md5": CONTENT_MD5})
    assert response.status_code == 409


def test_complete_requires_auth(client):
    response = client.post("/api/upload/video/complete", json={"md5": CONTENT_MD5})
    assert response.status_code in (401, 403)
