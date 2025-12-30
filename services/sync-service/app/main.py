"""
数据同步服务主入口
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
from .syncer import WeRSSSync

logger = get_logger("sync-service")

app = FastAPI(
    title="Z-Pulse 数据同步服务",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("Starting sync service...")
    init_db()
    logger.info("Database initialized")


@app.get("/")
async def root():
    """健康检查"""
    return {"service": "sync-service", "status": "running"}


@app.post("/sync/account/{account_id}")
async def sync_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    同步指定公众号的文章
    
    Args:
        account_id: 公众号ID
    """
    try:
        syncer = WeRSSSync(db)
        result = await syncer.sync_account(account_id)
        return result
    except Exception as e:
        logger.error(f"Failed to sync account {account_id}: {str(e)}")
        return {"error": str(e)}, 500


@app.post("/sync/all")
async def sync_all(db: Session = Depends(get_db)):
    """
    同步所有活跃公众号的文章
    """
    try:
        syncer = WeRSSSync(db)
        result = await syncer.sync_all_accounts()
        return result
    except Exception as e:
        logger.error(f"Failed to sync all accounts: {str(e)}")
        return {"error": str(e)}, 500


@app.get("/sync/status")
async def get_sync_status():
    """
    获取同步状态
    """
    # TODO: 实现同步状态查询
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=True
    )

