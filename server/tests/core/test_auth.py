import pytest
from fastapi import HTTPException

from app.core.auth import create_access_token, decode_access_token


class TestCreateAccessToken:
    """JWT 签发测试"""

    def test_creates_valid_token(self):
        token = create_access_token("test_openid_abc")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_decodes_to_same_openid(self):
        token = create_access_token("openid_xyz")
        decoded = decode_access_token(token)
        assert decoded == "openid_xyz"


class TestDecodeAccessToken:
    """JWT 解码测试"""

    def test_valid_token_returns_openid(self):
        token = create_access_token("user_123")
        result = decode_access_token(token)
        assert result == "user_123"

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            decode_access_token("invalid.token.here")
        assert exc.value.status_code == 401
        assert "无效的 token" in str(exc.value.detail)

    def test_empty_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            decode_access_token("")
        assert exc.value.status_code == 401


class TestGetCurrentUser:
    """鉴权依赖测试 — 通过 auth_client fixture 测试（见 routers/test_auth.py）"""
