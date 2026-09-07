"""Admin 文件管理相关 Schema"""

from pydantic import BaseModel, Field


class FileUsageStatus:
    """文件使用状态常量（纯字符串集合，不依赖枚举类，保持与 str 字段兼容）。

    取值含义（138：扫描改为基于业务引用注册表的五态分类）：
    - in_use：使用中（业务记录仍引用该文件）
    - unreferenced：已登记但无任何业务引用（可清除）
    - missing：已登记但物理文件缺失
    - orphan：磁盘孤儿（文件在磁盘但 File 表无记录）
    - unregistered_ref：业务记录引用了未登记的路径
    - marked_deleted：已软删（deleted_at 非空，等待物理清理，可清除）
    """

    IN_USE = "in_use"
    UNREFERENCED = "unreferenced"
    MISSING = "missing"
    ORPHAN = "orphan"
    UNREGISTERED_REF = "unregistered_ref"
    MARKED_DELETED = "marked_deleted"


class AdminFileResponse(BaseModel):
    """Admin 文件列表响应"""

    id: int = Field(description="文件记录 ID")
    user_id: int = Field(description="用户 ID")
    md5: str = Field(description="文件 MD5")
    original_name: str = Field(description="原始文件名")
    rel_path: str = Field(description="相对路径")
    size_bytes: int = Field(description="文件大小（字节）")
    mime_type: str = Field(description="MIME 类型")
    upload_source: str = Field(description="上传来源")
    ref_count: int = Field(description="引用计数")
    business_type: str | None = Field(default=None, description="业务类型")
    business_id: int | None = Field(default=None, description="业务记录 ID")
    created_at: float = Field(description="创建时间戳")
    usage_status: str = Field(description="使用状态：in_use/unreferenced/marked_deleted/orphan")
    usage_reason: str = Field(default="", description="使用状态原因说明")


class AdminFileListResponse(BaseModel):
    """Admin 文件列表分页响应"""

    items: list[AdminFileResponse] = Field(description="文件列表")
    total: int = Field(description="总数")
    offset: int = Field(description="偏移量")
    limit: int = Field(description="每页限制")


class OrphanFileInfo(BaseModel):
    """未注册文件信息（扫描结果）"""

    rel_path: str = Field(description="相对路径")
    size_bytes: int = Field(description="文件大小（字节）")
    modified_at: float = Field(description="最后修改时间戳")
    inferred_user_id: int | None = Field(default=None, description="推断的用户 ID")
    inferred_source: str = Field(default="other", description="推断的上传来源")
    usage_status: str = Field(
        default=FileUsageStatus.ORPHAN, description="使用状态（孤儿固定为 orphan）"
    )
    usage_reason: str = Field(default="磁盘孤儿，未注册到文件表", description="使用状态原因说明")


class ScanResultResponse(BaseModel):
    """扫描结果（138：五态分类）"""

    total_files: int = Field(description="uploads 目录总文件数")
    registered_files: int = Field(description="已注册文件数")
    orphan_files: int = Field(description="待处理文件数（孤儿 / 未登记引用 / 文件缺失）")
    orphans: list[OrphanFileInfo] = Field(description="待处理文件列表")
    total_orphan_size: int = Field(description="待处理文件总大小（字节）")
    status_counts: dict[str, int] = Field(
        default_factory=dict,
        description="五态计数：in_use/unreferenced/missing/orphan/unregistered_ref",
    )


class RegisterFilesRequest(BaseModel):
    """注册文件请求"""

    files: list[str] = Field(
        default_factory=list,
        description="要注册的文件相对路径列表（空列表=扫描并注册全部孤儿）",
    )
    default_user_id: int = Field(default=0, description="默认用户 ID（路径无法推断时使用）")


class CleanupOrphansRequest(BaseModel):
    """清理孤儿文件请求"""

    files: list[str] = Field(description="要删除的孤儿文件相对路径列表")


class BatchDeleteRequest(BaseModel):
    """批量删除文件请求（按 File 记录 ID）"""

    file_ids: list[int] = Field(description="要删除的文件 ID 列表")
