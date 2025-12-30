"""
采集器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List
from sqlalchemy.orm import Session

from shared.database import OfficialAccount, Article


class BaseCollector(ABC):
    """采集器基类"""
    
    def __init__(self, db: Session):
        """
        初始化采集器
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    @abstractmethod
    def collect(self, account: OfficialAccount) -> Dict:
        """
        采集文章
        
        Args:
            account: 公众号对象
        
        Returns:
            采集结果 {"total": int, "new": int, "articles": List[Article]}
        """
        pass
    
    def save_articles(self, articles: List[Dict], account_id: int) -> int:
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
                **article_data
            )
            self.db.add(article)
            new_count += 1
        
        self.db.commit()
        return new_count

