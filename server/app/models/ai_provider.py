"""AI 服务商模型（ai_providers，手动维护的 OpenAI 兼容 API 凭据列表）"""

import json

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.types import TypeDecorator

from app.core.database import Base


class JSONList(TypeDecorator):
    """Text 列存 JSON 数组，Python 侧透明为 list[str]"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return "[]"
        if isinstance(value, str):
            return value
        return json.dumps(list(value))

    def process_result_value(self, value, dialect):
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(m).strip() for m in parsed if str(m).strip()]


class AiProvider(Base):
    __tablename__ = "ai_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False, index=True)  # 显示名（直选键）
    base_url = Column(String(255), nullable=False)  # OpenAI 兼容基地址
    api_key = Column(Text, nullable=True)  # 密钥（页面仅掩码）
    models = Column(JSONList, nullable=False)  # 模型列表（JSON 数组字符串，默认模型 = 首项）
    enabled = Column(Integer, default=1)  # 是否启用（停用条目不可被直选引用）
    sort_order = Column(Integer, default=0)
    created_at = Column(Float, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def default_model(self) -> str:
        """默认模型 = 列表首项"""
        return self.models[0] if self.models else ""
