"""调试脚本 scripts/debug-ai.py 纯函数单测（dataURL 构建 + /models 解析）"""

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "debug-ai.py"


@pytest.fixture(scope="module")
def debug_ai():
    spec = importlib.util.spec_from_file_location("debug_ai_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBuildDataUrl:
    def test_data_url_prefix_and_base64(self, debug_ai, tmp_path):
        img = tmp_path / "shot.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\nraw")
        url = debug_ai.build_data_url(img)
        import base64

        assert url.startswith("data:image/png;base64,")
        decoded = base64.b64decode(url.split(",", 1)[1])
        assert decoded == b"\x89PNG\r\n\x1a\nraw"

    def test_unknown_ext_mime_from_mimetypes(self, debug_ai, tmp_path):
        img = tmp_path / "frame.bin"
        img.write_bytes(b"abc")
        url = debug_ai.build_data_url(img)
        assert url.startswith("data:application/octet-stream;base64,")


class TestParseAvailableModels:
    def test_openai_data_objects(self, debug_ai):
        data = {"data": [{"id": "agnes-2.5-flash"}, {"id": "agnes-2.0-flash"}]}
        assert debug_ai.parse_available_models(data) == [
            "agnes-2.5-flash",
            "agnes-2.0-flash",
        ]

    def test_flat_strings(self, debug_ai):
        data = {"models": ["model-a", "model-b"]}
        assert debug_ai.parse_available_models(data) == ["model-a", "model-b"]

    def test_name_fallback_and_unparseable(self, debug_ai):
        assert debug_ai.parse_available_models({"data": [{"name": "x"}]}) == ["x"]
        assert debug_ai.parse_available_models({"unexpected": True}) == []
