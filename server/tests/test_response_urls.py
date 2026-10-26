"""147 阶段一 Step 7：响应层两态外链（§6.2 收口 + §6.3 资源接入）

两态规则（§6.1）：
- `SYNCED` 且位置即当前后端 → **绝对签名外链**（直连对象存储）
- 其余（`local` / `PENDING` / `FAILED` / dataURL / 绝对地址 / 无记录 / 未启用）→
  **原样返回相对路径**，走现有后端代理，永不 404

收口点：`ApiResponse.model_post_init` → `storage.urls.rewrite_response_urls`
（批量 `IN` 查询建映射，一次响应只查一次，满足 §6.2 N+1 防护）。
"""

import hashlib
import json
import time

import pytest

from app.core.config import settings
from app.models.analysis import Analysis
from app.models.file import (
    STORAGE_STATUS_FAILED,
    STORAGE_STATUS_PENDING,
    STORAGE_STATUS_SYNCED,
    File,
)
from app.models.gear import Gear
from app.schemas.common import ApiResponse
from app.services import storage
from app.services.storage.urls import (
    build_public_url_map,
    rewrite_response_urls,
    to_public_url,
)

pytestmark = pytest.mark.fast


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _clean_storage_rows(db) -> None:
    from app.models.system_config import SystemConfig

    db.query(SystemConfig).filter(SystemConfig.key.like("storage.%")).delete()
    db.commit()


@pytest.fixture(autouse=True)
def _storage_env(test_db):
    """清掉 storage.* 覆盖行 + 实例缓存，保证读到 settings（monkeypatch）默认值"""
    _clean_storage_rows(test_db)
    storage.clear_backend_cache()
    yield
    _clean_storage_rows(test_db)
    storage.clear_backend_cache()


def _add_file(
    db,
    rel_path: str,
    *,
    storage_col: str = "memory",
    status: int = STORAGE_STATUS_SYNCED,
    user_id: int = 1,
) -> File:
    row = File(
        user_id=user_id,
        md5=_md5(rel_path),
        original_name=rel_path.rsplit("/", 1)[-1],
        rel_path=rel_path,
        size_bytes=16,
        mime_type="image/jpeg",
        upload_source="gear_image",
        ref_count=1,
        created_at=time.time(),
        storage=storage_col,
        storage_status=status,
    )
    db.add(row)
    db.commit()
    return row


# ==================== build_public_url_map（批量映射） ====================


class TestBuildPublicUrlMap:
    def test_local_backend_returns_empty_map(self, test_db):
        """backend=local（回滚开关）→ 不查不转，全部走代理"""
        _add_file(test_db, "gears/1/local.jpg", storage_col="local")
        assert build_public_url_map(test_db, ["gears/1/local.jpg"]) == {}

    def test_synced_row_yields_signed_url(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        rel = "gears/1/synced.jpg"
        _add_file(test_db, rel)
        url_map = build_public_url_map(test_db, [rel])
        assert url_map[rel].startswith("https://")
        assert rel in url_map[rel]

    def test_pending_and_failed_excluded(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        pending, failed = "gears/1/pending.jpg", "gears/1/failed.jpg"
        _add_file(test_db, pending, status=STORAGE_STATUS_PENDING)
        _add_file(test_db, failed, status=STORAGE_STATUS_FAILED)
        assert build_public_url_map(test_db, [pending, failed]) == {}

    def test_local_row_excluded_when_backend_memory(self, test_db, monkeypatch):
        """存量未搬迁（storage=local + SYNCED）→ 回落代理，不出外链"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        rel = "gears/1/not-migrated.jpg"
        _add_file(test_db, rel, storage_col="local")
        assert build_public_url_map(test_db, [rel]) == {}

    def test_absolute_and_data_url_excluded(self, test_db, monkeypatch):
        """dataURL / 绝对地址不是 rel_path，不参与查询"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        assert build_public_url_map(test_db, ["https://cdn.example.com/a.jpg"]) == {}
        assert build_public_url_map(test_db, ["data:image/png;base64,iVBORw0KGgo="]) == {}

    def test_unknown_path_excluded(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        assert build_public_url_map(test_db, ["gears/1/no-record.jpg"]) == {}

    def test_empty_input(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        assert build_public_url_map(test_db, []) == {}

    def test_batch_single_query_result(self, test_db, monkeypatch):
        """多个 SYNCED 一次映射（列表接口 N+1 防护）"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        rels = [f"gears/1/batch{i}.jpg" for i in range(3)]
        for rel in rels:
            _add_file(test_db, rel)
        url_map = build_public_url_map(test_db, rels)
        assert set(url_map) == set(rels)


class TestToPublicUrl:
    def test_synced_returns_absolute(self, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        rel = "avatars/1/one.jpg"
        _add_file(test_db, rel)
        url = to_public_url(test_db, rel)
        assert url.startswith("https://") and rel in url

    def test_fallback_returns_rel_path(self, test_db):
        rel = "avatars/1/fallback.jpg"
        _add_file(test_db, rel, storage_col="local")
        assert to_public_url(test_db, rel) == rel


# ==================== 响应改写（无会话时安全跳过） ====================


class TestRewriteWithoutSession:
    def test_no_bound_session_is_noop(self):
        """未绑定请求会话（直接构造响应 / 后台任务）→ 原样返回，不抛错"""
        resp = ApiResponse(data={"avatar_url": "avatars/1/a.jpg"})
        assert resp.data["avatar_url"] == "avatars/1/a.jpg"

    def test_none_data_is_noop(self):
        resp = ApiResponse(code=10001, message="未登录", success=False, data=None)
        assert resp.data is None


# ==================== 端点两态（§6.3 接入清单） ====================


class TestMeAvatar:
    """#1 user.avatar_url（/api/auth/me）"""

    def test_synced_avatar_becomes_signed_url(self, auth_client, mock_user, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        rel = f"avatars/1/{_md5('avatar-a')}.jpg"
        _add_file(test_db, rel)
        mock_user.avatar_url = rel

        data = auth_client.get("/api/auth/me").json()["data"]
        assert data["avatar_url"].startswith("https://")
        assert rel in data["avatar_url"]

    def test_avatar_falls_back_when_local(self, auth_client, mock_user, test_db):
        rel = f"avatars/1/{_md5('avatar-b')}.jpg"
        _add_file(test_db, rel, storage_col="local")
        mock_user.avatar_url = rel

        data = auth_client.get("/api/auth/me").json()["data"]
        assert data["avatar_url"] == rel


class TestGearPhoto:
    """#2 gear.photo（/api/gears 列表）"""

    def _add_gear(self, db, photo: str) -> None:
        db.add(
            Gear(
                user_id=1,
                category="球拍",
                name="测试球拍",
                photo=photo,
                created_at=time.time(),
            )
        )
        db.commit()

    def test_photo_becomes_signed_url(self, auth_client, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        rel = f"gears/1/{_md5('gear-a')}.jpg"
        _add_file(test_db, rel)
        self._add_gear(test_db, rel)

        items = auth_client.get("/api/gears").json()["data"]
        assert len(items) == 1
        assert items[0]["photo"].startswith("https://")
        assert rel in items[0]["photo"]

    def test_data_url_untouched(self, auth_client, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        data_url = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
        self._add_gear(test_db, data_url)

        items = auth_client.get("/api/gears").json()["data"]
        assert items[0]["photo"] == data_url

    def test_pending_photo_falls_back(self, auth_client, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        rel = f"gears/1/{_md5('gear-pending')}.jpg"
        _add_file(test_db, rel, status=STORAGE_STATUS_PENDING)
        self._add_gear(test_db, rel)

        items = auth_client.get("/api/gears").json()["data"]
        assert items[0]["photo"] == rel


class TestAnalysisNested:
    """#3 analysis：video_url / thumb（column）+ highlights（json_list）+ pose（json_dict）"""

    FRAME_1 = "frames/1/a1.jpg"
    FRAME_2 = "frames/1/a2.jpg"
    SKEL_FRAME_1 = "skeleton/1/s1.jpg"
    SKEL_FRAME_2 = "skeleton/1/s2.jpg"
    VIDEO = "videos/1/clip.mp4"
    THUMB = "thumbs/1/clip.jpg"
    SKEL_VIDEO = "skeleton/1/clip_skeleton.mp4"

    def _all_paths(self) -> list[str]:
        return [
            self.VIDEO,
            self.THUMB,
            self.FRAME_1,
            self.FRAME_2,
            self.SKEL_FRAME_1,
            self.SKEL_FRAME_2,
            self.SKEL_VIDEO,
        ]

    def _add_analysis(self, db) -> Analysis:
        analysis = Analysis(
            user_id=1,
            date="2026-10-26",
            kind="综合",
            mode="single",
            score=88.5,
            summary="整体不错",
            thumb=self.THUMB,
            video_url=self.VIDEO,
            highlights=json.dumps([self.FRAME_1, self.FRAME_2]),
            pose=json.dumps(
                {
                    "skeleton_video_url": self.SKEL_VIDEO,
                    "skeleton_frames": [self.SKEL_FRAME_1, self.SKEL_FRAME_2],
                    "elbow_angle": 92.5,
                }
            ),
            status="completed",
            created_at=time.time(),
        )
        db.add(analysis)
        db.commit()
        return analysis

    def test_list_rewrites_all_nested_paths(self, auth_client, test_db, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        for rel in self._all_paths():
            _add_file(test_db, rel)
        self._add_analysis(test_db)

        items = auth_client.get("/api/analyses").json()["data"]["items"]
        assert len(items) == 1
        item = items[0]
        for value in (item["video_url"], item["thumb"]):
            assert value.startswith("https://")
        for frame in item["highlights"]:
            assert frame.startswith("https://")
        pose = item["pose"]
        assert pose["skeleton_video_url"].startswith("https://")
        assert all(f.startswith("https://") for f in pose["skeleton_frames"])
        assert pose["elbow_angle"] == 92.5  # 非路径字段不动
        # 全部外链互不相同（逐条 presign，未串键）
        urls = [
            item["video_url"],
            item["thumb"],
            *item["highlights"],
            pose["skeleton_video_url"],
            *pose["skeleton_frames"],
        ]
        assert len(set(urls)) == len(urls)

    def test_local_keeps_rel_paths(self, auth_client, test_db):
        for rel in self._all_paths():
            _add_file(test_db, rel, storage_col="local")
        self._add_analysis(test_db)

        item = auth_client.get("/api/analyses").json()["data"]["items"][0]
        assert item["video_url"] == self.VIDEO
        assert item["thumb"] == self.THUMB
        assert item["highlights"] == [self.FRAME_1, self.FRAME_2]
        assert item["pose"]["skeleton_video_url"] == self.SKEL_VIDEO
        assert item["pose"]["skeleton_frames"] == [self.SKEL_FRAME_1, self.SKEL_FRAME_2]


class TestQueryCount:
    """§6.2 N+1 防护：一次响应只对 files 批量查一次"""

    def test_list_response_queries_files_once(self, auth_client, test_db, monkeypatch):
        from sqlalchemy import event

        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        for index in range(5):
            rel = f"gears/1/batch{index}.jpg"
            _add_file(test_db, rel)
            test_db.add(
                Gear(
                    user_id=1,
                    category="球拍",
                    name=f"球拍{index}",
                    photo=rel,
                    created_at=time.time(),
                )
            )
        test_db.commit()

        counter = {"selects": 0}

        def _count(conn, cursor, statement, parameters, context, executemany):
            del conn, cursor, parameters, context, executemany
            if statement.lstrip().upper().startswith("SELECT") and "FROM files" in statement:
                counter["selects"] += 1

        engine = test_db.get_bind()
        event.listen(engine, "before_cursor_execute", _count)
        try:
            items = auth_client.get("/api/gears").json()["data"]
        finally:
            event.remove(engine, "before_cursor_execute", _count)

        assert len(items) == 5
        assert all(item["photo"].startswith("https://") for item in items)
        assert counter["selects"] == 1  # 单次 `IN` 批量查询，禁止逐行 query


class TestRewriteIsIdempotent:
    def test_second_pass_keeps_urls(self, test_db, monkeypatch):
        """改写后字段已是绝对地址 → 再次改写为 no-op（序列化重复校验安全）"""
        monkeypatch.setattr(settings, "STORAGE_BACKEND", "memory")
        rel = "gears/1/idem.jpg"
        _add_file(test_db, rel)
        resp = ApiResponse(data={"photo": rel})
        # 无请求会话时 model_post_init 跳过（见 TestRewriteWithoutSession），这里显式改写
        rewrite_response_urls(test_db, resp.data)
        first = resp.data["photo"]
        assert first.startswith("https://")

        rewrite_response_urls(test_db, resp.data)
        assert resp.data["photo"] == first
