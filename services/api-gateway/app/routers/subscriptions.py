"""
订阅管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional

from shared.database import get_db, Subscription, User, SubscriptionStatus
from ..security import get_current_active_user

router = APIRouter()


class SubscriptionCreate(BaseModel):
    """订阅创建模型"""
    email: EmailStr
    report_types: List[str]
    regions: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class SubscriptionResponse(BaseModel):
    """订阅响应模型"""
    id: int
    email: str
    report_types: List[str]
    regions: Optional[List[str]]
    keywords: Optional[List[str]]
    status: str
    total_sent: int
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户的订阅列表
    """
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).all()
    
    return subscriptions


@router.post("/", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    创建订阅
    """
    subscription = Subscription(
        user_id=current_user.id,
        email=subscription_data.email,
        report_types=subscription_data.report_types,
        regions=subscription_data.regions,
        keywords=subscription_data.keywords,
        status=SubscriptionStatus.ACTIVE
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    return subscription


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    更新订阅
    """
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    subscription.email = subscription_data.email
    subscription.report_types = subscription_data.report_types
    subscription.regions = subscription_data.regions
    subscription.keywords = subscription_data.keywords
    
    db.commit()
    db.refresh(subscription)
    
    return subscription


@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    删除订阅
    """
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    db.delete(subscription)
    db.commit()
    
    return {"message": "Subscription deleted successfully"}

