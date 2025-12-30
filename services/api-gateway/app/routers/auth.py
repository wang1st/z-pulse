"""
认证路由
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from shared.database import get_db, User
from shared.config import settings
from ..security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    get_current_active_user
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserCreate(BaseModel):
    """用户创建模型"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token响应模型"""
    access_token: str
    token_type: str


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    用户注册
    """
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
        is_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录，获取访问令牌
    """
    # 验证用户
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
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户信息
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    full_name: Optional[str] = None,
    email: Optional[EmailStr] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    """
    if full_name is not None:
        current_user.full_name = full_name
    
    if email is not None:
        # 检查邮箱是否已被其他用户使用
        existing = db.query(User).filter(
            User.email == email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = email
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

