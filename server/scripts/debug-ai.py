"""AI 模型调试脚本：直接打生效配置的模型，绕开小程序

生效配置解析与服务端一致（DB 服务商引用/覆盖 > env 默认），
`--model` / `--base-url` / `--api-key` 可临时覆盖（CLI 优先）。

用法：
    uv run python scripts/debug-ai.py                 # 等价 --chat ping（最小探测）
    uv run python scripts/debug-ai.py --chat          # 最小文本探测（ping）
    uv run python scripts/debug-ai.py --chat "你好"    # 任意文本对话（原始输出）
    uv run python scripts/debug-ai.py --models        # GET {base_url}/models 列出可用模型
    uv run python scripts/debug-ai.py --analyze --image a.jpg --image b.jpg \
        --kind 正手 --mode single
    uv run python scripts/debug-ai.py --chat --model agnes-2.5-flash \
        --base-url https://api.agnes-ai.cn/v1 --api-key sk-xxx

退出码：0 成功；1 失败。与生产不同：这里不吞错，非 200 直接打印真实响应。
"""

import argparse
import asyncio
import base64
import json
import mimetypes
import sys
import time
from pathlib import Path

# 使 app 包可从任意目录运行（python scripts/debug-ai.py 时 sys.path[0] 是 scripts/）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.services import ai_service
from app.services.config_service import AIConfig, mask_secret

TIMEOUT_SECONDS = 60


# ==================== 纯函数（可单测） ====================


def build_data_url(path: Path) -> str:
    """读取图片为 base64 dataURL（与小程序上传帧格式一致）"""
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    raw = path.read_bytes()
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def parse_available_models(data: dict) -> list[str]:
    """从 OpenAI 兼容 /models 响应解析可用模型 ID（data[]/models[]，取 id/name/字符串）"""
    payload = data.get("data") if isinstance(data.get("data"), list) else None
    if payload is None:
        payload = data.get("models") if isinstance(data.get("models"), list) else None
    available: list[str] = []
    for item in payload or []:
        if isinstance(item, str):
            available.append(item)
        elif isinstance(item, dict):
            name = item.get("id") or item.get("name")
            if name:
                available.append(str(name))
    return available


# ==================== 配置解析 ====================


def load_effective_config(args: argparse.Namespace) -> AIConfig:
    """生效配置：DB（get_ai_config，与服务端一致）> env；CLI 参数再覆盖"""
    try:
        from app.core.database import SessionLocal
        from app.services.config_service import get_ai_config

        with SessionLocal() as db:
            cfg = get_ai_config(db)
    except Exception as exc:  # noqa: BLE001 - 空库等场景回落 env 配置
        from app.core.config import settings

        print(f"[提示] 读取数据库配置失败（{exc!s}），回落环境变量配置", file=sys.stderr)
        cfg = AIConfig(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            model=settings.AI_MODEL,
        )
    return AIConfig(
        api_key=args.api_key or cfg.api_key,
        base_url=(args.base_url or cfg.base_url).rstrip("/"),
        model=args.model or cfg.model,
        provider="CLI 覆盖" if args.model or args.base_url or args.api_key else cfg.provider,
    )


def print_effective(cfg: AIConfig) -> None:
    """打印生效配置摘要（key 掩码）"""
    print("── 生效配置 ───────────────────────────────────────")
    print(f"  base_url : {cfg.base_url}")
    print(f"  model    : {cfg.model}")
    print(f"  provider : {cfg.provider}")
    print(f"  api_key  : {mask_secret(cfg.api_key) or '（未配置）'}")
    print("──────────────────────────────────────────────────")


# ==================== 动作 ====================


async def chat(cfg: AIConfig, text: str, max_tokens: int = 1024) -> int:
    """文本对话（默认 ping 最小探测）"""
    payload = {
        "model": cfg.model,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": text}],
    }
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    url = f"{cfg.base_url}/chat/completions"
    print(f"[请求] POST {url}  model={cfg.model}")
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.post(url, headers=headers, json=payload)
    cost = time.monotonic() - start
    if resp.status_code == 200:
        data = resp.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        usage = data.get("usage") or {}
        print(f"[成功] HTTP 200（{cost:.2f}s）tokens={usage}")
        print(content)
        return 0
    print(f"[失败] HTTP {resp.status_code}（{cost:.2f}s）")
    print((resp.text or "")[:500])
    return 1


async def list_models(cfg: AIConfig) -> int:
    """GET {base_url}/models 列出可用模型"""
    headers = {}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    url = f"{cfg.base_url}/models"
    print(f"[请求] GET {url}")
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.get(url, headers=headers)
    cost = time.monotonic() - start
    if resp.status_code == 200:
        try:
            available = parse_available_models(resp.json())
        except ValueError:
            available = []
        print(f"[成功] HTTP 200（{cost:.2f}s）可用模型 {len(available)} 个：")
        for m in available:
            print(f"  - {m}")
        return 0
    print(f"[失败] HTTP {resp.status_code}（{cost:.2f}s）")
    print(f"该服务商不支持 GET /models 列表接口（{resp.text[:200]}），可用 --chat 逐模型探测")
    return 1


async def analyze(cfg: AIConfig, args: argparse.Namespace) -> int:
    """完整六维分析：本地图片 → dataURL → 走生产同款 analyze_swing 链路"""
    if not args.image:
        print("缺少图片：--analyze 需要至少一个 --image <路径>", file=sys.stderr)
        return 1
    try:
        frames = [build_data_url(Path(p)) for p in args.image]
    except FileNotFoundError as exc:
        print(f"图片不存在: {exc}", file=sys.stderr)
        return 1
    print(f"[请求] analyze_swing kind={args.kind} mode={args.mode} frames={len(frames)}")
    start = time.monotonic()
    try:
        report = await ai_service.analyze_swing(frames, args.kind, args.mode, cfg)
    except Exception as exc:  # noqa: BLE001 - 打印真实错误
        print(f"[失败] 分析异常：{exc!s}")
        return 1
    cost = time.monotonic() - start
    print(f"[成功] 分析完成（{cost:.2f}s）score={report.get('score')} ntrp={report.get('ntrp')}")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 模型调试脚本")
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--chat",
        nargs="?",
        const="ping",
        metavar="TEXT",
        help="文本对话；不带参数 = 最小探测（ping）",
    )
    action.add_argument("--models", action="store_true", help="GET {base_url}/models 列出可用模型")
    action.add_argument(
        "--analyze",
        action="store_true",
        help="完整六维分析（图片 → dataURL → 生产同款链路）",
    )
    parser.add_argument("--image", action="append", metavar="PATH", help="分析用图片（可多次）")
    parser.add_argument("--kind", default="正手", help="动作类型（默认 正手）")
    parser.add_argument("--mode", default="single", choices=["single", "full"], help="分析模式")
    parser.add_argument("--model", help="临时覆盖模型名")
    parser.add_argument("--base-url", help="临时覆盖接口地址")
    parser.add_argument("--api-key", help="临时覆盖 API Key")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    cfg = load_effective_config(args)
    if not cfg.api_key:
        print("未配置 API Key（DB/服务商/env/CLI 均无），无法请求", file=sys.stderr)
        return 1
    print_effective(cfg)
    if args.models:
        return await list_models(cfg)
    if args.analyze:
        return await analyze(cfg, args)
    return await chat(cfg, args.chat or "ping", max_tokens=1 if not args.chat else 1024)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
