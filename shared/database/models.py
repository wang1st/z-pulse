"""
数据库模型定义 - 按照设计文档更新
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, 
    String, Text, JSON, Index, Date, ARRAY
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ArticleStatus(str, PyEnum):
    """文章处理状态"""
    PENDING = "pending"  # 待处理
    PROCESSED = "processed"  # 已处理
    FAILED = "failed"  # 处理失败


class ReportType(str, PyEnum):
    """报告类型"""
    DAILY = "daily"  # 日报
    WEEKLY = "weekly"  # 周报


class ReportJobType(str, PyEnum):
    """报告任务类型"""
    REGENERATE_DAILY = "regenerate_daily"


class ReportJobStatus(str, PyEnum):
    """报告任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ArticleCollectionJobStatus(str, PyEnum):
    """文章采集任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class OfficialAccount(Base):
    """
    表1: official_accounts (目标清单)
    存储监控的公众号"目标清单"
    """
    __tablename__ = "official_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="公众号名称")
    wechat_id = Column(String(100), unique=True, comment="微信ID")
    
    # we-mp-rss配置
    werss_feed_id = Column(String(100), unique=True, nullable=True, comment="we-mp-rss订阅ID")
    werss_sync_method = Column(String(20), default="rss", comment="同步方式: rss/api（固定为rss）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 统计信息
    total_articles = Column(Integer, default=0, comment="总文章数")
    last_collection_time = Column(DateTime, comment="最后采集时间")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 关系
    articles = relationship("Article", back_populates="account", cascade="all, delete-orphan")


class Article(Base):
    """
    表2: scraped_articles (原始数据)
    存储从rss-bridge采集的原始文章
    """
    __tablename__ = "scraped_articles"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(
        Integer,
        ForeignKey("official_accounts.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 基本信息
    title = Column(Text, nullable=False, comment="文章标题")
    article_url = Column(String(1024), unique=True, nullable=False, comment="文章URL（唯一性约束）")
    content = Column(Text, comment="文章内容（纯文本）")
    
    # 时间信息
    published_at = Column(DateTime, nullable=False, comment="发布时间")
    collected_at = Column(DateTime, default=datetime.utcnow, comment="采集时间")
    
    # AI处理状态（关键队列机制）
    status = Column(
        Enum(ArticleStatus),
        default=ArticleStatus.PENDING,
        nullable=False,
        comment="处理状态"
    )
    processed_at = Column(DateTime, comment="处理时间")
    
    # AI分析结果
    summary = Column(Text, comment="AI生成的摘要")
    keywords = Column(JSON, comment="关键词列表")
    category = Column(String(100), comment="分类")
    importance_score = Column(Integer, comment="重要性分数 0-100")
    
    # 其他
    author = Column(String(200), comment="作者")
    cover_image = Column(String(1000), comment="封面图")
    msg_id = Column(String(200), comment="消息ID")
    
    # 时间戳
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    account = relationship("OfficialAccount", back_populates="articles")

    __table_args__ = (
        Index('idx_articles_publish_timestamp', 'published_at'),
        Index('idx_articles_processed_by_ai', 'status'),
        Index('idx_articles_account_published', 'account_id', 'published_at'),
    )


class Report(Base):
    """
    表3: ai_generated_reports (AI产品)
    存储AI生成的日报和周报
    """
    __tablename__ = "ai_generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    
    # 报告信息
    report_type = Column(
        Enum(ReportType),
        nullable=False,
        comment="报告类型: daily/weekly"
    )
    report_date = Column(Date, nullable=False, comment="报告日期")
    title = Column(String(500), nullable=False, comment="报告标题")
    
    # 内容（Markdown格式）
    summary_markdown = Column(Text, nullable=False, comment="日报核心内容")
    analysis_markdown = Column(Text, comment="周报趋势分析")

    # 结构化内容（用于前端/邮件一致渲染；AI 输出 JSON，系统渲染为 HTML 存到 summary_markdown）
    content_json = Column(JSON, nullable=True, comment="结构化报告内容(JSON)，用于渲染展示/邮件")
    
    # 元数据
    source_article_ids = Column(JSON, comment="引用的源文章ID数组")
    article_count = Column(Integer, default=0, comment="包含文章数")
    
    # 统计
    view_count = Column(Integer, default=0, comment="查看次数")
    sent_count = Column(Integer, default=0, comment="发送次数")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_reports_report_date', 'report_date', postgresql_ops={'report_date': 'DESC'}),
        Index('idx_reports_type_date', 'report_type', 'report_date'),
        # 确保每天/每周只有一份报告
        Index('idx_reports_unique', 'report_type', 'report_date', unique=True),
    )


class ReportJob(Base):
    """
    报告生成/再生成任务队列（异步）
    - 解决“点击再生成导致 API 卡死”的问题：API 只入队，ai-worker 异步执行
    """
    __tablename__ = "report_jobs"

    id = Column(Integer, primary_key=True, index=True)

    job_type = Column(Enum(ReportJobType), nullable=False, comment="任务类型")
    status = Column(Enum(ReportJobStatus), nullable=False, default=ReportJobStatus.PENDING, comment="任务状态")

    target_date = Column(Date, nullable=False, comment="目标日期（日报）")
    report_id = Column(Integer, nullable=True, comment="生成/更新后的报告ID")

    requested_by = Column(String(100), nullable=True, comment="触发者用户名")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    error_message = Column(Text, nullable=True, comment="失败原因")

    __table_args__ = (
        Index("idx_report_jobs_status_created", "status", "created_at"),
        Index("idx_report_jobs_type_date", "job_type", "target_date"),
    )


class ArticleCollectionJob(Base):
    """
    文章采集任务（用于后台展示采集状态/进度）
    - API 触发后立即返回 job_id
    - 后台线程逐步更新进度
    """

    __tablename__ = "article_collection_jobs"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(
        Enum(ArticleCollectionJobStatus),
        nullable=False,
        default=ArticleCollectionJobStatus.PENDING,
        comment="任务状态",
    )
    requested_by = Column(String(100), nullable=True, comment="触发者用户名")
    mode = Column(String(50), nullable=True, comment="采集模式（sqlite/rss）")

    total_accounts = Column(Integer, default=0, comment="总账号数")
    processed_accounts = Column(Integer, default=0, comment="已处理账号数")
    new_articles = Column(Integer, default=0, comment="新增文章数")
    skipped_articles = Column(Integer, default=0, comment="跳过文章数（已存在）")
    error_count = Column(Integer, default=0, comment="错误账号数")

    # 仅保存摘要信息，避免无限增长
    last_error = Column(Text, nullable=True, comment="最近一次错误")
    details = Column(JSON, nullable=True, comment="任务详情（如每个账号新增数/耗时/错误摘要）")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_article_collect_jobs_status_created", "status", "created_at"),
        Index("idx_article_collect_jobs_created", "created_at"),
    )


class Subscriber(Base):
    """
    表4: subscribers (订阅用户)
    管理邮件列表和Double Opt-In订阅流程
    """
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, index=True)
    
    # 基本信息
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # Double Opt-In关键字段
    is_active = Column(Boolean, default=False, nullable=False, comment="是否已激活")
    verification_token = Column(String(128), unique=True, comment="验证令牌")
    token_expiry = Column(DateTime, comment="令牌过期时间")
    
    # 订阅偏好
    subscribe_daily = Column(Boolean, default=True, comment="订阅日报")
    subscribe_weekly = Column(Boolean, default=True, comment="订阅周报")
    regions = Column(JSON, comment="关注地区列表")
    
    # 统计
    total_sent = Column(Integer, default=0, comment="总发送次数")
    last_sent_at = Column(DateTime, comment="最后发送时间")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    activated_at = Column(DateTime, comment="激活时间")
    unsubscribed_at = Column(DateTime, comment="取消订阅时间")
    
    __table_args__ = (
        Index('idx_subscribers_email', 'email'),
        Index('idx_subscribers_token', 'verification_token'),
        Index('idx_subscribers_active', 'is_active'),
    )


class ArticleOneLiner(Base):
    """
    Persistent cache for per-article LLM one-liner topic condensation + tag scores.
    Used by "近日热点" pipeline to avoid recomputing previous days' intermediate results.
    """

    __tablename__ = "article_one_liners"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("scraped_articles.id", ondelete="CASCADE"), nullable=False, index=True)

    # One-liner summary (<= 20 chars recommended) + tag scores
    one_liner = Column(String(64), nullable=False, comment="20字以内一句话：发生了什么")
    tags = Column(JSON, nullable=False, comment="tag scores: {finance:0-3,minsheng:0-3,tech:0-3}")
    keep = Column(Boolean, default=False, nullable=False, comment="是否进入热点/后续处理")

    # cache metadata
    model = Column(String(100), nullable=True, comment="LLM model name")
    prompt_version = Column(String(40), nullable=False, default="v1", comment="prompt version for cache invalidation")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    article = relationship("Article")

    __table_args__ = (
        Index("idx_article_one_liners_article_version", "article_id", "prompt_version"),
        Index("idx_article_one_liners_keep", "keep"),
    )


class User(Base):
    """
    管理员用户表（用于后台管理）
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # 基本信息
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200))
    
    # 权限
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)
