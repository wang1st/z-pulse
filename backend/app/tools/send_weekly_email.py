#!/usr/bin/env python3
"""
在容器/后端环境内手动发送指定日期的周报邮件给已激活订阅者。

用法：
  python -m app.tools.send_weekly_email 2025-12-24
  python -m app.tools.send_weekly_email 2025-12-24 --email someone@example.com
  python -m app.tools.send_weekly_email 2025-12-24 --dry-run
"""

import argparse
import asyncio
from datetime import datetime, date
import sys
from pathlib import Path

# 确保容器内可 import shared（项目根目录 /app）
# /app/backend/app/tools/send_weekly_email.py -> project_root=/app
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from shared.database import SessionLocal, Report, ReportType, Subscriber  # noqa: E402
from shared.utils import get_logger  # noqa: E402
from ..services.email_service import send_weekly_report  # noqa: E402
from ..services.report_render import render_weekly_report_html, render_weekly_report_pdf, render_weekly_report_text  # noqa: E402

logger = get_logger("send_weekly_email")


def _parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("日期格式错误，应为 YYYY-MM-DD，例如：2025-12-24")


async def _send_all(report_date: date, only_email: str | None, dry_run: bool) -> int:
    db = SessionLocal()
    sent = 0
    try:
        report = (
            db.query(Report)
            .filter(Report.report_type == ReportType.WEEKLY, Report.report_date == report_date)
            .first()
        )
        if not report:
            raise RuntimeError(f"未找到周报：{report_date.isoformat()}（ReportType.WEEKLY）")

        # 计算日期范围字符串（周报日期是周一，往前推6天是上周二）
        from datetime import timedelta
        start_date = report_date - timedelta(days=6)
        date_range_str = f"{start_date.strftime('%Y年%m月%d日')} 至 {report_date.strftime('%m月%d日')}"

        # 重新渲染HTML，确保使用最新样式
        import json
        report_html = None
        report_json = None
        
        try:
            # 尝试解析content_json（可能是dict或str）
            if report.content_json:
                if isinstance(report.content_json, dict):
                    report_json = report.content_json
                elif isinstance(report.content_json, str):
                    report_json = json.loads(report.content_json)
                else:
                    report_json = {}
            
            # Generate plain text for email body
            if report.summary_markdown:
                report_text = render_weekly_report_text(
                    report.summary_markdown,
                    report_date.isoformat(),
                    date_range_str
                )
                logger.info(f"Generated weekly report plain text for email body")
            else:
                report_text = None
            
            # Also generate HTML for PDF (not used in email body, but kept for compatibility)
            report_html = render_weekly_report_html(
                report.summary_markdown or "",
                report_date.isoformat(),
                date_range_str,
                for_email=True
            )
        except Exception as e:
            logger.warning(f"Failed to generate weekly report text/HTML: {e}, will use saved summary_markdown")
            report_text = None
            report_html = report.summary_markdown or ""

        # 生成PDF附件（如果启用）
        pdf_bytes = None
        pdf_filename = None
        try:
            if report.summary_markdown:
                # 生成PDF
                logger.info(f"生成PDF: date={report_date.isoformat()}")
                pdf_bytes = render_weekly_report_pdf(
                    report.summary_markdown, 
                    report_date.isoformat(), 
                    date_range_str
                )
                pdf_filename = f"z-pulse-weekly-{report_date.isoformat()}.pdf"
                logger.info(f"PDF生成成功: size={len(pdf_bytes)} bytes")
            else:
                logger.warning("周报没有summary_markdown，跳过PDF生成")
                pdf_bytes = None
                pdf_filename = None
        except Exception as e:
            logger.error(f"PDF生成失败: {e}，将不附带PDF")
            pdf_bytes = None
            pdf_filename = None

        q = db.query(Subscriber).filter(
            Subscriber.is_active.is_(True),
            Subscriber.subscribe_weekly.is_(True),
        )
        if only_email:
            q = q.filter(Subscriber.email == only_email)

        subscribers = q.order_by(Subscriber.id.asc()).all()
        if not subscribers:
            logger.warning("没有找到符合条件的已激活订阅者（is_active=true, subscribe_weekly=true）")
            return 0

        logger.info(
            f"准备发送周报邮件：date={report_date.isoformat()} date_range={date_range_str} "
            f"subscribers={len(subscribers)} dry_run={dry_run} only_email={only_email or '-'} "
            f"pdf_attachment={pdf_filename is not None}"
        )

        for sub in subscribers:
            if dry_run:
                logger.info(f"[dry-run] would send to {sub.email} (pdf={pdf_filename is not None})")
                continue

            await send_weekly_report(
                email=sub.email,
                report_html=report_html,  # Keep for compatibility, but email body uses report_text
                report_date=report_date.isoformat(),
                date_range_str=date_range_str,
                report_text=report_text,  # Plain text for email body
                pdf_attachment=pdf_bytes,
                pdf_filename=pdf_filename,
            )
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
    parser = argparse.ArgumentParser(description="Send weekly report email to activated subscribers.")
    parser.add_argument("date", help="report date (Monday), YYYY-MM-DD")
    parser.add_argument("--email", help="only send to this email (optional)", default=None)
    parser.add_argument("--dry-run", help="do not actually send, just print recipients", action="store_true")
    args = parser.parse_args()

    report_date = _parse_date(args.date)
    asyncio.run(_send_all(report_date, args.email, args.dry_run))


if __name__ == "__main__":
    main()

