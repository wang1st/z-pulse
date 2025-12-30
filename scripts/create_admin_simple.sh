#!/bin/bash
# 简单的管理员创建脚本

USERNAME=${1:-admin}
EMAIL=${2:-admin@example.com}
PASSWORD=${3:-admin123}
FULL_NAME=${4:-管理员}

docker compose exec api-backend python -c "
import sys
sys.path.insert(0, '/app')
from shared.database import SessionLocal, User
from shared.auth import get_password_hash

db = SessionLocal()
try:
    existing = db.query(User).filter((User.username == '$USERNAME') | (User.email == '$EMAIL')).first()
    if existing:
        print(f'❌ 用户已存在: {existing.username}')
    else:
        user_count = db.query(User).count()
        is_superuser = user_count == 0
        
        user = User(
            username='$USERNAME',
            email='$EMAIL',
            full_name='$FULL_NAME',
            hashed_password=get_password_hash('$PASSWORD'),
            is_active=True,
            is_superuser=is_superuser,
        )
        db.add(user)
        db.commit()
        print('✅ 管理员用户创建成功!')
        print(f'   用户名: $USERNAME')
        print(f'   密码: $PASSWORD')
        print(f'   超级用户: {is_superuser}')
except Exception as e:
    print(f'❌ 错误: {e}')
    db.rollback()
finally:
    db.close()
"

