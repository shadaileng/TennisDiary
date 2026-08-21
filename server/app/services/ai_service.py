"""AI 评分代理服务层（OpenAI 兼容接口，Key 存服务端）

参考 Web 版 src/ai.ts 的 chatVision / extractJSON / analyzeSwing / buildLocalReport，
Key 只读服务端配置，不进入小程序包。
"""

import hashlib
import json
import re
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.analysis import Analysis
from app.models.diary import Diary
from app.models.user import User
from app.services.config_service import AIConfig

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


async def _post_completions(
    payload: dict,
    ai_config: AIConfig,
) -> str:
    """向 OpenAI 兼容 chat/completions 发送请求并返回文本内容"""
    if not ai_config.api_key:
        raise ValueError("未配置 API Key")
    base_url = ai_config.base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {ai_config.api_key}",
                },
                json=payload,
            )
    except httpx.TimeoutException as exc:
        logger.warning(f"AI 请求超时（120秒）: {exc}")
        raise RuntimeError("AI 请求超时（120 秒），请检查网络后重试") from exc
    except httpx.HTTPError as exc:
        logger.warning(f"AI 网络异常: {exc}")
        raise RuntimeError("网络异常，无法连接 AI 服务") from exc
    if resp.status_code != 200:
        text = resp.text[:200]
        raise RuntimeError(f"AI 请求失败 ({resp.status_code})：{text}")
    data = resp.json()
    return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""


async def chat_vision(
    images: list[str],
    prompt: str,
    ai_config: AIConfig,
    max_tokens: int = 2000,
) -> str:
    """调用 OpenAI 兼容 chat/completions（阿里云百炼），images 为 dataURL

    - 120s 超时保护；
    - 无 Key 直接抛错（不发起网络请求）。
    - ai_config 为生效配置（DB 覆盖 > env 默认），由路由层解析。
    """
    content: list[dict] = [{"type": "image_url", "image_url": {"url": url}} for url in images]
    content.append({"type": "text", "text": prompt})
    payload = {
        "model": ai_config.model,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": content}],
    }
    return await _post_completions(payload, ai_config)


async def chat_text(
    prompt: str,
    ai_config: AIConfig,
    max_tokens: int = 1000,
) -> str:
    """纯文本版 chat_vision：无图片，用于文案生成等文本任务"""
    content = [{"type": "text", "text": prompt}]
    payload = {
        "model": ai_config.model,
        "max_tokens": max_tokens,
        "temperature": 0.9,
        "messages": [{"role": "user", "content": content}],
    }
    return await _post_completions(payload, ai_config)


def extract_json(text: str) -> dict:
    """从 AI 返回文本中提取 JSON 对象（容错前后缀文字 / 代码块）"""
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("AI 返回内容无法解析")
    return json.loads(match.group(0))


async def analyze_swing(
    frames: list[str],
    kind: str,
    mode: str = "single",
    ai_config: AIConfig | None = None,
) -> dict:
    """AI 动作分析：frames 为按时间顺序抽取的关键帧，返回六维报告

    无 Key / 调用失败 / 解析失败时抛异常，由路由层转本地降级。
    ai_config 为生效配置（DB 覆盖 > env 默认），由路由层解析。
    """
    if ai_config is None:
        ai_config = AIConfig(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            model=settings.AI_MODEL,
        )
    prompt = _build_analyze_prompt(kind, mode)
    text = await chat_vision(frames, prompt, ai_config, max_tokens=2500)
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


# ==================== 分享文案生成 ====================

# 润色文案 LRU 缓存：同用户同输入命中直接返回，避免重复消耗 token
_CAPTION_CACHE_MAX = 20
_caption_cache: dict[str, str] = {}


def _caption_cache_key(template: str, style: str, text: str, context: dict) -> str:
    """生成润色文案缓存 key：MD5 摘要（template + style + text + 数据上下文）"""
    raw = f"{template}|{style}|{text}|{json.dumps(context, sort_keys=True)}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


STYLE_GUIDE = {
    "活泼": "活泼热情，多用 emoji 与感叹号，贴近小红书分享体，口语化有感染力",
    "简洁": "简洁克制，短句为主，少用 emoji，干净利落突出重点",
    "专业": "专业理性，使用网球技术术语，教练口吻，有数据有观点",
}


def build_caption_context(db: Session, user: User, template: str) -> dict:
    """按模板类型查库组装文案数据摘要（供 prompt 与本地降级共用）"""
    if template == "月度战报":
        month_key = datetime.now().strftime("%Y-%m")
        month_diaries = (
            db.query(Diary).filter(Diary.user_id == user.id, Diary.date.like(f"{month_key}%")).all()
        )
        total_minutes = sum(d.duration or 0 for d in month_diaries)
        total_cost = 0.0
        for d in month_diaries:
            for c in d.get_costs():
                total_cost += float(c.get("amount") or 0)
        return {
            "template": template,
            "month": str(int(month_key[5:])),
            "count": len(month_diaries),
            "total_hours": round(total_minutes / 60, 1),
            "total_minutes": total_minutes,
            "total_cost": round(total_cost, 2),
        }

    if template == "今日日记":
        diary = (
            db.query(Diary)
            .filter(Diary.user_id == user.id)
            .order_by(Diary.created_at.desc())
            .first()
        )
        return {
            "template": template,
            "diary": (
                {
                    "date": diary.date,
                    "type": diary.type,
                    "duration_minutes": diary.duration or 0,
                    "notes": diary.notes,
                }
                if diary
                else None
            ),
        }

    analysis = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .first()
    )
    report = {}
    if analysis and analysis.report:
        try:
            report = json.loads(analysis.report)
        except (ValueError, TypeError) as exc:
            logger.debug(f"分析报告 JSON 解析失败 analysis_id={analysis.id}: {exc}")
            report = {}
    dimensions = report.get("dimensions") or []
    best = max(
        dimensions,
        key=lambda d: float(d.get("score") or 0),
        default=None,
    )
    improvements = report.get("improvements") or []
    return {
        "template": template,
        "analysis": (
            {
                "kind": analysis.kind,
                "score": analysis.score or 0,
                "summary": analysis.summary or report.get("summary") or "",
                "best_dimension": (best.get("name") if best else None),
                "best_score": (best.get("score") if best else None),
                "next_improvement": (improvements[0].get("issue") if improvements else None),
            }
            if analysis
            else None
        ),
    }


def _fmt_money(n: float) -> str:
    return f"¥{int(n)}" if n % 1 == 0 else f"¥{n:.2f}"


def _fmt_duration(minutes: float) -> str:
    if minutes < 60:
        return f"{int(minutes)}分钟"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}小时{m}分" if m else f"{h}小时"


def build_local_caption(template: str, context: dict) -> str:
    """本地降级文案：与前端 genCaption 逻辑等价，AI 不可用时兜底"""
    if template == "月度战报":
        return (
            f"🎾 {context['month']}月网球月报\n\n"
            f"本月打球 {context['count']} 次，挥拍 {context['total_hours']} 小时，"
            f"投入 {_fmt_money(context['total_cost'])}。\n"
            "每一次上场都是和自己的对话，慢慢来，比较快。\n\n"
            "#网球 #网球日记 #运动打卡"
        )
    if template == "今日日记":
        diary = context.get("diary")
        if not diary:
            return "还没有日记，先去记一篇吧～"
        return (
            f"🎾 今日份网球\n\n{diary['date']} {diary['type']} "
            f"{_fmt_duration(diary['duration_minutes'])}\n"
            f"{diary['notes'] or '手感渐入佳境，继续加油！'}\n\n"
            "#网球 #网球日记 #网球初学者"
        )
    analysis = context.get("analysis")
    if not analysis:
        return "还没有分析报告，先去做一次分析吧～"
    line = f"🤖 教练给我的{analysis['kind']}打了 {analysis['score'] or '—'} 分！\n\n"
    line += f"{analysis['summary'] or ''}\n"
    if analysis.get("best_dimension"):
        line += f"最强项：{analysis['best_dimension']}（{analysis['best_score']}分）💪\n"
    if analysis.get("next_improvement"):
        line += f"下一步改进：{analysis['next_improvement']}\n"
    return line + "\n#网球 #教练 #网球技术 #网球日记"


def _build_caption_prompt(template: str, style: str, context: dict, text: str = "") -> str:
    """组装 AI 润色文案 prompt：在用户已有文案基础上结合数据润色"""
    data_desc = {
        "月度战报": "月度打球统计（次数/时长/花费）",
        "今日日记": "最新一篇日记（日期/类型/时长/笔记）",
        "技术评分": "AI 技术评分报告（类型/总分/总结/最强维度/改进项）",
    }[template]
    return (
        "你是一名网球运动社群文案创作者。请根据以下数据，对用户已有的分享文案进行润色改写。\n"
        f"模板类型：{template}（{data_desc}）\n"
        f"数据：{json.dumps(context, ensure_ascii=False)}\n"
        f"当前文案：{text or '（无）'}\n\n"
        f"风格要求：{STYLE_GUIDE[style]}\n"
        "要求：\n"
        "- 保留当前文案的核心意思和个人风格，润色优化表达\n"
        "- 结合提供的数据丰富内容，让文案更有说服力\n"
        "- 段落之间用空行分隔，总长 80-150 字\n"
        "- 结尾附 2-4 个话题标签（如 #网球 #网球日记 #运动打卡）\n"
        "- 只用中文，只输出润色后的文案正文，不要任何前后缀说明、标题或 JSON"
    )


async def generate_caption(
    template: str,
    style: str,
    context: dict,
    ai_config: AIConfig,
    text: str = "",
) -> str:
    """AI 文案润色：在已有文案基础上结合数据润色，返回文案字符串

    带 LRU 缓存：相同 template+style+text+context 直接返回缓存结果，
    避免重复调用 AI 消耗 token。无 Key / 调用失败 / 返回空时抛异常，由路由层转本地降级。
    """
    key = _caption_cache_key(template, style, text, context)
    if key in _caption_cache:
        logger.info(f"AI 文案润色命中缓存: template={template} style={style}")
        caption = _caption_cache.pop(key)  # 移到末尾（最近使用）
        _caption_cache[key] = caption
        return caption

    prompt = _build_caption_prompt(template, style, context, text)
    raw = await chat_text(prompt, ai_config, max_tokens=800)
    caption = raw.strip().strip("`")
    if not caption:
        raise RuntimeError("AI 文案润色结果为空")
    if len(_caption_cache) >= _CAPTION_CACHE_MAX:
        oldest_key = next(iter(_caption_cache))
        del _caption_cache[oldest_key]
    _caption_cache[key] = caption
    logger.info(f"AI 文案润色完成: template={template} style={style}")
    return caption
