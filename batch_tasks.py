#!/usr/bin/env python3
"""批量任务：采集文章 -> 生成晨报 -> 发送邮件"""
import sys
sys.path.insert(0, '/app/backend')

from shared.database import SessionLocal, ReportJob, ReportJobType
from datetime import date

def create_daily_reports():
    """创建12月15日到12月20日的晨报任务"""
    db = SessionLocal()
    try:
        dates = [
            date(2025, 12, 15),
            date(2025, 12, 16),
            date(2025, 12, 17),
            date(2025, 12, 18),
            date(2025, 12, 19),
            date(2025, 12, 20),
        ]
        
        job_ids = []
        for target_date in dates:
            job = ReportJob(
                job_type=ReportJobType.REGENERATE_DAILY,
                target_date=target_date,
                status='pending'
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_ids.append(job.id)
            print(f'Created report job {job.id} for {target_date}')
        
        print(f'\nTotal created: {len(job_ids)} jobs')
        print(f'Job IDs: {job_ids}')
        return job_ids
    finally:
        db.close()

if __name__ == '__main__':
    print('=== Creating Daily Report Jobs ===')
    create_daily_reports()
    print('\n=== Done ===')
