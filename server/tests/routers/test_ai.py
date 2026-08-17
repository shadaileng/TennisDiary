"""POST /api/ai/analyze AI 评分代理接口测试"""

from typing import ClassVar

import pytest

from app.core.config import settings

# ==================== 服务层单测：extract_json / build_local_report ====================


class TestExtractJson:
    """ai_service.extract_json 容错解析"""

    def _extract(self):
        from app.services import ai_service

        return ai_service.extract_json

    def test_extract_pure_json(self):
        """纯 JSON 字符串 → 正常解析"""
        report = self._extract()('{"score": 80, "summary": "ok"}')
        assert report["score"] == 80

    def test_extract_with_surrounding_text(self):
        """AI 返回带前后缀文字 → 提取 JSON 部分"""
        raw = '好的，以下是分析结果：```json\n{"score": 75, "summary": "不错"}\n``` 希望对你有帮助'
        report = self._extract()(raw)
        assert report["score"] == 75
        assert report["summary"] == "不错"

    def test_extract_invalid(self):
        """非法 JSON → 抛 ValueError"""
        with pytest.raises(ValueError):
            self._extract()("这不是 JSON")


class TestBuildLocalReport:
    """ai_service.build_local_report 降级报告"""

    def _build(self):
        from app.services import ai_service

        return ai_service.build_local_report

    def test_structure(self):
        """降级报告结构完整：score=0 + 说明"""
        report = self._build()("正手")
        assert report["score"] == 0
        assert report["summary"]
        assert "配置 AI" in report["summary"] or "AI" in report["summary"]
        assert isinstance(report["dimensions"], list)
        assert report["dimensions"] == []
        assert isinstance(report["strengths"], list)
        assert isinstance(report["improvements"], list)
        assert report["rhythm"]


# ==================== 接口测试：POST /api/ai/analyze ====================


class TestAnalyze:
    """测试 /api/ai/analyze"""

    VALID_PAYLOAD: ClassVar[dict] = {
        "frames": ["data:image/jpeg;base64,/9j/4AAQSkZJRg==", "/9j/4AAQSkZJRg=="],
        "kind": "正手",
        "mode": "single",
    }

    FULL_REPORT: ClassVar[dict] = {
        "score": 76,
        "summary": "整体发力流畅，重心稳定",
        "ntrp": "3.5",
        "dimensions": [
            {"name": "准备启动", "score": 70, "comment": "引拍稍慢"},
            {"name": "动力链", "score": 80, "comment": "蹬转发力充分"},
            {"name": "击球时机", "score": 75, "comment": "击球点略靠后"},
            {"name": "随挥收拍", "score": 78, "comment": "收拍完整"},
            {"name": "拍面控制", "score": 72, "comment": "拍面略开"},
            {"name": "身体稳定", "score": 81, "comment": "重心保持良好"},
        ],
        "rhythm": "整体节奏稳定，击球前有短暂停顿",
        "strengths": ["动力链连贯", "重心控制好"],
        "improvements": [{"issue": "引拍慢", "advice": "提前判断来球轨迹"}],
    }

    def test_analyze_success(self, auth_client, monkeypatch):
        """调用成功 → 200 + 六维报告"""
        from app.routers import ai as ai_router

        monkeypatch.setattr(settings, "AI_API_KEY", "sk-test")

        async def fake_analyze_swing(frames, kind, mode, ai_config):
            return self.FULL_REPORT

        monkeypatch.setattr(ai_router.ai_service, "analyze_swing", fake_analyze_swing)
        response = auth_client.post("/api/ai/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["score"] == 76
        assert len(data["dimensions"]) == 6

    def test_analyze_uses_db_override(self, auth_client, test_db, monkeypatch):
        """DB 覆盖生效：analyze_swing 收到覆盖后的 model / base_url"""
        from app.routers import ai as ai_router
        from app.services import config_service

        monkeypatch.setattr(settings, "AI_API_KEY", "sk-env-key")
        monkeypatch.setattr(settings, "AI_BASE_URL", "https://default.example.com/v1")
        config_service.set_config_value(test_db, "ai.model", "qwen-vl-plus", admin_id=1)
        config_service.set_config_value(
            test_db, "ai.base_url", "https://custom.example.com/v1", admin_id=1
        )

        captured = {}

        async def fake_analyze_swing(frames, kind, mode, ai_config):
            captured["model"] = ai_config.model
            captured["base_url"] = ai_config.base_url
            captured["api_key"] = ai_config.api_key
            return self.FULL_REPORT

        monkeypatch.setattr(ai_router.ai_service, "analyze_swing", fake_analyze_swing)
        response = auth_client.post("/api/ai/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        assert captured["model"] == "qwen-vl-plus"
        assert captured["base_url"] == "https://custom.example.com/v1"
        assert captured["api_key"] == "sk-env-key"

    def test_analyze_without_key_degrade(self, auth_client, monkeypatch):
        """无 AI_API_KEY → 200 + score=0 降级报告（不发起网络请求）"""
        monkeypatch.setattr(settings, "AI_API_KEY", "")
        response = auth_client.post("/api/ai/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["score"] == 0
        assert data["dimensions"] == []

    def test_analyze_service_error_degrade(self, auth_client, monkeypatch):
        """AI 调用异常 → 200 + score=0 降级报告"""
        from app.routers import ai as ai_router

        async def boom(frames, kind, mode, ai_config):
            raise RuntimeError("ai call failed")

        monkeypatch.setattr(ai_router.ai_service, "analyze_swing", boom)
        response = auth_client.post("/api/ai/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["score"] == 0

    def test_analyze_requires_auth(self, client):
        """未登录 → 401/403"""
        response = client.post("/api/ai/analyze", json=self.VALID_PAYLOAD)
        assert response.status_code in (401, 403)
