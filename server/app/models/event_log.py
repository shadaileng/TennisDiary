from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.core.database import Base


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    level = Column(String(16), nullable=False, index=True)  # info/warn/error/fatal
    type = Column(String(64), nullable=False, default="custom")  # network/business/crash/custom
    message = Column(Text, nullable=False)
    stack = Column(Text, default="")
    page = Column(String(256), default="")
    extra = Column(Text, default="")  # JSON 扩展字段，含 trace_id
    device_info = Column(Text, default="")  # 设备信息 JSON
    client_time = Column(Integer, nullable=True, index=True)  # 前端发送时的毫秒时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)
