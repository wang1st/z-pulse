"""
安全和认证工具函数
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from shared.config import settings
from shared.database import get_db, User

# OAuth2密码Bearer令牌
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    return bcrypt.checkpw(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
    
    Returns:
        JWT令牌字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # 使用JWT_SECRET_KEY，如果没有则使用DASHSCOPE_API_KEY作为fallback
    secret_key = getattr(settings, "JWT_SECRET_KEY", None) or settings.DASHSCOPE_API_KEY
    
    encoded_jwt = jwt.encode(
        to_encode,
        secret_key,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前用户
    
    Args:
        token: JWT令牌
        db: 数据库会话
    
    Returns:
        用户对象
    
    Raises:
        HTTPException: 凭证无效
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        secret_key = getattr(settings, "JWT_SECRET_KEY", None) or settings.DASHSCOPE_API_KEY
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户
    
    Args:
        current_user: 当前用户
    
    Returns:
        活跃用户对象
    
    Raises:
        HTTPException: 用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

