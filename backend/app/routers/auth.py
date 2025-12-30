"""
认证路由
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from shared.database import get_db, User
from shared.config import settings
from shared.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_active_user,
)
from shared.utils import get_logger

router = APIRouter()
logger = get_logger("api.auth")


class Token(BaseModel):
    """Token响应模型"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """用户创建模型"""
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    is_superuser: bool = False


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录，获取访问令牌
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    logger.info(f"User {user.username} logged in")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户信息"""
    return current_user


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    用户注册（仅限超级用户或首次注册）
    """
    # 检查是否已有用户
    existing_users = db.query(User).count()
    
    # 如果已有用户，需要超级用户权限
    if existing_users > 0:
        # 这里可以添加权限检查，暂时允许注册
        pass
    
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 创建新用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_superuser=user_data.is_superuser if existing_users == 0 else False,  # 第一个用户自动成为超级用户
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"New user registered: {user.username}")
    
    return user

