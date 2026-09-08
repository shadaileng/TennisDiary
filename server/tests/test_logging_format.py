"""日志格式规范测试（139 Step 6，目标 G1）

loguru 使用 `str.format()` 语义（`{}` 风格），**不支持** printf 的 `%s`：
传入的位置参数会被静默丢弃，日志里只剩 `未替换的 %s 占位符`，
导致真实异常被吞掉（139 故障中 `app.log:7203` 即为如此）。

本测试锁定规范：
1. 源码中不得再出现 printf 风格的日志调用（`%s` / `%d` 等）
2. 运行时不得输出含未替换 `%s` 的日志
"""

import re
from pathlib import Path

import pytest

from app.core.logging import logger

pytestmark = pytest.mark.fast

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# 匹配日志调用中的 printf 占位符（%s / %d / %.2f 等）
PRINTF_PATTERN = re.compile(r"%[-+ #0]*[0-9]*(\.[0-9]+)?[sdifFeEgGxXoc]")

# 日志调用起始（log.xxx( / logger.xxx(）
LOG_CALL_PATTERN = re.compile(
    r"\b(?:log|logger)\.(?:trace|debug|info|success|warning|error|critical|exception)\s*\("
)


def _iter_log_call_blocks(lines: list[str]):
    """提取日志调用块：从 `log.xxx(` 起到括号配对闭合

    多行调用（格式串在后续行）也能完整覆盖，例如：
        log.exception(
            "管线失败 analysis_id={}",
            self.analysis_id,
        )
    """
    start: int | None = None
    depth = 0
    for idx, line in enumerate(lines, start=1):
        if start is None:
            if LOG_CALL_PATTERN.search(line):
                depth = line.count("(") - line.count(")")
                if depth <= 0:
                    yield idx, [line]
                else:
                    start = idx
        else:
            depth += line.count("(") - line.count(")")
            if depth <= 0:
                yield start, lines[start - 1 : idx]
                start = None
                depth = 0


class _CaptureSink:
    """捕获日志消息的 sink"""

    def __init__(self):
        self.messages: list[str] = []

    def __call__(self, message):
        self.messages.append(str(message))

    def __enter__(self):
        self._handler_id = logger.add(self, format="{message}", level="DEBUG")
        return self

    def __exit__(self, *_exc):
        logger.remove(self._handler_id)


class TestNoPrintfStyleLogs:
    """源码与运行时均不得出现 printf 风格日志"""

    def test_source_has_no_printf_placeholders(self):
        """日志调用中不得使用 %s / %d 等 printf 占位符

        只检查**日志调用块**（`log.xxx(...)` / `logger.xxx(...)`），避免误伤
        `strftime("%Y-%m-%d")` 与 ffmpeg 图片序列通配符 `_sk%04d.jpg` 等
        非日志场景。
        """
        offenders: list[str] = []

        for py_file in APP_DIR.rglob("*.py"):
            lines = py_file.read_text(encoding="utf-8").splitlines()
            for lineno, block in _iter_log_call_blocks(lines):
                text = "\n".join(block)
                if PRINTF_PATTERN.search(text):
                    offenders.append(f"{py_file.relative_to(APP_DIR)}:{lineno}: {block[0].strip()}")

        assert not offenders, (
            "发现 printf 风格日志（loguru 不支持 %s，参数会被静默丢弃，请改用 {}）：\n"
            + "\n".join(offenders)
        )

    def test_runtime_log_does_not_contain_raw_placeholder(self):
        """运行时日志不得输出未替换的 %s 占位符

        模拟旧写法 `logger.warning("失败: %s - %s", a, b)`：
        loguru 会原样输出模板，真实值丢失——这正是 139 故障中异常被吞的原因。
        本用例确认新写法（{}）能正确替换，且不会产生裸占位符。
        """
        with _CaptureSink() as sink:
            logger.warning("旧写法模拟: %s - %s", "ARG1", "ARG2")
            logger.warning("新写法: {} - {}", "ARG1", "ARG2")

        rendered = "\n".join(sink.messages)

        # 新写法必须正确替换
        assert "新写法: ARG1 - ARG2" in rendered
        # 旧写法会保留裸 %s（文档化的反例，证明为何禁用）
        assert "旧写法模拟: %s - %s" in rendered

        # 关键：除刻意模拟的旧写法外，不得有其他裸占位符
        unexpected = [line for line in sink.messages if "%s" in line and "旧写法模拟" not in line]
        assert not unexpected, f"日志中出现未替换的 %s 占位符: {unexpected}"
