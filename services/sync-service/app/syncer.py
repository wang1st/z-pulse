"""
数据同步器 - 从we-mp-rss同步数据
"""
from datetime import datetime
from typing import Dict, List
import httpx
import feedparser
from sqlalchemy.orm import Session

from shared.config import settings
from shared.database import OfficialAccount, Article, ArticleStatus
from shared.utils import get_logger

logger = get_logger("sync-service.syncer")


class WeRSSSync:
    """we-mp-rss数据同步器"""
    
    def __init__(self, db: Session):
        """
        初始化同步器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.werss_base_url = settings.WERSS_API_URL
        self.werss_token = settings.WERSS_API_TOKEN
    
    async def sync_account(self, account_id: int) -> Dict:
        """
        同步指定公众号的文章
        
        Args:
            account_id: 公众号ID
        
        Returns:
            同步结果
        """
        account = self.db.query(OfficialAccount).filter(
            OfficialAccount.id == account_id
        ).first()
        
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        if not account.is_active:
            raise ValueError(f"Account {account_id} is not active")
        
        logger.info(f"Syncing account {account_id}: {account.name}")
        
        # 根据账号配置选择同步方式
        if account.werss_feed_id:
            # 使用we-mp-rss的RSS订阅
            articles = await self._sync_from_rss(account)
        else:
            # 使用we-mp-rss的API
            articles = await self._sync_from_api(account)
        
        # 保存文章
        new_count = self._save_articles(articles, account_id)
        
        # 更新账号统计
        account.total_articles += new_count
        account.last_collection_time = datetime.utcnow()
        self.db.commit()
        
        logger.info(
            f"Sync completed for account {account_id}: "
            f"{len(articles)} total, {new_count} new"
        )
        
        return {
            "account_id": account_id,
            "account_name": account.name,
            "total": len(articles),
            "new": new_count,
            "method": "rss" if account.werss_feed_id else "api"
        }
    
    async def sync_all_accounts(self) -> Dict:
        """
        同步所有活跃公众号
        
        Returns:
            同步结果汇总
        """
        accounts = self.db.query(OfficialAccount).filter(
            OfficialAccount.is_active == True
        ).all()
        
        logger.info(f"Starting sync for {len(accounts)} accounts")
        
        total_synced = 0
        total_new = 0
        failed_accounts = []
        
        for account in accounts:
            try:
                result = await self.sync_account(account.id)
                total_synced += result["total"]
                total_new += result["new"]
            except Exception as e:
                logger.error(f"Failed to sync account {account.id}: {str(e)}")
                failed_accounts.append({
                    "account_id": account.id,
                    "account_name": account.name,
                    "error": str(e)
                })
        
        return {
            "total_accounts": len(accounts),
            "total_synced": total_synced,
            "total_new": total_new,
            "failed_accounts": failed_accounts
        }
    
    async def _sync_from_rss(self, account: OfficialAccount) -> List[Dict]:
        """
        从RSS订阅同步文章
        
        Args:
            account: 公众号对象
        
        Returns:
            文章列表
        """
        rss_url = f"{self.werss_base_url}/rss/{account.werss_feed_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(rss_url)
                response.raise_for_status()
            
            # 解析RSS
            feed = feedparser.parse(response.text)
            articles = []
            
            for entry in feed.entries:
                article = {
                    "title": entry.title,
                    "content": entry.get("description", "") or entry.get("content", [{}])[0].get("value", ""),
                    "article_url": entry.link,
                    "published_at": self._parse_date(entry.get("published")),
                    "msg_id": entry.get("id") or entry.link,
                    "author": entry.get("author", ""),
                    "cover_image": self._extract_cover_image(entry)
                }
                articles.append(article)
            
            logger.info(f"Fetched {len(articles)} articles from RSS for {account.name}")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch RSS for {account.name}: {str(e)}")
            raise
    
    async def _sync_from_api(self, account: OfficialAccount) -> List[Dict]:
        """
        从API同步文章
        
        Args:
            account: 公众号对象
        
        Returns:
            文章列表
        """
        api_url = f"{self.werss_base_url}/api/feeds/{account.werss_feed_id}/articles"
        
        headers = {}
        if self.werss_token:
            headers["Authorization"] = f"Bearer {self.werss_token}"
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    api_url,
                    headers=headers,
                    params={"limit": 50}
                )
                response.raise_for_status()
                data = response.json()
            
            articles = []
            for item in data.get("articles", []):
                article = {
                    "title": item["title"],
                    "content": item["content"],
                    "article_url": item["url"],
                    "published_at": self._parse_date(item.get("publish_time")),
                    "msg_id": str(item["id"]),
                    "author": item.get("author", ""),
                    "cover_image": item.get("cover", ""),
                    "read_count": item.get("read_num", 0),
                    "like_count": item.get("like_num", 0)
                }
                articles.append(article)
            
            logger.info(f"Fetched {len(articles)} articles from API for {account.name}")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch from API for {account.name}: {str(e)}")
            raise
    
    def _save_articles(self, articles: List[Dict], account_id: int) -> int:
        """
        保存文章到数据库
        
        Args:
            articles: 文章列表
            account_id: 公众号ID
        
        Returns:
            新增文章数量
        """
        new_count = 0
        
        for article_data in articles:
            # 检查文章是否已存在
            msg_id = article_data.get("msg_id")
            if msg_id:
                existing = self.db.query(Article).filter(
                    Article.msg_id == msg_id
                ).first()
                if existing:
                    continue
            
            # 创建新文章
            article = Article(
                account_id=account_id,
                title=article_data["title"],
                content=article_data["content"],
                article_url=article_data["article_url"],
                published_at=article_data["published_at"],
                msg_id=msg_id,
                author=article_data.get("author"),
                cover_image=article_data.get("cover_image"),
                read_count=article_data.get("read_count", 0),
                like_count=article_data.get("like_count", 0),
                status=ArticleStatus.PENDING,  # 待AI处理
                collected_at=datetime.utcnow()
            )
            
            self.db.add(article)
            new_count += 1
        
        self.db.commit()
        return new_count
    
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
    
    def _extract_cover_image(self, entry) -> str:
        """
        从RSS条目中提取封面图片
        
        Args:
            entry: RSS条目
        
        Returns:
            封面图片URL
        """
        # 尝试从media:content获取
        if hasattr(entry, "media_content"):
            return entry.media_content[0].get("url", "")
        
        # 尝试从enclosure获取
        if hasattr(entry, "enclosures") and entry.enclosures:
            return entry.enclosures[0].get("href", "")
        
        return ""

