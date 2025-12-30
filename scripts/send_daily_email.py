#!/usr/bin/env python3
"""
手动发送指定日期的日报邮件给已激活订阅者。

用法：
  python scripts/send_daily_email.py 2025-12-18
  python scripts/send_daily_email.py 2025-12-18 --email someone@example.com
  python scripts/send_daily_email.py 2025-12-18 --dry-run
"""

import sys
import argparse
import asyncio
from pathlib import Path
from datetime import datetime, date

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database import SessionLocal, Report, ReportType, Subscriber  # noqa: E402
from shared.utils import get_logger  # noqa: E402

# 这里复用 backend 的邮件发送实现（会根据 EMAIL_PROVIDER 走 Brevo/SendGrid/Mailgun）
from backend.app.services.email_service import send_daily_report  # noqa: E402

logger = get_logger("send_daily_email")


def _parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("日期格式错误，应为 YYYY-MM-DD，例如：2025-12-18")


async def _send_all(report_date: date, only_email: str | None, dry_run: bool):
    db = SessionLocal()
    sent = 0
    try:
        report = (
            db.query(Report)
            .filter(Report.report_type == ReportType.DAILY, Report.report_date == report_date)
            .first()
        )
        if not report:
            raise RuntimeError(f"未找到日报：{report_date.isoformat()}（ReportType.DAILY）")

        # 这份字段里存的是“已渲染 HTML”，用于邮件模板嵌入
        report_html = report.summary_markdown

        q = db.query(Subscriber).filter(
            Subscriber.is_active.is_(True),
            Subscriber.subscribe_daily.is_(True),
        )
        if only_email:
            q = q.filter(Subscriber.email == only_email)

        subscribers = q.order_by(Subscriber.id.asc()).all()
        if not subscribers:
            logger.warning("没有找到符合条件的已激活订阅者（is_active=true, subscribe_daily=true）")
            return 0

        logger.info(
            f"准备发送日报邮件：date={report_date.isoformat()} "
            f"subscribers={len(subscribers)} dry_run={dry_run} "
            f"only_email={only_email or '-'}"
        )

        for sub in subscribers:
            if dry_run:
                logger.info(f"[dry-run] would send to {sub.email}")
                continue

            await send_daily_report(
                email=sub.email,
                report_html=report_html,
                report_date=report_date.isoformat(),
            )

            # 更新订阅者统计
            sub.total_sent = int(sub.total_sent or 0) + 1
            sub.last_sent_at = datetime.utcnow()
            sent += 1

        if not dry_run:
            report.sent_count = int(report.sent_count or 0) + sent
            db.commit()
            logger.info(f"✅ 已发送完成：sent={sent}")
        else:
            logger.info("✅ dry-run 完成：未实际发送")

        return sent
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Send daily report email to activated subscribers.")
    parser.add_argument("date", help="report date, YYYY-MM-DD")
    parser.add_argument("--email", help="only send to this email (optional)", default=None)
    parser.add_argument("--dry-run", help="do not actually send, just print recipients", action="store_true")
    args = parser.parse_args()

    report_date = _parse_date(args.date)

    try:
        sent = asyncio.run(_send_all(report_date, args.email, args.dry_run))
        if sent == 0 and not args.dry_run:
            # no recipients is not an error, but keep exit code 0
            pass
    except Exception as e:
        logger.error(f"❌ 发送失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


