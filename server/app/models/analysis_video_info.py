from sqlalchemy import Column, Float, ForeignKey, Integer, Text, UniqueConstraint

from app.core.database import Base


class AnalysisVideoInfo(Base):
    __tablename__ = "analysis_video_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    analysis_id = Column(
        Integer,
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    source_file_id = Column(Integer, ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    playback_file_id = Column(Integer, ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    cut_info = Column(Text, nullable=True)  # JSON: {segments, hit_time, mode, kind}
    derivatives = Column(Text, nullable=True)  # JSON: [{kind, rel_path, file_id, ...}]
    created_at = Column(Float, nullable=True)

    __table_args__ = (UniqueConstraint("analysis_id", name="uq_analysis_video_info_analysis_id"),)
