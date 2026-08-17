"""初始化默认角色和管理员数据"""

import json

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import DEFAULT_ROLES
from app.core.security import hash_password
from app.models.admin import Admin
from app.models.role import Role


def init_default_roles(db: Session) -> None:
    """初始化默认角色"""
    for role_data in DEFAULT_ROLES:
        existing = db.query(Role).filter(Role.code == role_data["code"]).first()
        if existing:
            continue

        role = Role(
            name=role_data["name"],
            code=role_data["code"],
            description=role_data["description"],
            permissions=json.dumps(role_data["permissions"], ensure_ascii=False),
            is_system=role_data["is_system"],
        )
        db.add(role)

    db.commit()
    print("[OK] 已初始化默认角色")


def init_default_admin(db: Session) -> None:
    """创建默认管理员账号（超级管理员）"""
    username = settings.ADMIN_DEFAULT_USERNAME
    password = settings.ADMIN_DEFAULT_PASSWORD

    existing = db.query(Admin).filter(Admin.username == username).first()
    if existing:
        return

    # 获取超级管理员角色
    role = db.query(Role).filter(Role.code == "superadmin").first()
    if role is None:
        print("[FAIL] 超级管理员角色不存在，请先运行 init_default_roles")
        return

    admin = Admin(
        username=username,
        password_hash=hash_password(password),
        nickname="超级管理员",
        role_id=role.id,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print(f"[OK] 已创建默认管理员账号: {username}")
