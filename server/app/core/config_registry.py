"""动态配置注册表（代码声明，覆盖 Settings 全部配置项）

- 配置定义（分类 / 标签 / 类型 / 是否可编辑 / env 映射）在代码中声明，不落库；
- DB（system_configs）只存「覆盖值」，环境变量始终作为默认值兜底；
- 生效值 = DB 覆盖 > 环境变量默认值（运行时从 settings 解析，兼容测试 monkeypatch）。
"""

from dataclasses import dataclass
from typing import Any

from app.core.config import settings

# 值类型
VALUE_TYPE_STR = "str"
VALUE_TYPE_SECRET = "secret"
VALUE_TYPE_URL = "url"
VALUE_TYPE_BOOL = "bool"
VALUE_TYPE_INT = "int"
VALUE_TYPE_SELECT = "select"

# 来源
SOURCE_DB = "db"  # DB 覆盖
SOURCE_ENV = "env"  # 环境变量默认
SOURCE_BUILTIN = "builtin"  # 代码内置只读常量


@dataclass(frozen=True)
class ConfigItemDef:
    key: str  # 唯一键，如 "ai.api_key"
    category: str  # 分类 key
    label: str  # 显示名
    description: str  # 说明
    value_type: str  # str | secret | url | bool | int | select
    env_key: str | None  # 关联环境变量（settings 属性名）；None = 内置常量
    editable: bool = False  # 是否可动态配置（可编辑）
    options: list[str] | None = None  # select 选项
    builtin_value: str | None = None  # 内置常量值（env_key 为 None 时生效）

    @property
    def default(self) -> str:
        """环境变量默认值（运行时解析）"""
        if self.env_key:
            return str(getattr(settings, self.env_key, "") or "")
        return self.builtin_value or ""


# 分类元数据（顺序即展示顺序）
CONFIG_CATEGORIES: list[dict[str, str]] = [
    {"key": "app", "label": "应用基础", "description": "应用名称、版本与调试开关"},
    {"key": "auth", "label": "认证与安全", "description": "JWT 与管理员账号默认配置（敏感）"},
    {"key": "wx", "label": "微信小程序", "description": "微信开放平台凭据（敏感）"},
    {
        "key": "ai",
        "label": "AI 服务",
        "description": "AI 评分网关（OpenAI 兼容，可在线配置，无需重启）",
    },
    {"key": "data", "label": "数据与存储", "description": "数据库与上传文件目录"},
    {"key": "pose", "label": "姿态模型", "description": "MediaPipe 姿态推理模型路径"},
    {"key": "log", "label": "日志", "description": "日志级别与轮转策略"},
]


def _it(
    key: str,
    category: str,
    label: str,
    description: str,
    value_type: str,
    env_key: str | None,
    editable: bool = False,
    options: list[str] | None = None,
    builtin_value: str | None = None,
) -> ConfigItemDef:
    return ConfigItemDef(
        key=key,
        category=category,
        label=label,
        description=description,
        value_type=value_type,
        env_key=env_key,
        editable=editable,
        options=options,
        builtin_value=builtin_value,
    )


CONFIG_ITEMS: list[ConfigItemDef] = [
    # ===== 应用基础 =====
    _it("app.name", "app", "应用名称", "API 应用名称", VALUE_TYPE_STR, "APP_NAME"),
    _it("app.version", "app", "应用版本", "API 版本号", VALUE_TYPE_STR, "APP_VERSION"),
    _it("app.debug", "app", "调试模式", "开启后输出 SQL 与更详细日志", VALUE_TYPE_BOOL, "DEBUG"),
    # ===== 认证与安全 =====
    _it(
        "auth.jwt_secret",
        "auth",
        "JWT 密钥",
        "用户 token 签名密钥（敏感，请勿外泄）",
        VALUE_TYPE_SECRET,
        "JWT_SECRET",
    ),
    _it(
        "auth.jwt_expiration_hours",
        "auth",
        "Token 有效期",
        "用户 token 有效时长（小时）",
        VALUE_TYPE_INT,
        "JWT_EXPIRATION_HOURS",
    ),
    _it(
        "auth.admin_default_username",
        "auth",
        "默认管理员账号",
        "首次初始化创建的超级管理员用户名",
        VALUE_TYPE_STR,
        "ADMIN_DEFAULT_USERNAME",
    ),
    _it(
        "auth.admin_default_password",
        "auth",
        "默认管理员密码",
        "首次初始化创建的超级管理员密码（敏感）",
        VALUE_TYPE_SECRET,
        "ADMIN_DEFAULT_PASSWORD",
    ),
    _it(
        "auth.admin_reset_key",
        "auth",
        "重置密钥",
        "忘记密码重置密钥（敏感）",
        VALUE_TYPE_SECRET,
        "ADMIN_RESET_KEY",
    ),
    # ===== 微信小程序 =====
    _it("wx.appid", "wx", "AppID", "小程序 AppID", VALUE_TYPE_STR, "WX_APPID"),
    _it("wx.secret", "wx", "AppSecret", "小程序 AppSecret（敏感）", VALUE_TYPE_SECRET, "WX_SECRET"),
    # ===== AI 服务 =====
    _it(
        "ai.provider",
        "ai",
        "服务商",
        "直选已维护的 AI 服务商（ai_providers），地址与密钥引用服务商条目；选自定义用下方独立配置",
        VALUE_TYPE_SELECT,
        "AI_PROVIDER",
        editable=True,
    ),
    _it(
        "ai.api_key",
        "ai",
        "API Key",
        "AI 服务密钥，OpenAI 兼容（敏感，页面仅展示掩码）",
        VALUE_TYPE_SECRET,
        "AI_API_KEY",
        editable=True,
    ),
    _it(
        "ai.base_url",
        "ai",
        "接口地址",
        "OpenAI 兼容 chat/completions 基地址，可切换任意兼容供应商",
        VALUE_TYPE_URL,
        "AI_BASE_URL",
        editable=True,
    ),
    _it(
        "ai.model",
        "ai",
        "模型名称",
        "选中服务商时可在服务商卡片二选其模型列表；自定义模式此处填模型名（如 qwen-vl-max）",
        VALUE_TYPE_STR,
        "AI_MODEL",
        editable=True,
    ),
    _it(
        "ai.timeout",
        "ai",
        "请求超时",
        "AI 请求超时（秒），代码内置",
        VALUE_TYPE_INT,
        None,
        builtin_value="120",
    ),
    _it(
        "ai.temperature",
        "ai",
        "采样温度",
        "AI 采样温度，代码内置",
        VALUE_TYPE_STR,
        None,
        builtin_value="0.3",
    ),
    # ===== 数据与存储 =====
    _it("data.dir", "data", "数据目录", "数据库与上传文件的根目录", VALUE_TYPE_STR, "DATA_DIR"),
    _it("data.database_url", "data", "数据库地址", "SQLite 连接串", VALUE_TYPE_STR, "DATABASE_URL"),
    _it(
        "data.upload_dir", "data", "上传目录", "用户上传文件存储目录", VALUE_TYPE_STR, "UPLOAD_DIR"
    ),
    _it(
        "data.max_upload_size_mb",
        "data",
        "上传大小上限",
        "单文件上传上限（MB）",
        VALUE_TYPE_INT,
        "MAX_UPLOAD_SIZE_MB",
    ),
    # ===== 姿态模型 =====
    _it(
        "pose.model_path",
        "pose",
        "姿态模型路径",
        "MediaPipe pose_landmarker 模型文件路径",
        VALUE_TYPE_STR,
        "POSE_MODEL_PATH",
    ),
    # ===== 日志 =====
    _it(
        "log.level",
        "log",
        "日志级别",
        "loguru 输出级别",
        VALUE_TYPE_SELECT,
        "LOG_LEVEL",
        options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    ),
    _it("log.dir", "log", "日志目录", "日志文件存储目录", VALUE_TYPE_STR, "LOG_DIR"),
    _it("log.rotation", "log", "轮转大小", "单个日志文件轮转大小", VALUE_TYPE_STR, "LOG_ROTATION"),
    _it("log.retention", "log", "保留时长", "日志文件保留时长", VALUE_TYPE_STR, "LOG_RETENTION"),
]

# key -> 定义索引
_CONFIG_BY_KEY: dict[str, ConfigItemDef] = {item.key: item for item in CONFIG_ITEMS}


def find_config_item(key: str) -> ConfigItemDef | None:
    """按 key 查找配置项定义"""
    return _CONFIG_BY_KEY.get(key)


def list_categories() -> list[dict[str, Any]]:
    """分类元数据 + 各项计数"""
    result = []
    for cat in CONFIG_CATEGORIES:
        items = [i for i in CONFIG_ITEMS if i.category == cat["key"]]
        result.append(
            {
                **cat,
                "item_count": len(items),
                "editable_count": sum(1 for i in items if i.editable),
            }
        )
    return result
