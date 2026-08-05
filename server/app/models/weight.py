from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.core.database import Base


class WeightRecord(Base):
    __tablename__ = "weight_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(String(10), nullable=False)
    weight = Column(Float, default=0)
    bust = Column(Float, nullable=True)
    waist = Column(Float, nullable=True)
    hip = Column(Float, nullable=True)
    created_at = Column(Float, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
