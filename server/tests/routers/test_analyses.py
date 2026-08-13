"""用户端分析报告落库与历史查询接口测试（GET/POST/DELETE /api/analyses）"""

from typing import ClassVar

# ==================== 接口测试：POST /api/analyses ====================


class TestCreateAnalysis:
    """测试 POST /api/analyses 落库"""

    VALID_PAYLOAD: ClassVar[dict] = {
        "date": "2026-08-13",
        "kind": "正手",
        "mode": "single",
        "score": 76,
        "summary": "整体发力流畅，重心稳定",
        "ntrp": "3.5",
        "report": {
            "score": 76,
            "summary": "整体发力流畅",
            "ntrp": "3.5",
            "dimensions": [
                {"name": "准备启动", "score": 70, "comment": "引拍稍慢"},
                {"name": "动力链", "score": 80, "comment": "蹬转发力充分"},
                {"name": "击球时机", "score": 75, "comment": "击球点略靠后"},
                {"name": "随挥收拍", "score": 78, "comment": "收拍完整"},
                {"name": "拍面控制", "score": 72, "comment": "拍面略开"},
                {"name": "身体稳定", "score": 81, "comment": "重心保持良好"},
            ],
            "rhythm": "整体节奏稳定",
            "strengths": ["动力链连贯"],
            "improvements": [{"issue": "引拍慢", "advice": "提前判断来球"}],
        },
        "thumb": "videos/abc_f0.jpg",
        "highlights": ["videos/abc_f1.jpg"],
        "video_url": "videos/abc.mp4",
    }

    def test_create_success(self, auth_client):
        """落库成功 → 200 + id/score/ntrp/video_url，DB 可查"""
        response = auth_client.post("/api/analyses", json=self.VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] > 0
        assert data["score"] == 76
        assert data["ntrp"] == "3.5"
        assert data["video_url"] == "videos/abc.mp4"
        assert data["user_id"] == 1

    def test_create_report_full_dimensions(self, auth_client):
        """report 含完整六维 → dimensions 长度 6"""
        response = auth_client.post("/api/analyses", json=self.VALID_PAYLOAD)
        data = response.json()["data"]
        assert len(data["report"]["dimensions"]) == 6

    def test_create_requires_auth(self, client):
        """未登录 → 401/403"""
        response = client.post("/api/analyses", json=self.VALID_PAYLOAD)
        assert response.status_code in (401, 403)


# ==================== 接口测试：GET /api/analyses ====================


class TestListAnalyses:
    """测试 GET /api/analyses 历史列表"""

    def _create(self, auth_client, date="2026-08-13", kind="正手", score=76):
        payload = {
            "date": date,
            "kind": kind,
            "mode": "single",
            "score": score,
            "summary": f"summary-{date}",
            "report": {
                "score": score,
                "summary": f"summary-{date}",
                "dimensions": [],
                "rhythm": "",
                "strengths": [],
                "improvements": [],
            },
        }
        return auth_client.post("/api/analyses", json=payload).json()["data"]

    def test_list_success(self, auth_client):
        """列表 → 200 + items 按 created_at 倒序 + total"""
        self._create(auth_client, date="2026-08-13", score=76)
        self._create(auth_client, date="2026-08-12", score=80)
        response = auth_client.get("/api/analyses")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 2
        assert len(data["items"]) == 2
        # 后创建的在前（倒序）
        assert data["items"][0]["id"] >= data["items"][1]["id"]

    def test_list_pagination(self, auth_client):
        """分页 offset/limit → 返回对应子集 + total"""
        for i in range(3):
            self._create(auth_client, date=f"2026-08-{10 + i}", score=70 + i)
        response = auth_client.get("/api/analyses?offset=1&limit=1")
        data = response.json()["data"]
        assert data["total"] == 3
        assert len(data["items"]) == 1

    def test_list_only_own(self, auth_client, test_db):
        """仅返回当前用户（mock_user.id=1）的数据"""
        from app.models.analysis import Analysis

        other = Analysis(
            user_id=999,
            date="2026-08-13",
            kind="正手",
            mode="single",
            score=90,
            summary="别人的",
            report=None,
            created_at=1.0,
        )
        test_db.add(other)
        test_db.commit()
        response = auth_client.get("/api/analyses")
        data = response.json()["data"]
        assert all(item["user_id"] == 1 for item in data["items"])
        assert data["total"] == 0  # 自己没有任何记录

    def test_list_requires_auth(self, client):
        """未登录 → 401/403"""
        response = client.get("/api/analyses")
        assert response.status_code in (401, 403)


# ==================== 接口测试：GET /api/analyses/{id} ====================


class TestGetAnalysis:
    """测试 GET /api/analyses/{id} 详情"""

    def _create(self, auth_client):
        payload = {
            "date": "2026-08-13",
            "kind": "正手",
            "mode": "single",
            "score": 76,
            "summary": "整体发力流畅",
            "report": {
                "score": 76,
                "summary": "整体发力流畅",
                "dimensions": [],
                "rhythm": "节奏稳定",
                "strengths": [],
                "improvements": [],
            },
            "video_url": "videos/abc.mp4",
        }
        return auth_client.post("/api/analyses", json=payload).json()["data"]

    def test_get_detail(self, auth_client):
        """详情 → 200 + report 结构化 JSON"""
        created = self._create(auth_client)
        response = auth_client.get(f"/api/analyses/{created['id']}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["report"]["score"] == 76
        assert data["report"]["rhythm"] == "节奏稳定"
        assert data["video_url"] == "videos/abc.mp4"

    def test_get_not_found(self, auth_client):
        """不存在 → 404"""
        response = auth_client.get("/api/analyses/99999")
        assert response.status_code == 404

    def test_get_others_forbidden(self, auth_client, test_db):
        """他人记录越权 → 404"""
        from app.models.analysis import Analysis

        other = Analysis(
            user_id=999,
            date="2026-08-13",
            kind="正手",
            mode="single",
            score=90,
            summary="别人的",
            report=None,
            created_at=1.0,
        )
        test_db.add(other)
        test_db.commit()
        response = auth_client.get(f"/api/analyses/{other.id}")
        assert response.status_code == 404

    def test_get_requires_auth(self, client):
        """未登录 → 401/403"""
        response = client.get("/api/analyses/1")
        assert response.status_code in (401, 403)


# ==================== 接口测试：DELETE /api/analyses/{id} ====================


class TestDeleteAnalysis:
    """测试 DELETE /api/analyses/{id}"""

    def _create(self, auth_client):
        payload = {
            "date": "2026-08-13",
            "kind": "正手",
            "mode": "single",
            "score": 76,
            "summary": "整体发力流畅",
        }
        return auth_client.post("/api/analyses", json=payload).json()["data"]

    def test_delete_success(self, auth_client):
        """删除成功 → 200 + 再查 404"""
        created = self._create(auth_client)
        response = auth_client.delete(f"/api/analyses/{created['id']}")
        assert response.status_code == 200
        detail = auth_client.get(f"/api/analyses/{created['id']}")
        assert detail.status_code == 404

    def test_delete_others_forbidden(self, auth_client, test_db):
        """他人记录越权删除 → 404"""
        from app.models.analysis import Analysis

        other = Analysis(
            user_id=999,
            date="2026-08-13",
            kind="正手",
            mode="single",
            score=90,
            summary="别人的",
            report=None,
            created_at=1.0,
        )
        test_db.add(other)
        test_db.commit()
        response = auth_client.delete(f"/api/analyses/{other.id}")
        assert response.status_code == 404

    def test_delete_not_found(self, auth_client):
        """不存在 → 404"""
        response = auth_client.delete("/api/analyses/99999")
        assert response.status_code == 404

    def test_delete_requires_auth(self, client):
        """未登录 → 401/403"""
        response = client.delete("/api/analyses/1")
        assert response.status_code in (401, 403)
