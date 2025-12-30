#!/usr/bin/env python
"""
删除所有周报，然后重新生成12月24日的周报
"""
import sys
from pathlib import Path
from datetime import date, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database import SessionLocal, Report, ReportType, Subscriber
from shared.utils import get_logger
from app.workers.ai_generate import AIWorker

logger = get_logger("delete_all_weekly_and_regenerate")

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("删除所有周报，然后重新生成12月24日的周报")
    logger.info("=" * 60)
    
    target_date = date(2025, 12, 24)  # 12月24日
    start_date = target_date - timedelta(days=6)  # 往前推6天，共7天
    
    logger.info(f"目标日期: {target_date}")
    logger.info(f"日期范围: {start_date} 至 {target_date}")
    
    db = SessionLocal()
    
    try:
        # 1. 删除所有周报
        logger.info("\n" + "=" * 60)
        logger.info("步骤1: 删除所有周报")
        logger.info("=" * 60)
        
        all_weekly_reports = db.query(Report).filter(
            Report.report_type == ReportType.WEEKLY
        ).all()
        
        logger.info(f"找到 {len(all_weekly_reports)} 份周报")
        
        if len(all_weekly_reports) > 0:
            for report in all_weekly_reports:
                logger.info(f"  删除周报 ID {report.id}: {report.report_date} - {report.title or '无标题'}")
                db.delete(report)
            
            db.commit()
            logger.info(f"✅ 已删除 {len(all_weekly_reports)} 份周报")
        else:
            logger.info("ℹ️  没有找到周报，无需删除")
        
        # 2. 检查日报数据
        logger.info("\n" + "=" * 60)
        logger.info("步骤2: 检查日报数据")
        logger.info("=" * 60)
        
        daily_reports = db.query(Report).filter(
            Report.report_type == ReportType.DAILY,
            Report.report_date >= start_date,
            Report.report_date <= target_date
        ).order_by(Report.report_date).all()
        
        logger.info(f"找到 {len(daily_reports)} 份日报（日期范围: {start_date} 至 {target_date}）")
        
        if len(daily_reports) < 3:
            logger.warning(f"⚠️  日报数量不足（需要至少3份，当前{len(daily_reports)}份）")
            logger.warning("请确保有足够的日报数据")
            return
        
        for report in daily_reports:
            logger.info(f"  - {report.report_date.isoformat()}: {report.title or '无标题'}")
        
        # 3. 检查订阅用户
        logger.info("\n" + "=" * 60)
        logger.info("步骤3: 检查订阅用户")
        logger.info("=" * 60)
        
        subscribers = db.query(Subscriber).filter(
            Subscriber.is_active.is_(True),
            Subscriber.subscribe_weekly.is_(True)
        ).all()
        
        logger.info(f"找到 {len(subscribers)} 个订阅周报的用户")
        if len(subscribers) > 0:
            for sub in subscribers:
                logger.info(f"  - {sub.email}")
        else:
            logger.warning("⚠️  没有订阅周报的用户")
        
        # 4. 生成周报（会自动发送）
        logger.info("\n" + "=" * 60)
        logger.info("步骤4: 生成12月24日的周报")
        logger.info("=" * 60)
        
        worker = AIWorker()
        worker.generate_weekly_report(target_date=target_date)
        
        # 5. 获取生成的周报
        weekly_report = db.query(Report).filter(
            Report.report_type == ReportType.WEEKLY,
            Report.report_date == target_date
        ).order_by(Report.created_at.desc()).first()
        
        if not weekly_report:
            logger.error("❌ 周报生成失败：未找到生成的周报")
            return
        
        db.refresh(weekly_report)
        
        # 计算日期范围字符串
        date_range_str = f"{start_date.strftime('%Y年%m月%d日')} 至 {target_date.strftime('%m月%d日')}"
        
        logger.info("=" * 60)
        logger.info(f"✅ 周报生成和发送完成！")
        logger.info(f"   周报ID: {weekly_report.id}")
        logger.info(f"   日期范围: {date_range_str}")
        logger.info(f"   标题: {weekly_report.title}")
        logger.info(f"   发送数量: {weekly_report.sent_count or 0}")
        if weekly_report.sent_count and weekly_report.sent_count > 0:
            logger.info(f"   ✅ 已自动发送给 {weekly_report.sent_count} 个订阅用户")
        elif len(subscribers) > 0:
            logger.warning(f"   ⚠️  有 {len(subscribers)} 个订阅用户，但发送数量为0，可能发送失败")
        else:
            logger.info(f"   ℹ️  没有订阅用户，未发送")
        logger.info("=" * 60)
        
        # 显示周报内容预览
        if weekly_report.summary_markdown:
            preview = weekly_report.summary_markdown[:300] + "..." if len(weekly_report.summary_markdown) > 300 else weekly_report.summary_markdown
            logger.info(f"\n周报内容预览:\n{preview}")
        
    except Exception as e:
        logger.error(f"❌ 操作失败: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()

