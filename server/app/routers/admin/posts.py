"""发布管理路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.post import Post
from app.models.user import User
from app.schemas.admin import PostAdminResponse
from app.schemas.common import ApiResponse, PaginatedData

router = APIRouter(prefix="/api/admin/posts", tags=["admin-posts"])


def _enrich_post(p: Post, db: Session) -> PostAdminResponse:
    resp = PostAdminResponse.model_validate(p)
    user = db.query(User).filter(User.id == p.user_id).first()
    if user:
        resp.user = {"id": user.id, "nickname": user.nickname or ""}
    return resp


@router.get("", response_model=ApiResponse[PaginatedData[PostAdminResponse]])
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
    return ApiResponse(
        data=PaginatedData(
            items=[_enrich_post(p, db) for p in posts],
            total=total,
            offset=offset,
            limit=limit,
        )
    )


@router.get("/{post_id}", response_model=ApiResponse[PostAdminResponse])
def get_post(
    post_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """发布详情"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    return ApiResponse(data=PostAdminResponse.model_validate(post))


@router.delete("/{post_id}", response_model=ApiResponse[None])
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
    return ApiResponse(message="删除成功")
