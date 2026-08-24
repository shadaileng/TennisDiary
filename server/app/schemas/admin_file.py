"""Admin 文件管理相关 Schema"""

from pydantic import BaseModel, Field


class DerivedFileInfo(BaseModel):
    """关联文件信息（derived files）"""

    id: int = Field(description="文件记录 ID")
    rel_path: str = Field(description="相对路径")
    upload_source: str = Field(description="上传来源")
    business_type: str | None = Field(default=None, description="业务类型")
    business_id: int | None = Field(default=None, description="业务记录 ID")
    size_bytes: int = Field(description="文件大小（字节）")
    mime_type: str = Field(description="MIME 类型")


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
    derived_files: list[DerivedFileInfo] = Field(
        default_factory=list, description="关联的派生文件列表"
    )


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


class ScanResultResponse(BaseModel):
    """扫描结果"""

    total_files: int = Field(description="uploads 目录总文件数")
    registered_files: int = Field(description="已注册文件数")
    orphan_files: int = Field(description="未注册文件数")
    orphans: list[OrphanFileInfo] = Field(description="未注册文件列表")
    total_orphan_size: int = Field(description="未注册文件总大小（字节）")


class RegisterFilesRequest(BaseModel):
    """注册文件请求"""

    files: list[str] = Field(description="要注册的文件相对路径列表")
    default_user_id: int = Field(default=0, description="默认用户 ID（路径无法推断时使用）")
