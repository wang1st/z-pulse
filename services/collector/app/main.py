"""
数据采集服务主入口
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from shared.database import get_db, init_db
from shared.config import settings
from shared.utils import get_logger
from .tasks import start_collection_task

logger = get_logger("collector")

app = FastAPI(
    title="Z-Pulse 数据采集服务",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("Starting collector service...")
    init_db()
    logger.info("Database initialized")


@app.get("/")
async def root():
    """健康检查"""
    return {"service": "collector", "status": "running"}


@app.post("/collect/{account_id}")
async def trigger_collection(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    手动触发采集任务
    
    Args:
        account_id: 公众号ID
    """
    task = start_collection_task.delay(account_id)
    return {
        "task_id": task.id,
        "account_id": account_id,
        "status": "submitted"
    }


@app.get("/collect/status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
    """
    from celery.result import AsyncResult
    task = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )

