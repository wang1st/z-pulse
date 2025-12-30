"""
Web爬虫采集器
"""
from datetime import datetime
from typing import Dict
import httpx
from bs4 import BeautifulSoup

from shared.config import settings
from shared.utils import get_logger
from .base import BaseCollector
from shared.database import OfficialAccount

logger = get_logger("collector.web")


class WebCollector(BaseCollector):
    """
    Web爬虫采集器
    
    通过网页爬取采集文章（备用方案）
    """
    
    def collect(self, account: OfficialAccount) -> Dict:
        """
        从网页爬取文章
        
        Args:
            account: 公众号对象
        
        Returns:
            采集结果
        """
        try:
            logger.info(f"Collecting from web: {account.name}")
            
            if not account.collection_url:
                raise ValueError(f"No collection URL for account {account.id}")
            
            # 获取网页内容
            response = httpx.get(
                account.collection_url,
                timeout=30,
                headers={"User-Agent": settings.COLLECTOR_USER_AGENT}
            )
            response.raise_for_status()
            
            # 解析网页
            articles = self.parse_html(response.text, account.collection_url)
            
            # 保存文章
            new_count = self.save_articles(articles, account.id)
            
            return {
                "total": len(articles),
                "new": new_count,
                "method": "web"
            }
            
        except Exception as e:
            logger.error(f"Failed to collect from web {account.name}: {str(e)}")
            raise
    
    def parse_html(self, html: str, base_url: str) -> list:
        """
        解析HTML内容
        
        Args:
            html: HTML内容
            base_url: 基础URL
        
        Returns:
            文章列表
        """
        soup = BeautifulSoup(html, 'lxml')
        articles = []
        
        # TODO: 根据具体的网页结构实现解析逻辑
        # 这里需要针对不同的网站定制解析规则
        
        # 示例：查找所有文章链接
        article_links = soup.find_all('a', class_='article-link')
        
        for link in article_links:
            try:
                article_url = link.get('href')
                if not article_url.startswith('http'):
                    article_url = base_url + article_url
                
                title = link.get_text(strip=True)
                
                # 获取文章详情
                article_detail = self.fetch_article_detail(article_url)
                
                if article_detail:
                    articles.append(article_detail)
                    
            except Exception as e:
                logger.warning(f"Failed to parse article link: {str(e)}")
                continue
        
        return articles
    
    def fetch_article_detail(self, url: str) -> dict:
        """
        获取文章详情
        
        Args:
            url: 文章URL
        
        Returns:
            文章数据字典
        """
        try:
            response = httpx.get(
                url,
                timeout=30,
                headers={"User-Agent": settings.COLLECTOR_USER_AGENT}
            )
            soup = BeautifulSoup(response.text, 'lxml')
            
            # TODO: 根据具体的网页结构提取文章内容
            title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
            content = soup.find('div', class_='content').get_text() if soup.find('div', class_='content') else ""
            
            return {
                "title": title,
                "content": content,
                "article_url": url,
                "published_at": datetime.utcnow(),
                "msg_id": url,
            }
            
        except Exception as e:
            logger.warning(f"Failed to fetch article detail from {url}: {str(e)}")
            return None

