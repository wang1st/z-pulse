#!/usr/bin/env python
"""
重新生成今天的晨报并发送邮件，包含详细的调试信息
"""
import sys
from pathlib import Path
from datetime import date

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database import SessionLocal, Report, ReportType, Subscriber
from shared.utils import get_logger
from app.workers.ai_generate import AIWorker
import json

logger = get_logger("regenerate_daily_debug")

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("重新生成今天的晨报（包含调试信息）")
    logger.info("=" * 60)
    
    target_date = date.today()
    logger.info(f"目标日期: {target_date}")
    
    db = SessionLocal()
    
    try:
        # 检查是否已有晨报
        existing = db.query(Report).filter(
            Report.report_type == ReportType.DAILY,
            Report.report_date == target_date
        ).first()
        
        if existing:
            logger.info(f"已存在 {target_date} 的晨报（ID: {existing.id}）")
            logger.info("将删除旧晨报并重新生成...")
            db.delete(existing)
            db.commit()
            logger.info("✅ 旧晨报已删除")
        
        # 检查订阅用户
        subscribers = db.query(Subscriber).filter(
            Subscriber.is_active.is_(True),
            Subscriber.subscribe_daily.is_(True)
        ).all()
        
        logger.info(f"\n找到 {len(subscribers)} 个订阅晨报的用户")
        if len(subscribers) > 0:
            for sub in subscribers:
                logger.info(f"  - {sub.email}")
        
        # 生成晨报（会自动发送）
        logger.info("\n" + "=" * 60)
        logger.info("开始生成晨报（包含调试信息）...")
        logger.info("=" * 60)
        
        worker = AIWorker()
        report = worker.generate_daily_report(target_date=target_date, send_emails=True)
        
        if not report:
            logger.error("❌ 晨报生成失败：返回None")
            return
        
        # 刷新报告以获取最新数据
        db.refresh(report)
        
        # 分析热点数据
        logger.info("\n" + "=" * 60)
        logger.info("热点数据调试信息")
        logger.info("=" * 60)
        
        content = report.content_json or {}
        hotspots = content.get('recent_hotspots', [])
        keywords = content.get('keywords', [])
        recent_hotspots_meta = content.get('recent_hotspots_meta', {})
        
        logger.info(f"recent_hotspots 总数: {len(hotspots)}")
        logger.info(f"keywords 总数: {len(keywords)}")
        logger.info(f"recent_hotspots_meta: {recent_hotspots_meta}")
        
        if hotspots:
            logger.info(f"\n所有热点详情:")
            for i, h in enumerate(hotspots, 1):
                event = h.get('event', '')
                coverage_accounts = h.get('coverage_accounts', 0)
                coverage_docs = h.get('coverage_docs', 0)
                hotness = h.get('hotness', 0)
                source_ids = h.get('source_ids', [])
                logger.info(f"  {i}. {event[:50]}")
                logger.info(f"     - coverage_accounts: {coverage_accounts}")
                logger.info(f"     - coverage_docs: {coverage_docs}")
                logger.info(f"     - hotness: {hotness}")
                logger.info(f"     - source_ids count: {len(source_ids)}")
                logger.info(f"     - 是否符合条件 (>=3): {'✅ 是' if coverage_accounts >= 3 else '❌ 否'}")
            
            # 统计符合条件的热点
            filtered = [h for h in hotspots if h.get('coverage_accounts', 0) >= 3]
            logger.info(f"\n过滤结果:")
            logger.info(f"  - 符合条件 (coverage_accounts >= 3): {len(filtered)} 个")
            logger.info(f"  - 不符合条件: {len(hotspots) - len(filtered)} 个")
            
            if len(filtered) == 0:
                logger.warning("⚠️  没有符合条件的热点，前端将不显示'近日热点'部分")
                logger.info("\ncoverage_accounts 分布:")
                accounts_dist = {}
                for h in hotspots:
                    accounts = h.get('coverage_accounts', 0)
                    accounts_dist[accounts] = accounts_dist.get(accounts, 0) + 1
                for accounts, count in sorted(accounts_dist.items()):
                    logger.info(f"  {accounts} 个账号: {count} 个热点")
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ 晨报生成和发送完成！")
        logger.info(f"   晨报ID: {report.id}")
        logger.info(f"   日期: {report.report_date}")
        logger.info(f"   标题: {report.title}")
        logger.info(f"   发送数量: {report.sent_count or 0}")
        if report.sent_count and report.sent_count > 0:
            logger.info(f"   ✅ 已自动发送给 {report.sent_count} 个订阅用户")
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

