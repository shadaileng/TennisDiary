"""发布管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.post import Post
from app.schemas.admin import PaginatedResponse, PostAdminResponse

router = APIRouter(prefix="/api/admin/posts", tags=["admin-posts"])


@router.get("", response_model=PaginatedResponse[PostAdminResponse])
def list_posts(
    offset: int = 0,
    limit: int = 20,
    user_id: int | None = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """发布记录列表（分页+用户筛选）"""
    query = db.query(Post)
    if user_id is not None:
        query = query.filter(Post.user_id == user_id)

    total = query.count()
    posts = query.order_by(Post.date.desc()).offset(offset).limit(limit).all()
    return PaginatedResponse(
        items=[PostAdminResponse.model_validate(p) for p in posts],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{post_id}", response_model=PostAdminResponse)
def get_post(
    post_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """发布详情"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    return PostAdminResponse.model_validate(post)


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除发布记录"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    db.delete(post)
    db.commit()
    return {"message": "删除成功"}
