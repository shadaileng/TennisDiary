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


# ==================== 接口测试：POST /api/ai/caption ====================


class TestCaption:
    """测试 /api/ai/caption"""

    VALID_PAYLOAD: ClassVar[dict] = {"template": "技术评分", "style": "活泼"}

    def test_caption_success(self, auth_client, test_db, monkeypatch):
        """调用成功 → 200 + 文案字符串，text 透传到 generate_caption"""
        from app.routers import ai as ai_router

        monkeypatch.setattr(settings, "AI_API_KEY", "sk-test")

        captured = {}

        async def fake_generate_caption(template, style, context, ai_config, text=""):
            captured["template"] = template
            captured["style"] = style
            captured["text"] = text
            return "🤖 润色后的文案 #网球 #网球日记"

        monkeypatch.setattr(ai_router.ai_service, "generate_caption", fake_generate_caption)
        payload = {**self.VALID_PAYLOAD, "text": "本月打了好多次球，超级开心！"}
        response = auth_client.post("/api/ai/caption", json=payload)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["caption"] == "🤖 润色后的文案 #网球 #网球日记"
        assert captured["template"] == "技术评分"
        assert captured["style"] == "活泼"
        assert captured["text"] == "本月打了好多次球，超级开心！"

    def test_caption_prompt_polish_style(self, monkeypatch):
        """有 text 时 prompt 指示润色已有文案；空 text 时标注（无）"""
        from app.services import ai_service

        context = {"template": "技术评分", "analysis": None}
        prompt_with_text = ai_service._build_caption_prompt("技术评分", "活泼", context, "已有文案")
        assert "润色改写" in prompt_with_text
        assert "当前文案：已有文案" in prompt_with_text
        prompt_empty = ai_service._build_caption_prompt("技术评分", "活泼", context, "")
        assert "当前文案：（无）" in prompt_empty

    def test_caption_monthly_context(self, auth_client, mock_user, test_db, monkeypatch):
        """月度战报 → build_caption_context 返回当月统计上下文"""
        from app.services import ai_service

        context = ai_service.build_caption_context(test_db, mock_user, "月度战报")
        assert context["template"] == "月度战报"
        assert "count" in context
        assert "total_hours" in context
        assert "total_cost" in context

    def test_caption_today_context_empty(self, auth_client, mock_user, test_db, monkeypatch):
        """今日日记无数据 → context.diary 为 None"""
        from app.services import ai_service

        context = ai_service.build_caption_context(test_db, mock_user, "今日日记")
        assert context["template"] == "今日日记"
        assert context["diary"] is None

    def test_caption_without_key_degrade(self, auth_client, test_db, monkeypatch):
        """无 AI_API_KEY → 200 + 本地降级文案"""
        monkeypatch.setattr(settings, "AI_API_KEY", "")
        response = auth_client.post("/api/ai/caption", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["caption"]
        assert "还没有分析报告" in data["caption"]

    def test_caption_service_error_degrade(self, auth_client, test_db, monkeypatch):
        """AI 调用异常 → 200 + 本地降级文案"""
        from app.routers import ai as ai_router

        async def boom(template, style, context, ai_config, text=""):
            raise RuntimeError("ai call failed")

        monkeypatch.setattr(ai_router.ai_service, "generate_caption", boom)
        response = auth_client.post("/api/ai/caption", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["caption"]

    def test_caption_invalid_template(self, auth_client):
        """非法模板 → 422"""
        response = auth_client.post("/api/ai/caption", json={"template": "未知", "style": "活泼"})
        assert response.status_code == 422

    def test_caption_invalid_style(self, auth_client):
        """非法风格 → 422"""
        response = auth_client.post(
            "/api/ai/caption", json={"template": "技术评分", "style": "文艺"}
        )
        assert response.status_code == 422

    def test_caption_requires_auth(self, client):
        """未登录 → 401/403"""
        response = client.post("/api/ai/caption", json=self.VALID_PAYLOAD)
        assert response.status_code in (401, 403)


# ==================== 服务层单测：本地降级文案 / 纯文本 chat ====================


class TestBuildLocalCaption:
    """ai_service.build_local_caption 本地模板文案"""

    def _build(self):
        from app.services import ai_service

        return ai_service.build_local_caption

    def test_monthly(self):
        """月度战报模板文案"""
        context = {
            "template": "月度战报",
            "month": "8",
            "count": 3,
            "total_hours": 4.5,
            "total_cost": 120,
        }
        text = self._build()("月度战报", context)
        assert "8月网球月报" in text
        assert "3 次" in text
        assert "4.5 小时" in text
        assert "¥120" in text
        assert "#网球" in text

    def test_today_no_diary(self):
        """今日日记无数据 → 占位文案"""
        text = self._build()("今日日记", {"template": "今日日记", "diary": None})
        assert "还没有日记" in text

    def test_today_with_diary(self):
        """今日日记有数据 → 含日期/类型/时长"""
        context = {
            "template": "今日日记",
            "diary": {
                "date": "2026-08-19",
                "type": "训练",
                "duration_minutes": 90,
                "notes": "手感很好",
            },
        }
        text = self._build()("今日日记", context)
        assert "2026-08-19" in text
        assert "训练" in text
        assert "1小时30分" in text
        assert "手感很好" in text

    def test_score_no_analysis(self):
        """技术评分无报告 → 占位文案"""
        text = self._build()("技术评分", {"template": "技术评分", "analysis": None})
        assert "还没有分析报告" in text

    def test_score_with_analysis(self):
        """技术评分有报告 → 含评分/最强项/改进项"""
        context = {
            "template": "技术评分",
            "analysis": {
                "kind": "正手",
                "score": 85,
                "summary": "发力流畅",
                "best_dimension": "动力链",
                "best_score": 90,
                "next_improvement": "反手稳定性",
            },
        }
        text = self._build()("技术评分", context)
        assert "85" in text
        assert "动力链" in text
        assert "90分" in text
        assert "反手稳定性" in text


class TestChatText:
    """ai_service.chat_text 纯文本调用请求体"""

    def test_payload_no_images(self, monkeypatch):
        """chat_text 请求 content 为文本（无 image_url）"""
        import asyncio

        from app.services import ai_service

        captured = {}

        async def fake_post(payload, ai_config):
            captured["payload"] = payload
            return "生成的文案"

        monkeypatch.setattr(ai_service, "_post_completions", fake_post)
        ai_config = ai_service.AIConfig(
            api_key="sk-test", base_url="https://x/v1", model="qwen-plus"
        )
        text = asyncio.run(ai_service.chat_text("prompt", ai_config))
        assert text == "生成的文案"
        content = captured["payload"]["messages"][0]["content"]
        assert isinstance(content, list)
        assert content == [{"type": "text", "text": "prompt"}]


class TestCaptionCache:
    """ai_service.generate_caption LRU 缓存"""

    def _make_ai_config(self):
        from app.services import ai_service

        return ai_service.AIConfig(api_key="sk-test", base_url="https://x/v1", model="qwen-plus")

    def _clear_cache(self):
        from app.services import ai_service

        ai_service._caption_cache.clear()

    def test_cache_hit_skips_ai_call(self, monkeypatch):
        """相同参数第二次调用 → 命中缓存，chat_text 不再被调用"""
        import asyncio

        from app.services import ai_service

        self._clear_cache()

        async def fake_post(payload, ai_config):
            return "润色文案 A"

        monkeypatch.setattr(ai_service, "_post_completions", fake_post)
        ai_config = self._make_ai_config()
        context = {"template": "技术评分", "analysis": None}

        text1 = asyncio.run(
            ai_service.generate_caption("技术评分", "活泼", context, ai_config, "原文案")
        )
        text2 = asyncio.run(
            ai_service.generate_caption("技术评分", "活泼", context, ai_config, "原文案")
        )
        assert text1 == "润色文案 A"
        assert text2 == "润色文案 A"
        assert len(ai_service._caption_cache) == 1

    def test_cache_miss_different_text(self, monkeypatch):
        """text 不同 → 缓存未命中，chat_text 被调用两次"""
        import asyncio

        from app.services import ai_service

        self._clear_cache()
        calls = {"n": 0}

        async def fake_post(payload, ai_config):
            calls["n"] += 1
            return "润色文案"

        monkeypatch.setattr(ai_service, "_post_completions", fake_post)
        ai_config = self._make_ai_config()
        context = {"template": "技术评分", "analysis": None}

        asyncio.run(ai_service.generate_caption("技术评分", "活泼", context, ai_config, "原文案 A"))
        asyncio.run(ai_service.generate_caption("技术评分", "活泼", context, ai_config, "原文案 B"))
        assert calls["n"] == 2

    def test_cache_miss_different_style(self, monkeypatch):
        """style 不同 → 缓存未命中"""
        import asyncio

        from app.services import ai_service

        self._clear_cache()
        calls = {"n": 0}

        async def fake_post(payload, ai_config):
            calls["n"] += 1
            return "润色文案"

        monkeypatch.setattr(ai_service, "_post_completions", fake_post)
        ai_config = self._make_ai_config()
        context = {"template": "技术评分", "analysis": None}

        asyncio.run(ai_service.generate_caption("技术评分", "活泼", context, ai_config, "原文案"))
        asyncio.run(ai_service.generate_caption("技术评分", "简洁", context, ai_config, "原文案"))
        assert calls["n"] == 2

    def test_cache_eviction_max(self, monkeypatch):
        """超过容量 → 淘汰最旧条目，缓存大小 ≤ 20"""
        import asyncio

        from app.services import ai_service

        self._clear_cache()

        async def fake_post(payload, ai_config):
            return "润色文案"

        monkeypatch.setattr(ai_service, "_post_completions", fake_post)
        ai_config = self._make_ai_config()
        context = {"template": "技术评分", "analysis": None}

        keys = []
        for i in range(21):
            asyncio.run(
                ai_service.generate_caption("技术评分", "活泼", context, ai_config, f"原文案 {i}")
            )
            keys.append(ai_service._caption_cache_key("技术评分", "活泼", f"原文案 {i}", context))
        assert len(ai_service._caption_cache) <= 20
        assert keys[0] not in ai_service._caption_cache

    def test_cache_key_stability(self):
        """相同输入生成相同 key；不同输入生成不同 key"""
        from app.services import ai_service

        context = {"template": "技术评分", "analysis": None}
        k1 = ai_service._caption_cache_key("技术评分", "活泼", "原文案", context)
        k2 = ai_service._caption_cache_key("技术评分", "活泼", "原文案", context)
        k3 = ai_service._caption_cache_key("技术评分", "活泼", "原文案 X", context)
        assert k1 == k2
        assert k1 != k3
