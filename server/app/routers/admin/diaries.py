"""日记管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.diary import Diary
from app.schemas.admin import DiaryAdminResponse
from app.schemas.common import ApiResponse, PaginatedData

router = APIRouter(prefix="/api/admin/diaries", tags=["admin-diaries"])


@router.get("", response_model=ApiResponse[PaginatedData[DiaryAdminResponse]])
def list_diaries(
    offset: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """日记列表（分页+用户筛选）"""
    query = db.query(Diary)
    if user_id is not None:
        query = query.filter(Diary.user_id == user_id)

    total = query.count()
    diaries = query.order_by(Diary.date.desc()).offset(offset).limit(limit).all()
    return ApiResponse(
        data=PaginatedData(
            items=[DiaryAdminResponse.model_validate(d) for d in diaries],
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.get("/{diary_id}", response_model=ApiResponse[DiaryAdminResponse])
def get_diary(
    diary_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """日记详情"""
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if diary is None:
        raise HTTPException(status_code=404, detail="日记不存在")
    return ApiResponse(data=DiaryAdminResponse.model_validate(diary))


@router.delete("/{diary_id}", response_model=ApiResponse[None])
def delete_diary(
    diary_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除日记"""
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if diary is None:
        raise HTTPException(status_code=404, detail="日记不存在")

    db.delete(diary)
    db.commit()
    return ApiResponse(message="删除成功")
