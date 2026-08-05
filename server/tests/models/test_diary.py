import json

from app.models.diary import Diary


class TestDiaryModel:
    """Diary ORM 模型测试"""

    def test_create_diary(self, test_db):
        diary = Diary(
            user_id=1,
            date="2026-08-05",
            time="14:30",
            type="训练",
            duration=90,
            intensity=4,
            mood=5,
            costs=json.dumps([{"name": "场地费", "amount": 80}]),
            gears=json.dumps([{"name": "Wilson Pro Staff", "feeling": "好"}]),
            notes="正手练习",
            created_at=1754400000.0,
        )
        test_db.add(diary)
        test_db.commit()

        saved = test_db.query(Diary).filter_by(user_id=1).first()
        assert saved is not None
        assert saved.date == "2026-08-05"
        assert saved.type == "训练"
        assert saved.duration == 90

    def test_get_costs_deserializes_json(self, test_db):
        diary = Diary(
            user_id=1, date="2026-08-05", costs=json.dumps([{"name": "球费", "amount": 50}])
        )
        test_db.add(diary)
        test_db.commit()

        saved = test_db.query(Diary).filter_by(user_id=1).first()
        costs = saved.get_costs()
        assert len(costs) == 1
        assert costs[0]["name"] == "球费"
        assert costs[0]["amount"] == 50

    def test_get_costs_empty_default(self, test_db):
        diary = Diary(user_id=1, date="2026-08-05")
        test_db.add(diary)
        test_db.commit()

        saved = test_db.query(Diary).filter_by(user_id=1).first()
        assert saved.get_costs() == []

    def test_get_gears_deserializes_json(self, test_db):
        diary = Diary(
            user_id=1,
            date="2026-08-05",
            gears=json.dumps([{"name": "Wilson", "feeling": "不错"}]),
        )
        test_db.add(diary)
        test_db.commit()

        saved = test_db.query(Diary).filter_by(user_id=1).first()
        gears = saved.get_gears()
        assert len(gears) == 1
        assert gears[0]["name"] == "Wilson"

    def test_get_gears_empty_default(self, test_db):
        diary = Diary(user_id=1, date="2026-08-05")
        test_db.add(diary)
        test_db.commit()

        saved = test_db.query(Diary).filter_by(user_id=1).first()
        assert saved.get_gears() == []

    def test_default_values(self, test_db):
        diary = Diary(user_id=1, date="2026-08-05")
        test_db.add(diary)
        test_db.commit()

        saved = test_db.query(Diary).filter_by(user_id=1).first()
        assert saved.type == "训练"
        assert saved.intensity == 3
        assert saved.mood == 3
        assert saved.duration == 0
        assert saved.notes == ""
