"""业务引用注册表（138 文件管理重构）

声明「哪些业务表的哪些字段引用受管文件」，供三处复用：

1. 引用计数的绑定 / 解绑（file_ref_service）
2. 文件扫描的五态判定（file_service.scan）
3. 反查「某个文件被哪些业务记录引用」

**仅允许被 `app.services.file_service` 门面调用**。
"""

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.logging import get_logger

log = get_logger("user")


@dataclass(frozen=True)
class BusinessRef:
    """一条业务引用：某业务记录的某字段引用了 rel_path"""

    rel_path: str
    business_type: str
    business_id: int
    user_id: int
    field: str


@dataclass(frozen=True)
class RefExtractor:
    """字段提取器

    kind:
    - column：列值是单个相对路径字符串
    - json_list：列值是 JSON 字符串数组
    - json_dict：列值是 JSON 对象，keys 为字符串路径键，list_keys 为字符串数组键
    - json_list_of_dict：列值是 JSON 对象数组，keys 指定取哪个键（如 rel_path）
    """

    column: str
    field: str = ""
    kind: str = "column"
    keys: tuple[str, ...] = ()
    list_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.field:
            object.__setattr__(self, "field", self.column)


@dataclass(frozen=True)
class FileRefSpec:
    """一张业务表的文件引用声明"""

    business_type: str
    model_path: str  # "app.models.user.User" 形式，延迟导入避免循环依赖
    owner_field: str  # 归属用户字段名
    id_field: str = "id"
    extractors: tuple[RefExtractor, ...] = ()
    file_id_columns: tuple[str, ...] = ()  # 直接外键 files.id 的列

    def model(self):
        """延迟导入模型类"""
        module_name, class_name = self.model_path.rsplit(".", 1)
        import importlib

        return getattr(importlib.import_module(module_name), class_name)


FILE_REF_SPECS: tuple[FileRefSpec, ...] = (
    FileRefSpec(
        business_type="user",
        model_path="app.models.user.User",
        owner_field="id",
        extractors=(RefExtractor(column="avatar_url", field="avatar_url"),),
    ),
    FileRefSpec(
        business_type="gear",
        model_path="app.models.gear.Gear",
        owner_field="user_id",
        extractors=(RefExtractor(column="photo", field="photo"),),
    ),
    FileRefSpec(
        business_type="analysis",
        model_path="app.models.analysis.Analysis",
        owner_field="user_id",
        extractors=(
            RefExtractor(column="video_url", field="video_url"),
            RefExtractor(column="thumb", field="thumb"),
            RefExtractor(column="highlights", field="highlights", kind="json_list"),
            RefExtractor(
                column="pose",
                field="pose",
                kind="json_dict",
                keys=("skeleton_video_url", "skeleton_thumb", "skeleton_cover"),
                list_keys=("skeleton_frames",),
            ),
        ),
    ),
    FileRefSpec(
        business_type="analysis_video_info",
        model_path="app.models.analysis_video_info.AnalysisVideoInfo",
        owner_field="user_id",
        extractors=(
            RefExtractor(
                column="derivatives",
                field="derivatives",
                kind="json_list_of_dict",
                keys=("rel_path",),
            ),
        ),
        file_id_columns=("source_file_id", "playback_file_id"),
    ),
)

SPEC_BY_TYPE: dict[str, FileRefSpec] = {spec.business_type: spec for spec in FILE_REF_SPECS}


def _load_json(raw) -> object | None:
    """安全解析 JSON 列（字符串 / 已解析对象）"""
    if raw is None or raw == "":
        return None
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        log.warning("业务引用字段 JSON 解析失败: %s", exc)
        return None


def extract_paths(record, extractor: RefExtractor) -> list[str]:
    """从单条业务记录提取一个字段引用的相对路径列表"""
    raw = getattr(record, extractor.column, None)

    if extractor.kind == "column":
        return [raw] if isinstance(raw, str) and raw else []

    parsed = _load_json(raw)
    if parsed is None:
        return []

    paths: list[str] = []

    if extractor.kind == "json_list":
        if isinstance(parsed, list):
            paths.extend(p for p in parsed if isinstance(p, str) and p)
        return paths

    if extractor.kind == "json_list_of_dict":
        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                for key in extractor.keys:
                    value = item.get(key)
                    if isinstance(value, str) and value:
                        paths.append(value)
        return paths

    if extractor.kind == "json_dict":
        if not isinstance(parsed, dict):
            return []
        for key in extractor.keys:
            value = parsed.get(key)
            if isinstance(value, str) and value:
                paths.append(value)
        for key in extractor.list_keys:
            value = parsed.get(key)
            if isinstance(value, list):
                paths.extend(p for p in value if isinstance(p, str) and p)
        return paths

    return []


def collect_business_refs(
    db: Session,
    user_id: int | None = None,
) -> dict[str, list[BusinessRef]]:
    """全量收集业务表引用的相对路径

    Args:
        db: 数据库会话
        user_id: 仅收集指定用户的引用；None 表示全量

    Returns:
        {rel_path: [BusinessRef, ...]}，一次遍历建字典避免 N+1
    """
    from app.models.file import File

    refs: dict[str, list[BusinessRef]] = {}

    def add(path: str, business_type: str, business_id: int, owner_id: int, field_name: str):
        refs.setdefault(path, []).append(
            BusinessRef(
                rel_path=path,
                business_type=business_type,
                business_id=business_id,
                user_id=owner_id,
                field=field_name,
            )
        )

    id_to_path: dict[int, str] = {}
    needed_ids: set[int] = set()

    for spec in FILE_REF_SPECS:
        model = spec.model()
        query = db.query(model)
        if user_id is not None:
            query = query.filter(getattr(model, spec.owner_field) == user_id)
        records = query.all()

        for record in records:
            biz_id = getattr(record, spec.id_field, None)
            owner_id = getattr(record, spec.owner_field, None)
            if biz_id is None:
                continue
            for extractor in spec.extractors:
                for path in extract_paths(record, extractor):
                    add(path, spec.business_type, int(biz_id), int(owner_id or 0), extractor.field)
            for column in spec.file_id_columns:
                file_id = getattr(record, column, None)
                if file_id:
                    needed_ids.add(int(file_id))

    if needed_ids:
        rows = db.query(File.id, File.rel_path).filter(File.id.in_(needed_ids)).all()
        id_to_path = {row[0]: row[1] for row in rows}
        for file_id in needed_ids:
            path = id_to_path.get(file_id)
            if path:
                add(path, "analysis_video_info", file_id, 0, "file_id")

    return refs


def refs_of_record(db: Session, business_type: str, business_id: int) -> list[str]:
    """列出某条业务记录当前引用的全部相对路径（用于 rebind 差量计算）"""
    spec = SPEC_BY_TYPE.get(business_type)
    if spec is None:
        return []
    model = spec.model()
    record = db.query(model).filter(getattr(model, spec.id_field) == business_id).first()
    if record is None:
        return []
    paths: list[str] = []
    for extractor in spec.extractors:
        paths.extend(extract_paths(record, extractor))
    for column in spec.file_id_columns:
        file_id = getattr(record, column, None)
        if file_id:
            from app.models.file import File

            file_record = db.query(File).filter(File.id == file_id).first()
            if file_record:
                paths.append(file_record.rel_path)
    return paths


def specs() -> tuple[FileRefSpec, ...]:
    """注册表快照（供测试/管理端展示）"""
    return FILE_REF_SPECS
