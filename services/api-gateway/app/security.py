"""
安全和认证模块
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from shared.config import settings
from shared.database import get_db, User

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2密码Bearer令牌
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
    
    Returns:
        是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码哈希
    
    Args:
        password: 明文密码
    
    Returns:
        哈希密码
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间间隔
    
    Returns:
        JWT令牌
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.API_SECRET_KEY,
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
        payload = jwt.decode(
            token,
            settings.API_SECRET_KEY,
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
        用户对象
    
    Raises:
        HTTPException: 用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user


def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    获取当前超级用户
    
    Args:
        current_user: 当前用户
    
    Returns:
        用户对象
    
    Raises:
        HTTPException: 权限不足
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges"
        )
    
    return current_user

