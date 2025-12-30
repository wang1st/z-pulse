"""
健康检查路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """健康检查"""
    try:
        # 测试数据库连接
        db.execute("SELECT 1")
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    return {
        "status": "running",
        "database": db_status
    }

