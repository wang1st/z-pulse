#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app/backend')
from shared.database import SessionLocal, ReportJob
import time

db = SessionLocal()
try:
    jobs = db.query(ReportJob).filter(ReportJob.id.in_([68,69,70,71,72,73])).order_by(ReportJob.id).all()
    print('\n任务状态：')
    for job in jobs:
        status_icon = {'pending': '⏳', 'running': '🔄', 'success': '✅', 'failed': '❌'}.get(job.status.value, '?')
        print(f'  {status_icon} Job {job.id} ({job.target_date}): {job.status.value}')
    
    pending = sum(1 for j in jobs if j.status.value == 'pending')
    running = sum(1 for j in jobs if j.status.value == 'running')
    success = sum(1 for j in jobs if j.status.value == 'success')
    failed = sum(1 for j in jobs if j.status.value == 'failed')
    
    print(f'\n统计：待处理={pending}, 运行中={running}, 成功={success}, 失败={failed}')
    print(f'完成率：{success}/6 ({success*100//6}%)')
finally:
    db.close()
