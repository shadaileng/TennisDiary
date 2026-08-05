import json
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from app.core.database import Base


class Diary(Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    time = Column(String(5), default="")  # HH:mm
    type = Column(String(16), default="训练")  # 训练/比赛/发球机/发球练习
    duration = Column(Integer, default=0)  # 分钟
    intensity = Column(Integer, default=3)  # 1-5
    mood = Column(Integer, default=3)  # 1-5
    costs = Column(Text, default="[]")  # JSON: [{"name":"","amount":0}]
    gears = Column(Text, default="[]")  # JSON: [{"name":"","feeling":""}]
    notes = Column(Text, default="")
    created_at = Column(Float, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def get_costs(self) -> list[dict]:
        return json.loads(self.costs) if self.costs else []

    def get_gears(self) -> list[dict]:
        return json.loads(self.gears) if self.gears else []
