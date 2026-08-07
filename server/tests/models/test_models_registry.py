"""模型注册与元数据完整性测试。

确保 `app/models/__init__.py` 已集中导入全部模型，
使 Alembic 迁移（`app.core.database.Base.metadata`）能发现所有表。
若新增模型未在 __init__ 导出，此处将失败。
"""

from app.core.database import Base

EXPECTED_TABLES = {
    "users",
    "diaries",
    "gears",
    "weight_records",
    "analyses",
    "checkins",
    "posts",
}


class TestModelsRegistry:
    """Base.metadata 应包含全部业务表"""

    def test_all_tables_registered(self):
        """所有模型表都已注册到 Base.metadata"""
        missing = EXPECTED_TABLES - set(Base.metadata.tables.keys())
        assert not missing, f"以下表未在 Base.metadata 注册：{missing}"

    def test_users_has_profile_columns(self):
        """users 表应包含性别与生日列（Step 38 新增）"""
        users_table = Base.metadata.tables["users"]
        assert "gender" in users_table.c
        assert "birthday" in users_table.c

    def test_openid_index_is_unique(self):
        """users.openid 唯一索引存在"""
        users_table = Base.metadata.tables["users"]
        assert users_table.c.openid.unique is True
