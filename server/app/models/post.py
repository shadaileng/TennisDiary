import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(String(10), nullable=False)
    platform = Column(String(16), default="小红书")
    title = Column(String(256), default="")
    content = Column(Text, default="")
    status = Column(String(8), default="草稿")  # 草稿/已发布
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc), server_default=func.now()
    )
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
