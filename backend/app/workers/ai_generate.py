"""
AI Worker - AI报告生成工作节点

职责：
1. 每天23:00生成日报
2. 每周日22:00生成周报
3. 使用阿里云Qwen API
4. 使用BERTopic进行主题聚类
"""
import sys
import json
import re
import time
import os
import asyncio
from datetime import time as dtime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Optional
import schedule

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI
from bertopic import BERTopic
from sqlalchemy.orm import Session

from shared.config import settings
from shared.database import (
    SessionLocal,
    init_db,
    Article,
    Report,
    ReportType,
    ArticleStatus,
    ReportJob,
    ReportJobStatus,
    ReportJobType,
    Subscriber,
)
from shared.utils import get_logger
from ..services.email_service import send_daily_report, send_weekly_report
from ..services.report_render import render_daily_report_html, render_daily_report_text, render_daily_report_pdf, render_markdown_to_html, render_weekly_report_pdf, render_weekly_report_text
from ..services.daily_briefing import DailyBriefingGenerator

logger = get_logger("ai-worker")


class AIWorker:
    """AI报告生成器"""
    
    def __init__(self):
        """初始化"""
        # Ensure DB schema is up-to-date (creates new tables like article_one_liners)
        try:
            init_db()
        except Exception as e:
            logger.warning(f"init_db failed in ai-worker init (non-fatal): {e}")

        # 初始化阿里云Qwen客户端（兼容OpenAI接口）
        self.client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        # Model selection (separate models for cost/perf tuning)
        # - Daily report generation: prefer stronger model (default: qwen-plus)
        # - Finance filtering: prefer cheaper/faster model (default: qwen-flash)
        self.daily_model = os.getenv("QWEN_DAILY_MODEL", "qwen-plus")
        self.filter_model = os.getenv("QWEN_FILTER_MODEL", "qwen-flash")
        # - Keyword extraction: cheap model (default: qwen-flash)
        self.keywords_model = os.getenv("QWEN_KEYWORDS_MODEL", "qwen-flash")
        # - Weekly report generation: prefer higher quality (default: qwen-max-latest)
        self.weekly_model = os.getenv("QWEN_WEEKLY_MODEL", "qwen-max-latest")

        # Daily report format:
        # - smart_brevity: 按财政信息聚合方案输出固定模块（推荐）
        # - voice: 旧版“口播稿分段”结构（兼容回滚）
        self.daily_format = os.getenv("DAILY_REPORT_FORMAT", "smart_brevity").strip().lower()
        
        logger.info("AI Worker initialized with Qwen API")
    
    def generate_daily_report(self, target_date: Optional[datetime.date] = None, send_emails: bool = True):
        """
        生成日报
        
        流程：
        1. 查询指定日期发布的所有文章（来自各地地方官微，仅限指定日期）
        2. 使用Qwen筛选出与财政相关的内容
        3. 使用Qwen生成结构化摘要
        4. 存入数据库
        5. 发送给订阅者
        
        Args:
            target_date: 目标日期，如果为None则使用今天
            send_emails: 是否在生成完成后自动发送给订阅者（默认 True；历史再生成建议 False）
        """
        db = SessionLocal()
        
        try:
            # 确定目标日期
            if target_date is None:
                target_date = datetime.now().date()
            
            logger.info(f"Starting daily report generation for {target_date}...")
            
            # 查询文章窗口（改为“昨日生成日报之后 + 今日(09:45)前”）：
            # - 覆盖：当日文章（凌晨至生成时刻） + 昨日生成日报后发布的文章
            # - 机制：优先用“昨日日报 created_at”作为窗口起点；若缺失则回退到固定 24h 窗口
            tz = ZoneInfo(os.getenv("TZ", "Asia/Shanghai") or "Asia/Shanghai")
            report_time_str = (os.getenv("DAILY_REPORT_TIME") or "09:45").strip()
            try:
                hh, mm = report_time_str.split(":")
                end_h = int(hh)
                end_m = int(mm)
            except Exception:
                end_h, end_m = 9, 45

            end_local = datetime.combine(target_date, dtime(end_h, end_m), tzinfo=tz)
            # 固定回退：从前一日相同时刻起算 24h
            fallback_start_local = end_local - timedelta(days=1)
            end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
            start_utc = fallback_start_local.astimezone(timezone.utc).replace(tzinfo=None)

            # 尝试读取“昨日日报”的创建时间，作为更精确的窗口起点
            try:
                prev_date = target_date - timedelta(days=1)
                prev_report = (
                    db.query(Report)
                    .filter(Report.report_type == ReportType.DAILY, Report.report_date == prev_date)
                    .order_by(Report.created_at.desc())
                    .first()
                )
                if prev_report and getattr(prev_report, "created_at", None):
                    # created_at 为 UTC naive（datetime.utcnow），与 Article.published_at 同口径可直接比较
                    # 但“历史再生成”时，prev_report.created_at 可能晚于当前 target_date 的 end_utc（会导致窗口反转、查不到文章）。
                    # 仅当 prev_created_at < end_utc 时才允许用作窗口起点。
                    if prev_report.created_at < end_utc:
                        start_utc = max(start_utc, prev_report.created_at)
                        logger.info(
                            f"Daily report window uses prev_report.created_at as start: "
                            f"prev_date={prev_date.isoformat()}, prev_created_at={prev_report.created_at.isoformat()}"
                        )
                    else:
                        logger.warning(
                            f"Ignore prev_report.created_at for window start (prev_created_at >= end_utc): "
                            f"prev_date={prev_date.isoformat()}, prev_created_at={prev_report.created_at.isoformat()}, "
                            f"end_utc={end_utc.isoformat()}"
                        )
            except Exception as e:
                logger.warning(f"Failed to load previous daily report created_at for window start: {e}")

            logger.info(
                f"Daily report article window (UTC): [{start_utc.isoformat()} ~ {end_utc.isoformat()}) "
                f"report_time_local={end_local.strftime('%H:%M')}"
            )

            articles = (
                db.query(Article)
                .filter(Article.published_at >= start_utc, Article.published_at < end_utc)
                .all()
            )

            # Recent hotspots window (近日热点): anchor at end_utc, roll back N days (default 3)
            # Backward compatible: still uses RECENT_HOTWORDS_WINDOW_DAYS if set.
            recent_window_days = int(os.getenv("RECENT_HOTSPOTS_WINDOW_DAYS", os.getenv("RECENT_HOTWORDS_WINDOW_DAYS", "3")) or "3")
            if recent_window_days < 1:
                recent_window_days = 3
            recent_start_utc = end_utc - timedelta(days=recent_window_days)
            recent_articles = (
                db.query(Article)
                .filter(Article.published_at >= recent_start_utc, Article.published_at < end_utc)
                .all()
            )
            logger.info(
                f"Recent hotspots article window (UTC): [{recent_start_utc.isoformat()} ~ {end_utc.isoformat()}) "
                f"rows={len(recent_articles)} days={recent_window_days}"
            )
            
            if not articles:
                logger.warning(f"No articles found for {target_date}'s report")
                return None
            
            logger.info(f"Found {len(articles)} articles from local government accounts")
            
            # 阶段1: 筛选与财政相关的内容
            finance_related_articles = self._filter_finance_related_articles(articles)
            non_finance_articles = [a for a in articles if a not in set(finance_related_articles or [])]
            
            if not finance_related_articles:
                logger.warning(f"No finance-related articles found for {target_date}'s report")
                return None
            
            logger.info(f"Filtered {len(finance_related_articles)} finance-related articles from {len(articles)} total articles")

            report_json = None
            # Smart Brevity 财政信息聚合格式
            if self.daily_format == "smart_brevity":
                # recent de-dup context: read last 3 daily reports (excluding today)
                recent_focus_styles: list[str] = []
                recent_lead_variants: list[str] = []
                recent_focus_topics: list[str] = []
                try:
                    recent = (
                        db.query(Report)
                        .filter(Report.report_type == ReportType.DAILY, Report.report_date < target_date)
                        .order_by(Report.report_date.desc())
                        .limit(3)
                        .all()
                    )
                    for r in recent:
                        cj = getattr(r, "content_json", None) or {}
                        if isinstance(cj, dict):
                            fs = cj.get("focus_style")
                            lv = cj.get("lead_variant")
                            ft = cj.get("focus_topic")
                            kws = cj.get("keywords")
                            srcs = cj.get("sources")
                            if isinstance(fs, str) and fs:
                                recent_focus_styles.append(fs)
                            if isinstance(lv, str) and lv:
                                recent_lead_variants.append(lv)
                            if isinstance(ft, str) and ft:
                                recent_focus_topics.append(ft)
                except Exception as e:
                    logger.warning(f"Failed to load recent focus styles for dedupe: {e}")

                gen = DailyBriefingGenerator(qwen_client=self.client, model=self.daily_model, keywords_model=self.keywords_model)
                report_json = gen.generate(
                    target_date=target_date,
                    finance_articles=finance_related_articles,
                    all_articles=recent_articles or articles,
                    recent_hotwords_end_utc=end_utc,
                    recent_hotwords_window_days=recent_window_days,
                    recent_focus_styles=recent_focus_styles,
                    recent_lead_variants=recent_lead_variants,
                    recent_focus_topics=recent_focus_topics,
                )
                if not report_json:
                    logger.error("Failed to generate smart_brevity daily report; falling back to voice")
                    self.daily_format = "voice"
                else:
                    # Add optional "今日彩蛋" from non-finance articles (can be not finance-related)
                    try:
                        egg = self._pick_daily_easter_egg(non_finance_articles)
                        if egg:
                            report_json["easter_egg"] = egg
                    except Exception as e:
                        logger.warning(f"Failed to attach easter_egg: {e}")

            # 旧版口播稿（voice）- 保留作为回滚路径
            if self.daily_format != "smart_brevity":
                # 阶段2: 准备AI输入（只使用财政相关的文章），并为引用提供稳定编号
                articles_text, sources_for_prompt = self._prepare_articles_text(finance_related_articles)

                # 调用Qwen：两阶段“先总后分”
                plan_text = self._generate_summary_with_qwen(
                    articles_text,
                    self._get_daily_report_plan_prompt(target_date=target_date),
                )
                if not plan_text:
                    logger.error("Failed to generate daily plan")
                    return None

                plan_json: dict = {}
                try:
                    plan_json = json.loads(plan_text)
                except Exception:
                    logger.warning("Daily plan output is not valid JSON; using fallback plan")
                    plan_json = {"themes": [], "low_relevance": []}

                draft_text = self._generate_summary_with_qwen(
                    articles_text,
                    self._get_daily_report_draft_prompt(target_date=target_date, plan_json=plan_json),
                )
                if not draft_text:
                    logger.error("Failed to generate report content")
                    return None

                try:
                    report_json = json.loads(draft_text)
                except Exception:
                    logger.warning("Daily report output is not valid JSON; falling back to minimal JSON wrapper")
                    report_json = {
                        "header": {
                            "title": f"财政日报（{target_date.isoformat()}）",
                            "date": target_date.isoformat(),
                            "brief": [draft_text[:800]],
                        },
                        "body": [
                            {
                                "topic": "正文（原始输出）",
                                "text": (draft_text or "")[:1200],
                                "citations": [],
                            }
                        ],
                        "low_relevance_notes": [],
                        "sources": sources_for_prompt,
                    }

                # 规范化：日期强制为 target_date；引用编号重排为 1..N 并同步 sources
                report_json = self._normalize_daily_report_json(
                    report_json=report_json,
                    sources_for_prompt=sources_for_prompt,
                    target_date=target_date,
                )

            # 将结构化 JSON 渲染为 HTML（前端/邮件一致展示）
            report_html = render_daily_report_html(report_json)
            
            # 如果已存在该日期日报：原地更新，避免“重新生成”导致 report_id 变化
            existing_report = db.query(Report).filter(
                Report.report_type == ReportType.DAILY,
                Report.report_date == target_date
            ).first()

            if existing_report:
                existing_report.title = f"财政晨报 - {target_date.strftime('%Y年%m月%d日')}"
                existing_report.summary_markdown = report_html
                existing_report.content_json = report_json
                existing_report.article_count = len(finance_related_articles)
                existing_report.source_article_ids = [a.id for a in finance_related_articles]
                db.commit()
                logger.info(f"Daily report updated in place: ID={existing_report.id} for {target_date}")
                if send_emails:
                    try:
                        asyncio.run(self._distribute_daily_report(db, existing_report))
                    except Exception as e:
                        logger.error(f"Auto-distribute failed for {target_date}: {e}")
                return existing_report

            # 不存在则创建
            report = Report(
                report_type=ReportType.DAILY,
                report_date=target_date,
                title=f"财政晨报 - {target_date.strftime('%Y年%m月%d日')}",
                summary_markdown=report_html,
                content_json=report_json,
                article_count=len(finance_related_articles),
                source_article_ids=[a.id for a in finance_related_articles]
            )

            db.add(report)
            db.commit()

            logger.info(f"Daily report created: ID={report.id} for {target_date}")
            if send_emails:
                try:
                    asyncio.run(self._distribute_daily_report(db, report))
                except Exception as e:
                    logger.error(f"Auto-distribute failed for {target_date}: {e}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate daily report: {str(e)}")
            db.rollback()
        finally:
            db.close()

    async def _distribute_daily_report(self, db: Session, report: Report) -> int:
        """
        将日报发送给已激活且订阅日报的用户，并更新统计。
        说明：当前为同步循环直发（适合早期/小规模）。订阅者很多时建议引入队列/批处理。
        """
        # 保护：只对“日报”做分发
        if report.report_type != ReportType.DAILY:
            return 0

        report_date = report.report_date.isoformat()
        
        # 优先从content_json重新渲染HTML，确保使用最新样式
        # 如果没有content_json，则使用数据库中保存的summary_markdown
        report_html = None
        report_json = None
        try:
            content_json = getattr(report, "content_json", None)
            if content_json:
                if isinstance(content_json, dict):
                    report_json = content_json
                elif isinstance(content_json, str):
                    report_json = json.loads(content_json)
                
                if report_json:
                    # 重新渲染HTML，使用最新的样式
                    report_html = render_daily_report_html(report_json)
                    logger.info(f"Re-rendered HTML from content_json for email (using latest styles)")
        except Exception as e:
            logger.warning(f"Failed to re-render HTML from content_json: {e}, will use saved summary_markdown")
        
        # 如果没有content_json或渲染失败，使用数据库中保存的HTML
        if not report_html:
            report_html = report.summary_markdown
        
        try:
            report_text = render_daily_report_text(report_json or getattr(report, "content_json", None) or {})
        except Exception:
            report_text = None

        # 生成PDF附件（如果启用）
        pdf_bytes = None
        pdf_filename = None
        if settings.ENABLE_PDF_ATTACHMENT:
            try:
                # 如果上面已经解析了report_json，直接使用；否则重新解析
                if not report_json:
                    content_json = getattr(report, "content_json", None)
                    if content_json:
                        if isinstance(content_json, dict):
                            report_json = content_json
                        elif isinstance(content_json, str):
                            report_json = json.loads(content_json)
                        else:
                            report_json = {}
                    else:
                        report_json = {}

                if report_json:
                    logger.info(f"Generating PDF for daily report: date={report_date}")
                    pdf_bytes = render_daily_report_pdf(report_json, report_date)
                    pdf_filename = f"z-pulse-daily-{report_date}.pdf"
                    logger.info(f"PDF generated successfully: size={len(pdf_bytes)} bytes")
                else:
                    logger.warning("Report content_json is empty, skipping PDF generation")
            except Exception as e:
                logger.error(f"PDF generation failed: {e}, will send email without PDF attachment")
                pdf_bytes = None
                pdf_filename = None

        max_per_run = int(os.getenv("DAILY_EMAIL_MAX_PER_RUN", "5000"))
        batch_commit = int(os.getenv("DAILY_EMAIL_COMMIT_EVERY", "20"))

        subscribers = (
            db.query(Subscriber)
            .filter(
                Subscriber.is_active.is_(True),
                Subscriber.subscribe_daily.is_(True),
            )
            .order_by(Subscriber.id.asc())
            .limit(max_per_run)
            .all()
        )

        if not subscribers:
            logger.warning("No active daily subscribers to send")
            return 0

        logger.info(f"Auto-sending daily report {report_date} to {len(subscribers)} subscribers (max_per_run={max_per_run}, pdf_attachment={pdf_filename is not None})")

        sent = 0
        errors = 0
        for idx, sub in enumerate(subscribers, start=1):
            try:
                did_send = await send_daily_report(
                    email=sub.email,
                    report_html=report_html,
                    report_text=report_text,
                    report_date=report_date,
                    pdf_attachment=pdf_bytes,
                    pdf_filename=pdf_filename,
                )
                if did_send:
                    sub.total_sent = int(sub.total_sent or 0) + 1
                    sub.last_sent_at = datetime.utcnow()
                    sent += 1
            except Exception as e:
                errors += 1
                logger.error(f"Failed to send daily report to {sub.email}: {e}")

            # 周期性提交，避免事务太大；也避免单封失败影响全部回滚
            if idx % batch_commit == 0:
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"Commit failed during distribution batch: {e}")

        # 更新报告统计
        report.sent_count = int(report.sent_count or 0) + sent
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Final commit failed after distribution: {e}")

        logger.info(f"Auto-distribute done for {report_date}: sent={sent}, errors={errors}")
        return sent

    def _pick_daily_easter_egg(self, articles: list[Article]):
        """
        Pick 1 'fun' non-finance article as today's easter egg.
        Output MUST be grounded in the chosen article title/snippet.
        Returns: {account,title,url,teaser}
        """
        if not articles:
            return None

        # Cap candidates to keep prompt cheap
        candidates = articles[:40]
        items = []
        idx_to_article = {}
        for i, a in enumerate(candidates, start=1):
            account_name = ""
            try:
                if getattr(a, "account", None) and getattr(a.account, "name", None):
                    account_name = a.account.name
            except Exception:
                account_name = ""
            title = (getattr(a, "title", "") or "").strip()
            url = (getattr(a, "article_url", "") or "").strip()
            content = (getattr(a, "content", "") or "").strip()
            snippet = (content[:120].replace("\n", " ").replace("\r", " ")).strip()
            if not title:
                continue
            idx_to_article[i] = a
            items.append(f"[{i}] {account_name or '（未知）'}｜{title}｜{url or '（无URL）'}｜{snippet}")

        if not items:
            return None

        system = (
            "你是日报的“今日彩蛋”挑选器。\n"
            "从候选文章中选出1篇最有趣/最能吸引人点击的（不要求财政相关）。\n"
            "要求：\n"
            "- 只输出严格JSON，不要任何解释。\n"
            "- pick 必须是候选列表里的编号。\n"
            "- teaser 必须基于候选里给出的标题/摘要片段改写成1句话（<=40字），不得编造事实。\n"
            "输出格式：{\"pick\":1,\"teaser\":\"...\"}"
        )
        user = "候选文章：\n" + "\n".join(items)

        try:
            resp = self.client.chat.completions.create(
                model=self.keywords_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.7,
                timeout=40,
            )
            text = (resp.choices[0].message.content or "").strip()
            # best-effort JSON parse
            obj = None
            try:
                l = text.find("{")
                r = text.rfind("}")
                if l != -1 and r != -1 and r > l:
                    obj = json.loads(text[l : r + 1])
            except Exception:
                obj = None
            if not isinstance(obj, dict):
                return None
            pick = obj.get("pick")
            try:
                pick = int(pick)
            except Exception:
                return None
            teaser = str(obj.get("teaser") or "").strip()
            a = idx_to_article.get(pick)
            if not a:
                return None

            account_name = ""
            try:
                if getattr(a, "account", None) and getattr(a.account, "name", None):
                    account_name = a.account.name
            except Exception:
                account_name = ""
            return {
                "account": account_name,
                "title": (getattr(a, "title", "") or "").strip(),
                "url": (getattr(a, "article_url", "") or "").strip(),
                "teaser": teaser[:120],
            }
        except Exception as e:
            logger.warning(f"Easter egg model call failed: {e}")
            return None
    
    def generate_weekly_report(self, target_date: Optional[date] = None):
        """
        生成周报（一周述评格式）
        
        流程：
        1. 获取过去7天的所有日报（包括刚生成的周一晨报）
        2. 使用BERTopic识别核心主题
        3. 使用Qwen生成Markdown格式的周报综述
        4. 存入数据库
        
        Args:
            target_date: 目标日期（周一的日期），如果为None则使用当前日期
        """
        db = SessionLocal()

        try:
            logger.info("Starting weekly report generation...")

            # 获取过去7天的日报
            end_date = target_date if target_date else datetime.now().date()
            start_date = end_date - timedelta(days=6)  # 包括今天，共7天

            daily_reports = db.query(Report).filter(
                Report.report_type == ReportType.DAILY,
                Report.report_date >= start_date,
                Report.report_date <= end_date
            ).order_by(Report.report_date).all()

            if len(daily_reports) < 3:
                logger.warning("Not enough daily reports for weekly summary")
                return

            logger.info(f"Generating weekly report from {len(daily_reports)} daily reports")

            # 使用BERTopic提取主题
            topics = self._extract_topics_with_bertopic(daily_reports)

            # 准备每日摘要
            daily_summaries = {}
            for report in daily_reports:
                date_str = report.report_date.strftime('%Y年%m月%d日')
                # 从content_json中提取关键信息
                content = report.content_json or {}
                header = content.get('header', {})
                title = header.get('title', '')
                lede = header.get('lede', '')
                why = content.get('why_it_matters', '')
                # 组合摘要
                summary = f"{title}。{lede}。{why}".strip()
                if summary:
                    daily_summaries[date_str] = summary

            if not daily_summaries:
                logger.warning("No daily summaries extracted")
                return

            # 计算日期范围字符串
            date_range = f"{start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%m月%d日')}"

            # 生成Markdown综述
            markdown_content = self._generate_weekly_analysis_with_qwen(
                topics=topics,
                daily_summaries=daily_summaries,
                date_range=date_range
            )

            if not markdown_content:
                logger.error("Failed to generate weekly review")
                return

            # 保存周报（使用Markdown格式）
            report = Report(
                report_type=ReportType.WEEKLY,
                report_date=end_date,  # 周一日期
                title=f"财政周报述评 - {start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%m月%d日')}",
                summary_markdown=markdown_content,  # 存储Markdown综述
                analysis_markdown=None,
                article_count=sum(r.article_count for r in daily_reports),
                source_article_ids=[],
                content_json=None  # 不再使用JSON格式
            )

            db.add(report)
            db.commit()

            logger.info(f"Weekly report created: ID={report.id}")

            # 自动发送周报给订阅用户
            asyncio.run(self._distribute_weekly_report(db, report, date_range))

        except Exception as e:
            logger.error(f"Failed to generate weekly report: {str(e)}")
            db.rollback()
        finally:
            db.close()

    async def _distribute_weekly_report(self, db: Session, report: Report, date_range_str: str) -> int:
        """
        将周报发送给已激活且订阅周报的用户，并更新统计。
        """
        # 保护：只对"周报"做分发
        if report.report_type != ReportType.WEEKLY:
            return 0

        report_date = report.report_date.isoformat()
        # Generate plain text for email body
        from app.services.report_render import render_weekly_report_html, render_weekly_report_text
        report_text = render_weekly_report_text(
            report.summary_markdown or "",
            report_date,
            date_range_str
        )
        logger.info(f"Generated weekly report plain text for email body")
        
        # Also generate HTML for PDF (not used in email body, but kept for compatibility)
        report_html = render_weekly_report_html(
            report.summary_markdown or "",
            report_date,
            date_range_str,
            for_email=True  # Content-only HTML for email template embedding (if needed)
        )

        # 生成PDF附件（如果启用）
        pdf_bytes = None
        pdf_filename = None
        if settings.ENABLE_PDF_ATTACHMENT:
            try:
                logger.info(f"Generating PDF for weekly report: date={report_date}")
                pdf_bytes = render_weekly_report_pdf(
                    report.summary_markdown or "",
                    report_date,
                    date_range_str
                )
                pdf_filename = f"z-pulse-weekly-{report_date}.pdf"
                logger.info(f"PDF generated successfully: size={len(pdf_bytes)} bytes")
            except Exception as e:
                logger.error(f"PDF generation failed: {e}, will send email without PDF attachment")
                pdf_bytes = None
                pdf_filename = None

        max_per_run = int(os.getenv("WEEKLY_EMAIL_MAX_PER_RUN", "5000"))
        batch_commit = int(os.getenv("WEEKLY_EMAIL_COMMIT_EVERY", "20"))

        subscribers = (
            db.query(Subscriber)
            .filter(
                Subscriber.is_active.is_(True),
                Subscriber.subscribe_weekly.is_(True),  # 假设有subscribe_weekly字段
            )
            .order_by(Subscriber.id.asc())
            .limit(max_per_run)
            .all()
        )

        if not subscribers:
            logger.warning("No active weekly subscribers to send")
            return 0

        logger.info(f"Auto-sending weekly report {report_date} to {len(subscribers)} subscribers (max_per_run={max_per_run}, pdf_attachment={pdf_filename is not None})")

        sent = 0
        errors = 0
        for idx, sub in enumerate(subscribers, start=1):
            try:
                did_send = await send_weekly_report(
                    email=sub.email,
                    report_html=report_html,  # Keep for compatibility, but email body uses report_text
                    report_date=report_date,
                    date_range_str=date_range_str,
                    report_text=report_text,  # Plain text for email body
                    pdf_attachment=pdf_bytes,
                    pdf_filename=pdf_filename,
                )
                if did_send:
                    sub.total_sent = int(sub.total_sent or 0) + 1
                    sub.last_sent_at = datetime.utcnow()
                    sent += 1
            except Exception as e:
                errors += 1
                logger.error(f"Failed to send weekly report to {sub.email}: {e}")

            # 周期性提交，避免事务太大；也避免单封失败影响全部回滚
            if idx % batch_commit == 0:
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"Commit failed during weekly distribution batch: {e}")

        # 更新报告统计
        report.sent_count = int(report.sent_count or 0) + sent
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Final commit failed after weekly distribution: {e}")

        logger.info(f"Auto-distribute weekly report done for {report_date}: sent={sent}, errors={errors}")
        return sent

    def process_pending_jobs(self, limit: int = 1):
        """
        处理待执行的后台任务（避免 API 再生成阻塞导致“系统死机”）
        """
        db = SessionLocal()
        try:
            # 回收“卡死”的 RUNNING（例如 worker 重启/崩溃后永远不会再被处理）
            stale_minutes = int(os.getenv("REPORT_JOB_STALE_MINUTES", "60"))
            stale_cutoff = datetime.utcnow() - timedelta(minutes=stale_minutes)
            stale_jobs = db.query(ReportJob).filter(
                ReportJob.job_type == ReportJobType.REGENERATE_DAILY,
                ReportJob.status == ReportJobStatus.RUNNING,
                ReportJob.started_at.isnot(None),
                ReportJob.started_at < stale_cutoff,
                ReportJob.finished_at.is_(None),
            ).all()
            if stale_jobs:
                for j in stale_jobs:
                    j.status = ReportJobStatus.FAILED
                    j.finished_at = datetime.utcnow()
                    j.error_message = f"Stale RUNNING reclaimed after {stale_minutes} minutes (worker restart/crash suspected)"
                db.commit()

            # 找一个待执行任务
            query = db.query(ReportJob).filter(ReportJob.status == ReportJobStatus.PENDING).order_by(ReportJob.created_at.asc())
            jobs = query.limit(max(1, min(limit, 5))).all()
            if not jobs:
                return

            for job in jobs:
                # 仅处理日报再生成
                if job.job_type != ReportJobType.REGENERATE_DAILY:
                    job.status = ReportJobStatus.FAILED
                    job.error_message = f"Unsupported job_type: {job.job_type}"
                    job.finished_at = datetime.utcnow()
                    db.commit()
                    continue

                # 标记为运行中
                job.status = ReportJobStatus.RUNNING
                job.started_at = datetime.utcnow()
                job.error_message = None
                db.commit()

                logger.info(f"Processing job: id={job.id}, type={job.job_type.value}, date={job.target_date}")

                try:
                    # 再生成任务默认不自动群发，避免重复打扰订阅用户
                    report = self.generate_daily_report(target_date=job.target_date, send_emails=False)
                    if report is None:
                        raise RuntimeError("generate_daily_report returned None (no finance-related or AI failed)")

                    job.status = ReportJobStatus.SUCCESS
                    job.report_id = report.id
                    job.finished_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"Job success: id={job.id}, report_id={report.id}")
                except Exception as e:
                    logger.error(f"Job failed: id={job.id}, error={str(e)}")
                    job.status = ReportJobStatus.FAILED
                    job.error_message = str(e)
                    job.finished_at = datetime.utcnow()
                    db.commit()
        finally:
            db.close()

    def _prepare_articles_text(self, articles) -> str:
        """准备文章文本用于AI分析（带引用编号与来源信息）"""
        max_total_chars = int(os.getenv("DAILY_REPORT_MAX_INPUT_CHARS", "180000"))
        per_article_max_chars = int(os.getenv("DAILY_REPORT_PER_ARTICLE_MAX_CHARS", "12000"))

        def _clean_text(s: str) -> str:
            if not isinstance(s, str):
                return ""
            # collapse whitespace but keep newlines as separators
            s = s.replace("\r\n", "\n").replace("\r", "\n")
            s = re.sub(r"[ \t]+", " ", s)
            s = re.sub(r"\n{3,}", "\n\n", s)
            return s.strip()

        def _extract_key_snippets(content: str, max_snippets: int = 10) -> list[str]:
            """
            Pull out short sentences/clauses containing high-signal facts:
            - numbers (investment/area/timeline/capacity), AND/OR
            - project purpose / what it is / what it builds (for project articles)
            This helps avoid missing key details that appear mid/late in long articles,
            without biasing the model to only repeat numbers.
            """
            if not content:
                return []
            # Split by common Chinese punctuation / line breaks
            parts = re.split(r"[。！？；;\n]", content)
            snippets: list[str] = []
            seen: set[str] = set()
            purpose_kw = [
                "项目", "基地", "平台", "示范", "产业", "生态圈", "园区", "港",
                "建设", "规划", "包含", "打造", "形成", "用于", "致力于", "服务",
                "温室", "大棚", "交易", "种植", "研发", "生产", "运营", "投用",
                "补贴", "补助", "津贴", "申领", "申请", "发放", "标准", "条件", "对象",
            ]
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                # Keep sentences that either contain numbers OR clearly describe purpose/content.
                has_num = bool(re.search(r"\d", p))
                has_purpose = any(k in p for k in purpose_kw)
                if not (has_num or has_purpose):
                    continue
                if len(p) < 10:
                    continue
                # avoid extremely long snippets
                if len(p) > 120:
                    p = p[:120].rstrip() + "…"
                if p in seen:
                    continue
                seen.add(p)
                snippets.append(p)
                if len(snippets) >= max_snippets:
                    break
            return snippets

        def _build_fulltext_for_prompt(content: str) -> str:
            """
            Prefer sending full original text (plain visible text) to Qwen.
            If extremely long, keep as much as possible while staying within per-article cap.
            """
            content = _clean_text(content or "")
            if not content:
                return ""
            if len(content) <= per_article_max_chars:
                return content
            # For very long articles, keep head + tail + key snippets (best-effort within cap).
            head_chars = int(per_article_max_chars * 0.65)
            tail_chars = int(per_article_max_chars * 0.25)
            head = content[:head_chars].rstrip()
            tail = content[-tail_chars:].lstrip()
            facts = _extract_key_snippets(content, max_snippets=12)
            facts_block = ""
            if facts:
                facts_block = "关键句（原文摘录）：\n- " + "\n- ".join(facts)
            merged = _clean_text("\n\n".join([head, facts_block, tail]).strip())
            return merged[:per_article_max_chars].rstrip()

        texts = []
        sources = []
        total_chars = 0
        for idx, article in enumerate(articles, start=1):
            account_name = ""
            try:
                if getattr(article, "account", None) and getattr(article.account, "name", None):
                    account_name = article.account.name
            except Exception:
                account_name = ""
            url = getattr(article, "article_url", "") or ""
            published_at = ""
            try:
                if getattr(article, "published_at", None):
                    published_at = article.published_at.isoformat()
            except Exception:
                published_at = ""
            body = _build_fulltext_for_prompt(article.content or "")
            block = "\n".join(
                [
                    f"[{idx}] 标题: {article.title}",
                    f"公众号: {account_name}" if account_name else "公众号: （未知）",
                    f"URL: {url}" if url else "URL: （未知）",
                    f"发布时间: {published_at}" if published_at else "发布时间: （未知）",
                    f"原文内容（纯文本）: {body}",
                ]
            )
            # stop when exceeding total budget
            if total_chars + len(block) > max_total_chars:
                break
            total_chars += len(block)
            sources.append(
                {"id": idx, "account": account_name, "title": article.title, "url": url}
            )
            texts.append(block)
        return "\n\n---\n\n".join(texts), sources
    
    def _filter_finance_related_articles(self, articles) -> list:
        """
        筛选与财政相关的文章
        
        优化策略：批量处理，减少API调用次数
        
        Args:
            articles: 文章列表
        
        Returns:
            与财政相关的文章列表
        """
        if not articles:
            return []
        
        finance_related = []

        # Heuristic fallback (only used when model output can't be parsed for some items).
        # Keep this conservative to avoid "everything is related" when parsing fails.
        finance_kw = [
            "财政", "预算", "决算", "税", "税收", "税务", "缴费", "收费", "减免",
            "补贴", "补助", "津贴", "救助", "低保", "医保", "社保", "公积金",
            "专项资金", "财政资金", "拨款", "经费", "补偿", "资金来源",
            "政府采购", "招标", "投标", "中标",
            "专项债", "债券", "国债", "基金", "融资",
            "预算执行", "绩效", "转移支付", "财会", "审计", "国资", "国企",
        ]
        strong_finance_kw = set(finance_kw)
        non_finance_title_kw = [
            "天气", "气温", "冷空气", "降温", "流星雨", "许愿",
            "演出", "音乐会", "官宣", "体育中心", "张韶涵", "于文文",
            "放假", "考试时间", "违章抓拍", "绕行", "打卡", "治愈",
            "好人", "上榜", "邀请赛", "海上急救",
        ]

        def _heuristic_keep(a) -> bool:
            t = (getattr(a, "title", "") or "") + " " + (getattr(a, "content", "") or "")
            t = t.strip()
            if not t:
                return False
            return any(k in t for k in finance_kw)

        def _looks_non_finance(a) -> bool:
            title = (getattr(a, "title", "") or "").strip()
            if not title:
                return False
            if any(k in title for k in non_finance_title_kw):
                # allow override if it also clearly contains finance keywords
                blob = title + " " + (getattr(a, "content", "") or "")
                if any(k in blob for k in strong_finance_kw):
                    return False
                return True
            return False

        filter_prompt = """角色: 你是一名专业的财政信息筛选专家。

任务: 阅读每篇文章的标题与正文片段，判断“是否与财政/资金/税费/补贴/政府采购招投标/专项债等明确相关”。

判为【相关】的必要条件（满足其一即可）：
- 明确出现财政/预算/决算/预算执行/转移支付/财政资金/专项资金/经费/拨款/资金来源等
- 明确出现税收/税务/减税降费/收费减免等
- 明确出现补贴/补助/津贴/救助/低保/医保/社保/公积金等“给付/待遇/资金标准/申领口径”
- 明确出现政府采购/招标/投标/中标/采购公告等
- 明确出现专项债/国债/地方债/债券/融资等

判为【不相关】（除非正文明确出现上述财政要素）：
- 天气预报、节假日通知、文化旅游宣传、演出赛事、好人表彰、摄影打卡、交通绕行/抓拍、单纯会议报道/领导活动等。

重要：如果不确定，判为【不相关】（宁可漏掉，也不要把全部文章都判为相关）。

输出格式(严格)：只输出 JSON（不要其他文字）。
{"items":[{"n":1,"keep":0},{"n":2,"keep":1}]} 其中 keep=1 表示相关，keep=0 表示不相关。items 必须覆盖所有给定序号。"""
        
        # 批量处理，每次处理10篇文章以提高效率
        batch_size = 10
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i+batch_size]
            try:
                # 准备批量文章内容
                batch_content = []
                for idx, article in enumerate(batch):
                    article_num = i + idx + 1
                    article_text = f"文章{article_num}:\n标题: {article.title}\n内容: {(article.content or '')[:500]}\n"
                    batch_content.append(article_text)
                
                batch_text = "\n---\n".join(batch_content)
                
                # 调用Qwen批量判断
                completion = self.client.chat.completions.create(
                    model=self.filter_model,
                    messages=[
                        {"role": "system", "content": filter_prompt},
                        {"role": "user", "content": f"请判断以下{len(batch)}篇文章是否与财政相关：\n\n{batch_text}"}
                    ],
                    temperature=0.0,
                    timeout=30  # 30秒超时
                )
                try:
                    usage = getattr(completion, "usage", None)
                    if usage:
                        logger.info(
                            f"Qwen usage (filter batch): prompt_tokens={getattr(usage,'prompt_tokens',None)}, "
                            f"completion_tokens={getattr(usage,'completion_tokens',None)}, total_tokens={getattr(usage,'total_tokens',None)}"
                        )
                except Exception:
                    pass
                
                result = (completion.choices[0].message.content or "").strip()

                # 解析结果：优先 JSON，其次回退到“序号: 相关/不相关”
                decisions_keep: dict[int, int] = {}
                try:
                    # Some models may wrap JSON with extra text / code fences; try to extract the first JSON object.
                    json_text = result
                    if "```" in json_text:
                        json_text = re.sub(r"^```[a-zA-Z]*\s*", "", json_text.strip())
                        json_text = re.sub(r"\s*```$", "", json_text.strip())
                    l = json_text.find("{")
                    r = json_text.rfind("}")
                    if l != -1 and r != -1 and r > l:
                        json_text = json_text[l : r + 1]

                    parsed = json.loads(json_text)
                    items = parsed.get("items") if isinstance(parsed, dict) else None
                    if isinstance(items, list):
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            n = it.get("n")
                            keep = it.get("keep")
                            if isinstance(n, int) and keep in (0, 1):
                                decisions_keep[n] = int(keep)
                except Exception:
                    pass

                if not decisions_keep:
                    line_pat = re.compile(r"^\s*(?:文章)?\s*(\d+)\s*[:：]\s*(相关|不相关)\s*$")
                    for line in result.splitlines():
                        m = line_pat.match(line.strip())
                        if not m:
                            continue
                        num = int(m.group(1))
                        label = m.group(2)
                        decisions_keep[num] = 1 if label == "相关" else 0

                # 解析批次 + 保护：明显非财政的标题直接剔除（除非有强财政关键词）
                kept, missing = 0, 0
                for idx, article in enumerate(batch):
                    article_num = i + idx + 1
                    keep = decisions_keep.get(article_num)
                    if keep is None:
                        missing += 1
                        keep = 1 if _heuristic_keep(article) else 0
                    if keep == 1 and _looks_non_finance(article):
                        keep = 0
                    if keep == 1:
                        finance_related.append(article)
                        kept += 1

                logger.info(
                    f"Filter batch {i//batch_size + 1}: kept={kept}/{len(batch)}, missing={missing}/{len(batch)}"
                )
                    
            except Exception as e:
                logger.warning(f"Failed to filter batch {i//batch_size + 1}: {str(e)}")
                # 如果批量判断失败，为了不遗漏重要内容，默认保留这批文章
                finance_related.extend(batch)
                logger.info(f"Kept {len(batch)} articles due to filter error")
        
        return finance_related
    
    def _get_daily_report_prompt(self, target_date: datetime.date) -> str:
        """获取日报生成提示词"""
        prompt = """你是一名资深的地方财政政策研究员，同时也是“新闻主播口播稿”的撰稿人。

任务：阅读用户提供的材料（均为公众号文章“原文纯文本”），生成一份“财政日报简报”（方案A：新闻简报+财政视角解读）。
报告日期：{REPORT_DATE}（必须严格写入 header.date，并体现在 header.title 中）。

事实优先（强制执行）：
- 尽量只陈述材料中出现的事实，不做推测/评价/建议。
- 禁止使用这类表达（除非材料原文明确出现）：可能、预计、或将、考验、压力、风险、需提前、尚待明确、效果需观察、带来……影响 等。
- 当信息缺失时：直接省略，不要写“材料未提供/尚未披露/待明确”等模板句，也不要给建议。

表达风格：
- 目标是“可语音播报的新闻稿”：短句、节奏清楚、像主播在娓娓道来今天的财政相关动态。
- 不要写清单/要点/分条，不要出现“1. / 2.”、“- ”、“•” 这类列表痕迹。
- 语言自然、精炼、有信息密度；避免“官样文章”和“填表式”句子（例如“地区：/内容：/时间节点：”）。
- 允许适度归纳，但归纳必须基于材料事实，不能引入判断性结论。
- 栏目按内容动态生成，只输出有内容的板块；禁止出现“本日无相关动态”。

数量控制：
- 正文 body：必须 3–5 段（每段一个主题），每段 2–4 句短句；段与段之间要自然过渡（如“再看…/另外…/同时…”）。
- 每段举例“点到为止”：提到 2–3 个代表性地方/事项即可，把关键口径说清楚即可（读者可通过引用看原文）。
- low_relevance_notes 最多 3 条，放在末尾做一段“顺带一提”，用口语化一句话说明为什么低相关。

引用规则（重要）：
- 材料中每篇文章都有编号，例如 [1]、[2]… 你必须在每段/每条旁注的 citations 数组中填写引用编号（可多引用）。
- header.brief/body.text/low_relevance_notes.text 中禁止手写任何形如 [1] 的引用符号（否则会重复显示）。
- sources 只列出你在 citations 中实际用到的条目，并包含 account/title/url。

正文写作要点（强制执行）：
- 每段都要把“发生地/发布主体/事项口径”说清楚：谁发布了什么、涉及谁、怎么执行、何时起、适用范围/期限（材料里有就写）。
- 每段必须覆盖 2–3 个“点到为止”的例子（不同地区/不同事项均可），并在 text 里点名提到（例如“湖州…；永康…；庆元…”），避免只写一个地方。
- 每段 citations 至少 3 个（对应段内提到的例子），最多 8 个；引用要“有用就引”，不要只引 1–2 篇导致覆盖面过窄。
- 涉及补贴：必须说清**是什么补贴**、给谁、怎么发（标准/次数/时间/渠道）。
- 涉及项目：优先说清“项目是做什么的/要建成什么”，数字只点 1 个关键锚点即可（如总投资或面积二选一）。
- 禁止写“未详述/未说明/未披露/未提及”等偷懒句；材料里有细节就复述，没有就省略。

输出格式（必须是严格 JSON；只输出 JSON，不能夹带任何其他文本）：
{
  "header": {
    "title": "财政日报（YYYY-MM-DD）",
    "date": "YYYY-MM-DD",
    "brief": ["3-6句总体判断/脉络串联（人话）", "..."]
  },
  "body": [
    {
      "topic": "主题段标题（例如：民生保障与补贴、医保与医疗、教育与人才、项目与基建、财政运行与资金管理等）",
      "text": "一段口播稿正文（2-4句短句，人话，按事实串起来，不要分条）",
      "citations": [1,3]
    }
  ],
  "low_relevance_notes": [
    { "text": "低财政相关旁注（说明低相关原因）", "citations": [4] }
  ],
  "sources": [
    { "id": 1, "account": "公众号名", "title": "文章标题", "url": "https://..." }
  ]
}

质量约束：
- 必须遵守数量要求（body 3–5 段；low_relevance_notes ≤3）。
- 只引用材料中确实出现的信息；不要编造金额、城市、政策细则。
"""
        return prompt.replace("{REPORT_DATE}", target_date.isoformat())

    def _get_daily_report_plan_prompt(self, target_date: datetime.date) -> str:
        """
        Top-down planning prompt: extract themes/common threads first, no body paragraphs yet.
        Output is used as an internal outline for the second pass.
        """
        prompt = """你是一名资深的地方财政政策研究员。

任务：阅读用户提供的材料（均为公众号文章“原文纯文本”，按[编号]区分），先做“先总后分”的提纲规划。

要求（强制）：
- 只做归纳与挑选代表性材料，不写正文口播稿，不输出任何 HTML。
- 先总后分：先抽取今天最重要/最共性的 3–5 个主题线索（themes），再为每个主题挑选 4–8 篇最能代表的材料编号（source_ids）。
- 每个主题给出 2–4 条“共性事实要点”（facts），必须来自材料，不得推测。
- 不输出低相关旁注（本系统不展示“顺带一提”）。
- 引用号（如 [12]）只用于后续正文在“地名后”内联，不要在本提纲中出现。

输出格式（必须是严格 JSON；只输出 JSON）：
{
  "date": "YYYY-MM-DD",
  "themes": [
    {
      "topic": "主题名（短）",
      "facts": ["共性事实要点（短句）", "..."],
      "source_ids": [1,3,5]
    }
  ],
  "low_relevance": []
}
"""
        return prompt.replace("YYYY-MM-DD", target_date.isoformat())

    def _get_daily_report_draft_prompt(self, target_date: datetime.date, plan_json: dict) -> str:
        """
        Draft prompt: write voice-style body paragraphs from the plan, then attach citations per paragraph.
        """
        plan_text = json.dumps(plan_json or {}, ensure_ascii=False)
        prompt = f"""你是一名资深的地方财政政策研究员，同时也是“新闻主播口播稿”的撰稿人。

任务：根据给定“提纲规划”（plan），把日报写成可语音播报的口播稿：先总后分。
报告日期：{target_date.isoformat()}（必须严格写入 header.date，并体现在 header.title 中）。

硬性要求（强制执行）：
- 正文 body 必须 3–5 段，每段一个主题；每段 2–4 句短句，口语化，但只讲材料事实。
- 先总后分：每段先用 1 句概括本段共性，再用 1–3 句点到为止举 2–3 个例子（不同地区/事项），例子必须来自 plan.themes[].source_ids 指向的材料。
- 引用（很重要）：不要“段末堆叠引用”。你必须把引用号写在正文里，紧跟在**具体地名**后面（例如：湖州[2]、永康[5]、庆元[7]），通常每处地名只跟 1 个引用号即可。
  - body.citations 仍然要给出该段用到的所有引用编号（用于生成 sources 列表和重排编号），但渲染时不会再把 citations 堆在段末。
- 简报概览 header.brief：3–6 句，必须从正文各段“第一句概括”改写而来（不要出现正文没有的地名/事项）。
- 不输出 low_relevance_notes 字段（去掉“顺带一提”）。

提纲规划（plan）如下（JSON）：\n{plan_text}

输出格式（必须是严格 JSON；只输出 JSON）：
{{
  "header": {{
    "title": "财政日报（YYYY-MM-DD）",
    "date": "YYYY-MM-DD",
    "brief": ["3-6句（从正文概括改写）", "..."]
  }},
  "body": [
    {{
      "topic": "主题段标题（短）",
      "text": "2-4句口播正文（短句、人话，不分条；地名后面要内联引用号，如 湖州[2]）",
      "citations": [1,3]
    }}
  ],
  "low_relevance_notes": [],
  "sources": [
    {{ "id": 1, "account": "公众号名", "title": "文章标题", "url": "https://..." }}
  ]
}}
"""
        return prompt

    def _normalize_daily_report_json(self, report_json: dict, sources_for_prompt: list, target_date: datetime.date) -> dict:
        """
        规范化日报 JSON：
        1) header.date 强制为 target_date
        2) 清理文本内残留的 [数字] 引用，避免与渲染器重复
        3) 引用编号重排为 1..N（只保留被引用的来源），并同步 sources 列表
        """
        if not isinstance(report_json, dict):
            return report_json

        header = report_json.get("header")
        if not isinstance(header, dict):
            header = {}
            report_json["header"] = header
        header["date"] = target_date.isoformat()
        header["title"] = f"财政日报（{target_date.isoformat()}）"

        # strip inline [123] that might appear in text fields
        inline_pat = re.compile(r"(?:\s*\[\d+\]){1,}")

        def strip_inline(s):
            if not isinstance(s, str):
                return s
            return inline_pat.sub("", s).strip()

        # remove templated/filler sentences if model still outputs them
        banned_fragments = [
            "材料未提供",
            "尚待明确",
            "待明确",
            "需跟踪",
            "需关注",
            "效果需观察",
            "未详述",
            "未说明",
            "未披露",
            "未提及",
        ]

        def strip_banned(s):
            if not isinstance(s, str):
                return s
            out = s
            for frag in banned_fragments:
                if frag in out:
                    # drop the whole line/sentence by returning empty; caller will filter empties
                    return ""
            return out.strip()

        # Heuristic topic tokens to detect mismatch between what and explanation
        topic_tokens = [
            "育儿", "生育", "生娃",
            "高龄", "养老",
            "医保", "医疗",
            "教育", "学校",
            "人才", "引才", "高校",
            "就业",
            "采购", "招标",
            "项目", "开工", "投资",
            "文旅", "免门票",
            "补贴", "津贴", "补助",
            "税", "减免",
            "应急", "演练",
            "科技", "创新", "研发",
        ]

        def extract_topics(text: str) -> set[str]:
            if not isinstance(text, str) or not text:
                return set()
            found: set[str] = set()
            for t in topic_tokens:
                if t in text:
                    found.add(t)
            return found

        ordered_old_ids: list[int] = []
        seen: set[int] = set()

        def consume_citations(cits):
            if not isinstance(cits, list):
                return []
            out = []
            for x in cits:
                try:
                    n = int(x)
                except Exception:
                    continue
                out.append(n)
                if n not in seen:
                    seen.add(n)
                    ordered_old_ids.append(n)
            return out

        def normalize_item(obj: dict, text_keys: list[str]):
            if not isinstance(obj, dict):
                return
            for k in text_keys:
                if k in obj:
                    obj[k] = strip_banned(strip_inline(obj.get(k)))
            if "citations" in obj:
                obj["citations"] = consume_citations(obj.get("citations"))

            # Enforce "what" as headline derived from explanation (best-effort, no new facts).
            if isinstance(obj, dict):
                what_txt = obj.get("what")
                exp_txt = obj.get("explanation")
                if isinstance(exp_txt, str):
                    exp_txt = exp_txt.strip()
                if isinstance(what_txt, str):
                    what_txt = what_txt.strip()

                # Make explanation shorter / more "human": 1–2 sentences, remove trailing fillers.
                if isinstance(exp_txt, str) and exp_txt:
                    # Drop common bureaucratic openers
                    exp_txt = re.sub(r"^(?:据了解|据悉|记者从|为进一步|为深入|为切实|近日|日前|近期|本次|此次)\s*", "", exp_txt).strip()
                    # Keep at most 2 sentence-like segments
                    segs = [s.strip() for s in re.split(r"[。！？;\n]", exp_txt) if s.strip()]
                    exp_txt = "。".join(segs[:2]).strip()
                    if exp_txt and not exp_txt.endswith(("。", "！", "？")):
                        exp_txt += "。"
                    # Soft length cap (avoid overly long explanations)
                    if len(exp_txt) > 90:
                        exp_txt = exp_txt[:90].rstrip()
                        # ensure not ending with comma-like punctuation
                        exp_txt = re.sub(r"[，,、:：；;]+$", "", exp_txt).strip()
                        if exp_txt and not exp_txt.endswith(("。", "！", "？")):
                            exp_txt += "。"
                    obj["explanation"] = exp_txt

                if isinstance(exp_txt, str) and exp_txt:
                    if (not isinstance(what_txt, str)) or (not what_txt) or len(what_txt) > 80 or ("\n" in what_txt):
                        # Use first sentence/clause of explanation as fallback headline.
                        first = re.split(r"[。；;\n]", exp_txt, maxsplit=1)[0].strip()
                        if first:
                            what_txt = first
                    # make "what" look like a title: remove trailing punctuation
                    if isinstance(what_txt, str) and what_txt:
                        what_txt = re.sub(r"[。；;：:，,]+$", "", what_txt).strip()
                        # soft length cap
                        if len(what_txt) > 60:
                            what_txt = what_txt[:60].rstrip()
                        obj["what"] = what_txt

        def shorten_spoken(text: str, *, max_sents: int = 2, max_chars: int = 180, ensure_punct: bool = True) -> str:
            """Short, spoken-style: keep N sentences and remove common bureaucratic openers."""
            if not isinstance(text, str):
                return ""
            t = text.strip()
            if not t:
                return ""
            t = re.sub(r"^(?:据了解|据悉|记者从|为进一步|为深入|为切实|近日|日前|近期|本次|此次)\s*", "", t).strip()
            segs = [s.strip() for s in re.split(r"[。！？;\n]", t) if s.strip()]
            t = "。".join(segs[: max_sents]).strip()
            if ensure_punct and t and not t.endswith(("。", "！", "？")):
                t += "。"
            if len(t) > max_chars:
                t = t[:max_chars].rstrip()
                t = re.sub(r"[，,、:：；;]+$", "", t).strip()
                if ensure_punct and t and not t.endswith(("。", "！", "？")):
                    t += "。"
            return t

        # New schema mode: body paragraphs (主播口播)
        body = report_json.get("body")
        has_body = isinstance(body, list) and any(isinstance(x, dict) for x in body)
        if has_body:
            # brief cleanup
            if isinstance(header.get("brief"), list):
                header["brief"] = [strip_banned(strip_inline(x)) for x in header["brief"] if isinstance(x, str)]
                header["brief"] = [x for x in header["brief"] if x]
            # normalize body segments
            for seg in body:
                if not isinstance(seg, dict):
                    continue
                seg["topic"] = strip_banned(strip_inline(seg.get("topic"))) if isinstance(seg.get("topic"), str) else ""
                # Keep inline citations like “湖州[12]” in body text (no strip_inline here).
                seg["text"] = strip_banned(seg.get("text")) if isinstance(seg.get("text"), str) else ""
                seg["topic"] = shorten_spoken(seg["topic"], max_sents=1, max_chars=40, ensure_punct=False).rstrip("。！？?").strip()
                # Body is a spoken paragraph: keep up to 4 short sentences (2-4 is desired), avoid over-truncation.
                seg["text"] = shorten_spoken(seg["text"], max_sents=4, max_chars=320, ensure_punct=True)
                seg["citations"] = consume_citations(seg.get("citations"))
                # Also consume inline citations to ensure sources list covers them
                try:
                    inline_nums = [int(x) for x in re.findall(r"\[(\d+)\]", seg["text"])]
                    consume_citations(inline_nums)
                except Exception:
                    pass
            # 用户要求：去掉 low_relevance_notes（不展示/不输出）
            report_json.pop("low_relevance_notes", None)

            # Rebuild brief from body to ensure consistency (brief should not mention places/themes absent in body)
            rebuilt_brief: list[str] = []
            for seg in body:
                if not isinstance(seg, dict):
                    continue
                t = seg.get("text") if isinstance(seg.get("text"), str) else ""
                if not t:
                    continue
                # take first sentence-like segment as one brief line
                first = re.split(r"[。！？;\n]", t.strip(), maxsplit=1)[0].strip()
                # remove inline citation markers from brief
                first = re.sub(r"(?:\s*\[\d+\]){1,}", "", first).strip()
                if first:
                    rebuilt_brief.append(first)
            # keep 3-6 lines if available
            if rebuilt_brief:
                header["brief"] = rebuilt_brief[:6]

        highlights = [] if has_body else (report_json.get("highlights") or [])
        if not has_body and isinstance(highlights, list):
            for it in highlights:
                normalize_item(it, ["text"])

        sections = [] if has_body else (report_json.get("sections") or [])
        if not has_body and isinstance(sections, list):
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                items = sec.get("items")
                if isinstance(items, list):
                    for it in items:
                        normalize_item(it, ["what", "explanation"])
                        if isinstance(it, dict):
                            it.pop("so_what", None)
                            # If what/explanation talk about different topics, drop explanation to avoid wrong info.
                            what_txt = (it.get("what") or "") if isinstance(it.get("what"), str) else ""
                            exp_txt = (it.get("explanation") or "") if isinstance(it.get("explanation"), str) else ""
                            what_topics = extract_topics(what_txt)
                            exp_topics = extract_topics(exp_txt)
                            if what_txt and exp_txt and what_topics and exp_topics and what_topics.isdisjoint(exp_topics):
                                it["explanation"] = ""
                            # Ensure explanation is not empty: if model omitted it, degrade to what (no new facts).
                            if (not it.get("explanation")) and what_txt:
                                it["explanation"] = what_txt
                            # Derive what from explanation if what is missing/too short, to follow "explanation -> what" flow.
                            exp_txt2 = (it.get("explanation") or "") if isinstance(it.get("explanation"), str) else ""
                            if exp_txt2 and (not what_txt or len(what_txt.strip()) < 10):
                                # take first sentence-like segment as headline
                                seg = re.split(r"[。！？；;\n]", exp_txt2.strip())[0].strip()
                                if seg:
                                    it["what"] = seg
                        if isinstance(it, dict) and isinstance(it.get("signals"), list):
                            it["signals"] = [strip_banned(strip_inline(s)) for s in it["signals"] if s]
                            it["signals"] = [s for s in it["signals"] if s]
                            # 去重：signals 不要重复 what/explanation 已包含的事实；过滤过短信号
                            what_txt = (it.get("what") or "") if isinstance(it.get("what"), str) else ""
                            exp_txt = (it.get("explanation") or "") if isinstance(it.get("explanation"), str) else ""
                            what_topics = extract_topics(what_txt)
                            combined = f"{what_txt} {exp_txt}"
                            filtered = []
                            for s in it["signals"]:
                                if not isinstance(s, str):
                                    continue
                                if len(s.strip()) < 8:
                                    continue
                                if s.strip() in combined:
                                    continue
                                sig_topics = extract_topics(s)
                                if what_topics and sig_topics and sig_topics.isdisjoint(what_topics):
                                    continue
                                filtered.append(s.strip())
                            it["signals"] = filtered[:4]
                        if isinstance(it, dict) and isinstance(it.get("explanation"), str) and not it["explanation"]:
                            # keep empty allowed; no-op
                            pass

        # Rebuild highlights only for legacy schema (sections/items)
        if not has_body:
            section_items: list[dict] = []
            if isinstance(sections, list):
                for sec in sections:
                    if isinstance(sec, dict) and isinstance(sec.get("items"), list):
                        for it in sec["items"]:
                            if isinstance(it, dict) and (it.get("what") or it.get("explanation")):
                                section_items.append(it)

            rebuilt_highlights = []
            for it in section_items[:4]:
                text = it.get("what") or ""
                if isinstance(text, str):
                    first = re.split(r"[。\n]", text, maxsplit=1)[0].strip()
                    if first:
                        rebuilt_highlights.append({"text": first, "citations": it.get("citations") or []})
            if rebuilt_highlights:
                report_json["highlights"] = rebuilt_highlights
                highlights = report_json["highlights"]
        else:
            # voice format doesn't use highlights/sections
            report_json.pop("highlights", None)
            report_json.pop("sections", None)

        # 报告中不展示“明日关注”，即便模型输出也直接移除
        if "watchlist" in report_json:
            report_json.pop("watchlist", None)

        low_notes = report_json.get("low_relevance_notes")
        if isinstance(low_notes, list):
            for it in low_notes:
                normalize_item(it, ["text"])

        # Map original prompt ids -> source dict
        id_to_source = {}
        for s in sources_for_prompt or []:
            if isinstance(s, dict) and "id" in s:
                try:
                    id_to_source[int(s["id"])] = s
                except Exception:
                    pass

        mapping: dict[int, int] = {}
        new_sources: list[dict] = []
        next_id = 1
        for old in ordered_old_ids:
            src = id_to_source.get(old)
            if not src:
                continue
            mapping[old] = next_id
            new_sources.append(
                {
                    "id": next_id,
                    "account": src.get("account") or "",
                    "title": src.get("title") or "",
                    "url": src.get("url") or "",
                }
            )
            next_id += 1

        def remap_cits(cits):
            if not isinstance(cits, list):
                return []
            out = []
            for x in cits:
                try:
                    old = int(x)
                except Exception:
                    continue
                if old in mapping:
                    out.append(mapping[old])
            # de-dup keep order
            seen2 = set()
            dedup = []
            for n in out:
                if n not in seen2:
                    seen2.add(n)
                    dedup.append(n)
            return dedup

        def remap_inline_markers(text: str) -> str:
            if not isinstance(text, str) or not text:
                return ""
            def _rep(m):
                try:
                    old = int(m.group(1))
                except Exception:
                    return m.group(0)
                if old in mapping:
                    return f"[{mapping[old]}]"
                return m.group(0)
            return re.sub(r"\[(\d+)\]", _rep, text)

        if isinstance(highlights, list):
            for it in highlights:
                if isinstance(it, dict):
                    it["citations"] = remap_cits(it.get("citations"))

        if isinstance(sections, list):
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                items = sec.get("items")
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict):
                            it["citations"] = remap_cits(it.get("citations"))

        # watchlist 已移除

        if isinstance(low_notes, list):
            for it in low_notes:
                if isinstance(it, dict):
                    it["citations"] = remap_cits(it.get("citations"))

        # remap citations in new voice-format body
        body3 = report_json.get("body")
        if isinstance(body3, list):
            for seg in body3:
                if isinstance(seg, dict):
                    seg["citations"] = remap_cits(seg.get("citations"))
                    # keep inline markers in sync with remapped ids
                    if isinstance(seg.get("text"), str):
                        seg["text"] = remap_inline_markers(seg.get("text"))

        report_json["sources"] = new_sources
        return report_json
    
    def _generate_summary_with_qwen(self, articles_text: str, system_prompt: str) -> str:
        """
        使用Qwen生成摘要
        
        Args:
            articles_text: 文章原文
            system_prompt: 系统提示词
        
        Returns:
            生成的报告内容
        """
        import time
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling Qwen API (attempt {attempt + 1}/{max_retries})...")
                max_chars = int(os.getenv("DAILY_REPORT_MAX_INPUT_CHARS", "180000"))
                material = articles_text[:max_chars]
                completion = self.client.chat.completions.create(
                    model=self.daily_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"请分析以下原始材料（均为原文纯文本，按[编号]区分）：\n\n{material}"}
                    ],
                    temperature=0.3,  # 降低随机性，确保财经报告的严肃性
                    timeout=120  # 120秒超时
                )
                
                try:
                    usage = getattr(completion, "usage", None)
                    if usage:
                        logger.info(
                            f"Qwen usage (daily report): prompt_tokens={getattr(usage,'prompt_tokens',None)}, "
                            f"completion_tokens={getattr(usage,'completion_tokens',None)}, total_tokens={getattr(usage,'total_tokens',None)}"
                        )
                except Exception:
                    pass
                
                result = completion.choices[0].message.content
                logger.info("Successfully generated report content")
                return result
                
            except Exception as e:
                logger.warning(f"Qwen API call failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"Failed to call Qwen API after {max_retries} attempts: {str(e)}")
                    return None
        
        return None
    
    def _extract_topics_with_bertopic(self, daily_reports) -> list:
        """
        使用BERTopic提取核心主题
        
        Args:
            daily_reports: 日报列表
        
        Returns:
            主题列表
        """
        try:
            # 准备文档
            documents = [report.summary_markdown for report in daily_reports if report.summary_markdown]
            
            if not documents:
                logger.warning("No documents available for topic extraction")
                return []
            
            logger.info(f"Starting BERTopic extraction for {len(documents)} documents...")
            
            # 初始化BERTopic模型
            topic_model = BERTopic(
                language="chinese (simplified)",
                calculate_probabilities=True,
                verbose=True
            )
            
            # 训练模型并提取主题（无论耗时多长都要完成）
            topics, probs = topic_model.fit_transform(documents)
            
            # 获取主题信息
            topic_info = topic_model.get_topic_info()
            
            # 提取前5个主题
            core_topics = []
            for idx in range(min(5, len(topic_info) - 1)):  # 跳过-1（噪音主题）
                topic_words = topic_model.get_topic(idx)
                if topic_words:
                    topic_keywords = [word for word, _ in topic_words[:5]]
                    core_topics.append({
                        "topic_id": idx,
                        "keywords": topic_keywords,
                        "description": ", ".join(topic_keywords)
                    })
            
            logger.info(f"Extracted {len(core_topics)} core topics")
            return core_topics
            
        except Exception as e:
            logger.warning(f"Failed to extract topics (will continue without topics): {str(e)}")
            # 即使BERTopic失败，也返回空列表，让周报生成继续
            return []

    def _generate_weekly_smart_brevity(
        self,
        daily_content_list: list,
        all_articles: list,
        start_date,
        end_date
    ) -> dict:
        """
        使用Qwen生成周报Smart Brevity格式

        Args:
            daily_content_list: 每日报告的content_json列表
            all_articles: 所有文章列表
            start_date: 周报开始日期
            end_date: 周报结束日期

        Returns:
            Smart Brevity格式的周报JSON
        """
        import json

        # 提取本周关键主题
        weekly_themes = []
        all_keywords = {}

        for daily in daily_content_list:
            content = daily.get('content', {})
            header = content.get('header', {})
            keywords = content.get('recent_hotspots', content.get('keywords', []))

            # 收集关键词频率
            for kw in keywords:
                if isinstance(kw, dict):
                    word = kw.get('event', kw.get('word', ''))
                else:
                    word = str(kw)

                if word:
                    all_keywords[word] = all_keywords.get(word, 0) + 1

            # 收集焦点主题
            lede = header.get('lede', '')
            if lede:
                weekly_themes.append(lede[:200])

        # 排序关键词（取前15个）
        top_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:15]

        # 准备Smart Brevity格式的prompt
        system_prompt = """你是一位资深财政分析专家，擅长撰写简洁有力的周报分析。

请基于过去7天的日报内容，生成一份Smart Brevity格式的周报。要求：
1. 标题：简洁有力，一句话概括本周核心
2. 导语（lede）：3-4句话，说清本周最重要的事情
3. 为何重要：解释为什么这周值得关注
4. 本周热点：列出5-7个本周最热门的关键词
5. 来源引用：引用具体的文章来源

输出必须是严格的JSON格式，包含以下字段：
{
  "schema": "smart_brevity_v1",
  "header": {
    "title": "周报标题",
    "lede": "导语内容",
    "lede_citations": [1, 2, 3]
  },
  "why_it_matters": "为何重要",
  "why_citations": [4, 5],
  "recent_hotspots": [
    {
      "event": "热点事件",
      "hotness": 10,
      "why_hot": "为什么热门",
      "source_ids": [1, 2]
    }
  ],
  "recent_hotspots_meta": {
    "window_days": 7
  },
  "sources": [
    {
      "id": 1,
      "account": "公众号名称",
      "title": "文章标题",
      "url": "链接"
    }
  ]
}"""

        # 准备日报摘要
        daily_summary = ""
        for i, daily in enumerate(daily_content_list[:7]):
            date = daily.get('date', '')
            content = daily.get('content', {})
            header = content.get('header', {})
            title = header.get('title', '')
            lede = header.get('lede', '')

            daily_summary += f"\n日期: {date}\n标题: {title}\n导语: {lede[:150]}\n"

        # 准备文章来源（前20篇）
        sources_text = ""
        for i, article in enumerate(all_articles[:20]):
            if isinstance(article, dict):
                account = article.get('account', '未知')
                title = article.get('title', '')
                sources_text += f"\n[{i+1}] {account} - {title}"

        user_prompt = f"""请生成周报，时间范围：{start_date} 至 {end_date}

本周关键词热度：
{chr(10).join([f'{word}({count}次)' for word, count in top_keywords[:10]])}

日报摘要：
{daily_summary}

文章来源：
{sources_text}

请生成Smart Brevity格式的JSON周报。"""

        try:
            completion = self.client.chat.completions.create(
                model=self.weekly_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )

            response_text = completion.choices[0].message.content.strip()

            # 尝试提取JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text

            report_json = json.loads(json_str)

            # 添加sources
            if not report_json.get('sources'):
                report_json['sources'] = []
                for i, article in enumerate(all_articles[:30]):
                    if isinstance(article, dict):
                        report_json['sources'].append({
                            "id": i + 1,
                            "account": article.get('account', ''),
                            "title": article.get('title', ''),
                            "url": article.get('url', '')
                        })

            return report_json

        except Exception as e:
            logger.error(f"Failed to generate weekly Smart Brevity: {str(e)}")
            return None

    def _generate_weekly_analysis_with_qwen(
        self,
        topics: list,
        daily_summaries: dict,
        date_range: str = ""
    ) -> str:
        """
        使用Qwen生成周报分析（综述评价型）
        
        Args:
            topics: BERTopic提取的主题列表
            daily_summaries: 每日摘要字典
            date_range: 日期范围字符串（用于标题）
        
        Returns:
            Markdown格式的周报内容
        """
        topics_text = "\n".join([
            f"主题 {i+1}: {t['description']}"
            for i, t in enumerate(topics)
        ])
        
        daily_text = "\n\n".join([
            f"**{day}**: {summary[:300]}..."
            for day, summary in daily_summaries.items()
        ])
        
        system_prompt = f"""角色: 你是一位具有战略思维和跨领域洞察力的财政分析专家。你擅长从海量信息中发现隐藏的模式、趋势和深层逻辑，提供人类视角难以察觉的独特洞察。你能够跳出财政看财政，将财政动态与宏观经济、社会趋势、政策周期、区域发展等更广阔的背景联系起来。

任务: 基于过去7天的晨报内容，撰写一份"深度洞察周报"。这不是简单的事实汇总，而是一次"模式发现"和"逻辑推理"的智力探索。

核心要求：
1. **跳出财政看财政**：从宏观经济、社会趋势、政策周期、区域发展等更广阔视角分析财政动态，揭示财政与其他领域的深层逻辑关系。
2. **全局视角**：不要逐一分析事件，要从全局视角识别本周最有价值的1个核心洞察。
3. **深度洞察**：只有真正发现深刻洞察时才写，不要勉强。洞察要有深度和说服力，有逻辑支撑。
4. **跨领域连接**：将财政动态与更宏观的背景联系起来，例如：
   - 宏观经济趋势（经济结构调整、增长动力转换等）
   - 社会趋势（人口结构、就业形势、民生需求等）
   - 政策周期（政策窗口期、政策协同效应等）
   - 区域发展（区域差异、协同发展等）
   - 系统性逻辑（资源配置逻辑、政策组合效应等）

识别出的核心主题 (本周焦点):
{topics_text}

每日摘要 (原始材料):
{daily_text}

输出格式 (必须严格遵守, 使用Markdown):

# [一句话总结本周最深刻的跨领域洞察，例如："年末政策窗口效应：财政资源配置的时间逻辑与民生优先导向"或"财政与区域发展的协同逻辑：从分散到系统的资源配置转变"等。不要包含日期，因为日期已在标题栏显示。]

[核心洞察 - 550-650字]
从宏观经济、社会趋势、政策周期、区域发展等更广阔视角，
深入分析本周财政动态背后的深层逻辑。

分析维度（根据实际情况选择最合适的角度）：
1. **宏观背景**：本周财政动态反映了什么宏观经济趋势？
2. **政策周期**：在政策周期中的位置和意义？
3. **社会趋势**：与民生、就业、区域发展等社会趋势的关系？
4. **系统性逻辑**：财政资源配置背后的系统性逻辑是什么？
5. **未来影响**：可能带来的影响和趋势？

要求：
- 不要逐一列举事件，要从全局视角提炼洞察
- 要有跨领域的连接和思考，跳出财政看财政
- 洞察要有深度和说服力，有逻辑支撑
- 语言精炼，每句话都有信息量
- 每段控制在3-4句，不超过5句
- **重要：在分析过程中自然地融入2-3个关键事件或数据点作为支撑，但不要单独列出"关键证据"部分，要将证据融入到正文分析中**

字数控制（严格执行，必须遵守）：
- 核心洞察：550-650字（包含融入的关键事件和数据点）
- 总计：550-650字（严格控制在600字左右，绝对不能超过700字）

写作风格：
- 语言专业、深刻、有洞察力
- 每段3-4句，不超过5句
- 精简表达，每句话都要有信息量
- 聚焦最深刻的洞察，不展开细节
- 以事实为基础，但要有深度分析
- **重要：不要使用任何内联引用标注（如[1]、[2]等），保持文本的流畅性和连贯性，让读者能够顺畅阅读**
- **重要：不要使用任何二级标题（##），直接写核心洞察内容，将关键事件和数据点自然融入到正文分析中，不要单独列出"关键证据"部分**"""
        
        try:
            completion = self.client.chat.completions.create(
                model=self.weekly_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请生成本周的财政周报深度洞察，字数严格控制在600字左右（绝对不能超过700字，目标550-650字）。要求：1. 跳出财政看财政，从宏观经济、社会趋势、政策周期、区域发展等更广阔视角分析；2. 不要逐一分析事件，要从全局视角识别本周最有价值的1个核心洞察；3. 只有真正发现深刻洞察时才写，不要勉强，洞察要有深度和说服力；4. 将财政动态与更宏观的背景联系起来，揭示跨领域的深层逻辑关系；5. 在分析过程中自然地融入2-3个关键事件或数据点作为支撑，不要单独列出\"关键证据\"部分，要将证据融入到正文分析中；6. 不要使用任何内联引用标注（如[1]、[2]等），保持文本流畅性和阅读连贯性；7. 不要使用任何二级标题（##），直接写核心洞察内容；8. 生成后请检查总字数，如果超过700字必须精简到600字左右；9. 每段控制在3-4句，不超过5句。"}
                ],
                temperature=0.7
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate weekly report: {str(e)}")
            return None


def main():
    """主函数 - 定时任务调度"""
    worker = AIWorker()
    
    # 配置定时任务
    daily_time = settings.DAILY_REPORT_TIME
    
    # 生成晨报的包装函数：如果是周一，晨报生成后立即生成周报
    def generate_daily_with_weekly_check():
        report = worker.generate_daily_report()
        # 如果是周一（weekday() 返回 0），晨报生成后立即生成周报
        if report and datetime.now().weekday() == 0:  # 0 = Monday
            logger.info("Monday detected, generating weekly report after daily report...")
            time.sleep(5)  # 等待5秒确保晨报已保存到数据库
            worker.generate_weekly_report()
    
    # 每天生成晨报（周一晨报生成后会自动生成周报）
    schedule.every().day.at(daily_time).do(generate_daily_with_weekly_check)
    logger.info(f"Scheduled daily report at {daily_time} (weekly report auto-triggers on Monday after daily report)")
    
    logger.info("AI Worker started, waiting for scheduled tasks...")

    # 每分钟处理一次后台任务队列
    schedule.every(1).minutes.do(worker.process_pending_jobs)
    logger.info("Scheduled job queue processing every 1 minute")
    
    # 运行调度器
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {str(e)}")
            time.sleep(60)


if __name__ == "__main__":
    main()

