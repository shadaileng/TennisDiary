import pytest

from app.models.user import User


class TestUserModel:
    """User ORM 模型测试"""

    def test_create_user(self, test_db):
        user = User(openid="test_openid_001", nickname="测试")
        test_db.add(user)
        test_db.commit()

        saved = test_db.query(User).filter_by(openid="test_openid_001").first()
        assert saved is not None
        assert saved.nickname == "测试"
        assert saved.openid == "test_openid_001"

    def test_openid_unique_constraint(self, test_db):
        user1 = User(openid="unique_oid")
        test_db.add(user1)
        test_db.commit()

        user2 = User(openid="unique_oid")
        test_db.add(user2)
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_default_values(self, test_db):
        user = User(openid="default_test")
        test_db.add(user)
        test_db.commit()

        saved = test_db.query(User).filter_by(openid="default_test").first()
        assert saved.nickname == ""
        assert saved.avatar_url == ""

    def test_created_at_auto_set(self, test_db):
        user = User(openid="timestamp_test")
        test_db.add(user)
        test_db.commit()

        saved = test_db.query(User).filter_by(openid="timestamp_test").first()
        assert saved.created_at is not None
