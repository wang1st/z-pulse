"""
邮件发送服务主入口
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from shared.database import get_db, init_db
from shared.config import settings
from shared.utils import get_logger
from .sender import EmailSender

logger = get_logger("email-sender")

app = FastAPI(
    title="Z-Pulse 邮件发送服务",
    version="1.0.0",
)


class SendReportRequest(BaseModel):
    """发送报告请求模型"""
    report_id: int
    recipients: List[str]


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("Starting email sender service...")
    init_db()
    logger.info("Database initialized")


@app.get("/")
async def root():
    """健康检查"""
    return {"service": "email-sender", "status": "running"}


@app.post("/send/report")
async def send_report(
    request: SendReportRequest,
    db: Session = Depends(get_db)
):
    """
    发送报告邮件
    
    Args:
        request: 发送请求，包含报告ID和收件人列表
    """
    try:
        sender = EmailSender(db)
        result = sender.send_report(
            report_id=request.report_id,
            recipients=request.recipients
        )
        return result
    except Exception as e:
        logger.error(f"Failed to send report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send/daily-reports")
async def send_daily_reports(db: Session = Depends(get_db)):
    """
    发送日报给所有订阅者
    """
    try:
        sender = EmailSender(db)
        result = sender.send_daily_reports()
        return result
    except Exception as e:
        logger.error(f"Failed to send daily reports: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send/weekly-reports")
async def send_weekly_reports(db: Session = Depends(get_db)):
    """
    发送周报给所有订阅者
    """
    try:
        sender = EmailSender(db)
        result = sender.send_weekly_reports()
        return result
    except Exception as e:
        logger.error(f"Failed to send weekly reports: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )

