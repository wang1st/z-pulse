"""
Celery任务定义 - 数据同步
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from celery import Celery

from shared.config import settings
from shared.database import SessionLocal
from shared.utils import get_logger
from .syncer import WeRSSSync

logger = get_logger("sync-service.tasks")

# 创建Celery应用
celery_app = Celery(
    "sync-service",
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


@celery_app.task(name="sync.sync_account")
async def sync_account_task(account_id: int):
    """
    同步单个公众号
    
    Args:
        account_id: 公众号ID
    """
    db = SessionLocal()
    try:
        syncer = WeRSSSync(db)
        result = await syncer.sync_account(account_id)
        return result
    finally:
        db.close()


@celery_app.task(name="sync.sync_all")
async def sync_all_task():
    """
    同步所有公众号（定时任务）
    """
    db = SessionLocal()
    try:
        syncer = WeRSSSync(db)
        result = await syncer.sync_all_accounts()
        logger.info(
            f"Scheduled sync completed: "
            f"{result['total_new']} new articles from {result['total_accounts']} accounts"
        )
        return result
    finally:
        db.close()


# 定时任务配置
celery_app.conf.beat_schedule = {
    "sync-all-accounts": {
        "task": "sync.sync_all",
        "schedule": 3600,  # 每小时执行一次
    },
}

