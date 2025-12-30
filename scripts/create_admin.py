#!/usr/bin/env python
"""
创建初始管理员用户脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database import SessionLocal, User
from shared.auth import get_password_hash
from shared.utils import get_logger

logger = get_logger("create_admin")


def create_admin(username: str, email: str, password: str, full_name: str = None):
    """创建管理员用户"""
    db = SessionLocal()
    
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            logger.warning(f"User {username} or {email} already exists")
            return False
        
        # 检查是否已有用户
        user_count = db.query(User).count()
        is_superuser = user_count == 0  # 第一个用户自动成为超级用户
        
        # 创建新用户
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=is_superuser,
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Admin user created: {username} (superuser: {is_superuser})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create admin user: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create_admin.py <username> <email> <password> [full_name]")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    full_name = sys.argv[4] if len(sys.argv) > 4 else None
    
    if create_admin(username, email, password, full_name):
        print(f"✅ Admin user '{username}' created successfully")
    else:
        print(f"❌ Failed to create admin user '{username}'")
        sys.exit(1)

