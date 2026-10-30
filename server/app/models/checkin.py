import datetime

from sqlalchemy import Column, DateTime, Integer, String, func

from app.core.database import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    course_id = Column(String(64), nullable=False)
    date = Column(String(10), nullable=False)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc), server_default=func.now()
    )
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
