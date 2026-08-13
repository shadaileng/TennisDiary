"""AI 评分代理服务层（OpenAI 兼容接口，Key 存服务端）

参考 Web 版 src/ai.ts 的 chatVision / extractJSON / analyzeSwing / buildLocalReport，
Key 只读服务端配置，不进入小程序包。
"""

import json
import re

import httpx

from app.core.config import settings
from app.core.logging import logger

# 六维评分维度（与前端 / 参考版契约一致）
DIMENSIONS = ["准备启动", "动力链", "击球时机", "随挥收拍", "拍面控制", "身体稳定"]

AI_TIMEOUT_SECONDS = 120


def _build_analyze_prompt(kind: str, mode: str) -> str:
    """组装六维评分 prompt（与参考版 ai.ts analyzeSwing 一致）"""
    mode_desc = (
        f"这是一次{kind}挥拍动作的连续关键帧（按时间顺序）"
        if mode == "single"
        else f"这是一段网球训练视频的关键帧抽样（按时间顺序），请做{kind}方向的综合分析"
    )
    return (
        f"你是一名专业网球教练。{mode_desc}。请仔细观察画面中球员的身体姿态、"
        "挥拍轨迹和步伐，给出专业分析。\n"
        "\n"
        "严格按以下 JSON 格式输出（不要输出任何其他文字）：\n"
        "{\n"
        '  "score": 总分0-100整数,\n'
        '  "summary": "一句话总结（30字内）",\n'
        '  "ntrp": "参考NTRP等级，1.0-7.0之间、0.5步进的字符串，如\\"2.5\\"，'
        '基于画面动作水平客观评估",\n'
        '  "dimensions": [\n'
        '    {"name": "准备启动", "score": 0-100, "comment": "简短点评（25字内）"},\n'
        '    {"name": "动力链", "score": 0-100, "comment": "..."},\n'
        '    {"name": "击球时机", "score": 0-100, "comment": "..."},\n'
        '    {"name": "随挥收拍", "score": 0-100, "comment": "..."},\n'
        '    {"name": "拍面控制", "score": 0-100, "comment": "..."},\n'
        '    {"name": "身体稳定", "score": 0-100, "comment": "..."}\n'
        "  ],\n"
        '  "rhythm": "节奏与战术观察（50字内，若为单次挥拍则谈发力节奏）",\n'
        '  "strengths": ["亮点1", "亮点2"],\n'
        '  "improvements": [\n'
        '    {"issue": "问题描述", "advice": "具体改进建议与练习方法"},\n'
        '    {"issue": "...", "advice": "..."}\n'
        "  ]\n"
        "}\n"
        "评分校准标尺（必须严格执行，禁止偏高）：\n"
        "- 90-100：职业/准职业，动力链教科书级（极罕见，几乎不该给出）\n"
        "- 80-89：高水平业余（NTRP 4.5+），动作自动化、可变节奏\n"
        "- 70-79：进阶业余（NTRP 3.5-4.0），动作定型、偶有瑕疵\n"
        "- 60-69：中级业余（NTRP 2.5-3.0），动作基本完整但动力链有明显断点\n"
        "- 50-59：初学进步期（NTRP 2.0-2.5），有挥拍框架、稳定性差\n"
        "- 50 以下：初学（NTRP 1.0-1.5），动作要素缺失\n"
        "打分流程：先逐帧找出所有技术问题并扣分，再对照标尺定总分；拿不准时取所在档位的"
        "中值，不要因画质、光线、拍摄角度等非技术因素额外压分；业余爱好者上传的视频总分"
        "大多应落在 55-70。ntrp 字段必须与总分所在档位一致。点评要具体可执行，引用画面中"
        '观察到的细节。若画面过暗、黑屏或无法辨识动作，请在 summary 中如实说明"画面无法'
        '辨识"，不要虚构分析内容。'
    )


async def chat_vision(images: list[str], prompt: str, max_tokens: int = 2000) -> str:
    """调用 OpenAI 兼容 chat/completions（阿里云百炼），images 为 dataURL

    - 120s 超时保护；
    - 无 Key 直接抛错（不发起网络请求）。
    """
    if not settings.AI_API_KEY:
        raise ValueError("未配置 API Key")
    content: list[dict] = [{"type": "image_url", "image_url": {"url": url}} for url in images]
    content.append({"type": "text", "text": prompt})
    payload = {
        "model": settings.AI_MODEL,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": content}],
    }
    base_url = settings.AI_BASE_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                },
                json=payload,
            )
    except httpx.TimeoutException:
        raise RuntimeError("AI 请求超时（120 秒），请检查网络后重试") from None
    except httpx.HTTPError:
        raise RuntimeError("网络异常，无法连接 AI 服务") from None
    if resp.status_code != 200:
        text = resp.text[:200]
        raise RuntimeError(f"AI 请求失败 ({resp.status_code})：{text}")
    data = resp.json()
    return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""


def extract_json(text: str) -> dict:
    """从 AI 返回文本中提取 JSON 对象（容错前后缀文字 / 代码块）"""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("AI 返回内容无法解析")
    return json.loads(match.group(0))


async def analyze_swing(frames: list[str], kind: str, mode: str = "single") -> dict:
    """AI 动作分析：frames 为按时间顺序抽取的关键帧，返回六维报告

    无 Key / 调用失败 / 解析失败时抛异常，由路由层转本地降级。
    """
    prompt = _build_analyze_prompt(kind, mode)
    text = await chat_vision(frames, prompt, max_tokens=2500)
    report = extract_json(text)

    # 兜底校验（与参考版 analyzeSwing 尾部一致）
    dimensions = report.get("dimensions")
    if not isinstance(dimensions, list) or len(dimensions) == 0:
        report["dimensions"] = [
            {"name": name, "score": report.get("score") or 60, "comment": "—"}
            for name in DIMENSIONS
        ]
    report["strengths"] = report.get("strengths") or []
    report["improvements"] = report.get("improvements") or []
    logger.info(f"AI 分析完成: kind={kind} mode={mode} score={report.get('score')}")
    return report


def build_local_report(kind: str, metrics: dict | None = None) -> dict:
    """本地降级报告（无 API Key / 调用失败时），基于姿态测量数据

    metrics 可为 None（姿态推理尚未接入时），此时给出配置提示。
    """
    notes: list[str] = []
    improvements: list[dict] = []
    metrics = metrics or {}

    knee_angle = metrics.get("kneeAngle")
    elbow_angle = metrics.get("elbowAngle")
    trunk_lean = metrics.get("trunkLean")
    if knee_angle is not None:
        if knee_angle > 165:
            improvements.append(
                {
                    "issue": f"击球瞬间膝角约 {round(knee_angle)}°，腿部弯曲不足",
                    "advice": "准备时降低重心，膝角保持在 130-150°，用蹬地启动发力",
                }
            )
        else:
            notes.append(f"膝角约 {round(knee_angle)}°，重心下沉到位")
    if elbow_angle is not None and kind in ("正手", "反手"):
        if elbow_angle < 90:
            improvements.append(
                {
                    "issue": f"击球手肘角约 {round(elbow_angle)}°，手臂过于收紧",
                    "advice": "放松前臂，保持自然伸展的击球空间",
                }
            )
        else:
            notes.append(f"手肘角约 {round(elbow_angle)}°，击球空间舒展")
    if trunk_lean is not None and abs(trunk_lean) > 20:
        improvements.append(
            {
                "issue": f"躯干倾斜约 {round(abs(trunk_lean))}°，身体稳定性欠佳",
                "advice": "击球时保持头部固定、核心收紧，避免上身过度前倾或后仰",
            }
        )
    if not improvements:
        improvements.append(
            {
                "issue": "本地分析未发现明显姿态问题",
                "advice": "配置 AI Key 后可获得教练级的动力链与战术分析",
            }
        )
    return {
        "score": 0,
        "summary": f"本地姿态测量完成（{kind}），配置 AI 后可获得完整评分点评",
        "dimensions": [],
        "rhythm": "本地模式不提供节奏战术分析",
        "strengths": notes if notes else ["骨架追踪正常，动作记录完整"],
        "improvements": improvements,
    }
