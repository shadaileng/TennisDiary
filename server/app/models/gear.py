from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from app.core.database import Base


class Gear(Base):
    __tablename__ = "gears"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    category = Column(String(32), default="")
    name = Column(String(128), default="")
    buy_date = Column(String(10), default="")
    price = Column(Float, default=0)
    feeling = Column(Text, default="")
    photo = Column(Text, default="")  # dataURL 或文件路径
    created_at = Column(Float, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
