#!/usr/bin/env python3
"""
批量入队：重新生成全部晨报（ReportType.DAILY）。

设计目标：
- 不直接在脚本里跑生成（可能耗时/阻塞/失败重试困难）
- 只负责把日期写入 report_jobs 队列，由 ai-worker 异步逐个执行

用法：
  python -m app.tools.queue_regenerate_all_daily --dry-run
  python -m app.tools.queue_regenerate_all_daily
  python -m app.tools.queue_regenerate_all_daily --force
  python -m app.tools.queue_regenerate_all_daily --since 2025-12-01 --until 2025-12-18
  python -m app.tools.queue_regenerate_all_daily --limit 20
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

# 确保容器内可 import shared（项目根目录 /app）
# /app/backend/app/tools/queue_regenerate_all_daily.py -> project_root=/app
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from shared.database import (  # noqa: E402
    SessionLocal,
    Article,
    Report,
    ReportJob,
    ReportJobStatus,
    ReportJobType,
    ReportType,
)
from shared.utils import get_logger  # noqa: E402

logger = get_logger("queue_regenerate_all_daily")

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


@dataclass(frozen=True)
class Result:
    total_candidates: int
    queued: int
    skipped_existing: int
    skipped_no_articles: int
    errors: int


def _has_articles_for_day(db, d: date) -> bool:
    start = datetime(d.year, d.month, d.day)
    end = start + timedelta(days=1)
    return (
        db.query(Article.id)
        .filter(Article.published_at >= start, Article.published_at < end)
        .limit(1)
        .first()
        is not None
    )


def _already_queued_or_running(db, d: date) -> int | None:
    existing = (
        db.query(ReportJob)
        .filter(
            ReportJob.job_type == ReportJobType.REGENERATE_DAILY,
            ReportJob.target_date == d,
            ReportJob.status.in_([ReportJobStatus.PENDING, ReportJobStatus.RUNNING]),
        )
        .order_by(ReportJob.created_at.desc())
        .first()
    )
    return existing.id if existing else None


def _queue_one(db, d: date, requested_by: str | None, force: bool, dry_run: bool) -> tuple[bool, str]:
    """
    Returns:
      (queued, message)
    """
    if not _has_articles_for_day(db, d):
        return False, "skip_no_articles"

    existing_id = _already_queued_or_running(db, d)
    if existing_id and not force:
        return False, f"skip_existing_job:{existing_id}"

    if dry_run:
        return True, "dry_run_queued"

    if existing_id and force:
        # 将旧任务标记为失败，避免永远拦截（与 admin.py 中逻辑一致的最小子集）
        old = db.query(ReportJob).filter(ReportJob.id == existing_id).first()
        if old:
            old.status = ReportJobStatus.FAILED
            old.finished_at = datetime.utcnow()
            old.error_message = f"Superseded by forced requeue by {requested_by or 'cli'}"

    job = ReportJob(
        job_type=ReportJobType.REGENERATE_DAILY,
        status=ReportJobStatus.PENDING,
        target_date=d,
        requested_by=requested_by or "cli",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return True, f"queued_job:{job.id}"


def main() -> int:
    parser = argparse.ArgumentParser(description="批量入队：重新生成全部晨报（异步队列）")
    parser.add_argument("--since", type=str, default=None, help="起始日期（含），YYYY-MM-DD")
    parser.add_argument("--until", type=str, default=None, help="结束日期（含），YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=None, help="最多入队多少天（按日期升序截断）")
    parser.add_argument("--force", action="store_true", help="即使已有 pending/running 任务也强制重新入队")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划入队的日期，不写数据库")
    parser.add_argument("--requested-by", type=str, default="admin", help="写入 report_jobs.requested_by")

    args = parser.parse_args()

    since = _parse_date(args.since) if args.since else None
    until = _parse_date(args.until) if args.until else None
    if since and until and since > until:
        raise SystemExit("--since 不能晚于 --until")

    db = SessionLocal()
    try:
        # If both bounds are provided, queue by explicit date range (even if reports are missing).
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

        total_candidates = len(dates)
        logger.info(
            f"发现晨报日期 {total_candidates} 个，将批量入队再生成："
            f"since={since or '-'} until={until or '-'} limit={args.limit or '-'} "
            f"force={bool(args.force)} dry_run={bool(args.dry_run)}"
        )

        queued = 0
        skipped_existing = 0
        skipped_no_articles = 0
        errors = 0

        for d in dates:
            try:
                ok, msg = _queue_one(
                    db=db,
                    d=d,
                    requested_by=args.requested_by,
                    force=bool(args.force),
                    dry_run=bool(args.dry_run),
                )
                if ok:
                    queued += 1
                    logger.info(f"{d.isoformat()} -> {msg}")
                else:
                    if msg == "skip_no_articles":
                        skipped_no_articles += 1
                    elif msg.startswith("skip_existing_job:"):
                        skipped_existing += 1
                    logger.info(f"{d.isoformat()} -> {msg}")
            except Exception as e:
                errors += 1
                logger.error(f"{d.isoformat()} -> error: {e}")

        r = Result(
            total_candidates=total_candidates,
            queued=queued,
            skipped_existing=skipped_existing,
            skipped_no_articles=skipped_no_articles,
            errors=errors,
        )

        logger.info(
            "批量入队完成："
            f"candidates={r.total_candidates} queued={r.queued} "
            f"skipped_existing={r.skipped_existing} skipped_no_articles={r.skipped_no_articles} errors={r.errors}"
        )
        return 0 if errors == 0 else 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())


