"""extract_json 单元测试（纯函数，标记 fast）"""

import json

import pytest

from app.services.ai_service import extract_json

pytestmark = pytest.mark.fast


class TestExtractJson:
    """extract_json 容错解析测试"""

    def test_normal_json(self):
        """直接返回合法 JSON"""
        text = '{"score": 80, "summary": "good"}'
        assert extract_json(text) == {"score": 80, "summary": "good"}

    def test_json_in_markdown_code_block(self):
        """从 markdown 代码块中提取 JSON"""
        text = '```json\n{"score": 75, "summary": "ok"}\n```'
        assert extract_json(text) == {"score": 75, "summary": "ok"}

    def test_json_with_surrounding_text(self):
        """前后缀文字不影响提取"""
        text = '以下是分析结果：\n{"score": 70, "summary": "不错"}\n以上。'
        assert extract_json(text) == {"score": 70, "summary": "不错"}

    def test_repair_missing_comma(self):
        """json-repair 修复缺失逗号"""
        text = '{"a": 1 "b": 2}'
        result = extract_json(text)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_repair_trailing_comma(self):
        """json-repair 修复 trailing comma"""
        text = '{"score": 80, "summary": "ok",}'
        result = extract_json(text)
        assert result["score"] == 80

    def test_repair_unescaped_quotes_in_string(self):
        """json-repair 修复字符串内未转义引号"""
        text = '{"summary": "他说"你好""}'
        result = extract_json(text)
        assert "summary" in result

    def test_unrepairable_no_braces_raises(self):
        """不含花括号的非法文本抛出 ValueError"""
        with pytest.raises(ValueError, match="无法解析"):
            extract_json("这根本不是JSON也没有花括号")

    def test_no_json_at_all_raises(self):
        """不含任何 {} 的文本抛出 ValueError"""
        with pytest.raises(ValueError, match="无法解析"):
            extract_json("hello world no braces here")

    def test_complex_nested_json(self):
        """复杂嵌套 JSON 正常解析"""
        data = {
            "score": 64,
            "summary": "动作框架完整流畅",
            "ntrp": "3.0",
            "dimensions": [{"name": "准备启动", "score": 75, "comment": "不错"}],
            "strengths": ["亮点1"],
            "improvements": [{"issue": "问题", "advice": "建议"}],
        }
        text = json.dumps(data, ensure_ascii=False)
        assert extract_json(text) == data
