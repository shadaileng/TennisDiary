"""日记相关路由：列表 / 创建 / 详情 / 编辑 / 删除"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import logger
from app.models.diary import Diary
from app.models.user import User
from app.schemas.schemas import CostItem, DiaryCreate, DiaryResponse, DiaryUpdate, GearUse

router = APIRouter(prefix="/api/diaries", tags=["diaries"])


def diary_to_response(diary: Diary) -> DiaryResponse:
    """将 ORM Diary 转换为 DiaryResponse，解析 JSON 文本字段"""
    costs = [CostItem(**c) for c in (json.loads(diary.costs) if diary.costs else [])]
    gears = [GearUse(**g) for g in (json.loads(diary.gears) if diary.gears else [])]
    return DiaryResponse(
        id=diary.id,
        user_id=diary.user_id,
        date=diary.date,
        time=diary.time,
        type=diary.type,
        duration=diary.duration,
        intensity=diary.intensity,
        mood=diary.mood,
        costs=costs,
        gears=gears,
        notes=diary.notes,
        created_at=diary.created_at,
    )


def _get_owned_diary(db: Session, diary_id: int, user: User) -> Diary:
    """获取属于当前用户的日记，不存在或越权返回 404"""
    diary = db.query(Diary).filter(Diary.id == diary_id, Diary.user_id == user.id).first()
    if diary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日记不存在")
    return diary


@router.get("", response_model=list[DiaryResponse])
def list_diaries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户的日记列表，按日期倒序"""
    diaries = (
        db.query(Diary).filter(Diary.user_id == current_user.id).order_by(Diary.date.desc()).all()
    )
    return [diary_to_response(d) for d in diaries]


@router.post("", response_model=DiaryResponse, status_code=status.HTTP_200_OK)
def create_diary(
    body: DiaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建日记"""
    import time

    diary = Diary(
        user_id=current_user.id,
        date=body.date,
        time=body.time,
        type=body.type,
        duration=body.duration,
        intensity=body.intensity,
        mood=body.mood,
        costs=json.dumps([c.model_dump() for c in body.costs], ensure_ascii=False),
        gears=json.dumps([g.model_dump() for g in body.gears], ensure_ascii=False),
        notes=body.notes,
        created_at=time.time(),
    )
    db.add(diary)
    db.commit()
    db.refresh(diary)
    logger.info("创建日记成功", user_id=current_user.id, diary_id=diary.id)
    return diary_to_response(diary)


@router.get("/{diary_id}", response_model=DiaryResponse)
def get_diary(
    diary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """日记详情"""
    return diary_to_response(_get_owned_diary(db, diary_id, current_user))


@router.put("/{diary_id}", response_model=DiaryResponse)
def update_diary(
    diary_id: int,
    body: DiaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑日记 — 仅更新传入的字段"""
    diary = _get_owned_diary(db, diary_id, current_user)

    if body.date is not None:
        diary.date = body.date
    if body.time is not None:
        diary.time = body.time
    if body.type is not None:
        diary.type = body.type
    if body.duration is not None:
        diary.duration = body.duration
    if body.intensity is not None:
        diary.intensity = body.intensity
    if body.mood is not None:
        diary.mood = body.mood
    if body.costs is not None:
        diary.costs = json.dumps([c.model_dump() for c in body.costs], ensure_ascii=False)
    if body.gears is not None:
        diary.gears = json.dumps([g.model_dump() for g in body.gears], ensure_ascii=False)
    if body.notes is not None:
        diary.notes = body.notes

    db.commit()
    db.refresh(diary)
    logger.info("更新日记成功", user_id=current_user.id, diary_id=diary.id)
    return diary_to_response(diary)


@router.delete("/{diary_id}", status_code=status.HTTP_200_OK)
def delete_diary(
    diary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除日记"""
    diary = _get_owned_diary(db, diary_id, current_user)
    db.delete(diary)
    db.commit()
    logger.info("删除日记成功", user_id=current_user.id, diary_id=diary_id)
    return {"message": "删除成功"}
