"""
公众号管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from shared.database import get_db, OfficialAccount, User
from ..security import get_current_active_user

router = APIRouter()


class AccountResponse(BaseModel):
    """公众号响应模型"""
    id: int
    name: str
    wechat_id: str
    description: Optional[str]
    level: str
    region: Optional[str]
    is_active: bool
    total_articles: int
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[AccountResponse])
async def list_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    level: Optional[str] = None,
    region: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取公众号列表
    """
    query = db.query(OfficialAccount)
    
    if level:
        query = query.filter(OfficialAccount.level == level)
    
    if region:
        query = query.filter(OfficialAccount.region == region)
    
    if is_active is not None:
        query = query.filter(OfficialAccount.is_active == is_active)
    
    accounts = query.offset(skip).limit(limit).all()
    return accounts


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取公众号详情
    """
    account = db.query(OfficialAccount).filter(
        OfficialAccount.id == account_id
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account

