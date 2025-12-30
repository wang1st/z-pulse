#!/usr/bin/env python
"""
模拟在12月22日生成周报并发送给订阅用户

使用方法:
    python scripts/simulate_weekly_report_2025_12_22.py
"""
import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置时区
os.environ['TZ'] = 'Asia/Shanghai'

from shared.database import SessionLocal, Report, ReportType
from shared.utils import get_logger
from app.workers.ai_generate import AIWorker

logger = get_logger("simulate_weekly_report")

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始模拟12月22日周报生成和发送")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 检查是否有足够的日报数据（12月16日-12月22日）
        target_date = date(2025, 12, 22)  # 周一
        start_date = target_date - timedelta(days=6)  # 12月16日
        
        logger.info(f"检查日期范围: {start_date} 至 {target_date}")
        
        daily_reports = db.query(Report).filter(
            Report.report_type == ReportType.DAILY,
            Report.report_date >= start_date,
            Report.report_date <= target_date
        ).order_by(Report.report_date).all()
        
        logger.info(f"找到 {len(daily_reports)} 份日报")
        
        if len(daily_reports) < 3:
            logger.warning(f"⚠️  日报数量不足（需要至少3份，当前{len(daily_reports)}份）")
            logger.info("建议先确保12月16日-12月22日期间有足够的日报数据")
            return
        
        # 显示日报日期
        for report in daily_reports:
            logger.info(f"  - {report.report_date.isoformat()}: {report.title or '无标题'}")
        
        # 检查是否已有12月22日的周报
        existing_weekly = db.query(Report).filter(
            Report.report_type == ReportType.WEEKLY,
            Report.report_date == target_date
        ).first()
        
        if existing_weekly:
            logger.warning(f"⚠️  已存在 {target_date} 的周报（ID: {existing_weekly.id}）")
            response = input("是否删除旧周报并重新生成？(y/N): ").strip().lower()
            if response == 'y':
                db.delete(existing_weekly)
                db.commit()
                logger.info("已删除旧周报")
            else:
                logger.info("使用现有周报")
                weekly_report = existing_weekly
        else:
            # 生成周报
            logger.info("\n开始生成周报...")
            worker = AIWorker()
            worker.generate_weekly_report(target_date=target_date)
            
            # 获取刚生成的周报
            weekly_report = db.query(Report).filter(
                Report.report_type == ReportType.WEEKLY,
                Report.report_date == target_date
            ).order_by(Report.created_at.desc()).first()
            
            if not weekly_report:
                logger.error("❌ 周报生成失败：未找到生成的周报")
                return
            
            logger.info(f"✅ 周报生成成功 (ID: {weekly_report.id})")
        
        # 刷新周报数据以获取最新的sent_count
        db.refresh(weekly_report)
        
        # 检查订阅用户
        from shared.database import Subscriber
        subscribers = db.query(Subscriber).filter(
            Subscriber.is_active.is_(True),
            Subscriber.subscribe_weekly.is_(True)
        ).all()
        
        logger.info(f"\n找到 {len(subscribers)} 个订阅周报的用户")
        
        if len(subscribers) == 0:
            logger.warning("⚠️  没有订阅周报的用户")
        else:
            for sub in subscribers:
                logger.info(f"  - {sub.email}")
        
        # 计算日期范围字符串
        date_range_str = f"{start_date.strftime('%Y年%m月%d日')} 至 {target_date.strftime('%m月%d日')}"
        
        # 检查发送状态
        sent_count = weekly_report.sent_count or 0
        
        logger.info("=" * 60)
        logger.info(f"✅ 周报生成和发送完成！")
        logger.info(f"   周报ID: {weekly_report.id}")
        logger.info(f"   日期范围: {date_range_str}")
        logger.info(f"   发送数量: {sent_count}")
        if sent_count > 0:
            logger.info(f"   ✅ 已自动发送给 {sent_count} 个订阅用户")
        elif len(subscribers) > 0:
            logger.warning(f"   ⚠️  有 {len(subscribers)} 个订阅用户，但发送数量为0，可能发送失败")
        else:
            logger.info(f"   ℹ️  没有订阅用户，未发送")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 操作失败: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()

