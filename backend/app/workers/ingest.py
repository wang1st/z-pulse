"""
Ingestion Worker - RSS采集工作节点

职责：定期轮询rss-bridge服务，解析RSS，并将新文章存入数据库
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, date

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx
import feedparser
import re
import html as _html
import os
import sqlite3
from sqlalchemy.orm import Session

from shared.config import settings
from shared.database import SessionLocal, OfficialAccount, Article, ArticleStatus
from shared.utils import get_logger

logger = get_logger("ingestion-worker")

def _parse_min_article_date() -> date | None:
    """
    Minimum published date allowed for ingestion (local policy).
    Set via env MIN_ARTICLE_DATE=YYYY-MM-DD.
    """
    v = (os.getenv("MIN_ARTICLE_DATE") or "").strip()
    if not v:
        return None
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except Exception:
        return None


class IngestionWorker:
    """RSS采集工作器"""
    
    def __init__(self):
        """初始化"""
        self.rss_bridge_url = settings.RSS_BRIDGE_URL
        self.poll_interval = settings.POLL_INTERVAL
        self._ingest_offset_minutes = int(os.getenv("INGEST_OFFSET_MINUTES", "0") or "0")
        self._werss_token: str | None = None
        self._werss_token_exp_ts: float = 0.0
        self._fetch_full_content = (os.getenv("FETCH_FULL_CONTENT", "True").lower() == "true")
        self._werss_username = os.getenv("WERSS_ADMIN_USERNAME") or "admin"
        self._werss_password = os.getenv("WERSS_ADMIN_PASSWORD") or "admin@123"
        self._fulltext_timeout = float(os.getenv("FULLTEXT_TIMEOUT", "40"))
        self._fulltext_max_retries = int(os.getenv("FULLTEXT_MAX_RETRIES", "3"))
        self._fulltext_retry_base_sleep = float(os.getenv("FULLTEXT_RETRY_BASE_SLEEP", "2"))
        # Throttle between fulltext requests (seconds) to reduce rate-limit / 风控
        self._fulltext_min_interval = float(os.getenv("FULLTEXT_MIN_INTERVAL", "1.5"))
        self._last_fulltext_ts: float = 0.0
        self._werss_db_path = os.getenv("WERSS_DB_PATH") or ""
        self._use_werss_db = (os.getenv("USE_WERSS_DB", "True").lower() == "true")
        self._werss_db_limit = int(os.getenv("WERSS_DB_LIMIT", "400"))
        self._min_article_date = _parse_min_article_date()
    
    def run(self):
        """
        主运行循环
        
        默认按固定间隔执行采集。
        当 poll_interval=1800（30分钟）时，为了满足“整点/半点开始采集”，会对齐到每小时的 :00 / :30 触发。
        """
        logger.info("Ingestion worker started")
        logger.info(f"RSS Bridge URL: {self.rss_bridge_url}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
        while True:
            try:
                # 每天只跑一次：对齐到 21:00（本地时区）
                if self.poll_interval >= 86400:
                    run_at = (os.getenv("INGEST_RUN_AT") or "21:00").strip()
                    self._sleep_until_daily_time(run_at)
                    self.collect_all_feeds()
                    # 下一轮继续对齐到次日 21:00（避免按固定秒数漂移）
                    continue

                # 对齐到整点/半点（仅在 30 分钟模式启用）
                if self.poll_interval == 1800:
                    self._sleep_until_next_half_hour(offset_minutes=self._ingest_offset_minutes)

                self.collect_all_feeds()
                # 如果是 30 分钟模式，这里不再固定 sleep 1800，
                # 而是下一轮再次对齐到 :00 / :30，避免漂移。
                if self.poll_interval != 1800:
                    logger.info(f"Sleeping for {self.poll_interval} seconds...")
                    time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("Worker stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {str(e)}")
                time.sleep(60)  # 错误后等待1分钟再重试

    def _sleep_until_daily_time(self, hhmm: str) -> None:
        """Sleep until the next occurrence of hh:mm (local time)."""
        try:
            hh, mm = hhmm.split(":")
            target_h = int(hh)
            target_m = int(mm)
        except Exception:
            target_h, target_m = 21, 0

        now = datetime.now()
        target = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)
        sleep_seconds = (target - now).total_seconds()
        if sleep_seconds > 0:
            logger.info(
                f"Daily mode enabled. Sleeping for {int(sleep_seconds)} seconds until {target.isoformat(sep=' ', timespec='seconds')}..."
            )
            time.sleep(sleep_seconds)

    def _sleep_until_next_half_hour(self, offset_minutes: int = 0) -> None:
        """
        Sleep until the next half-hour boundary, optionally with a minute offset.
        - offset_minutes=0  -> :00 / :30
        - offset_minutes=5  -> :05 / :35  (recommended for staggering with weRSS jobs)
        """
        # Clamp offset to [0, 29] to keep "two runs per hour" semantics.
        try:
            offset_minutes = int(offset_minutes)
        except Exception:
            offset_minutes = 0
        if offset_minutes < 0:
            offset_minutes = 0
        if offset_minutes > 29:
            offset_minutes = 29

        now = datetime.now()

        m1 = offset_minutes
        m2 = 30 + offset_minutes
        if m2 >= 60:
            # should not happen due to clamp, but keep safe
            m2 -= 60

        if (now.minute in (m1, m2)) and now.second == 0:
            return

        # Build the next run time among two candidates in the current hour; otherwise the first candidate next hour.
        cand1 = now.replace(minute=m1, second=0, microsecond=0)
        cand2 = now.replace(minute=m2, second=0, microsecond=0)

        if now < cand1:
            next_run = cand1
        elif now < cand2:
            next_run = cand2
        else:
            next_run = (cand1 + timedelta(hours=1))

        sleep_seconds = (next_run - now).total_seconds()
        if sleep_seconds > 0:
            logger.info(
                f"Aligning to half-hour boundary (offset={offset_minutes}m). Sleeping for {int(sleep_seconds)} seconds until {next_run.isoformat(sep=' ', timespec='seconds')}..."
            )
            time.sleep(sleep_seconds)
    
    def collect_all_feeds(self):
        """采集所有活跃公众号的RSS"""
        db = SessionLocal()
        
        try:
            accounts = db.query(OfficialAccount).filter(
                OfficialAccount.is_active == True
            ).all()
            
            logger.info(f"Starting collection for {len(accounts)} accounts")
            
            total_new = 0
            for account in accounts:
                try:
                    new_count = self.collect_feed(db, account)
                    total_new += new_count
                    logger.info(
                        f"Account {account.name}: {new_count} new articles"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to collect from {account.name}: {str(e)}"
                    )
            
            logger.info(f"Collection completed: {total_new} new articles in total")
            
        finally:
            db.close()
    
    def collect_feed(self, db: Session, account: OfficialAccount) -> int:
        """
        采集单个公众号的RSS
        
        Args:
            db: 数据库会话
            account: 公众号对象
        
        Returns:
            新文章数量
        """
        if not account.werss_feed_id:
            logger.warning(f"Account {account.name} has no werss_feed_id")
            return 0

        # Preferred: read from weRSS sqlite directly (eliminates /rss HTTP timeouts when rss-bridge is busy/hung).
        if self._use_werss_db and self._werss_db_path and os.path.exists(self._werss_db_path):
            try:
                return self._collect_feed_from_werss_sqlite(db, account)
            except Exception as e:
                logger.warning(
                    f"Failed to collect from weRSS sqlite for {account.name}, fallback to HTTP RSS: {e}"
                )
        
        # 构建RSS URL
        rss_url = f"{self.rss_bridge_url}/rss/{account.werss_feed_id}"
        
        try:
            # 获取RSS内容
            logger.debug(f"Fetching RSS from: {rss_url}")
            response = httpx.get(rss_url, timeout=30)
            response.raise_for_status()
            
            # 解析RSS
            feed = feedparser.parse(response.text)
            
            # 诊断信息
            logger.info(f"RSS feed for {account.name}: status={response.status_code}, entries={len(feed.entries) if feed.entries else 0}, feed_title={feed.feed.get('title', 'N/A')}")
            
            if not feed.entries:
                logger.warning(f"No entries in RSS for {account.name} (URL: {rss_url})")
                return 0
            
            new_count = 0
            skipped_count = 0
            
            for entry in feed.entries:
                try:
                    # 使用URL作为唯一标识
                    article_url = entry.link
                    
                    # 检查是否已存在
                    existing = db.query(Article).filter(
                        Article.article_url == article_url
                    ).first()
                    
                    # 提取“原文内容”（优先 RSS content:encoded，其次 description/summary）
                    # - we-mp-rss 的 RSS description 往往是摘要/短HTML
                    # - full content 通常在 entry.content[0].value (content:encoded)
                    raw_content = ""
                    if getattr(entry, "content", None):
                        try:
                            raw_content = (entry.content[0].value or "")
                        except Exception:
                            raw_content = ""
                    if not raw_content:
                        raw_content = entry.get("description", "") or entry.get("summary", "") or ""

                    content = self._to_visible_text(raw_content)

                    # 如果 RSS 里只有摘要/占位，自动回源抓取微信原文全文并保存（用户期望：每篇文章都保存原文纯文本）
                    if self._fetch_full_content and article_url and self._looks_like_placeholder_text(content):
                        fulltext = self._fetch_fulltext_from_werss(article_url)
                        if fulltext and len(fulltext) > len(content) + 200:
                            content = fulltext
                    
                    # 解析发布时间
                    published_at = self._parse_date(entry.get("published"))

                    # Global ingestion cutoff: skip storing older articles
                    if self._min_article_date is not None:
                        try:
                            if published_at.date() < self._min_article_date:
                                skipped_count += 1
                                continue
                        except Exception:
                            pass
                    
                    if existing:
                        # 已存在则尝试“回填更完整的原文内容”（避免历史数据一直是摘要）
                        old = (existing.content or "").strip()
                        def _looks_like_html(s: str) -> bool:
                            return bool(s) and ("<" in s and ">" in s)

                        should_backfill = False
                        if content:
                            # Prefer replacing HTML-ish/placeholder content
                            if _looks_like_html(old) and not _looks_like_html(content):
                                should_backfill = True
                            # If old is short/placeholder but new is meaningfully longer
                            if len(content) > len(old) + 200:
                                should_backfill = True
                            # If old ends with truncation marks, accept moderate improvements
                            if old.endswith(("...", "…")) and len(content) > len(old) + 80:
                                should_backfill = True

                        if should_backfill:
                            existing.content = content
                            # 不强行改状态，避免影响其它流程；如需重新生成报告可手动再生成
                            logger.info(
                                f"Backfilled content for existing article: account={account.name}, url={article_url}, old_len={len(old)}, new_len={len(content)}"
                            )
                            db.add(existing)
                        skipped_count += 1
                        continue

                    # 创建新文章（保存“可视纯文本”）
                    article = Article(
                        account_id=account.id,
                        title=entry.title,
                        content=content,
                        article_url=article_url,
                        published_at=published_at,
                        msg_id=article_url,
                        status=ArticleStatus.PENDING,  # 待AI处理
                        collected_at=datetime.utcnow()
                    )

                    db.add(article)
                    new_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to parse RSS entry: {str(e)}")
                    continue
            
            # 提交所有新文章
            db.commit()
            
            # 更新公众号统计
            if new_count > 0:
                account.total_articles += new_count
                account.last_collection_time = datetime.utcnow()
                db.commit()
            
            # 详细日志
            if new_count > 0:
                logger.info(f"Account {account.name}: {new_count} new articles, {skipped_count} skipped (already exist)")
            elif skipped_count > 0:
                logger.info(f"Account {account.name}: {skipped_count} articles already exist, 0 new")
            else:
                logger.warning(f"Account {account.name}: No articles found in RSS feed")
            
            return new_count
            
        except Exception as e:
            logger.error(f"Failed to fetch RSS for {account.name}: {str(e)}")
            raise

    def _collect_feed_from_werss_sqlite(self, db: Session, account: OfficialAccount) -> int:
        """
        Collect articles by reading weRSS sqlite DB directly.
        This avoids relying on rss-bridge HTTP endpoints, which may hang while Playwright/jobs are running.
        """
        feed_id = account.werss_feed_id

        # Use last_collection_time as a soft cutoff (dedupe by url anyway).
        cutoff_dt = account.last_collection_time or (datetime.utcnow() - timedelta(days=10))
        # Add buffer to avoid missing late-updated items.
        since_ts = int((cutoff_dt - timedelta(days=2)).timestamp())
        # Apply global cutoff as well (don't even read older rows)
        if self._min_article_date is not None:
            try:
                min_dt = datetime.combine(self._min_article_date, datetime.min.time())
                since_ts = max(since_ts, int((min_dt - timedelta(days=2)).timestamp()))
            except Exception:
                pass
        limit = max(50, self._werss_db_limit)

        rows = self._fetch_werss_articles(feed_id=feed_id, since_ts=since_ts, limit=limit)
        if not rows:
            logger.warning(f"No entries in weRSS sqlite for {account.name} (feed_id={feed_id})")
            return 0

        new_count = 0
        skipped_count = 0

        for r in rows:
            try:
                article_url = (r.get("url") or "").strip()
                if not article_url:
                    continue

                existing = db.query(Article).filter(Article.article_url == article_url).first()

                raw_content = (r.get("content") or r.get("description") or "").strip()
                content = self._to_visible_text(raw_content)

                # Ensure we store full original text: if sqlite content is still placeholder/short, fetch full text via weRSS API.
                if self._fetch_full_content and article_url and self._looks_like_placeholder_text(content):
                    fulltext = self._fetch_fulltext_from_werss(article_url)
                    if fulltext and len(fulltext) > len(content) + 200:
                        content = fulltext

                published_at = datetime.utcfromtimestamp(int(r.get("publish_time") or 0)) if r.get("publish_time") else datetime.utcnow()

                # Global ingestion cutoff: skip storing older articles
                if self._min_article_date is not None:
                    try:
                        if published_at.date() < self._min_article_date:
                            skipped_count += 1
                            continue
                    except Exception:
                        pass

                if existing:
                    old = (existing.content or "").strip()
                    def _looks_like_html(s: str) -> bool:
                        return bool(s) and ("<" in s and ">" in s)

                    should_backfill = False
                    if content:
                        if _looks_like_html(old) and not _looks_like_html(content):
                            should_backfill = True
                        if len(content) > len(old) + 200:
                            should_backfill = True
                        if old.endswith(("...", "…")) and len(content) > len(old) + 80:
                            should_backfill = True
                        if self._looks_like_placeholder_text(old) and not self._looks_like_placeholder_text(content) and len(content) > len(old) + 80:
                            should_backfill = True

                    if should_backfill:
                        existing.title = existing.title or (r.get("title") or "")
                        existing.content = content
                        db.add(existing)
                        logger.info(
                            f"Backfilled content for existing article from weRSS sqlite: account={account.name}, url={article_url}, old_len={len(old)}, new_len={len(content)}"
                        )
                    skipped_count += 1
                    continue

                article = Article(
                    account_id=account.id,
                    title=(r.get("title") or "").strip() or "(untitled)",
                    content=content,
                    article_url=article_url,
                    published_at=published_at,
                    msg_id=article_url,
                    status=ArticleStatus.PENDING,
                    collected_at=datetime.utcnow(),
                )
                db.add(article)
                new_count += 1
            except Exception as e:
                logger.warning(f"Failed to parse weRSS sqlite article row: {e}")
                continue

        db.commit()

        if new_count > 0:
            account.total_articles += new_count
            account.last_collection_time = datetime.utcnow()
            db.commit()

        if new_count > 0:
            logger.info(f"Account {account.name} (sqlite): {new_count} new, {skipped_count} skipped")
        elif skipped_count > 0:
            logger.info(f"Account {account.name} (sqlite): {skipped_count} exist, 0 new")
        else:
            logger.warning(f"Account {account.name} (sqlite): No articles found")

        return new_count

    def _fetch_werss_articles(self, feed_id: str, since_ts: int, limit: int) -> list[dict]:
        """
        Read articles from weRSS sqlite.
        Schema (we-mp-rss): articles(mp_id,title,url,description,content,publish_time,...)
        """
        db_path = self._werss_db_path
        if not db_path:
            return []

        # Read-only connection with busy timeout to handle concurrent writer.
        uri = f"file:{db_path}?mode=ro"
        con = sqlite3.connect(uri, uri=True, timeout=5)
        try:
            con.execute("PRAGMA busy_timeout=5000")
            cur = con.cursor()
            cur.execute(
                """
                SELECT title, url, description, content, publish_time
                FROM articles
                WHERE mp_id = ? AND publish_time >= ?
                ORDER BY publish_time DESC
                LIMIT ?
                """,
                (feed_id, int(since_ts), int(limit)),
            )
            out = []
            for title, url, description, content, publish_time in cur.fetchall():
                out.append(
                    {
                        "title": title,
                        "url": url,
                        "description": description,
                        "content": content,
                        "publish_time": publish_time,
                    }
                )
            return out
        finally:
            try:
                con.close()
            except Exception:
                pass
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
        
        Returns:
            datetime对象
        """
        if not date_str:
            return datetime.utcnow()
        
        from dateutil import parser
        try:
            return parser.parse(date_str)
        except:
            return datetime.utcnow()

    def _to_visible_text(self, raw: str) -> str:
        """
        Convert RSS HTML-ish content into user-visible plain text.
        WeChat/we-mp-rss feeds often embed HTML; AI needs readable text, not tags.
        """
        if not raw:
            return ""
        s = raw
        # unescape HTML entities first
        try:
            s = _html.unescape(s)
        except Exception:
            pass

        # Heuristic: if it looks like HTML, strip tags to visible text
        if "<" in s and ">" in s:
            try:
                from lxml import html as lxml_html
                doc = lxml_html.fromstring(s)
                # drop non-content nodes
                for bad in doc.xpath("//script|//style|//noscript"):
                    bad.drop_tree()
                s = doc.text_content()
            except Exception:
                # fallback: very rough tag removal
                s = re.sub(r"<[^>]+>", " ", s)

        # normalize whitespace
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        s = re.sub(r"[ \t]+", " ", s)
        # remove wechat "图片" placeholders when they are standalone lines
        lines = []
        for line in s.split("\n"):
            t = line.strip()
            if not t:
                continue
            if t in ("图片", "image", "Image"):
                continue
            lines.append(t)
        s = "\n".join(lines)
        s = re.sub(r"\n{3,}", "\n\n", s).strip()
        return s

    def _looks_like_werss_blocked_text(self, s: str) -> bool:
        """
        Detect WeChat anti-bot / environment verification pages returned as "content".
        We must NOT store these as article正文.
        """
        if not isinstance(s, str):
            return True
        t = s.strip()
        if not t:
            return True
        blocked_markers = [
            "当前环境异常",
            "完成验证后即可继续访问",
            "环境异常",
            "访问过于频繁",
            "请完成验证",
        ]
        return any(m in t for m in blocked_markers)

    def _looks_like_placeholder_text(self, s: str) -> bool:
        """Detect common placeholder/summary-only cases."""
        if not isinstance(s, str):
            return True
        t = s.strip()
        if not t:
            return True
        if "欢迎关注" in t and len(t) < 120:
            return True
        if t in ("图片", "image", "Image"):
            return True
        # too short -> likely only title/summary
        return len(t) < 300

    def _get_werss_token(self) -> str | None:
        """Login to weRSS and cache token for fulltext fetch."""
        import time
        now = time.time()
        if self._werss_token and self._werss_token_exp_ts > now + 30:
            return self._werss_token
        try:
            # weRSS auth endpoint (same base as rss-bridge)
            url = f"{self.rss_bridge_url.rstrip('/')}/api/v1/wx/auth/login"
            resp = httpx.post(
                url,
                data={"username": self._werss_username, "password": self._werss_password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self._fulltext_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            token = (data.get("data") or {}).get("access_token")
            if token:
                self._werss_token = token
                self._werss_token_exp_ts = now + 30 * 60
            return token
        except Exception as e:
            logger.warning(f"Failed to login weRSS for fulltext fetch: {e}")
            return None

    def _clear_werss_token(self) -> None:
        self._werss_token = None
        self._werss_token_exp_ts = 0.0

    def _fetch_fulltext_from_werss(self, article_url: str) -> str | None:
        """
        Fetch original article full content from weRSS (Playwright+logged-in session).
        Returns visible plain text.
        """
        url = f"{self.rss_bridge_url.rstrip('/')}/api/v1/wx/mps/by_article"
        token = self._get_werss_token()
        if not token:
            return None

        import random
        import time as _time

        # Throttle between requests (best-effort)
        now = _time.time()
        gap = now - (self._last_fulltext_ts or 0.0)
        if gap < self._fulltext_min_interval:
            _time.sleep(max(0.0, self._fulltext_min_interval - gap))

        for attempt in range(1, max(1, self._fulltext_max_retries) + 1):
            try:
                resp = httpx.post(
                    url,
                    params={"url": article_url},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=self._fulltext_timeout,
                )

                # auth token might expire / be invalid
                if resp.status_code in (401, 403):
                    logger.warning(f"weRSS token rejected ({resp.status_code}); re-login and retry. url={article_url}")
                    self._clear_werss_token()
                    token = self._get_werss_token()
                    if not token:
                        return None
                    continue

                resp.raise_for_status()

                # Response is expected to be JSON with data.content (html)
                try:
                    payload = resp.json()
                except Exception:
                    raise RuntimeError(f"weRSS non-JSON response: status={resp.status_code}, body={resp.text[:300]}")

                info = payload.get("data") or {}
                raw = info.get("content") or ""
                txt = self._to_visible_text(raw)

                # Detect anti-bot pages / environment abnormal
                if self._looks_like_werss_blocked_text(txt):
                    raise RuntimeError(
                        "weRSS returned WeChat verification page (环境异常/需验证). "
                        "Please re-login in weRSS Web UI and slow down crawling."
                    )

                self._last_fulltext_ts = _time.time()
                return txt or None

            except Exception as e:
                # Exponential backoff with jitter
                sleep_s = min(30.0, self._fulltext_retry_base_sleep * (2 ** (attempt - 1)))
                sleep_s = sleep_s + random.uniform(0.0, 0.8)
                logger.warning(
                    f"Fulltext fetch failed (attempt {attempt}/{self._fulltext_max_retries}) "
                    f"for {article_url}: {e} (sleep {sleep_s:.1f}s)"
                )
                if attempt >= self._fulltext_max_retries:
                    return None
                _time.sleep(sleep_s)
                # keep token; if the error was auth it would have been cleared above
                continue

        return None


def main():
    """主函数"""
    worker = IngestionWorker()
    worker.run()


if __name__ == "__main__":
    main()

