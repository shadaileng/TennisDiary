"""微信小程序服务（登录 + access_token + 内容安全）"""

import time

import httpx
from loguru import logger

from app.core.config import settings

WX_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
WX_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"

# access_token 缓存
_ACCESS_TOKEN_CACHE: dict = {"token": "", "expires_at": 0.0}


def _fetch_access_token() -> str:
    """同步获取微信 access_token（内部方法）"""
    now = time.time()
    if _ACCESS_TOKEN_CACHE["token"] and now < _ACCESS_TOKEN_CACHE["expires_at"]:
        return _ACCESS_TOKEN_CACHE["token"]

    params = {
        "grant_type": "client_credential",
        "appid": settings.WX_APPID,
        "secret": settings.WX_SECRET,
    }
    resp = httpx.get(WX_ACCESS_TOKEN_URL, params=params, timeout=10.0)
    data = resp.json()

    if "errcode" in data and data["errcode"] != 0:
        errmsg = data.get("errmsg", "unknown error")
        raise RuntimeError(f"获取 access_token 失败: {errmsg} (code: {data['errcode']})")

    token = data.get("access_token")
    if not token:
        raise RuntimeError("微信返回数据缺少 access_token")

    expires_in = data.get("expires_in", 7200)
    _ACCESS_TOKEN_CACHE["token"] = token
    _ACCESS_TOKEN_CACHE["expires_at"] = now + expires_in - 300
    logger.info("微信 access_token 已刷新", expires_in=expires_in)
    return token


def get_access_token_sync() -> str:
    """同步获取微信 access_token（带缓存，提前5分钟过期）"""
    return _fetch_access_token()


async def get_access_token() -> str:
    """获取微信 access_token（带缓存，提前5分钟过期）

    Returns:
        有效的 access_token

    Raises:
        RuntimeError: 微信 API 调用失败或返回错误
    """
    return _fetch_access_token()


async def code_to_openid(code: str) -> str:
    """使用 wx.login 返回的临时 code 换取 openid

    Args:
        code: wx.login 返回的临时 code

    Returns:
        用户的 openid

    Raises:
        ValueError: code 无效或微信 API 返回错误
        RuntimeError: 微信 API 网络异常
    """
    params = {
        "appid": settings.WX_APPID,
        "secret": settings.WX_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(WX_CODE2SESSION_URL, params=params, timeout=10.0)
            data = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"微信 API 调用失败: {e!s}") from e

    if "errcode" in data and data["errcode"] != 0:
        errmsg = data.get("errmsg", "unknown error")
        raise ValueError(f"微信登录失败: {errmsg} (code: {data['errcode']})")

    openid = data.get("openid")
    if not openid:
        raise ValueError("微信返回数据缺少 openid")

    return openid
