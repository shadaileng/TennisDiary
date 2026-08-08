"""系统监控路由测试"""

import os
from pathlib import Path

from app.core.config import settings


def test_system_health(auth_client, test_db):
    """测试系统健康检查增强接口"""
    response = auth_client.get("/api/admin/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "database" in data
    assert "disk_usage" in data
    assert "uptime" in data


def test_system_stats(auth_client, test_db):
    """测试运行时指标接口"""
    response = auth_client.get("/api/admin/system/stats")
    assert response.status_code == 200
    data = response.json()
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
    data = response.json()
    assert "logs" in data
    assert "total" in data
    assert isinstance(data["logs"], list)


def test_query_logs_with_params(auth_client, test_db):
    """测试日志查询接口（带参数）"""
    response = auth_client.get("/api/admin/system/logs?level=INFO&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "total" in data


def test_backup_database(auth_client, test_db):
    """测试数据库备份接口"""
    # 创建临时备份目录
    backup_dir = Path(settings.DATA_DIR) / "backups"
    backup_dir.mkdir(exist_ok=True)

    # 模拟数据库文件存在
    db_path = Path(settings.DATA_DIR) / "tennis_diary.db"
    if not db_path.exists():
        # 创建临时数据库文件
        with open(db_path, "w") as f:
            f.write("")

    response = auth_client.post("/api/admin/system/backup")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "备份成功" in data["message"]


def test_list_backups(auth_client, test_db):
    """测试备份列表接口"""
    # 创建临时备份目录
    backup_dir = Path(settings.DATA_DIR) / "backups"
    backup_dir.mkdir(exist_ok=True)

    # 创建临时备份文件
    temp_backup = backup_dir / "backup_20260808_120000.db"
    with open(temp_backup, "w") as f:
        f.write("")

    response = auth_client.get("/api/admin/system/backups")
    assert response.status_code == 200
    data = response.json()
    assert "backups" in data
    assert "total" in data
    assert isinstance(data["backups"], list)

    # 清理临时文件
    if temp_backup.exists():
        os.unlink(temp_backup)
