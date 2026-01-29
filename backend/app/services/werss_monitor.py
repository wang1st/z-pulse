"""
WeRSS Token监控服务

监控微信公众号登录token状态，在即将过期时发送提醒邮件
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from datetime import datetime, timedelta
from typing import Optional
import requests
import secrets
from shared.database.database import SessionLocal
from shared.database.models import OfficialAccount, OneTimeToken
from shared.config import settings
from shared.utils import get_logger
from backend.app.services.email_service import send_email_raw

logger = get_logger("werss_monitor")


# WeRSS API配置
WERSS_BASE_URL = settings.RSS_BASE_URL  # http://localhost:8080
WERSS_SECRET = settings.WERSS_SECRET_KEY


def get_werss_token_status(account_id: str) -> Optional[dict]:
    """
    查询WeRSS中公众号的token状态

    Args:
        account_id: weRSS feed_id

    Returns:
        Token状态信息，包含expiry_date等
    """
    try:
        url = f"{WERSS_BASE_URL}/api/feeds/{account_id}"
        headers = {
            "X-Secret": WERSS_SECRET
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # 从feed信息中提取token过期时间
        # WeRSS通常在feed对象中包含updated_at或类似字段
        return {
            "account_id": account_id,
            "last_update": data.get("updated_at"),
            "title": data.get("title", ""),
            "status": data.get("status", "unknown")
        }

    except Exception as e:
        logger.error(f"Failed to get token status for {account_id}: {e}")
        return None


def check_all_tokens() -> list[dict]:
    """
    检查所有公众号的token状态

    Returns:
        即将过期的token列表
    """
    db = SessionLocal()
    expiring_soon = []

    try:
        # 查询所有启用的公众号
        accounts = db.query(OfficialAccount).filter(
            OfficialAccount.is_active == True,
            OfficialAccount.werss_feed_id.isnot(None)
        ).all()

        logger.info(f"Checking {len(accounts)} WeRSS accounts for token expiry")

        # 假设token有效期为4天（96小时）
        # 实际应该从WeRSS API获取，这里做估算
        TOKEN_VALIDITY_HOURS = 96

        for account in accounts:
            status = get_werss_token_status(account.werss_feed_id)

            if not status:
                continue

            # 如果没有更新时间，跳过
            if not status.get("last_update"):
                continue

            # 计算token剩余时间
            try:
                last_update = datetime.fromisoformat(
                    status["last_update"].replace('Z', '+00:00')
                )
                expiry_time = last_update + timedelta(hours=TOKEN_VALIDITY_HOURS)
                remaining = expiry_time - datetime.now()

                # 如果剩余时间小于24小时，加入提醒列表
                if remaining.total_seconds() < 24 * 3600:
                    expiring_soon.append({
                        "account": account,
                        "expiry_time": expiry_time,
                        "remaining_hours": remaining.total_seconds() / 3600,
                        "status": status
                    })

            except Exception as e:
                logger.warning(f"Failed to calculate expiry for {account.name}: {e}")
                continue

        return expiring_soon

    finally:
        db.close()


def generate_relogin_token(account_id: Optional[str] = None) -> str:
    """
    生成一次性重新登录token并保存到数据库

    Args:
        account_id: 关联的公众号ID（可选）

    Returns:
        一次性token字符串
    """
    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta(hours=24)

    db = SessionLocal()
    try:
        one_time_token = OneTimeToken(
            token=token,
            purpose="werss_relogin",
            expiry=expiry,
            context={"account_id": account_id} if account_id else None
        )
        db.add(one_time_token)
        db.commit()

        logger.info(f"Generated relogin token: {token[:8]}... (expires {expiry})")
        return token

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save relogin token: {e}")
        raise
    finally:
        db.close()


def send_token_expiry_alert(expiring_accounts: list[dict]):
    """
    发送token过期提醒邮件

    Args:
        expiring_accounts: 即将过期的账号列表
    """
    from jinja2 import Template

    db = SessionLocal()
    try:
        for item in expiring_accounts:
            account = item["account"]
            expiry_time = item["expiry_time"]
            remaining_hours = item["remaining_hours"]

            # 生成重新登录token（关联公众号ID）
            relogin_token = generate_relogin_token(account_id=account.werss_feed_id)

            # 构建重新登录URL
            relogin_url = f"{settings.WEB_URL}/we-rss-relogin?token={relogin_token}"

            # 邮件模板
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .alert { background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .btn { display: inline-block; padding: 12px 24px; background: #dc3545; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }
                    .info { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>⚠️ 微信公众号Token即将过期</h2>

                    <div class="alert">
                        <strong>账号：</strong> {{account_name}}<br>
                        <strong>过期时间：</strong> {{expiry_time}}<br>
                        <strong>剩余时间：</strong> {{remaining_hours}} 小时
                    </div>

                    <p>您的微信公众号抓取token即将过期，过期后将无法正常抓取文章。</p>

                    <p><strong>受影响功能：</strong></p>
                    <ul>
                        <li>公众号文章自动抓取</li>
                        <li>晨报数据完整性</li>
                    </ul>

                    <div class="info">
                        <h3>✅ 解决方法（仅需30秒）：</h3>
                        <ol>
                            <li>点击下方按钮直接跳转到扫码页面</li>
                            <li>使用微信扫描二维码</li>
                            <li>确认登录</li>
                            <li>完成！无需其他操作</li>
                        </ol>
                    </div>

                    <p><a href="{{relogin_url}}" class="btn">📱 点击此处直接扫码重新登录</a></p>

                    <p style="color: #666; font-size: 12px;">
                        此链接24小时内有效，点击后可直接进入扫码页面，<strong>无需登录后台</strong>。<br>
                        如果链接失效，请联系管理员重新生成。
                    </p>
                </div>
            </body>
            </html>
            """

            # 渲染模板
            template = Template(html_template)
            html_content = template.render(
                account_name=account.name,
                expiry_time=expiry_time.strftime("%Y-%m-%d %H:%M"),
                remaining_hours=f"{remaining_hours:.1f}",
                relogin_url=relogin_url
            )

            # 发送邮件给所有管理员
            subject = f"⚠️ 【重要】微信Token即将过期 - {account.name}"

            for admin_email in settings.ADMIN_EMAILS:
                try:
                    send_email_raw(
                        to_email=admin_email,
                        subject=subject,
                        html_content=html_content
                    )
                    logger.info(f"Sent token expiry alert to {admin_email} for {account.name}")
                except Exception as e:
                    logger.error(f"Failed to send email to {admin_email}: {e}")

    finally:
        db.close()


def monitor_tokens():
    """
    主函数：检查所有token并发送提醒
    """
    logger.info("Starting WeRSS token monitoring...")

    expiring_accounts = check_all_tokens()

    if expiring_accounts:
        logger.warning(f"Found {len(expiring_accounts)} tokens expiring soon")
        send_token_expiry_alert(expiring_accounts)
    else:
        logger.info("All tokens are healthy")

    return len(expiring_accounts)


if __name__ == "__main__":
    import sys
    sys.exit(monitor_tokens())
