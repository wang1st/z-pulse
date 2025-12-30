"""
订阅管理路由 - 实现Double Opt-In
"""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from shared.database import get_db, Subscriber
from shared.config import settings
from shared.utils import get_logger
from ..services.email_service import send_verification_email, email_config_status

router = APIRouter()
logger = get_logger("api.subscriptions")


class SubscribeRequest(BaseModel):
    """订阅请求模型"""
    email: EmailStr


class SubscribeResponse(BaseModel):
    """订阅响应模型"""
    message: str
    email: str


@router.post("/", response_model=SubscribeResponse)
async def subscribe_user(
    request: SubscribeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    用户订阅请求 - Double Opt-In第一步
    
    流程：
    1. 创建订阅记录（is_active=False）
    2. 生成安全令牌
    3. 异步发送验证邮件
    4. 立即返回响应
    """
    email = request.email

    # 邮件配置自检：避免“提示成功但实际上不发信”的假成功
    email_ok, email_reason = email_config_status()
    
    # 检查是否已订阅
    existing = db.query(Subscriber).filter(Subscriber.email == email).first()
    
    if existing:
        if existing.is_active:
            return SubscribeResponse(
                message="该邮箱已经订阅",
                email=email
            )
        else:
            # 重新发送验证邮件
            token = secrets.token_urlsafe(32)
            existing.verification_token = token
            existing.token_expiry = datetime.utcnow() + timedelta(hours=24)
            db.commit()
            
            if email_ok: background_tasks.add_task(send_verification_email, email=email, token=token)
            else:
                logger.error(
                    f"Email not configured; verification email not sent. "
                    f"email={email}, reason={email_reason}"
            )
            
            return SubscribeResponse(
                message="验证邮件已发送（如未收到请检查垃圾箱），或稍后重试",
                email=email
            )
    
    # 创建新订阅（未激活状态）
    token = secrets.token_urlsafe(32)  # 使用安全的随机令牌
    
    subscriber = Subscriber(
        email=email,
        is_active=False,  # 关键：初始状态为未激活
        verification_token=token,
        token_expiry=datetime.utcnow() + timedelta(hours=24)
    )
    
    db.add(subscriber)
    db.commit()
    
    logger.info(f"New subscription request: {email}")
    
    # 后台任务：发送验证邮件
    if email_ok: background_tasks.add_task(send_verification_email, email=email, token=token)
    else:
        logger.error(
            f"Email not configured; verification email not sent. "
            f"email={email}, reason={email_reason}"
        )
        message = "订阅已登记，但邮件服务暂不可用，无法发送验证邮件，请联系管理员或稍后重试。"
    
    return SubscribeResponse(
        message=message,
        email=email
    )


@router.get("/verify/{token}")
async def verify_subscription(
    token: str,
    db: Session = Depends(get_db)
):
    """
    验证订阅 - Double Opt-In第二步
    
    用户点击邮件中的链接后到达此端点
    """
    # 查找令牌
    subscriber = db.query(Subscriber).filter(
        Subscriber.verification_token == token
    ).first()
    
    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail="无效的验证链接"
        )
    
    # 检查令牌是否过期
    if subscriber.token_expiry and subscriber.token_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="验证链接已过期，请重新订阅"
        )
    
    # 激活订阅
    subscriber.is_active = True
    subscriber.verification_token = None  # 使令牌失效
    subscriber.activated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Subscription activated: {subscriber.email}")
    
    # 重定向到前端成功页面（避免浏览器显示 JSON）
    return RedirectResponse(
        url=f"{settings.WEB_URL}/subscription-confirmed",
        status_code=303
    )


@router.post("/unsubscribe")
async def unsubscribe_user(
    request: SubscribeRequest,
    db: Session = Depends(get_db)
):
    """
    取消订阅
    """
    subscriber = db.query(Subscriber).filter(
        Subscriber.email == request.email
    ).first()
    
    if not subscriber:
        raise HTTPException(status_code=404, detail="未找到该订阅")
    
    # 软删除：设置为不活跃
    subscriber.is_active = False
    db.commit()
    
    logger.info(f"Subscription cancelled: {request.email}")
    
    return {"message": "订阅已取消"}

