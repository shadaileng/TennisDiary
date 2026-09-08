"""POST /api/analyses/start 凭 file_id 启动分析（137 阶段一 Step 4）

覆盖：正常启动并触发管线 / 返回 file_id / 他人 file_id 越权 404 /
物理文件缺失 404 / 非 video 来源 404 / 未登录 401。
"""

import io

from app.models.analysis import Analysis
from app.services import file_service

VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


class TestAnalysisStart:
    @staticmethod
    def _upload_video(client, content: bytes = VIDEO_BYTES, filename: str = "clip.mp4"):
        resp = client.post(
            "/api/upload/video",
            files={"file": (filename, io.BytesIO(content), "video/mp4")},
        )
        assert resp.status_code == 200
        return resp.json()["data"]

    @staticmethod
    def _register_file(test_db, user_id: int, content: bytes, category: str, ext: str):
        record, _ = file_service.register(
            db=test_db,
            user_id=user_id,
            content=content,
            category=category,
            original_name=f"sample{ext}",
            ext=ext,
        )
        test_db.commit()
        return record

    def _start(self, client, file_id: int, **extra):
        payload = {"file_id": file_id, "date": "2026-09-08", "kind": "正手", "mode": "single"}
        payload.update(extra)
        return client.post("/api/analyses/start", json=payload)

    def test_start_success_triggers_pipeline(self, auth_client, test_db, monkeypatch):
        calls: list[tuple] = []
        monkeypatch.setattr(
            "app.routers.analyses._run_analysis_pipeline",
            lambda analysis_id, video_path, metadata: calls.append(
                (analysis_id, video_path, metadata)
            ),
        )
        data = self._upload_video(auth_client)

        resp = self._start(auth_client, data["file_id"], hit_time=1.5)
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["id"] > 0
        assert body["status"] == "processing"
        assert body["file_id"] == data["file_id"]
        assert body["pipeline_status"]["step"] == "init"

        # 后台管线被触发，且携带受管视频绝对路径
        assert len(calls) == 1
        analysis_id, video_path, metadata = calls[0]
        assert analysis_id == body["id"]
        assert video_path == file_service.abs_of(data["url"])
        assert metadata["kind"] == "正手"
        assert metadata["hit_time"] == 1.5

        analysis = test_db.query(Analysis).filter(Analysis.id == body["id"]).first()
        assert analysis is not None
        assert analysis.status == "processing"

    def test_start_binds_video_file(self, auth_client, test_db, monkeypatch):
        """启动后源文件绑定到该分析（ref_count +1）"""
        monkeypatch.setattr(
            "app.routers.analyses._run_analysis_pipeline",
            lambda *args, **kwargs: None,
        )
        data = self._upload_video(auth_client)
        body = self._start(auth_client, data["file_id"]).json()["data"]

        test_db.expire_all()
        record = file_service.find_by_id(test_db, 1, data["file_id"])
        assert record is not None
        assert (record.ref_count or 0) >= 1
        assert record.business_type == "analysis"
        assert record.business_id == body["id"]

    def test_start_with_cuts(self, auth_client, monkeypatch):
        """cuts 以 JSON 数组传递（不再需要手工 JSON 字符串）"""
        captured: list[dict] = []
        monkeypatch.setattr(
            "app.routers.analyses._run_analysis_pipeline",
            lambda analysis_id, video_path, metadata: captured.append(metadata),
        )
        data = self._upload_video(auth_client, content=VIDEO_BYTES + b"-cuts")

        resp = self._start(
            auth_client,
            data["file_id"],
            cuts=[{"start": 0.5, "end": 3.0}],
            mode="full",
        )
        assert resp.status_code == 200
        assert captured[0]["cuts"] == [{"start": 0.5, "end": 3.0}]
        assert captured[0]["mode"] == "full"

    def test_other_user_file_id_not_found(self, auth_client, test_db, monkeypatch):
        monkeypatch.setattr("app.routers.analyses._run_analysis_pipeline", lambda *a, **k: None)
        record = self._register_file(test_db, 2, b"other-user-video", "video", ".mp4")

        resp = self._start(auth_client, record.id)
        assert resp.status_code == 404

    def test_missing_physical_file_not_found(self, auth_client, monkeypatch):
        monkeypatch.setattr("app.routers.analyses._run_analysis_pipeline", lambda *a, **k: None)
        data = self._upload_video(auth_client)
        file_service.unlink(data["url"])

        resp = self._start(auth_client, data["file_id"])
        assert resp.status_code == 404

    def test_non_video_source_not_found(self, auth_client, test_db, monkeypatch):
        monkeypatch.setattr("app.routers.analyses._run_analysis_pipeline", lambda *a, **k: None)
        record = self._register_file(test_db, 1, b"not-a-video", "avatar", ".png")

        resp = self._start(auth_client, record.id)
        assert resp.status_code == 404

    def test_requires_auth(self, client, test_db):
        record = self._register_file(test_db, 1, b"no-auth-video", "video", ".mp4")
        resp = self._start(client, record.id)
        assert resp.status_code in (401, 403)
