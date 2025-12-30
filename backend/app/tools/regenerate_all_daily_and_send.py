#!/usr/bin/env python3
"""
重算全部晨报（ReportType.DAILY）并发送给所有已激活订阅者。

说明：
- 直接在 ai-worker 环境内执行（需要 DASHSCOPE_API_KEY + 邮件配置）
- 重算采用“原地更新”，不会改变 report_id

用法：
  python -m app.tools.regenerate_all_daily_and_send --dry-run
  python -m app.tools.regenerate_all_daily_and_send
  python -m app.tools.regenerate_all_daily_and_send --since 2025-12-15 --until 2025-12-19
  python -m app.tools.regenerate_all_daily_and_send --limit 10
  python -m app.tools.regenerate_all_daily_and_send --no-send
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime
import sys
from pathlib import Path

# Ensure `/app` is in sys.path inside container
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from shared.database import SessionLocal  # noqa: E402
from shared.database.models import Report, ReportType  # noqa: E402
from shared.utils import get_logger  # noqa: E402
from app.services.email_service import email_config_status  # noqa: E402
from app.workers.ai_generate import AIWorker  # noqa: E402

logger = get_logger("regen_all_daily_and_send")

def _date_range_inclusive(since: date, until: date) -> list[date]:
    if since > until:
        return []
    out: list[date] = []
    cur = since
    while cur <= until:
        out.append(cur)
        cur = date.fromordinal(cur.toordinal() + 1)
    return out


def _parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("日期格式错误，应为 YYYY-MM-DD，例如：2025-12-18")


def main() -> int:
    parser = argparse.ArgumentParser(description="重算全部晨报并群发给已激活订阅者")
    parser.add_argument("--since", type=str, default=None, help="起始日期（含），YYYY-MM-DD")
    parser.add_argument("--until", type=str, default=None, help="结束日期（含），YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=None, help="最多处理多少天（按日期升序截断）")
    parser.add_argument("--no-send", action="store_true", help="只重算，不发送邮件")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不实际调用模型/不发邮件")
    args = parser.parse_args()

    since = _parse_date(args.since) if args.since else None
    until = _parse_date(args.until) if args.until else None
    if since and until and since > until:
        raise SystemExit("--since 不能晚于 --until")

    if not args.no_send:
        ok, reason = email_config_status()
        if not ok:
            logger.error(f"Email not configured; abort sending. reason={reason}")
            return 2

    db = SessionLocal()
    try:
        # If both bounds are provided, regenerate by explicit date range (even if reports are missing).
        # Otherwise, fall back to existing report dates in DB.
        if since and until:
            dates = _date_range_inclusive(since, until)
        else:
            q = db.query(Report.report_date).filter(Report.report_type == ReportType.DAILY).distinct()
            if since:
                q = q.filter(Report.report_date >= since)
            if until:
                q = q.filter(Report.report_date <= until)
            dates = [row[0] for row in q.order_by(Report.report_date.asc()).all()]
        if args.limit is not None:
            dates = dates[: max(0, int(args.limit))]

        logger.info(
            f"计划处理晨报 {len(dates)} 天：since={since or '-'} until={until or '-'} "
            f"limit={args.limit or '-'} send={not args.no_send} dry_run={bool(args.dry_run)}"
        )
    finally:
        db.close()

    if args.dry_run:
        for d in dates:
            logger.info(f"[dry-run] {d.isoformat()}")
        return 0

    worker = AIWorker()
    for d in dates:
        logger.info(f"Regenerating daily report: {d.isoformat()}")
        r = worker.generate_daily_report(target_date=d, send_emails=False)
        if not r:
            logger.error(f"Regenerate failed/returned None: {d.isoformat()}")
            continue
        if args.no_send:
            continue
        # Send to all active subscribers (existing helper updates sent_count/sub stats)
        try:
            db2 = SessionLocal()
            try:
                # reload report in this session
                rr = (
                    db2.query(Report)
                    .filter(Report.report_type == ReportType.DAILY, Report.report_date == d)
                    .first()
                )
                if not rr:
                    logger.error(f"Report missing after regen: {d.isoformat()}")
                    continue
                asyncio.run(worker._distribute_daily_report(db2, rr))
            finally:
                db2.close()
        except Exception as e:
            logger.error(f"Send failed for {d.isoformat()}: {e}")

    logger.info("All done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


