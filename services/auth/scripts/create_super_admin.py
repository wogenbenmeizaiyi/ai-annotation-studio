import getpass

from app.core.redis_client import sync_user_state
from app.core.security import hash_password, normalize_username
from app.db.database import SessionLocal
from app.models.user import User


def main() -> None:
    username = input("超级管理员用户名: ").strip()
    display_name = input("显示名称: ").strip() or username
    password = getpass.getpass("密码（至少 12 个字符）: ")
    confirmation = getpass.getpass("再次输入密码: ")
    if len(password) < 12 or len(password) > 128:
        raise SystemExit("密码长度必须为 12 到 128 个字符")
    if password != confirmation:
        raise SystemExit("两次密码不一致")

    db = SessionLocal()
    try:
        normalized = normalize_username(username)
        if db.query(User).filter(User.username_normalized == normalized).first():
            raise SystemExit("用户名已存在")
        is_platform_owner = db.query(User).filter(User.is_platform_owner.is_(True)).first() is None
        user = User(
            username=username,
            username_normalized=normalized,
            display_name=display_name,
            password_hash=hash_password(password),
            role="super_admin",
            is_platform_owner=is_platform_owner,
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        sync_user_state(user)
        account_type = "平台所有者" if user.is_platform_owner else "超级管理员"
        print(f"{account_type}已创建: {user.username} ({user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
