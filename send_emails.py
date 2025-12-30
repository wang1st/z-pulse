#!/usr/bin/env python3
"""发送晨报邮件给所有活跃用户"""
import sys
sys.path.insert(0, '/app/backend')

from shared.database import SessionLocal, Report, ReportType
from datetime import date
import subprocess

def send_reports_to_users():
    """发送12月15-20日的晨报给所有活跃用户"""
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
        
        # 检查每个日期的晨报是否已生成
        for target_date in dates:
            report = db.query(Report).filter(
                Report.report_type == ReportType.DAILY,
                Report.report_date == target_date
            ).first()
            
            if report:
                print(f'✅ Report exists for {target_date} (ID: {report.id})')
                # 调用邮件发送API
                try:
                    result = subprocess.run(
                        ['curl', '-X', 'POST', 
                         f'http://localhost:8000/api/reports/daily/{target_date.isoformat()}/send-email',
                         '-H', 'Content-Type: application/json'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        print(f'   📧 Email sent for {target_date}')
                    else:
                        print(f'   ❌ Email failed for {target_date}: {result.stderr}')
                except Exception as e:
                    print(f'   ❌ Error sending email for {target_date}: {e}')
            else:
                print(f'⏳ Report not ready for {target_date} - will retry later')
        
    finally:
        db.close()

if __name__ == '__main__':
    print('=== Sending Daily Reports via Email ===\n')
    send_reports_to_users()
    print('\n=== Done ===')
