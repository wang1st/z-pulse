"""
邮件发送服务 - 支持SendGrid和Brevo（原Sendinblue）
"""
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

import httpx

from shared.config import settings
from shared.utils import get_logger

logger = get_logger("email-service")

# 初始化Jinja2模板
template_dir = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

def _is_blank(value: Optional[str]) -> bool:
    return value is None or str(value).strip() == ""


def email_config_status() -> tuple[bool, str]:
    """
    检查邮件服务是否已正确配置。

    Returns:
        (ok, reason)  ok=True 表示可发送；否则 reason 描述缺失项/错误。
    """
    provider = (settings.EMAIL_PROVIDER or "").lower().strip()
    if not provider:
        return False, "EMAIL_PROVIDER 未配置"

    if _is_blank(settings.EMAIL_FROM):
        return False, "EMAIL_FROM 未配置"

    if provider == "sendgrid":
        if _is_blank(settings.SENDGRID_API_KEY):
            return False, "SENDGRID_API_KEY 未配置"
        return True, ""

    if provider == "brevo":
        if _is_blank(settings.BREVO_API_KEY):
            return False, "BREVO_API_KEY 未配置"
        return True, ""

    if provider == "mailgun":
        if _is_blank(settings.MAILGUN_API_KEY) or _is_blank(settings.MAILGUN_DOMAIN):
            return False, "MAILGUN_API_KEY 或 MAILGUN_DOMAIN 未配置"
        return True, ""

    return False, f"不支持的 EMAIL_PROVIDER: {provider}"


def _get_brevo_sdk():
    """
    Brevo Python SDK 在不同版本/历史包名下可能暴露不同模块名。
    这里做兼容导入，避免运行时 ImportError 导致“假成功不发信”。
    """
    try:
        import brevo as sdk  # type: ignore
        return sdk
    except ImportError:
        # 兼容历史 Sendinblue SDK 命名
        try:
            import sib_api_v3_sdk as sdk  # type: ignore
            return sdk
        except ImportError as e:
            raise ImportError(
                "Brevo SDK not installed. Install `brevo-python` (recommended) or `sib-api-v3-sdk`."
            ) from e


def _brevo_base_url() -> str:
    return "https://api.brevo.com/v3"


async def _brevo_send_transactional_email(
    *,
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
):
    """
    Brevo 事务邮件 REST 调用（不依赖 SDK）。
    Docs: /smtp/email
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": str(settings.BREVO_API_KEY),
    }
    payload = {
        "sender": {"name": settings.EMAIL_FROM_NAME, "email": settings.EMAIL_FROM},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }
    if not _is_blank(text_content):
        payload["textContent"] = str(text_content)
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{_brevo_base_url()}/smtp/email", headers=headers, json=payload)
        if resp.status_code >= 400:
            # Brevo 会返回 JSON 错误体，打印出来方便定位（如 sender 未验证）
            raise RuntimeError(f"Brevo REST error {resp.status_code}: {resp.text}")
        return resp.json()


def _get_email_client():
    """根据配置获取邮件客户端"""
    provider = settings.EMAIL_PROVIDER.lower()
    
    if provider == "sendgrid":
        from sendgrid import SendGridAPIClient
        if _is_blank(settings.SENDGRID_API_KEY):
            raise ValueError("SendGrid API key not configured")
        return ("sendgrid", SendGridAPIClient(settings.SENDGRID_API_KEY))
    
    elif provider == "brevo":
        # 优先 SDK；若环境里没有 SDK（或不方便装包），自动回退到 REST 调用。
        try:
            sdk = _get_brevo_sdk()
            if _is_blank(settings.BREVO_API_KEY):
                raise ValueError("Brevo API key not configured")

            if hasattr(sdk, "Configuration"):
                configuration = sdk.Configuration()
                configuration.api_key["api-key"] = settings.BREVO_API_KEY
                api_client = sdk.ApiClient(configuration)
            else:
                api_client = sdk.ApiClient()
                if hasattr(api_client, "set_api_key"):
                    api_client.set_api_key("api-key", settings.BREVO_API_KEY)
            return ("brevo_sdk", sdk.TransactionalEmailsApi(api_client), sdk)
        except Exception as e:
            logger.warning(f"Brevo SDK unavailable; falling back to REST. err={e}")
            return ("brevo_rest", None)
    
    elif provider == "mailgun":
        import requests
        if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
            raise ValueError("Mailgun API key or domain not configured")
        return ("mailgun", {
            "api_key": settings.MAILGUN_API_KEY,
            "domain": settings.MAILGUN_DOMAIN
        })
    
    else:
        raise ValueError(f"Unsupported email provider: {provider}. Supported: sendgrid, brevo, mailgun")


async def send_verification_email(email: str, token: str):
    """
    发送验证邮件（Double Opt-In）
    支持SendGrid、Brevo和Mailgun
    
    Args:
        email: 收件人邮箱
        token: 验证令牌
    """
    try:
        ok, reason = email_config_status()
        if not ok:
            logger.error(f"Email not configured, skip sending verification email: {reason}")
            return

        verification_url = f"{settings.WEB_URL}/api/subscribe/verify/{token}"
        
        # 渲染邮件模板
        template = jinja_env.get_template('verification_email.html')
        html_content = template.render(
            verification_url=verification_url,
            web_url=settings.WEB_URL
        )
        
        provider_client = _get_email_client()
        provider = provider_client[0]
        client = provider_client[1]
        
        if provider == "sendgrid":
            from sendgrid.helpers.mail import Mail, Email, To, Content
            message = Mail(
                from_email=Email(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME),
                to_emails=To(email),
                subject="请确认您的订阅 - Z-Pulse 财政晨报",
                html_content=Content("text/html", html_content)
            )
            response = client.send(message)
            logger.info(f"Verification email sent via SendGrid to {email}, status: {response.status_code}")
        
        elif provider == "brevo_sdk":
            sdk = provider_client[2]
            send_smtp_email = sdk.SendSmtpEmail(
                sender=sdk.SendSmtpEmailSender(
                    email=settings.EMAIL_FROM,
                    name=settings.EMAIL_FROM_NAME
                ),
                to=[sdk.SendSmtpEmailTo(email=email)],
                subject="请确认您的订阅 - Z-Pulse 财政晨报",
                html_content=html_content
            )
            response = client.send_transac_email(send_smtp_email)
            message_id = getattr(response, "message_id", None)
            logger.info(f"Verification email sent via Brevo(SDK) to {email}, message_id: {message_id}")

        elif provider == "brevo_rest":
            data = await _brevo_send_transactional_email(
                to_email=email,
                subject="请确认您的订阅 - Z-Pulse 财政日报",
                html_content=html_content,
            )
            # REST 返回里通常含 messageId / messageIds（按版本）
            logger.info(f"Verification email sent via Brevo(REST) to {email}, resp: {data}")
        
        elif provider == "mailgun":
            import requests
            response = requests.post(
                f"https://api.mailgun.net/v3/{client['domain']}/messages",
                auth=("api", client["api_key"]),
                data={
                    "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
                    "to": email,
                    "subject": "请确认您的订阅 - Z-Pulse 财政晨报",
                    "html": html_content
                }
            )
            response.raise_for_status()
            logger.info(f"Verification email sent via Mailgun to {email}, status: {response.status_code}")
        
    except Exception as e:
        # 后台任务失败不应让接口“假成功”，这里记录堆栈并吞掉异常
        logger.exception(f"Failed to send verification email to {email}: {str(e)}")
        return


async def send_daily_report(
    email: str,
    report_html: str,
    report_date: str,
    report_text: Optional[str] = None,
    pdf_attachment: Optional[bytes] = None,
    pdf_filename: Optional[str] = None,
) -> bool:
    """
    发送日报（支持PDF附件）
    支持SendGrid、Brevo和Mailgun

    Args:
        email: 收件人邮箱
        report_html: 报告内容（HTML，建议为后端渲染后的安全HTML）
        report_date: 报告日期
        report_text: 纯文本版本（可选）
        pdf_attachment: PDF文件字节内容（可选）
        pdf_filename: PDF文件名（可选）
    """
    try:
        ok, reason = email_config_status()
        if not ok:
            logger.error(f"Email not configured, skip sending daily report: {reason}")
            return False

        # 直接使用report_html，不使用模板包装
        html_content = report_html

        provider_client = _get_email_client()
        provider = provider_client[0]
        client = provider_client[1]

        # Use plain text as email body (report_text includes web link)
        # HTML content is not used for email body, only for PDF generation
        if not report_text or _is_blank(report_text):
            logger.warning("Daily report text is empty, using fallback")
            email_body_text = "（晨报内容为空）"
        else:
            email_body_text = str(report_text)

        if provider == "sendgrid":
            from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileType, Disposition, ContentId

            # Build email with HTML content
            message = Mail(
                from_email=Email(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME),
                to_emails=To(email),
                subject=f"财政晨报 - {report_date}",
                html_content=Content("text/html", html_content),  # 使用模板渲染后的HTML（包含底部链接）
            )

            # 如果有纯文本内容，也添加
            if report_text and not _is_blank(report_text):
                message.add_content(Content("text/plain", str(report_text)))

            # 不再添加PDF附件 - 永久禁用以避免内存不足
            logger.info("PDF attachment disabled to prevent OOM errors")

            response = client.send(message)
            logger.info(f"Daily report sent via SendGrid to {email}, status: {response.status_code}")
            return True

        elif provider == "brevo_sdk":
            sdk = provider_client[2]
            # Use HTML content
            kwargs = dict(
                sender=sdk.SendSmtpEmailSender(
                    email=settings.EMAIL_FROM,
                    name=settings.EMAIL_FROM_NAME
                ),
                to=[sdk.SendSmtpEmailTo(email=email)],
                subject=f"财政晨报 - {report_date}",
                html_content=html_content  # 使用模板渲染后的HTML（包含底部链接）
            )

            # 如果有纯文本内容，也添加
            if report_text and not _is_blank(report_text):
                kwargs["text_content"] = str(report_text)

            # 不再添加PDF附件 - 永久禁用以避免内存不足
            logger.info("PDF attachment disabled to prevent OOM errors")

            send_smtp_email = sdk.SendSmtpEmail(**kwargs)
            response = client.send_transac_email(send_smtp_email)
            message_id = getattr(response, "message_id", None)
            logger.info(f"Daily report sent via Brevo(SDK) to {email}, message_id: {message_id}")
            return True

        elif provider == "brevo_rest":
            # Brevo REST API with HTML body
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": str(settings.BREVO_API_KEY),
            }

            # 构建邮件内容，优先使用HTML，纯文本作为fallback
            email_body = {
                "sender": {"name": settings.EMAIL_FROM_NAME, "email": settings.EMAIL_FROM},
                "to": [{"email": email}],
                "subject": f"财政晨报 - {report_date}",
                "htmlContent": html_content,  # 使用模板渲染后的HTML（包含底部链接）
            }

            # 如果有纯文本内容，也添加（作为fallback）
            if report_text and not _is_blank(report_text):
                email_body["textContent"] = str(report_text)

            # 不再添加PDF附件 - 永久禁用以避免内存不足
            logger.info("PDF attachment disabled to prevent OOM errors")

            async with httpx.AsyncClient() as http_client:
                resp = await http_client.post(
                    f"{_brevo_base_url()}/smtp/email",
                    headers=headers,
                    json=email_body,
                    timeout=30.0
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info(f"Daily report sent via Brevo(REST) to {email}, resp: {data}")
            return True

        elif provider == "mailgun":
            import requests

            # Use plain text only (no HTML)
            data = {
                "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
                "to": email,
                "subject": f"财政晨报 - {report_date}",
                "text": email_body_text,  # Plain text only
            }

            # Mailgun 使用 multipart/form-data 发送附件
            files = {}
            if pdf_attachment and pdf_filename:
                files["attachment"] = (pdf_filename, pdf_attachment, "application/pdf")
                logger.info(f"Attached PDF: {pdf_filename} ({len(pdf_attachment)} bytes)")

            response = requests.post(
                f"https://api.mailgun.net/v3/{client['domain']}/messages",
                auth=("api", client["api_key"]),
                data=data,
                files=files if files else None
            )
            response.raise_for_status()
            logger.info(f"Daily report sent via Mailgun to {email}, status: {response.status_code}")
            return True

    except Exception as e:
        logger.error(f"Failed to send daily report to {email}: {str(e)}")
        raise

    # Should not reach here, but keep safe
    return False


async def send_weekly_report(
    email: str,
    report_html: str,
    report_date: str,
    date_range_str: Optional[str] = None,
    report_text: Optional[str] = None,
    pdf_attachment: Optional[bytes] = None,
    pdf_filename: Optional[str] = None,
) -> bool:
    """
    发送周报（支持PDF附件）
    支持SendGrid、Brevo和Mailgun

    Args:
        email: 收件人邮箱
        report_html: 报告内容（HTML，建议为后端渲染后的安全HTML）
        report_date: 报告日期
        date_range_str: 日期范围字符串（可选，用于标题）
        report_text: 纯文本版本（可选）
        pdf_attachment: PDF文件字节内容（可选）
        pdf_filename: PDF文件名（可选）
    """
    try:
        ok, reason = email_config_status()
        if not ok:
            logger.error(f"Email not configured, skip sending weekly report: {reason}")
            return False

        provider_client = _get_email_client()
        provider = provider_client[0]
        client = provider_client[1]

        # 构建标题
        if date_range_str:
            subject = f"财政周报 - {date_range_str}"
        else:
            subject = f"财政周报 - {report_date}"

        # Use plain text as email body (report_text includes web link)
        # HTML content is not used for email body, only for PDF generation
        if not report_text or _is_blank(report_text):
            logger.warning("Weekly report text is empty, using fallback")
            email_body_text = "（周报内容为空）"
        else:
            email_body_text = str(report_text)

        if provider == "sendgrid":
            from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileType, Disposition, FileContent

            # Build email with plain text only (no HTML)
            message = Mail(
                from_email=Email(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME),
                to_emails=To(email),
                subject=subject,
                plain_text_content=Content("text/plain", email_body_text),
            )

            # 添加PDF附件
            if pdf_attachment and pdf_filename:
                import base64
                encoded_pdf = base64.b64encode(pdf_attachment).decode()
                attachment = Attachment(
                    file_content=FileContent(encoded_pdf),
                    file_type=FileType("application/pdf"),
                    file_name=Disposition(pdf_filename),
                    disposition="attachment",
                    content_id=None
                )
                message.add_attachment(attachment)
                logger.info(f"Attached PDF: {pdf_filename} ({len(pdf_attachment)} bytes)")

            response = client.send(message)
            logger.info(f"Weekly report sent via SendGrid to {email}, status: {response.status_code}")
            return True

        elif provider == "brevo_sdk":
            sdk = provider_client[2]
            # Use plain text only (no HTML)
            kwargs = dict(
                sender=sdk.SendSmtpEmailSender(
                    email=settings.EMAIL_FROM,
                    name=settings.EMAIL_FROM_NAME
                ),
                to=[sdk.SendSmtpEmailTo(email=email)],
                subject=subject,
                text_content=email_body_text  # Plain text only
            )

            # 添加PDF附件
            if pdf_attachment and pdf_filename:
                import base64
                encoded_pdf = base64.b64encode(pdf_attachment).decode()
                attachment = sdk.SendSmtpEmailAttachment(
                    name=pdf_filename,
                    content=encoded_pdf,
                    encoding="base64"
                )
                kwargs["attachment"] = [attachment]
                logger.info(f"Attached PDF: {pdf_filename} ({len(pdf_attachment)} bytes)")

            send_smtp_email = sdk.SendSmtpEmail(**kwargs)
            response = client.send_transac_email(send_smtp_email)
            message_id = getattr(response, "message_id", None)
            logger.info(f"Weekly report sent via Brevo(SDK) to {email}, message_id: {message_id}")
            return True

        elif provider == "brevo_rest":
            # Brevo REST API with plain text body only
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": str(settings.BREVO_API_KEY),
            }

            payload = {
                "sender": {"name": settings.EMAIL_FROM_NAME, "email": settings.EMAIL_FROM},
                "to": [{"email": email}],
                "subject": subject,
                "textContent": email_body_text,  # Plain text only
            }

            # 添加PDF附件
            if pdf_attachment and pdf_filename:
                import base64
                encoded_pdf = base64.b64encode(pdf_attachment).decode()
                payload["attachment"] = [{
                    "name": pdf_filename,
                    "content": encoded_pdf
                }]
                logger.info(f"Attached PDF: {pdf_filename} ({len(pdf_attachment)} bytes)")

            async with httpx.AsyncClient() as http_client:
                resp = await http_client.post(
                    f"{_brevo_base_url()}/smtp/email",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info(f"Weekly report sent via Brevo(REST) to {email}, resp: {data}")
            return True

        elif provider == "mailgun":
            import requests
            client_dict = provider_client[1]
            # Use plain text only (no HTML)
            data = {
                "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
                "to": email,
                "subject": subject,
                "text": email_body_text,  # Plain text only
            }

            files = {}
            if pdf_attachment and pdf_filename:
                files["attachment"] = (pdf_filename, pdf_attachment, "application/pdf")
                logger.info(f"Attached PDF: {pdf_filename} ({len(pdf_attachment)} bytes)")

            response = requests.post(
                f"https://api.mailgun.net/v3/{client_dict['domain']}/messages",
                auth=("api", client_dict["api_key"]),
                data=data,
                files=files if files else None
            )
            response.raise_for_status()
            logger.info(f"Weekly report sent via Mailgun to {email}, status: {response.status_code}")
            return True

    except Exception as e:
        logger.error(f"Failed to send weekly report to {email}: {str(e)}")
        raise

    # Should not reach here, but keep safe
    return False

