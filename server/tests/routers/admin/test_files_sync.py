"""147 阶段一 Step 8：管理端 scan 扩展 + 双删 + S3 同步端点骨架

覆盖（§9.2 + §9.1 端点契约）：

- `scan`：新增 `pending_sync`（未同步到对象存储）；`missing` 在启用对象存储后
  重定义为「DB 有而**对象存储**无」；`backend=local` 时保持旧语义（回滚档位）
- 双删（§5.4）：`/cleanup` 物理清理时对象同步删除（失败不阻塞）；`/cleanup-orphans` 同
- 同步端点：`GET /sync-status`（统计）、`POST /sync`（scope + dry_run）、`POST /sync/{id}`（单条）
  - `backend=local` → 400「未启用对象存储」；执行中重复触发 → 409；未登录 → 401/403

对象后端用 `memory` 注入（`settings.STORAGE_BACKEND` monkeypatch + 工厂缓存清空）。
"""

import hashlib
import os
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.models.file import (
    STORAGE_STATUS_FAILED,
    STORAGE_STATUS_PENDING,
    STORAGE_STATUS_SYNCED,
    File,
)
from app.services import file_service, storage
from app.services import storage_sync_service as svc

pytestmark = pytest.mark.fast

_seq = 0


def _next_seq() -> int:
    global _seq
    _seq += 1
    return _seq


def _next_uid() -> int:
    return 6000 + _next_seq()


@pytest.fixture(autouse=True)
def _storage_env(test_db, monkeypatch):
    """启用 memory 对象存储 + 清后端实例缓存 + 清 storage.* 覆盖行（用后复原）"""
    from app.models.system_config import SystemConfig

    def _clean():
        test_db.query(SystemConfig).filter(SystemConfig.key.like("storage.%")).delete()
        test_db.commit()
        storage.clear_backend_cache()

    _clean()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
    yield
    _clean()


def _backend(test_db):
    """当前配置快照解析出的后端实例（与被测代码同实例，可断言对象存在性）"""
    return storage.resolve_backend(storage.load_storage_config(test_db))


@pytest.fixture(autouse=True)
def _restore_auth_header(auth_client, admin_token):
    """模块级 client 的鉴权头可能被前序用例（test_endpoints_require_admin）清掉，先复原"""
    auth_client.headers["X-Auth-Token"] = admin_token


def _write_disk(rel_path: str, content: bytes = b"disk-content") -> str:
    abs_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(content)
    return rel_path


def _insert_file(
    test_db,
    *,
    user_id: int | None = None,
    rel_path: str | None = None,
    storage_col: str = "local",
    status: int = STORAGE_STATUS_SYNCED,
    write_disk: bool = True,
    size: int = 32,
) -> File:
    seq = _next_seq()
    user_id = user_id or _next_uid()
    rel_path = rel_path or f"sync-test/{user_id}/file-{seq}.jpg"
    if write_disk:
        _write_disk(rel_path, b"x" * size)
    record = File(
        user_id=user_id,
        md5=hashlib.md5(f"sync-{seq}-{rel_path}".encode()).hexdigest(),
        original_name=os.path.basename(rel_path),
        rel_path=rel_path,
        size_bytes=size,
        mime_type="image/jpeg",
        upload_source="gear_image",
        ref_count=0,
        created_at=datetime.now(timezone.utc),
        storage=storage_col,
        storage_status=status,
    )
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)
    return record


def _status_of(report: dict, rel_path: str) -> str | None:
    for item in report["items"]:
        if item["rel_path"] == rel_path:
            return item["status"]
    return None


# ==================== scan 扩展（§9.2） ====================


class TestScanStorageStates:
    def test_unmigrated_record_is_pending_sync(self, test_db):
        """存量 `storage=local` + backend=memory → pending_sync（待搬迁）"""
        rec = _insert_file(test_db, storage_col="local")
        report = file_service.scan(test_db)
        assert _status_of(report, rec.rel_path) == "pending_sync"
        assert report["status_counts"]["pending_sync"] >= 1

    @pytest.mark.parametrize(
        "status,expect_reason",
        [
            (STORAGE_STATUS_PENDING, "未同步"),
            (STORAGE_STATUS_FAILED, "失败"),
        ],
    )
    def test_unsynced_status_is_pending_sync(self, test_db, status, expect_reason):
        """位置已是当前后端但状态非 SYNCED（PENDING/FAILED）→ pending_sync"""
        rec = _insert_file(test_db, storage_col="memory", status=status)
        report = file_service.scan(test_db)
        assert _status_of(report, rec.rel_path) == "pending_sync"
        item = next(i for i in report["items"] if i["rel_path"] == rec.rel_path)
        assert expect_reason in item["reason"]

    def test_missing_redefined_as_object_absent(self, test_db):
        """`SYNCED` 记录但对象存储里没有该对象 → missing（§9.2 重定义）"""
        rec = _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_SYNCED)
        report = file_service.scan(test_db)
        assert _status_of(report, rec.rel_path) == "missing"
        item = next(i for i in report["items"] if i["rel_path"] == rec.rel_path)
        assert "对象存储" in item["reason"]

    def test_object_present_local_missing_is_not_missing(self, test_db):
        """对象在、本地副本缺失（local_retention 清理后）→ 按引用态分类，**不再判 missing**"""
        rec = _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_SYNCED)
        _backend(test_db).put(rec.rel_path, b"object-bytes")
        os.remove(os.path.join(os.path.abspath(settings.UPLOAD_DIR), rec.rel_path))

        report = file_service.scan(test_db)
        assert _status_of(report, rec.rel_path) == "unreferenced"

    def test_local_backend_keeps_legacy_missing_semantics(self, test_db, monkeypatch):
        """回滚档位（backend=local）：missing 仍是「本地物理文件缺失」"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
        storage.clear_backend_cache()
        rec = _insert_file(test_db, storage_col="local", write_disk=False)
        report = file_service.scan(test_db)
        assert _status_of(report, rec.rel_path) == "missing"


class TestScanEndpoint:
    def test_scan_reports_pending_sync_and_excludes_from_orphans(self, auth_client, test_db):
        """扫描端点：status_counts 含 pending_sync，且未同步记录不进 orphans 待处理列表"""
        rec = _insert_file(test_db, storage_col="local")
        resp = auth_client.post("/api/admin/files/scan")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status_counts"].get("pending_sync", 0) >= 1
        assert not any(o["rel_path"] == rec.rel_path for o in data["orphans"])


# ==================== 双删（§5.4） ====================


class TestDoubleDelete:
    def test_cleanup_expired_removes_object_too(self, test_db):
        """物理清理：删行 + 删本地 + **删对象**"""
        rec = _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_SYNCED)
        backend = _backend(test_db)
        backend.put(rec.rel_path, b"object-bytes")
        rec.deleted_at = datetime.now(timezone.utc) - timedelta(days=31)
        test_db.commit()

        file_service.cleanup(test_db, days=30)
        test_db.commit()  # 与路由行为一致（cleanup 在路由层 commit）

        assert test_db.query(File).filter(File.id == rec.id).first() is None
        assert backend.head(rec.rel_path) is None
        assert not os.path.exists(os.path.join(os.path.abspath(settings.UPLOAD_DIR), rec.rel_path))

    def test_cleanup_continues_when_object_delete_fails(self, test_db, monkeypatch):
        """对象删除失败 → 记日志继续删行（不阻塞清理，对象侧交生命周期兜底）"""
        rec = _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_SYNCED)
        backend = _backend(test_db)
        backend.put(rec.rel_path, b"object-bytes")

        def _boom(key):
            raise storage.StorageError("模拟对象删除失败")

        monkeypatch.setattr(backend, "delete", _boom)
        rec.deleted_at = datetime.now(timezone.utc) - timedelta(days=31)
        test_db.commit()

        file_service.cleanup(test_db, days=30)  # 不应抛错
        test_db.commit()
        assert test_db.query(File).filter(File.id == rec.id).first() is None

    def test_cleanup_orphans_endpoint_deletes_object(self, auth_client, test_db):
        """`/cleanup-orphans`：磁盘孤儿的对象也一并删除"""
        rel = f"orphan-sync/{_next_uid()}/stray.jpg"
        _write_disk(rel, b"stray")
        _backend(test_db).put(rel, b"object-stray")

        resp = auth_client.post("/api/admin/files/cleanup-orphans", json={"files": [rel]})
        assert resp.status_code == 200
        assert resp.json()["data"]["cleaned"] >= 1
        assert _backend(test_db).head(rel) is None


# ==================== 同步端点（§9.1） ====================


class TestSyncEndpointGate:
    def test_all_endpoints_400_when_backend_local(self, auth_client, monkeypatch):
        """回滚档位（backend=local）→ 三个端点全部 400"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
        storage.clear_backend_cache()

        assert auth_client.get("/api/admin/files/sync-status").status_code == 400
        assert (
            auth_client.post(
                "/api/admin/files/sync", json={"scope": "local", "dry_run": True}
            ).status_code
            == 400
        )
        assert auth_client.post("/api/admin/files/sync/1").status_code == 400

    def test_endpoints_require_admin(self, client):
        client.headers.pop("X-Auth-Token", None)
        assert client.get("/api/admin/files/sync-status").status_code in (401, 403)

    def test_selected_scope_requires_file_ids(self, auth_client):
        resp = auth_client.post("/api/admin/files/sync", json={"scope": "selected"})
        assert resp.status_code == 400


class TestSyncStatus:
    def test_counts_match_db(self, auth_client, test_db):
        """统计口径与 DB 实际一致（total/synced/pending/failed/local_only）"""
        _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_SYNCED)
        _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_PENDING)
        _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_FAILED)
        _insert_file(test_db, storage_col="local", status=STORAGE_STATUS_SYNCED)

        data = auth_client.get("/api/admin/files/sync-status").json()["data"]

        rows = test_db.query(File).filter(File.deleted_at.is_(None)).all()
        expected = {
            "total": len(rows),
            "synced": sum(1 for r in rows if r.storage_status == STORAGE_STATUS_SYNCED),
            "pending": sum(1 for r in rows if r.storage_status == STORAGE_STATUS_PENDING),
            "failed": sum(1 for r in rows if r.storage_status == STORAGE_STATUS_FAILED),
            "local_only": sum(1 for r in rows if r.storage != "memory"),
        }
        for key, value in expected.items():
            assert data[key] == value, key
        assert data["running"] is False
        assert data["last_sync_at"] is None

    def test_running_flag_reported(self, auth_client):
        """执行中 → running=True（供前端进度轮询判断）"""
        svc.RUN_STATE.running = True
        try:
            data = auth_client.get("/api/admin/files/sync-status").json()["data"]
            assert data["running"] is True
        finally:
            svc.RUN_STATE.running = False


class TestSyncRun:
    def test_dry_run_returns_counts_without_changes(self, auth_client, test_db):
        """dry_run=true：返回条数/字节，**零数据改动**（验收 #13）"""
        rec = _insert_file(test_db, storage_col="local")

        resp = auth_client.post("/api/admin/files/sync", json={"scope": "local", "dry_run": True})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["dry_run"] is True
        assert data["queued"] >= 1
        assert data["estimate_bytes"] >= rec.size_bytes
        assert data["task_id"] is None

        test_db.refresh(rec)
        assert rec.storage == "local"  # 未被改动
        assert _backend(test_db).head(rec.rel_path) is None

    def test_scope_local_migrates_records(self, auth_client, test_db):
        """正式执行 scope=local → 存量记录搬迁到对象存储（SYNCED + 对象存在）"""
        rec = _insert_file(test_db, storage_col="local")

        resp = auth_client.post("/api/admin/files/sync", json={"scope": "local"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["dry_run"] is False
        assert data["queued"] >= 1
        assert data["task_id"]

        test_db.refresh(rec)
        assert rec.storage == "memory"
        assert rec.storage_status == STORAGE_STATUS_SYNCED
        assert _backend(test_db).head(rec.rel_path) is not None

        status = auth_client.get("/api/admin/files/sync-status").json()["data"]
        assert status["local_only"] == 0  # 存量已全部搬迁

    def test_scope_failed_compensates(self, auth_client, test_db):
        """scope=failed：失败记录补偿重传 → SYNCED（验收 #14 后半）"""
        rec = _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_FAILED)

        resp = auth_client.post("/api/admin/files/sync", json={"scope": "failed"})
        assert resp.status_code == 200
        test_db.refresh(rec)
        assert rec.storage_status == STORAGE_STATUS_SYNCED

    def test_concurrent_trigger_returns_409(self, auth_client, test_db):
        """执行中重复触发 → 409（验收 #14；前端 useActionLock 二次防护）

        用例自包含：自带一条 FAILED 记录，避免依赖前序用例的残留数据
        （xdist 分发下前序用例可能在其它 worker 执行）。
        """
        _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_FAILED)
        svc.RUN_STATE.running = True
        try:
            resp = auth_client.post("/api/admin/files/sync", json={"scope": "failed"})
            assert resp.status_code == 409
        finally:
            svc.RUN_STATE.running = False

    def test_single_sync_success(self, auth_client, test_db):
        """单条同步：本地文件在 → SYNCED"""
        rec = _insert_file(test_db, storage_col="local")
        resp = auth_client.post(f"/api/admin/files/sync/{rec.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "synced"
        test_db.refresh(rec)
        assert rec.storage_status == STORAGE_STATUS_SYNCED
        assert _backend(test_db).head(rec.rel_path) is not None

    def test_single_sync_local_missing_marks_failed(self, auth_client, test_db):
        """单条同步：本地文件缺失 → 状态置 FAILED、HTTP 仍 200（可补偿，不 500）"""
        rec = _insert_file(test_db, storage_col="local", write_disk=False)
        resp = auth_client.post(f"/api/admin/files/sync/{rec.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "failed"
        test_db.refresh(rec)
        assert rec.storage_status == STORAGE_STATUS_FAILED

    def test_single_sync_unknown_id_404(self, auth_client):
        assert auth_client.post("/api/admin/files/sync/999999").status_code == 404


class TestListStorageColumns:
    """§9.1 前端状态列/筛选的后端支撑：列表带 storage/storage_status + 按同步状态过滤"""

    def test_list_returns_storage_fields(self, auth_client, test_db):
        rec = _insert_file(test_db, storage_col="memory", status=STORAGE_STATUS_PENDING)
        resp = auth_client.get(f"/api/admin/files?user_id={rec.user_id}")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["storage"] == "memory"
        assert items[0]["storage_status"] == STORAGE_STATUS_PENDING

    def test_list_filter_by_storage_status(self, auth_client, test_db):
        uid = _next_uid()
        _insert_file(test_db, user_id=uid, storage_col="memory", status=STORAGE_STATUS_PENDING)
        _insert_file(test_db, user_id=uid, storage_col="memory", status=STORAGE_STATUS_SYNCED)

        resp = auth_client.get(
            f"/api/admin/files?user_id={uid}&storage_status={STORAGE_STATUS_PENDING}"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["storage_status"] == STORAGE_STATUS_PENDING

    def test_list_filter_rejects_invalid_status(self, auth_client):
        assert auth_client.get("/api/admin/files?storage_status=9").status_code == 422
