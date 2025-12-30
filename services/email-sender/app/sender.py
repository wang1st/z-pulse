"""
邮件发送器
"""
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

from shared.config import settings
from shared.database import Report, Subscription, SubscriptionStatus, ReportType
from shared.utils import get_logger

logger = get_logger("email-sender.sender")


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, db: Session):
        """
        初始化发送器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        
        # 初始化SendGrid客户端
        if settings.EMAIL_PROVIDER == "sendgrid":
            if not settings.SENDGRID_API_KEY:
                raise ValueError("SendGrid API key not configured")
            self.sg_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        else:
            raise ValueError(f"Unsupported email provider: {settings.EMAIL_PROVIDER}")
        
        # 初始化Jinja2模板环境
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def send_report(
        self,
        report_id: int,
        recipients: List[str],
        custom_subject: str = None
    ) -> Dict:
        """
        发送报告邮件
        
        Args:
            report_id: 报告ID
            recipients: 收件人列表
            custom_subject: 自定义主题（可选）
        
        Returns:
            发送结果
        """
        # 获取报告
        report = self.db.query(Report).filter(
            Report.id == report_id
        ).first()
        
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        logger.info(f"Sending report {report_id} to {len(recipients)} recipients")
        
        # 准备邮件内容
        subject = custom_subject or report.title
        html_content = self._render_report_email(report)
        
        # 发送邮件
        success_count = 0
        failed_count = 0
        
        for recipient in recipients:
            try:
                self._send_email(
                    to_email=recipient,
                    subject=subject,
                    html_content=html_content
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send to {recipient}: {str(e)}")
                failed_count += 1
        
        # 更新报告统计
        report.sent_count += success_count
        report.last_sent_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(
            f"Report {report_id} sent: {success_count} success, {failed_count} failed"
        )
        
        return {
            "report_id": report_id,
            "total_recipients": len(recipients),
            "success_count": success_count,
            "failed_count": failed_count
        }
    
    def send_daily_reports(self) -> Dict:
        """
        发送日报给所有订阅者
        
        Returns:
            发送结果
        """
        # 获取最新的日报
        report = self.db.query(Report).filter(
            Report.report_type == ReportType.DAILY
        ).order_by(Report.created_at.desc()).first()
        
        if not report:
            raise ValueError("No daily report found")
        
        # 获取订阅日报的用户
        subscriptions = self.db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.report_types.contains(["daily"])
        ).all()
        
        if not subscriptions:
            logger.info("No active daily report subscriptions")
            return {"sent_count": 0}
        
        # 发送邮件
        recipients = [sub.email for sub in subscriptions]
        result = self.send_report(
            report_id=report.id,
            recipients=recipients
        )
        
        # 更新订阅统计
        for subscription in subscriptions:
            subscription.total_sent += 1
            subscription.last_sent_at = datetime.utcnow()
        self.db.commit()
        
        return result
    
    def send_weekly_reports(self) -> Dict:
        """
        发送周报给所有订阅者
        
        Returns:
            发送结果
        """
        # 获取最新的周报
        report = self.db.query(Report).filter(
            Report.report_type == ReportType.WEEKLY
        ).order_by(Report.created_at.desc()).first()
        
        if not report:
            raise ValueError("No weekly report found")
        
        # 获取订阅周报的用户
        subscriptions = self.db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.report_types.contains(["weekly"])
        ).all()
        
        if not subscriptions:
            logger.info("No active weekly report subscriptions")
            return {"sent_count": 0}
        
        # 发送邮件
        recipients = [sub.email for sub in subscriptions]
        result = self.send_report(
            report_id=report.id,
            recipients=recipients
        )
        
        # 更新订阅统计
        for subscription in subscriptions:
            subscription.total_sent += 1
            subscription.last_sent_at = datetime.utcnow()
        self.db.commit()
        
        return result
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str
    ) -> None:
        """
        发送单封邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 主题
            html_content: HTML内容
        """
        message = Mail(
            from_email=Email(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        response = self.sg_client.send(message)
        
        if response.status_code not in [200, 202]:
            raise Exception(f"SendGrid API error: {response.status_code}")
    
    def _render_report_email(self, report: Report) -> str:
        """
        渲染报告邮件模板
        
        Args:
            report: 报告对象
        
        Returns:
            HTML内容
        """
        # 将Markdown转换为HTML
        content_html = markdown.markdown(
            report.content,
            extensions=['extra', 'codehilite', 'toc']
        )
        
        # 渲染模板
        template = self.jinja_env.get_template('report_email.html')
        html = template.render(
            title=report.title,
            content=content_html,
            article_count=report.article_count,
            start_date=report.start_date.strftime('%Y-%m-%d'),
            end_date=report.end_date.strftime('%Y-%m-%d'),
            report_type=report.report_type.value,
            current_year=datetime.now().year
        )
        
        return html

