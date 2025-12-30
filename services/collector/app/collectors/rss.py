"""
RSS采集器
"""
from datetime import datetime
from typing import Dict
import httpx
from bs4 import BeautifulSoup

from shared.utils import get_logger
from .base import BaseCollector
from shared.database import OfficialAccount

logger = get_logger("collector.rss")


class RSSCollector(BaseCollector):
    """
    RSS/Feed采集器
    
    通过RSS/Atom feed采集文章
    """
    
    def collect(self, account: OfficialAccount) -> Dict:
        """
        从RSS源采集文章
        
        Args:
            account: 公众号对象
        
        Returns:
            采集结果
        """
        try:
            logger.info(f"Collecting from RSS: {account.name}")
            
            if not account.collection_url:
                raise ValueError(f"No collection URL for account {account.id}")
            
            # 获取RSS内容
            response = httpx.get(
                account.collection_url,
                timeout=30,
                headers={"User-Agent": "Z-Pulse RSS Collector"}
            )
            response.raise_for_status()
            
            # 解析RSS
            articles = self.parse_rss(response.text)
            
            # 保存文章
            new_count = self.save_articles(articles, account.id)
            
            return {
                "total": len(articles),
                "new": new_count,
                "method": "rss"
            }
            
        except Exception as e:
            logger.error(f"Failed to collect from RSS {account.name}: {str(e)}")
            raise
    
    def parse_rss(self, content: str) -> list:
        """
        解析RSS内容
        
        Args:
            content: RSS XML内容
        
        Returns:
            文章列表
        """
        soup = BeautifulSoup(content, 'xml')
        articles = []
        
        # 尝试解析RSS 2.0格式
        items = soup.find_all('item')
        if not items:
            # 尝试解析Atom格式
            items = soup.find_all('entry')
        
        for item in items:
            try:
                title = item.find('title').text if item.find('title') else ""
                link = item.find('link').text if item.find('link') else ""
                description = item.find('description')
                if not description:
                    description = item.find('content')
                content = description.text if description else ""
                
                pub_date = item.find('pubDate')
                if not pub_date:
                    pub_date = item.find('published')
                published_at = self.parse_date(pub_date.text) if pub_date else datetime.utcnow()
                
                articles.append({
                    "title": title,
                    "content": content,
                    "article_url": link,
                    "published_at": published_at,
                    "msg_id": link,  # 使用链接作为唯一标识
                })
                
            except Exception as e:
                logger.warning(f"Failed to parse RSS item: {str(e)}")
                continue
        
        return articles
    
    def parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
        
        Returns:
            datetime对象
        """
        from dateutil import parser
        try:
            return parser.parse(date_str)
        except:
            return datetime.utcnow()

