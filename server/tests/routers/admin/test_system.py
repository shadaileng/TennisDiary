"""系统监控路由测试"""

import io
import os
import tarfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.models.backup_record import BackupRecord


@pytest.fixture(autouse=True)
def _clean_backup_records(test_meta_db):
    """每个测试前清空备份元数据库记录，避免跨测试累积导致唯一约束冲突"""
    test_meta_db.query(BackupRecord).delete()
    test_meta_db.commit()
    yield


def test_system_health(auth_client, test_db):
    """测试系统健康检查增强接口"""
    response = auth_client.get("/api/admin/system/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "database" in data
    assert "disk_usage" in data
    assert "uptime" in data


def test_system_stats(auth_client, test_db):
    """测试运行时指标接口"""
    response = auth_client.get("/api/admin/system/stats")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "stats" in data
    assert "database_size" in data
    # 验证统计字段存在
    stats = data["stats"]
    assert "users" in stats
    assert "diaries" in stats
    assert "gears" in stats
    assert "weights" in stats
    assert "checkins" in stats
    assert "analyses" in stats
    assert "posts" in stats


def test_query_logs(auth_client, test_db):
    """测试日志查询接口"""
    response = auth_client.get("/api/admin/system/logs")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "logs" in data
    assert "total" in data
    assert isinstance(data["logs"], list)


def test_query_logs_with_params(auth_client, test_db):
    """测试日志查询接口（带参数）"""
    response = auth_client.get("/api/admin/system/logs?level=INFO&limit=10")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "logs" in data
    assert "total" in data


def test_backup_database(auth_client, test_db):
    """测试数据目录整体备份接口（tar.gz）"""
    # settings.DATA_DIR 已被 autouse fixture _isolate_data_dirs 隔离到 tmp_path
    data_dir = Path(settings.DATA_DIR)
    backup_dir = data_dir / "backups"
    backup_dir.mkdir()

    # 模拟数据库文件存在
    db_path = data_dir / "tennis_diary.db"
    db_path.write_text("")

    response = auth_client.post("/api/admin/system/backup")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "备份成功" in data["message"]

    # 生成的是 .tar.gz
    backups = list(backup_dir.glob("backup_*.tar.gz"))
    assert len(backups) >= 1

    # 校验压缩包不含 backups 目录自身（避免递归膨胀）
    with tarfile.open(backups[-1], "r:gz") as tar:
        names = tar.getnames()
    assert not any("backups/" in n for n in names)

    # GNU 格式打包，不应产生 PaxHeaders 元数据噪声
    assert not any("PaxHeaders" in n for n in names)

    # 归档内 arcname 必须唯一（防止 tar.add 对目录递归展开导致文件重复）
    assert len(names) == len(set(names)), (
        f"归档内出现重名条目: {sorted({n for n in names if names.count(n) > 1})}"
    )


def test_restore_backup(auth_client, test_db, test_meta_db):
    """测试恢复接口：恢复前会无条件生成一份完整备份（pre_restore_*.tar.gz）

    注意：restore 接口会 tar.extractall(settings.DATA_DIR) 覆盖数据库，
    autouse _isolate_data_dirs 已将 DATA_DIR 隔离到 tmp_path，避免污染真实环境。
    """
    # settings.DATA_DIR 已被 autouse fixture _isolate_data_dirs 隔离到 tmp_path
    data_dir = Path(settings.DATA_DIR)
    backup_dir = data_dir / "backups"
    backup_dir.mkdir()

    # 模拟数据库文件存在
    db_path = data_dir / "tennis_diary.db"
    db_path.write_text("current data")

    # 先建一份待恢复的备份（同时在元数据库登记记录，用于验证状态关联）
    target = backup_dir / "backup_20260812_120000.tar.gz"
    with tarfile.open(target, "w:gz") as tar:
        content = io.BytesIO(b"restored data")
        info = tarfile.TarInfo("tennis_diary.db")
        info.size = len(content.getvalue())
        tar.addfile(info, content)
    test_meta_db.add(
        BackupRecord(
            name=target.name,
            size=1,
            type="manual",
            status="created",
        )
    )
    test_meta_db.commit()

    response = auth_client.post(f"/api/admin/system/restore/{target.name}")
    assert response.status_code == 200
    assert "恢复成功" in response.json()["message"]

    # 恢复后应生成 pre_restore_*.tar.gz 完整备份，且不覆盖待恢复的源备份
    pres = list(backup_dir.glob("pre_restore_*.tar.gz"))
    assert len(pres) >= 1
    with tarfile.open(pres[-1], "r:gz") as tar:
        pnames = tar.getnames()
    assert "tennis_diary.db" in pnames

    # 目标备份文件仍在（_pack_data_dir 不会把它递归进自身备份）
    assert target.exists()

    # 元数据库写入 pre_restore 兜底记录
    pre_records = test_meta_db.query(BackupRecord).filter(BackupRecord.type == "pre_restore").all()
    assert len(pre_records) >= 1
    pre_record = pre_records[-1]

    # 目标备份被标记 restored，并关联到本次恢复前生成的兜底备份
    target_record = (
        test_meta_db.query(BackupRecord).filter(BackupRecord.name == target.name).first()
    )
    assert target_record is not None
    assert target_record.status == "restored"
    assert target_record.restored_at is not None
    assert target_record.restored_from_id == pre_record.id

    # 列表接口返回 restored_from_name（还原关联的兜底备份文件名）
    resp = auth_client.get("/api/admin/system/backups")
    assert resp.status_code == 200
    list_items = resp.json()["data"]["backups"]
    item = next(i for i in list_items if i["name"] == target.name)
    assert item["status"] == "restored"
    assert item["restored_from_name"] == pre_record.name


def test_restore_resets_previous_restored(auth_client, test_db, test_meta_db):
    """恢复新备份时，旧的 restored 状态被重置，保证同时只有一个 restored"""
    # settings.DATA_DIR 已被 autouse fixture _isolate_data_dirs 隔离到 tmp_path
    data_dir = Path(settings.DATA_DIR)
    backup_dir = data_dir / "backups"
    backup_dir.mkdir()

    db_path = data_dir / "tennis_diary.db"
    db_path.write_text("current data")

    # 两份待恢复备份，都登记在元数据库
    target_a = backup_dir / "backup_a.tar.gz"
    target_b = backup_dir / "backup_b.tar.gz"
    for t in (target_a, target_b):
        with tarfile.open(t, "w:gz") as tar:
            content = io.BytesIO(b"data")
            info = tarfile.TarInfo("tennis_diary.db")
            info.size = len(content.getvalue())
            tar.addfile(info, content)
    test_meta_db.add_all(
        [
            BackupRecord(name=target_a.name, size=1, type="manual", status="created"),
            BackupRecord(name=target_b.name, size=1, type="manual", status="created"),
        ]
    )
    test_meta_db.commit()

    # 第一次恢复 target_a
    r1 = auth_client.post(f"/api/admin/system/restore/{target_a.name}")
    assert r1.status_code == 200

    restored_count = (
        test_meta_db.query(BackupRecord).filter(BackupRecord.status == "restored").count()
    )
    assert restored_count == 1
    rec_a = test_meta_db.query(BackupRecord).filter(BackupRecord.name == target_a.name).first()
    assert rec_a.status == "restored"

    # 第二次恢复 target_b：target_a 的 restored 应被重置
    r2 = auth_client.post(f"/api/admin/system/restore/{target_b.name}")
    assert r2.status_code == 200

    restored_count_after = (
        test_meta_db.query(BackupRecord).filter(BackupRecord.status == "restored").count()
    )
    assert restored_count_after == 1

    test_meta_db.expire_all()
    rec_a_after = (
        test_meta_db.query(BackupRecord).filter(BackupRecord.name == target_a.name).first()
    )
    rec_b_after = (
        test_meta_db.query(BackupRecord).filter(BackupRecord.name == target_b.name).first()
    )
    assert rec_a_after.status == "created"
    assert rec_a_after.restored_from_id is None
    assert rec_b_after.status == "restored"
    assert rec_b_after.restored_from_id is not None


def test_list_backups(auth_client, test_meta_db):
    """测试备份列表接口（纯表驱动）"""
    # 在独立元数据库插入一条记录
    record = BackupRecord(
        name="backup_20260808_120000.tar.gz",
        size=1024,
        type="manual",
        status="created",
    )
    test_meta_db.add(record)
    test_meta_db.commit()

    response = auth_client.get("/api/admin/system/backups")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "backups" in data
    assert "total" in data
    assert isinstance(data["backups"], list)
    assert any(b["name"] == "backup_20260808_120000.tar.gz" for b in data["backups"])


def test_list_backups_includes_types(auth_client, test_meta_db):
    """备份列表应返回手动/兜底/上传类型，并带 type/status 字段"""
    test_meta_db.add_all(
        [
            BackupRecord(
                name="backup_20260810_100000.tar.gz",
                size=2048,
                type="manual",
                status="created",
            ),
            BackupRecord(
                name="pre_restore_20260811_100000.tar.gz",
                size=1024,
                type="pre_restore",
                status="created",
            ),
            BackupRecord(
                name="upload_abc123.tar.gz",
                size=512,
                type="upload",
                status="created",
                note="上传自 x.tar.gz",
            ),
        ]
    )
    test_meta_db.commit()

    response = auth_client.get("/api/admin/system/backups")
    assert response.status_code == 200
    backups = response.json()["data"]["backups"]

    by_name = {b["name"]: b for b in backups}
    assert by_name["backup_20260810_100000.tar.gz"]["type"] == "manual"
    assert by_name["pre_restore_20260811_100000.tar.gz"]["type"] == "pre_restore"
    assert by_name["upload_abc123.tar.gz"]["type"] == "upload"
    assert "status" in by_name["backup_20260810_100000.tar.gz"]
    assert "note" in by_name["upload_abc123.tar.gz"]


def test_download_backup(auth_client, test_db):
    """测试下载备份文件接口"""
    # settings.DATA_DIR 已被 autouse fixture _isolate_data_dirs 隔离到 tmp_path
    data_dir = Path(settings.DATA_DIR)
    backup_dir = data_dir / "backups"
    backup_dir.mkdir()

    # 创建真实 tar.gz 备份文件
    backup_path = backup_dir / "backup_20260808_120000.tar.gz"
    with tarfile.open(backup_path, "w:gz") as tar:
        content = io.BytesIO(b"hello backup")
        info = tarfile.TarInfo("tennis_diary.db")
        info.size = len(content.getvalue())
        tar.addfile(info, content)

    response = auth_client.get(f"/api/admin/system/backup/download/{backup_path.name}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/gzip"
    assert response.content.startswith(b"\x1f\x8b")  # gzip 魔数

    os.unlink(backup_path)


def test_download_backup_traversal(auth_client, test_db):
    """测试下载接口路径穿越防护"""
    # settings.DATA_DIR 已被 autouse fixture _isolate_data_dirs 隔离到 tmp_path
    data_dir = Path(settings.DATA_DIR)
    backup_dir = data_dir / "backups"
    backup_dir.mkdir()

    response = auth_client.get("/api/admin/system/backup/download/..%2F..%2Fsecret.tar.gz")
    assert response.status_code in (400, 404)


def test_delete_backup(auth_client, test_db, test_meta_db):
    """测试删除备份记录（物理删文件 + 软删记录）接口"""
    # settings.DATA_DIR 已被 autouse fixture _isolate_data_dirs 隔离到 tmp_path
    data_dir = Path(settings.DATA_DIR)
    backup_dir = data_dir / "backups"
    backup_dir.mkdir()

    backup_path = backup_dir / "backup_20260808_120000.tar.gz"
    backup_path.write_text("x")

    # 元数据库记录
    test_meta_db.add(
        BackupRecord(
            name=backup_path.name,
            size=1,
            type="manual",
            status="created",
        )
    )
    test_meta_db.commit()

    # 删除成功
    response = auth_client.delete(f"/api/admin/system/backup/{backup_path.name}")
    assert response.status_code == 200
    assert not backup_path.exists()

    # 软删：列表不再展示，但记录仍保留（deleted_at 非空）
    record = test_meta_db.query(BackupRecord).filter(BackupRecord.name == backup_path.name).first()
    assert record is not None
    assert record.deleted_at is not None
    assert record.status == "deleted"

    response = auth_client.get("/api/admin/system/backups")
    backups = response.json()["data"]["backups"]
    assert not any(b["name"] == backup_path.name for b in backups)

    # 再次删除返回 404（文件已不存在）
    response = auth_client.delete(f"/api/admin/system/backup/{backup_path.name}")
    assert response.status_code == 404


def test_upload_backup(auth_client, test_meta_db):
    """测试上传备份文件接口（multipart）"""
    # settings.DATA_DIR 已被 autouse fixture _isolate_data_dirs 隔离到 tmp_path
    data_dir = Path(settings.DATA_DIR)
    backup_dir = data_dir / "backups"
    backup_dir.mkdir()

    # 构造一个合法 tar.gz 内容
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        content = io.BytesIO(b"uploaded data")
        info = tarfile.TarInfo("tennis_diary.db")
        info.size = len(content.getvalue())
        tar.addfile(info, content)
    payload = buf.getvalue()

    response = auth_client.post(
        "/api/admin/system/backup/upload",
        files={"file": ("my_backup.tar.gz", payload, "application/gzip")},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"].startswith("upload_")
    assert data["name"].endswith(".tar.gz")

    # 上传的文件真实落盘
    uploaded_path = backup_dir / data["name"]
    assert uploaded_path.exists()

    # 记录入库，type=upload，可被列表展示
    record = test_meta_db.query(BackupRecord).filter(BackupRecord.name == data["name"]).first()
    assert record is not None
    assert record.type == "upload"
    assert "my_backup.tar.gz" in record.note

    response = auth_client.get("/api/admin/system/backups")
    backups = response.json()["data"]["backups"]
    assert any(b["name"] == data["name"] and b["type"] == "upload" for b in backups)

    # 上传的备份可恢复
    response = auth_client.post(f"/api/admin/system/restore/{data['name']}")
    assert response.status_code == 200

    os.unlink(uploaded_path)


def test_upload_backup_reject_bad_ext(auth_client):
    """上传非 .tar.gz/.db 文件应被拒绝"""
    response = auth_client.post(
        "/api/admin/system/backup/upload",
        files={"file": ("evil.exe", b"x", "application/octet-stream")},
    )
    assert response.status_code == 400
