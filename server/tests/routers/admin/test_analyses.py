"""分析报告管理路由测试（含详情完整报告返回）"""

import json

import pytest

from app.models.analysis import Analysis
from app.models.user import User


@pytest.fixture(scope="module")
def test_analysis_user(test_db):
    """创建用于分析报告的用户"""
    user = User(
        openid="openid_analysis_test",
        nickname="分析测试用户",
        avatar_url="",
        gender=0,
        birthday="",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _insert_analysis(test_db, **overrides):
    """插入一条分析报告并返回 ORM 对象"""
    data = dict(
        user_id=1,
        date="2026-08-13",
        kind="综合",
        mode="full",
        score=72.5,
        summary="发力链条顺畅，击球点稳定",
        ntrp="3.5",
        report=json.dumps(
            {
                "score": 72.5,
                "summary": "发力链条顺畅，击球点稳定",
                "ntrp": "3.5",
                "dimensions": [
                    {"name": "准备启动", "score": 70, "comment": "准备动作充分"},
                    {"name": "动力链", "score": 75, "comment": "蹬转发力连贯"},
                    {"name": "击球时机", "score": 72, "comment": "击球点靠前"},
                    {"name": "随挥收拍", "score": 68, "comment": "随挥完整"},
                    {"name": "拍面控制", "score": 74, "comment": "拍面稳定"},
                    {"name": "身体稳定", "score": 76, "comment": "重心平稳"},
                ],
                "rhythm": "整体节奏良好，发力顺序正确",
                "strengths": ["动力链完整", "击球时机精准"],
                "improvements": [
                    {"issue": "随挥略显仓促", "advice": "延长随挥轨迹"},
                ],
            },
            ensure_ascii=False,
        ),
        thumb="analyses/cover.jpg",
        highlights=json.dumps(["analyses/h1.jpg", "analyses/h2.jpg"]),
        created_at=0,
    )
    data.update(overrides)
    analysis = Analysis(**data)
    test_db.add(analysis)
    test_db.commit()
    test_db.refresh(analysis)
    return analysis


@pytest.fixture(scope="module")
def test_analysis(test_db, test_analysis_user):
    """创建一条完整六维报告的分析记录"""
    analysis = _insert_analysis(test_db, user_id=test_analysis_user.id)
    return analysis


def test_list_analyses(auth_client, test_analysis):
    """列表返回精简字段（不含完整 report），但含 mode"""
    response = auth_client.get("/api/admin/analyses")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) >= 1
    item = items[0]
    assert item["mode"] == "full"
    assert item["score"] == pytest.approx(72.5)
    assert "report" not in item


def test_get_analysis_detail(auth_client, test_analysis):
    """详情返回完整六维报告（report 为 JSON 对象）、thumb 与 highlights 数组"""
    response = auth_client.get(f"/api/admin/analyses/{test_analysis.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == test_analysis.id
    assert data["mode"] == "full"
    # report 已解析为 dict
    assert isinstance(data["report"], dict)
    assert data["report"]["score"] == pytest.approx(72.5)
    assert len(data["report"]["dimensions"]) == 6
    assert isinstance(data["report"]["strengths"], list)
    assert isinstance(data["report"]["improvements"], list)
    assert "rhythm" in data["report"]
    # thumb / highlights
    assert data["thumb"] == "analyses/cover.jpg"
    assert data["highlights"] == ["analyses/h1.jpg", "analyses/h2.jpg"]
    # user 信息已补齐
    assert data["user"]["nickname"] == "分析测试用户"


def test_get_analysis_detail_dirty_report(auth_client, test_db, test_analysis_user):
    """历史脏数据：report / highlights 非法 JSON → 返回 None 而非报错"""
    analysis = _insert_analysis(
        test_db,
        user_id=test_analysis_user.id,
        report="{invalid json",
        highlights="{invalid",
        thumb=None,
    )
    response = auth_client.get(f"/api/admin/analyses/{analysis.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["report"] is None
    assert data["highlights"] is None
    assert data["thumb"] is None


def test_get_analysis_not_found(auth_client):
    """不存在的分析报告 → 404"""
    response = auth_client.get("/api/admin/analyses/999999")
    assert response.status_code == 404


def test_delete_analysis(auth_client, test_db, test_analysis_user):
    """删除分析报告"""
    analysis = _insert_analysis(test_db, user_id=test_analysis_user.id)
    response = auth_client.delete(f"/api/admin/analyses/{analysis.id}")
    assert response.status_code == 200
    assert "删除成功" in response.json()["message"]
    again = auth_client.delete(f"/api/admin/analyses/{analysis.id}")
    assert again.status_code == 404


# ===== 筛选与排序测试（Step 124） =====


@pytest.fixture(scope="module")
def sample_analyses(test_db, test_analysis_user):
    """创建多条不同属性的分析记录用于筛选测试"""
    records = [
        _insert_analysis(
            test_db,
            user_id=test_analysis_user.id,
            date="2026-08-10",
            kind="正手",
            mode="single",
            score=65.0,
            status="completed",
            created_at=1754800000,
        ),
        _insert_analysis(
            test_db,
            user_id=test_analysis_user.id,
            date="2026-08-12",
            kind="综合",
            mode="full",
            score=75.0,
            status="completed",
            created_at=1754900000,
        ),
        _insert_analysis(
            test_db,
            user_id=test_analysis_user.id,
            date="2026-08-15",
            kind="反手",
            mode="single",
            score=80.0,
            status="completed",
            created_at=1755100000,
        ),
        _insert_analysis(
            test_db,
            user_id=test_analysis_user.id,
            date="2026-08-15",
            kind="截击",
            mode="full",
            score=70.0,
            status="processing",
            created_at=1755200000,
        ),
        _insert_analysis(
            test_db,
            user_id=test_analysis_user.id,
            date="2026-08-20",
            kind="发球",
            mode="single",
            score=None,
            status="failed",
            created_at=1755600000,
        ),
    ]
    return records


def test_list_analyses_with_date_filter(auth_client, sample_analyses):
    """日期范围筛选"""
    resp = auth_client.get(
        "/api/admin/analyses?date_from=2026-08-10&date_to=2026-08-15",
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    assert len(data) >= 3
    for item in data:
        assert "2026-08-10" <= item["date"] <= "2026-08-15"


def test_list_analyses_with_kind_filter(auth_client, sample_analyses):
    """类型筛选"""
    resp = auth_client.get(
        "/api/admin/analyses?kind=正手",
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    assert len(data) >= 1
    for item in data:
        assert item["kind"] == "正手"


def test_list_analyses_with_mode_filter(auth_client, sample_analyses):
    """模式筛选"""
    resp = auth_client.get(
        "/api/admin/analyses?mode=single",
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    assert len(data) >= 1
    for item in data:
        assert item["mode"] == "single"


def test_list_analyses_with_status_filter(auth_client, sample_analyses):
    """状态筛选"""
    resp = auth_client.get(
        "/api/admin/analyses?status=completed",
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    assert len(data) >= 1
    for item in data:
        assert item["status"] == "completed"


def test_list_analyses_with_combined_filters(auth_client, sample_analyses):
    """组合筛选：日期 + 类型 + 模式"""
    resp = auth_client.get(
        "/api/admin/analyses?date_from=2026-08-01&date_to=2026-08-31&kind=综合&mode=full",
    )
    assert resp.status_code == 200
    data = resp.json()["data"]["items"]
    assert len(data) >= 1
    for item in data:
        assert "2026-08-01" <= item["date"] <= "2026-08-31"
        assert item["kind"] == "综合"
        assert item["mode"] == "full"


def test_list_analyses_order_by_date_and_id(auth_client, sample_analyses):
    """排序验证：先按 date 降序，再按 id 降序"""
    resp = auth_client.get(
        "/api/admin/analyses",
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 2
    for i in range(len(items) - 1):
        curr = items[i]
        next_item = items[i + 1]
        # 日期降序，或同日期内 ID 降序
        assert (curr["date"] > next_item["date"]) or (
            curr["date"] == next_item["date"] and curr["id"] >= next_item["id"]
        )
