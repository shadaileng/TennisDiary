"""微信小程序 code2Session 服务"""

import httpx
from app.core.config import settings

WX_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


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
    except Exception as e:
        raise RuntimeError(f"微信 API 调用失败: {str(e)}")

    if "errcode" in data and data["errcode"] != 0:
        raise ValueError(f"微信登录失败: {data.get('errmsg', 'unknown error')} (code: {data['errcode']})")

    openid = data.get("openid")
    if not openid:
        raise ValueError("微信返回数据缺少 openid")

    return openid
