"""
文章管理路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from shared.database import get_db, Article, User
from ..security import get_current_active_user

router = APIRouter()


class ArticleResponse(BaseModel):
    """文章响应模型"""
    id: int
    title: str
    summary: Optional[str]
    category: Optional[str]
    keywords: Optional[List[str]]
    importance_score: Optional[int]
    published_at: datetime
    article_url: Optional[str]
    account_id: int
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[ArticleResponse])
async def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    account_id: Optional[int] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取文章列表
    """
    query = db.query(Article)
    
    if account_id:
        query = query.filter(Article.account_id == account_id)
    
    if category:
        query = query.filter(Article.category == category)
    
    if keyword:
        query = query.filter(Article.keywords.contains([keyword]))
    
    articles = query.order_by(
        Article.published_at.desc()
    ).offset(skip).limit(limit).all()
    
    return articles


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取文章详情
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return article

