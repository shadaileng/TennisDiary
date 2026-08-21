"""审计日志模型"""

from sqlalchemy import Boolean, Column, Float, Integer, String, Text

from app.core.audit_db import AuditBase


class AuditLog(AuditBase):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(16), nullable=False, index=True)  # "admin" / "user"
    admin_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    action = Column(String(32), nullable=False, index=True)  # CREATE/UPDATE/DELETE/UPLOAD/ANALYZE
    resource_type = Column(String(32), nullable=False, index=True)
    resource_id = Column(String(64), nullable=True)
    description = Column(String(256), default="")
    request_body = Column(Text, nullable=True)
    request_path = Column(String(256), default="")  # 请求路由路径
    request_method = Column(String(16), default="")  # HTTP 方法
    response_code = Column(Integer, default=0)
    response_success = Column(Boolean, default=True)
    response_message = Column(String(256), default="")
    duration_ms = Column(Float, default=0.0)
    ip_address = Column(String(45), default="")
    user_agent = Column(String(256), default="")
    created_at = Column(String(32), nullable=False, index=True)  # ISO8601 UTC Z
