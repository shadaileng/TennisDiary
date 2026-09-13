"""微信小程序内容安全检查服务"""

import httpx
from loguru import logger

from app.services.wx_service import get_access_token, get_access_token_sync

WX_MSG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/msg_sec_check"
WX_IMG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/img_sec_check"


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


# ==================== 同步版本（供 @audit 装饰器的同步路由使用） ====================

# 137 §2.2：mediaCheckAsync 仅支持 1=音频 / 2=图片，视频检测调用恒返回 40004，
# 且结果以消息推送方式下发、无按 trace_id 查询接口，故 check_media / check_media_sync
# 一并移除；视频在 /api/upload/video 上传阶段视为放行。


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
