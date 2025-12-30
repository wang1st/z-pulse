"""
AI处理服务主入口
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from shared.database import get_db, init_db
from shared.config import settings
from shared.utils import get_logger
from .processor import ArticleProcessor, ReportGenerator

logger = get_logger("ai-processor")

app = FastAPI(
    title="Z-Pulse AI处理服务",
    version="1.0.0",
)


class ProcessRequest(BaseModel):
    """处理请求模型"""
    article_id: int


class ReportRequest(BaseModel):
    """报告生成请求模型"""
    report_type: str  # daily, weekly, monthly
    start_date: str
    end_date: str


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("Starting AI processor service...")
    init_db()
    logger.info("Database initialized")


@app.get("/")
async def root():
    """健康检查"""
    return {"service": "ai-processor", "status": "running"}


@app.post("/process/article")
async def process_article(
    request: ProcessRequest,
    db: Session = Depends(get_db)
):
    """
    处理单篇文章
    
    分析文章内容，提取关键信息
    """
    try:
        processor = ArticleProcessor(db)
        result = processor.process_article(request.article_id)
        return result
    except Exception as e:
        logger.error(f"Failed to process article {request.article_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/report")
async def generate_report(
    request: ReportRequest,
    db: Session = Depends(get_db)
):
    """
    生成报告
    
    根据指定时间范围内的文章生成日报/周报/月报
    """
    try:
        generator = ReportGenerator(db)
        
        start_date = datetime.fromisoformat(request.start_date)
        end_date = datetime.fromisoformat(request.end_date)
        
        report = generator.generate_report(
            report_type=request.report_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "report_id": report.id,
            "title": report.title,
            "article_count": report.article_count,
            "created_at": report.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/daily-report")
async def generate_daily_report(db: Session = Depends(get_db)):
    """
    生成今日日报
    """
    try:
        generator = ReportGenerator(db)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        report = generator.generate_report(
            report_type="daily",
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "report_id": report.id,
            "title": report.title,
            "article_count": report.article_count
        }
    except Exception as e:
        logger.error(f"Failed to generate daily report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/weekly-report")
async def generate_weekly_report(db: Session = Depends(get_db)):
    """
    生成本周周报
    """
    try:
        generator = ReportGenerator(db)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        report = generator.generate_report(
            report_type="weekly",
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "report_id": report.id,
            "title": report.title,
            "article_count": report.article_count
        }
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )

