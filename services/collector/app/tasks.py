"""
Celery任务定义
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from celery import Celery
from sqlalchemy.orm import Session

from shared.config import settings
from shared.database import SessionLocal, OfficialAccount, CollectionTask
from shared.utils import get_logger
from .collectors import WechatCollector, RSSCollector, WebCollector

logger = get_logger("collector.tasks")

# 创建Celery应用
celery_app = Celery(
    "collector",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟
    task_soft_time_limit=25 * 60,  # 25分钟
)


@celery_app.task(bind=True, name="collector.start_collection")
def start_collection_task(self, account_id: int):
    """
    启动采集任务
    
    Args:
        account_id: 公众号ID
    
    Returns:
        采集结果统计
    """
    db = SessionLocal()
    task_record = None
    
    try:
        # 获取公众号信息
        account = db.query(OfficialAccount).filter(
            OfficialAccount.id == account_id
        ).first()
        
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        if not account.is_active:
            raise ValueError(f"Account {account_id} is not active")
        
        # 创建任务记录
        task_record = CollectionTask(
            account_id=account_id,
            task_id=self.request.id,
            status="STARTED",
            started_at=datetime.utcnow()
        )
        db.add(task_record)
        db.commit()
        
        logger.info(f"Starting collection for account {account_id}: {account.name}")
        
        # 根据采集方法选择采集器
        if account.collection_method == "api":
            collector = WechatCollector(db)
        elif account.collection_method == "rss":
            collector = RSSCollector(db)
        else:
            collector = WebCollector(db)
        
        # 执行采集
        result = collector.collect(account)
        
        # 更新任务记录
        task_record.status = "SUCCESS"
        task_record.articles_collected = result.get("total", 0)
        task_record.articles_new = result.get("new", 0)
        task_record.completed_at = datetime.utcnow()
        task_record.duration = (
            task_record.completed_at - task_record.started_at
        ).seconds
        
        # 更新公众号统计
        account.total_articles += result.get("new", 0)
        account.last_collection_time = datetime.utcnow()
        
        db.commit()
        
        logger.info(
            f"Collection completed for account {account_id}: "
            f"{result.get('new', 0)} new articles"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Collection failed for account {account_id}: {str(e)}")
        
        if task_record:
            task_record.status = "FAILURE"
            task_record.error_message = str(e)
            task_record.completed_at = datetime.utcnow()
            if task_record.started_at:
                task_record.duration = (
                    task_record.completed_at - task_record.started_at
                ).seconds
            db.commit()
        
        raise
        
    finally:
        db.close()


@celery_app.task(name="collector.scheduled_collection")
def scheduled_collection_task():
    """
    定时采集任务（采集所有活跃的公众号）
    """
    db = SessionLocal()
    try:
        accounts = db.query(OfficialAccount).filter(
            OfficialAccount.is_active == True
        ).all()
        
        logger.info(f"Starting scheduled collection for {len(accounts)} accounts")
        
        for account in accounts:
            start_collection_task.delay(account.id)
        
        return {"accounts": len(accounts)}
        
    finally:
        db.close()


# 定时任务配置
celery_app.conf.beat_schedule = {
    "scheduled-collection": {
        "task": "collector.scheduled_collection",
        "schedule": settings.COLLECTOR_INTERVAL_HOURS * 3600,  # 转换为秒
    },
}

