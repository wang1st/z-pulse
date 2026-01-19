#!/usr/bin/env python3
"""
基于晨报生成周报（正确的逻辑）
"""
import sys
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
from typing import Optional
import re

# 添加项目根目录到Python路径
sys.path.insert(0, '/app')

from shared.database import SessionLocal, Report, ReportType
from backend.app.workers.ai_generate import AIWorker
from shared.utils import get_logger
from bs4 import BeautifulSoup

logger = get_logger("generate_weekly_from_daily")

def extract_text_from_html(html_content):
    """从HTML中提取纯文本内容"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # 移除script和style标签
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator='\n', strip=True)
        # 清理多余的空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    except:
        return html_content

def generate_weekly_from_daily_reports(target_date: Optional[date] = None, send_emails: bool = True):
    """
    基于过去7天的晨报生成周报

    Args:
        target_date: 目标日期（周一）
        send_emails: 是否发送邮件
    """
    db = SessionLocal()

    try:
        logger.info("=" * 80)
        logger.info("🚀 开始生成周报（基于晨报）")
        logger.info("=" * 80)

        # 确定日期范围
        end_date = target_date if target_date else datetime.now().date()
        start_date = end_date - timedelta(days=6)

        logger.info(f"📅 日期范围: {start_date} 至 {end_date}")

        # 查询过去7天的晨报
        daily_reports = db.query(Report).filter(
            Report.report_type == ReportType.DAILY,
            Report.report_date >= start_date,
            Report.report_date <= end_date
        ).order_by(Report.report_date).all()

        logger.info(f"✅ 找到 {len(daily_reports)} 篇晨报")

        if len(daily_reports) == 0:
            logger.warning("⚠️  没有找到晨报")
            return None

        # 准备每日摘要
        logger.info("📝 准备每日摘要...")
        daily_summaries = {}

        for report in daily_reports:
            date_str = report.report_date.strftime('%Y年%m月%d日')

            # 从HTML中提取纯文本
            content = extract_text_from_html(report.summary_markdown or '')

            # 取前500字作为摘要
            preview = content[:500] if len(content) > 500 else content

            daily_summaries[date_str] = preview
            logger.info(f"  📅 {date_str}: {len(content)} 字符, 预览: {len(preview)} 字符")

        logger.info(f"✅ 总共准备了 {len(daily_summaries)} 天的晨报摘要")

        # 生成周报
        date_range = f"{start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%m月%d日')}"
        logger.info(f"📊 日期范围: {date_range}")
        logger.info(f"📊 准备生成周报综述，输入数据大小: {sum(len(v) for v in daily_summaries.values())} 字符")

        logger.info("🤖 调用Qwen生成周报综述...")
        worker = AIWorker()

        markdown_content = worker._generate_weekly_analysis_with_qwen(
            topics=[],
            daily_summaries=daily_summaries,
            date_range=date_range
        )

        if not markdown_content:
            logger.error("❌ 周报生成失败：Qwen API返回空内容")
            return None

        logger.info(f"✅ Qwen返回内容长度: {len(markdown_content)} 字符")

        # 添加免责声明
        disclaimer = "\n\n---\n\n**免责声明**：本报告由大模型自动生成，内容基于公开信息进行总结和分析，仅作为不同视角的参考，不构成任何投资建议或决策依据。"
        markdown_content_with_disclaimer = markdown_content + disclaimer

        # 保存到数据库
        logger.info("💾 保存周报到数据库...")

        existing_weekly = db.query(Report).filter(
            Report.report_type == ReportType.WEEKLY,
            Report.report_date == end_date
        ).first()

        if existing_weekly:
            logger.info(f"🔄 更新现有周报（ID: {existing_weekly.id}）")
            existing_weekly.summary_markdown = markdown_content_with_disclaimer
            existing_weekly.title = f"财政周报述评 - {date_range}"
            existing_weekly.article_count = len(daily_reports)
            weekly_report = existing_weekly
        else:
            logger.info("➕ 创建新周报")
            weekly_report = Report(
                report_type=ReportType.WEEKLY,
                report_date=end_date,
                title=f"财政周报述评 - {date_range}",
                summary_markdown=markdown_content_with_disclaimer,
                article_count=len(daily_reports),
                sent_count=0,
                view_count=0
            )
            db.add(weekly_report)

        db.commit()
        db.flush()
        db.refresh(weekly_report)

        logger.info("=" * 80)
        logger.info(f"✅ 周报生成成功！")
        logger.info(f"   🆔 周报ID: {weekly_report.id}")
        logger.info(f"   📅 日期范围: {date_range}")
        logger.info(f"   📰 标题: {weekly_report.title}")
        logger.info(f"   📊 基于晨报数量: {len(daily_reports)}")
        logger.info(f"   📝 内容长度: {len(weekly_report.summary_markdown or '')} 字符")
        logger.info("=" * 80)

        # 发送邮件
        if send_emails:
            logger.info("\n📧 开始发送周报邮件...")

            from shared.database import Subscriber
            subscribers = db.query(Subscriber).filter(
                Subscriber.is_active.is_(True),
                Subscriber.subscribe_weekly.is_(True)
            ).all()

            logger.info(f"👥 找到 {len(subscribers)} 个订阅周报的用户")

            if len(subscribers) > 0:
                try:
                    sent_count = worker._distribute_weekly_report(db, weekly_report)
                    logger.info(f"✅ 成功发送 {sent_count} 封邮件")

                    weekly_report.sent_count = sent_count
                    db.commit()
                    db.refresh(weekly_report)

                    logger.info(f"   📬 发送数量: {weekly_report.sent_count}")

                except Exception as e:
                    logger.error(f"❌ 发送邮件失败: {str(e)}", exc_info=True)
            else:
                logger.info("ℹ️  没有订阅周报的用户，跳过发送")

        return weekly_report

    except Exception as e:
        logger.error(f"❌ 生成周报失败: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='基于晨报生成周报')
    parser.add_argument('--date', type=str, help='目标日期（YYYY-MM-DD），默认为今天')
    parser.add_argument('--no-send', action='store_true', help='不发送邮件')

    args = parser.parse_args()

    # 解析日期
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"❌ 日期格式错误: {args.date}，请使用 YYYY-MM-DD 格式")
            return

    logger.info(f"⚙️  配置: target_date={target_date or '今天'}, send_emails={not args.no_send}")

    # 生成周报
    report = generate_weekly_from_daily_reports(
        target_date=target_date,
        send_emails=not args.no_send
    )

    if report:
        logger.info(f"\n✅ 周报生成完成！ID: {report.id}")
    else:
        logger.error("\n❌ 周报生成失败")

if __name__ == "__main__":
    main()
