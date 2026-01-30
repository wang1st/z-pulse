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
# 在Docker环境中使用容器名，本地开发使用localhost
WERSS_BASE_URL = os.getenv("WERSS_BASE_URL", settings.RSS_BASE_URL)
WERSS_SECRET = settings.WERSS_SECRET_KEY


def get_werss_token_status(account_id: str) -> Optional[dict]:
    """
    查询WeRSS全局token状态

    WeRSS使用全局token，不是每个公众号单独的token
    Token信息存储在 /app/data/wx.lic 文件中

    Args:
        account_id: weRSS feed_id (未使用，保留用于兼容性)

    Returns:
        Token状态信息，包含expiry_time等
    """
    try:
        # 调用WeRSS系统信息API获取全局token状态
        url = f"{WERSS_BASE_URL}/sys/info"
        headers = {
            "X-Secret": WERSS_SECRET
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # WeRSS API返回格式: {"code": 200, "data": {...}}
        if data.get("code") == 200 and "data" in data:
            wx_info = data["data"].get("wx", {})
            expiry_time_str = wx_info.get("expiry_time", "")
            is_login = wx_info.get("login", False)

            return {
                "account_id": account_id,
                "expiry_time": expiry_time_str,
                "is_login": is_login,
                "token": wx_info.get("token", "")
            }
        else:
            logger.warning(f"WeRSS API returned unexpected response: {data}")
            return None

    except Exception as e:
        logger.error(f"Failed to get token status: {e}")
        return None


def check_all_tokens() -> list[dict]:
    """
    检查WeRSS全局token状态

    WeRSS使用全局token，所有公众号共用同一个token
    只需要检查一次全局token状态即可

    Returns:
        即将过期的token列表（实际上只有一个全局token）
    """
    db = SessionLocal()
    expiring_soon = []

    try:
        # WeRSS使用全局token，只需要检查一次
        logger.info("Checking WeRSS global token status")

        # 获取全局token状态（account_id参数不重要）
        status = get_werss_token_status("global")

        if not status:
            # 无法获取状态，可能token已失效
            logger.warning("Could not get WeRSS token status, token may be expired")

            # 获取第一个启用的公众号用于提醒
            account = db.query(OfficialAccount).filter(
                OfficialAccount.is_active == True,
                OfficialAccount.werss_feed_id.isnot(None)
            ).first()

            if account:
                expiring_soon.append({
                    "account": account,
                    "expiry_time": datetime.now(),
                    "remaining_hours": 0,
                    "status": {"error": "无法获取token状态"}
                })
            return expiring_soon

        # 检查是否已登录
        if not status.get("is_login"):
            logger.warning("WeRSS token is not logged in")

            account = db.query(OfficialAccount).filter(
                OfficialAccount.is_active == True,
                OfficialAccount.werss_feed_id.isnot(None)
            ).first()

            if account:
                expiring_soon.append({
                    "account": account,
                    "expiry_time": datetime.now(),
                    "remaining_hours": 0,
                    "status": status
                })
            return expiring_soon

        # 解析过期时间
        expiry_time_str = status.get("expiry_time", "")
        if not expiry_time_str:
            logger.warning("No expiry time in WeRSS token status")
            return expiring_soon

        try:
            # 解析过期时间 (格式: "2026-01-17 16:40:16")
            expiry_time = datetime.strptime(expiry_time_str, "%Y-%m-%d %H:%M:%S")
            remaining = expiry_time - datetime.now()
            remaining_hours = remaining.total_seconds() / 3600

            logger.info(f"Token expiry time: {expiry_time_str}, remaining: {remaining_hours:.1f} hours")

            # 如果剩余时间小于24小时，加入提醒列表
            if remaining_hours < 24:
                logger.warning(f"Token expiring soon: {remaining_hours:.1f} hours remaining")

                # 获取一个公众号账号用于提醒
                account = db.query(OfficialAccount).filter(
                    OfficialAccount.is_active == True,
                    OfficialAccount.werss_feed_id.isnot(None)
                ).first()

                if account:
                    expiring_soon.append({
                        "account": account,
                        "expiry_time": expiry_time,
                        "remaining_hours": remaining_hours,
                        "status": status
                    })

        except ValueError as e:
            logger.error(f"Failed to parse expiry time '{expiry_time_str}': {e}")

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
            # 使用环境变量WEB_URL来构建完整URL
            base_url = settings.WEB_URL if hasattr(settings, 'WEB_URL') else "http://localhost:8899"
            relogin_url = f"{base_url}/we-rss-qrcode-direct"

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
                            <li>点击下方按钮直接打开二维码页面</li>
                            <li>使用微信扫描二维码</li>
                            <li>在手机上确认登录</li>
                            <li>完成！页面会自动显示"登录成功"</li>
                        </ol>
                    </div>

                    <p><a href="{{relogin_url}}" class="btn" target="_blank">📱 打开二维码扫码页面</a></p>

                    <p style="color: #666; font-size: 12px;">
                        <strong>直接访问：</strong> <a href="{{relogin_url}}">{{relogin_url}}</a><br>
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

            import asyncio

            async def send_alerts():
                for admin_email in settings.ADMIN_EMAILS:
                    try:
                        await send_email_raw(
                            to_email=admin_email,
                            subject=subject,
                            html_content=html_content
                        )
                        logger.info(f"Sent token expiry alert to {admin_email} for {account.name}")
                    except Exception as e:
                        logger.error(f"Failed to send email to {admin_email}: {e}")

            # 运行异步发送
            asyncio.run(send_alerts())

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
