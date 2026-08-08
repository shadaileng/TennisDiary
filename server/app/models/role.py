"""角色模型"""

import json

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), unique=True, nullable=False)
    code = Column(String(32), unique=True, nullable=False, index=True)
    description = Column(String(128), default="")
    permissions = Column(Text, default="[]")  # JSON: 权限列表
    is_system = Column(Boolean, default=False)  # 系统内置角色（不可删除）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def get_permissions(self) -> list[str]:
        """获取权限列表"""
        return json.loads(self.permissions) if self.permissions else []

    def set_permissions(self, perms: list[str]) -> None:
        """设置权限列表"""
        self.permissions = json.dumps(perms, ensure_ascii=False)
