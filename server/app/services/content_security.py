"""微信小程序内容安全检查服务"""

import httpx
from loguru import logger

from app.services.wx_service import get_access_token, get_access_token_sync

WX_MSG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/msg_sec_check"
WX_IMG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/img_sec_check"
WX_MEDIA_CHECK_ASYNC_URL = "https://api.weixin.qq.com/wxa/media_check_async"


class ContentSecurityError(Exception):
    """内容安全检查异常"""

    def __init__(self, errcode: int, errmsg: str):
        self.errcode = errcode
        self.errmsg = errmsg
        super().__init__(f"内容安全检查失败: {errmsg} (code: {errcode})")


async def check_text(content: str, openid: str, scene: int = 2, version: int = 2) -> bool:
    """检查文本内容是否安全

    Args:
        content: 要检查的文本
        openid: 用户openid
        scene: 场景值（1=资料 2=评论 3=论坛 4=其他）
        version: 接口版本（2=新版）

    Returns:
        True if safe

    Raises:
        ContentSecurityError: 内容不安全
        RuntimeError: API 调用失败
    """
    token = await get_access_token()
    url = f"{WX_MSG_SEC_CHECK_URL}?access_token={token}"
    payload = {
        "content": content,
        "openid": openid,
        "scene": scene,
        "version": version,
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            data = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"文本安全检查 API 调用失败: {e!s}") from e

    if data.get("errcode", 0) != 0:
        raise ContentSecurityError(data["errcode"], data.get("errmsg", "unknown"))

    result = data.get("result", {})
    suggest = result.get("suggest", "pass")
    if suggest != "pass":
        label = result.get("label", 100)
        logger.warning("文本内容安全检查不通过", suggest=suggest, label=label)
        raise ContentSecurityError(87014, "内容可能包含违规信息")

    return True


async def check_image(file_path: str, openid: str) -> bool:
    """检查图片内容是否安全（同步，限1MB）

    Args:
        file_path: 图片文件路径
        openid: 用户openid

    Returns:
        True if safe

    Raises:
        ContentSecurityError: 内容不安全
        RuntimeError: API 调用失败
    """
    token = await get_access_token()
    url = f"{WX_IMG_SEC_CHECK_URL}?access_token={token}"

    try:
        with open(file_path, "rb") as f:
            filename = file_path.split("/")[-1].split("\\")[-1]
            files = {"media": (filename, f, "image/jpeg")}
            data = {"openid": openid}
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, files=files, data=data, timeout=30.0)
                result = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"图片安全检查 API 调用失败: {e!s}") from e

    if result.get("errcode", 0) != 0:
        raise ContentSecurityError(result["errcode"], result.get("errmsg", "unknown"))

    return True


async def check_media(file_path: str, openid: str, media_type: int = 2) -> dict:
    """异步检查图片/音频/视频内容是否安全

    Args:
        file_path: 媒体文件路径
        openid: 用户openid
        media_type: 媒体类型（1=图片 2=音频 3=视频）

    Returns:
        {"trace_id": "..."} 用于后续查询结果

    Raises:
        RuntimeError: API 调用失败
    """
    token = await get_access_token()
    url = f"{WX_MEDIA_CHECK_ASYNC_URL}?access_token={token}"

    try:
        with open(file_path, "rb") as f:
            filename = file_path.split("/")[-1].split("\\")[-1]
            files = {"media": (filename, f, "video/mp4")}
            data = {
                "openid": openid,
                "scene": 1,
                "version": 2,
                "media_type": media_type,
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, files=files, data=data, timeout=60.0)
                result = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"多媒体安全检查 API 调用失败: {e!s}") from e

    if result.get("errcode", 0) != 0:
        errcode = result["errcode"]
        errmsg = result.get("errmsg", "unknown")
        logger.warning("多媒体安全检查 API 返回错误", errcode=errcode, errmsg=errmsg)
        # 异步检查不阻断上传，仅记录日志
        return {"trace_id": "", "errcode": errcode, "errmsg": errmsg}

    trace_id = result.get("trace_id", "")
    logger.info("多媒体安全检查已提交", trace_id=trace_id)
    return {"trace_id": trace_id}


# ==================== 同步版本（供 @audit 装饰器的同步路由使用） ====================


def check_image_sync(file_path: str, openid: str) -> bool:
    """同步检查图片内容是否安全（限1MB）"""
    token = get_access_token_sync()
    url = f"{WX_IMG_SEC_CHECK_URL}?access_token={token}"

    with open(file_path, "rb") as f:
        filename = file_path.split("/")[-1].split("\\")[-1]
        files = {"media": (filename, f, "image/jpeg")}
        data = {"openid": openid}
        resp = httpx.post(url, files=files, data=data, timeout=30.0)
        result = resp.json()

    errcode = result.get("errcode", 0)
    if errcode != 0:
        errmsg = result.get("errmsg", "unknown")
        logger.warning("图片安全检查不通过", errcode=errcode, errmsg=errmsg, file_path=file_path)
        raise ContentSecurityError(errcode, errmsg)

    logger.info("图片安全检查通过", file_path=file_path)
    return True


def check_media_sync(file_path: str, openid: str, media_type: int = 2) -> dict:
    """同步提交异步多媒体内容安全检查"""
    token = get_access_token_sync()
    url = f"{WX_MEDIA_CHECK_ASYNC_URL}?access_token={token}"

    with open(file_path, "rb") as f:
        filename = file_path.split("/")[-1].split("\\")[-1]
        files = {"media": (filename, f, "video/mp4")}
        data = {
            "openid": openid,
            "scene": 1,
            "version": 2,
            "media_type": media_type,
        }
        resp = httpx.post(url, files=files, data=data, timeout=60.0)
        result = resp.json()

    if result.get("errcode", 0) != 0:
        errcode = result["errcode"]
        errmsg = result.get("errmsg", "unknown")
        logger.warning("多媒体安全检查 API 返回错误", errcode=errcode, errmsg=errmsg)
        return {"trace_id": "", "errcode": errcode, "errmsg": errmsg}

    trace_id = result.get("trace_id", "")
    logger.info("多媒体安全检查已提交", trace_id=trace_id)
    return {"trace_id": trace_id}
