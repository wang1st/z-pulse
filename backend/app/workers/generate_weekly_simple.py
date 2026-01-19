#!/usr/bin/env python
"""
简化版周报生成脚本（带详细调试信息）
"""
import sys
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, '/app')

from shared.database import SessionLocal, Report, ReportType, Article, Subscriber
from backend.app.workers.ai_generate import AIWorker
from shared.utils import get_logger

logger = get_logger("generate_weekly_simple")

def generate_weekly_report_simple(target_date: Optional[date] = None, send_emails: bool = True, max_articles: int = 100):
    """
    简化版周报生成

    流程：
    1. 获取过去7天的所有文章
    2. 随机抽取最多max_articles篇文章
    3. 按日期分组
    4. 使用Qwen生成周报
    5. 存入数据库

    Args:
        target_date: 目标日期（周一）
        send_emails: 是否发送邮件
        max_articles: 最大处理文章数
    """
    db = SessionLocal()

    try:
        logger.info("=" * 80)
        logger.info("🚀 开始生成周报（简化版）")
        logger.info("=" * 80)

        # 确定日期范围
        end_date = target_date if target_date else datetime.now().date()
        start_date = end_date - timedelta(days=6)

        logger.info(f"📅 日期范围: {start_date} 至 {end_date}")

        # 查询文章
        start_utc = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_utc = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

        logger.info(f"🔍 查询文章时间范围: {start_utc} 至 {end_utc}")

        articles = db.query(Article).filter(
            Article.published_at >= start_utc,
            Article.published_at <= end_utc
        ).order_by(Article.published_at).all()

        logger.info(f"✅ 找到 {len(articles)} 篇文章")

        if len(articles) == 0:
            logger.warning("⚠️  没有找到任何文章")
            return None

        # 限制文章数量
        if len(articles) > max_articles:
            logger.info(f"📊 文章数量超过限制，从 {len(articles)} 篇中随机抽取 {max_articles} 篇")
            import random
            articles = random.sample(articles, max_articles)

        logger.info(f"📝 准备处理 {len(articles)} 篇文章")

        # 使用AI Worker筛选财政相关文章
        logger.info("🔧 开始筛选财政相关文章...")
        worker = AIWorker()

        try:
            finance_articles = worker._filter_finance_related_articles(articles)
            logger.info(f"✅ 筛选出 {len(finance_articles)} 篇财政相关文章")
        except Exception as e:
            logger.error(f"❌ 筛选文章失败: {str(e)}", exc_info=True)
            logger.info("⚠️  使用所有文章继续处理")
            finance_articles = articles

        if not finance_articles:
            logger.warning("⚠️  没有找到财政相关文章")
            return None

        # 按日期分组
        logger.info("📅 按日期分组文章...")
        from collections import defaultdict
        articles_by_date = defaultdict(list)

        for article in finance_articles:
            pub_date = article.published_at
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            local_date = pub_date.astimezone(timezone.utc).date()
            articles_by_date[local_date].append(article)
            logger.debug(f"  文章: {local_date} - {article.title[:50]}...")

        logger.info(f"✅ 文章已分组到 {len(articles_by_date)} 个日期")

        # 准备每日摘要
        logger.info("📝 准备每日摘要...")
        daily_summaries = {}

        for day, day_articles in sorted(articles_by_date.items()):
            date_str = day.strftime('%Y年%m月%d日')
            logger.info(f"  📅 {date_str}: {len(day_articles)} 篇文章")

            article_summaries = []
            for i, article in enumerate(day_articles[:15], 1):  # 每天最多15篇
                title = getattr(article, 'title', '') or ''
                content = getattr(article, 'content', '') or ''

                # 取前200字作为摘要
                preview = content[:200] if content else ''
                article_text = f"{title}。{preview}".strip()

                if article_text:
                    article_summaries.append(article_text)
                    logger.debug(f"    [{i}] {title[:50]}...")

            # 合并摘要
            if article_summaries:
                daily_summary = " | ".join(article_summaries[:8])  # 每天最多8篇
                daily_summaries[date_str] = daily_summary
                logger.info(f"    ✅ 准备了 {len(article_summaries)} 篇摘要")

        logger.info(f"✅ 总共准备了 {len(daily_summaries)} 天的摘要")

        if not daily_summaries:
            logger.warning("⚠️  没有提取到任何摘要")
            return None

        # 生成周报
        date_range = f"{start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%m月%d日')}"
        logger.info(f"📊 日期范围字符串: {date_range}")
        logger.info(f"📊 准备生成周报综述，输入数据大小: {sum(len(v) for v in daily_summaries.values())} 字符")

        logger.info("🤖 调用Qwen生成周报综述...")
        markdown_content = worker._generate_weekly_analysis_with_qwen(
            topics=[],
            daily_summaries=daily_summaries,
            date_range=date_range
        )

        if not markdown_content:
            logger.error("❌ 周报生成失败：Qwen API返回空内容")
            return None

        logger.info(f"✅ Qwen返回内容长度: {len(markdown_content)} 字符")
        logger.info(f"📄 内容预览: {markdown_content[:200]}...")

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
            existing_weekly.article_count = len(finance_articles)
            weekly_report = existing_weekly
        else:
            logger.info("➕ 创建新周报")
            weekly_report = Report(
                report_type=ReportType.WEEKLY,
                report_date=end_date,
                title=f"财政周报述评 - {date_range}",
                summary_markdown=markdown_content_with_disclaimer,
                article_count=len(finance_articles),
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
        logger.info(f"   📊 文章数量: {len(finance_articles)}")
        logger.info(f"   📝 内容长度: {len(weekly_report.summary_markdown or '')} 字符")
        logger.info("=" * 80)

        # 发送邮件
        if send_emails:
            logger.info("\n📧 开始发送周报邮件...")

            subscribers = db.query(Subscriber).filter(
                Subscriber.is_active.is_(True),
                Subscriber.subscribe_weekly.is_(True)
            ).all()

            logger.info(f"👥 找到 {len(subscribers)} 个订阅周报的用户")

            if len(subscribers) > 0:
                try:
                    logger.info("📮 调用邮件发送服务...")
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

    parser = argparse.ArgumentParser(description='生成周报（简化版）')
    parser.add_argument('--date', type=str, help='目标日期（YYYY-MM-DD），默认为今天')
    parser.add_argument('--no-send', action='store_true', help='不发送邮件')
    parser.add_argument('--max-articles', type=int, default=100, help='最大处理文章数（默认100）')

    args = parser.parse_args()

    # 解析日期
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"❌ 日期格式错误: {args.date}，请使用 YYYY-MM-DD 格式")
            return

    logger.info(f"⚙️  配置: target_date={target_date or '今天'}, send_emails={not args.no_send}, max_articles={args.max_articles}")

    # 生成周报
    report = generate_weekly_report_simple(
        target_date=target_date,
        send_emails=not args.no_send,
        max_articles=args.max_articles
    )

    if report:
        logger.info(f"\n✅ 周报生成完成！ID: {report.id}")
    else:
        logger.error("\n❌ 周报生成失败")

if __name__ == "__main__":
    main()
