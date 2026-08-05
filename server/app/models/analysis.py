from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from app.core.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(String(10), nullable=False)
    kind = Column(String(16), default="综合")  # 综合/正手/反手/截击/发球/高压
    mode = Column(String(8), default="single")  # single/full
    score = Column(Float, default=0)
    summary = Column(Text, default="")
    ntrp = Column(String(8), nullable=True)
    report = Column(Text, nullable=True)  # JSON: AnalysisReport
    thumb = Column(Text, nullable=True)  # 封面帧路径
    highlights = Column(Text, nullable=True)  # JSON: 高光帧路径数组
    created_at = Column(Float, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
