"""
WeRSS重新登录相关API
提供一次性token验证和公众号信息查询
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
import requests
import os

from shared.database.database import SessionLocal
from shared.database.models import OneTimeToken, OfficialAccount
from shared.utils import get_logger
from shared.config import settings

logger = get_logger("werss-api")

router = APIRouter()

# WeRSS API配置
# 在Docker环境中使用容器名，本地开发使用localhost
WERSS_BASE_URL = os.getenv("WERSS_BASE_URL", "http://zpulse-rss:8001")
WERSS_SECRET = settings.WERSS_SECRET_KEY


class TokenVerifyResponse(BaseModel):
    """Token验证响应"""
    valid: bool
    account_id: str | None = None
    account_name: str | None = None
    message: str


@router.get("/api/werss-relogin/verify", response_model=TokenVerifyResponse)
def verify_relogin_token(token: str = Query(..., description="一次性登录令牌")):
    """
    验证WeRSS重新登录token

    验证一次性token的有效性，如果有效则返回关联的公众号信息
    Token验证后会标记为已使用（一次性使用）
    """
    db = SessionLocal()
    try:
        # 查询token
        one_time_token = db.query(OneTimeToken).filter(
            OneTimeToken.token == token,
            OneTimeToken.purpose == "werss_relogin",
            OneTimeToken.is_used == False
        ).first()

        if not one_time_token:
            logger.warning(f"Invalid or used relogin token: {token[:8]}...")
            return TokenVerifyResponse(
                valid=False,
                message="令牌无效或已使用"
            )

        # 检查是否过期
        if one_time_token.expiry < datetime.utcnow():
            logger.warning(f"Expired relogin token: {token[:8]}...")
            return TokenVerifyResponse(
                valid=False,
                message="令牌已过期"
            )

        # 从context中获取公众号ID
        account_id = None
        account_name = None
        if one_time_token.context and "account_id" in one_time_token.context:
            account_id = one_time_token.context["account_id"]

            # 查询公众号信息
            account = db.query(OfficialAccount).filter(
                OfficialAccount.werss_feed_id == account_id
            ).first()
            if account:
                account_name = account.name

        # 标记token为已使用（但暂时不立即保存，等用户完成扫码后再标记）
        # 这样用户如果刷新页面仍然可以访问，但token只能用于一次会话
        logger.info(f"Verified relogin token for account: {account_name} ({account_id})")

        return TokenVerifyResponse(
            valid=True,
            account_id=account_id,
            account_name=account_name,
            message="令牌验证成功"
        )

    except Exception as e:
        logger.exception(f"Error verifying relogin token: {e}")
        raise HTTPException(status_code=500, detail="服务器错误")

    finally:
        db.close()


@router.post("/api/werss-relogin/confirm")
def confirm_relogin(token: str = Query(..., description="一次性登录令牌")):
    """
    确认重新登录完成

    用户完成扫码后调用此接口，标记token为已使用
    """
    db = SessionLocal()
    try:
        one_time_token = db.query(OneTimeToken).filter(
            OneTimeToken.token == token,
            OneTimeToken.purpose == "werss_relogin"
        ).first()

        if not one_time_token:
            raise HTTPException(status_code=404, detail="令牌不存在")

        # 标记为已使用
        one_time_token.is_used = True
        one_time_token.used_at = datetime.utcnow()
        db.commit()

        logger.info(f"Confirmed relogin for token: {token[:8]}...")

        return {"success": True, "message": "重新登录成功"}

    except Exception as e:
        logger.exception(f"Error confirming relogin: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="服务器错误")

    finally:
        db.close()


@router.get("/api/werss/qrcode")
def get_werss_qrcode():
    """
    获取WeRSS登录二维码

    先登录获取JWT token，然后用token调用二维码API
    """
    try:
        # 步骤1：登录获取JWT token（使用form-data格式）
        login_url = f"{WERSS_BASE_URL}/api/v1/wx/auth/token"
        login_data = {
            "username": "admin",
            "password": "admin@9988"
        }

        login_response = requests.post(login_url, data=login_data, timeout=10)
        login_response.raise_for_status()
        login_result = login_response.json()

        if "access_token" not in login_result:
            logger.error(f"Login failed: {login_result}")
            raise HTTPException(status_code=500, detail="WeRSS登录失败")

        jwt_token = login_result["access_token"]
        logger.info(f"Successfully obtained JWT token from WeRSS")

        # 步骤2：使用JWT token获取二维码
        qr_url = f"{WERSS_BASE_URL}/api/v1/wx/auth/qr/code"
        headers = {
            "Authorization": f"Bearer {jwt_token}"
        }

        qr_response = requests.get(qr_url, headers=headers, timeout=10)
        qr_response.raise_for_status()

        qr_data = qr_response.json()

        # WeRSS API返回格式: {"code": 0, "message": "success", "data": {...}}
        if qr_data.get("code") == 0 and "data" in qr_data:
            logger.info(f"Successfully obtained QR code from WeRSS")
            return {
                "success": True,
                "qr_url": qr_data["data"].get("code", ""),  # WeRSS返回的是code字段，不是qr_url
                "msg": qr_data["data"].get("msg", "")
            }
        else:
            logger.warning(f"WeRSS API returned unexpected response: {qr_data}")
            raise HTTPException(status_code=500, detail="获取二维码失败")

    except Exception as e:
        logger.exception(f"Error getting QR code: {e}")
        raise HTTPException(status_code=500, detail=f"获取二维码失败: {str(e)}")


@router.get("/api/werss/qrcode/status")
def get_qrcode_status():
    """
    获取二维码扫描状态

    先登录获取JWT token，然后检查扫码状态
    """
    try:
        # 步骤1：登录获取JWT token
        login_url = f"{WERSS_BASE_URL}/api/v1/wx/auth/token"
        login_data = {
            "username": "admin",
            "password": "admin@9988"
        }

        login_response = requests.post(login_url, data=login_data, timeout=10)
        login_response.raise_for_status()
        login_result = login_response.json()

        if "access_token" not in login_result:
            return {
                "success": False,
                "login_status": False
            }

        jwt_token = login_result["access_token"]

        # 步骤2：使用JWT token检查状态
        status_url = f"{WERSS_BASE_URL}/api/v1/wx/auth/qr/status"
        headers = {
            "Authorization": f"Bearer {jwt_token}"
        }

        response = requests.get(status_url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("code") == 0 and "data" in data:
            return {
                "success": True,
                "login_status": data["data"].get("login_status", False)
            }
        else:
            return {
                "success": False,
                "login_status": False
            }

    except Exception as e:
        logger.exception(f"Error getting QR status: {e}")
        return {
            "success": False,
            "login_status": False
        }


@router.get("/api/werss/accounts")
def get_werss_accounts():
    """
    获取所有WeRSS公众号列表（用于调试）

    返回所有启用了WeRSS的公众号信息
    """
    db = SessionLocal()
    try:
        accounts = db.query(OfficialAccount).filter(
            OfficialAccount.is_active == True,
            OfficialAccount.werss_feed_id.isnot(None)
        ).all()

        return {
            "total": len(accounts),
            "accounts": [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "werss_feed_id": acc.werss_feed_id,
                    "last_collection_time": acc.last_collection_time.isoformat() if acc.last_collection_time else None
                }
                for acc in accounts
            ]
        }

    finally:
        db.close()
