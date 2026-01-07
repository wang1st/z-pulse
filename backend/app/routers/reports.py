"""
报告API路由
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from shared.database import get_db, Report, ReportType
from shared.utils import get_logger

router = APIRouter()
logger = get_logger("api.reports")


class ReportResponse(BaseModel):
    """报告响应模型"""
    id: int
    report_type: str
    report_date: str
    title: str
    summary_markdown: str
    analysis_markdown: Optional[str]
    content_json: Optional[Dict[str, Any]] = None
    article_count: int
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[ReportResponse])
async def get_reports(
    report_type: Optional[str] = Query(None, description="报告类型: daily/weekly"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    获取报告列表
    
    支持分页、类型筛选和日期范围查询
    """
    from datetime import date
    
    query = db.query(Report)
    
    if report_type:
        query = query.filter(Report.report_type == ReportType(report_type))
    
    # 日期范围筛选
    if start_date:
        try:
            start = date.fromisoformat(start_date)
            query = query.filter(Report.report_date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = date.fromisoformat(end_date)
            query = query.filter(Report.report_date <= end)
        except ValueError:
            pass
    
    reports = query.order_by(
        Report.report_date.desc()
    ).offset(offset).limit(limit).all()
    
    return [
        ReportResponse(
            id=r.id,
            report_type=r.report_type.value,
            report_date=r.report_date.isoformat(),
            title=r.title,
            summary_markdown=r.summary_markdown,
            analysis_markdown=r.analysis_markdown,
            content_json=getattr(r, "content_json", None),
            article_count=r.article_count,
            created_at=r.created_at.isoformat()
        )
        for r in reports
    ]


@router.get("/latest/{report_type}", response_model=ReportResponse)
async def get_latest_report(
    report_type: str,
    db: Session = Depends(get_db)
):
    """
    获取最新的日报或周报
    """
    report = db.query(Report).filter(
        Report.report_type == ReportType(report_type)
    ).order_by(Report.report_date.desc()).first()
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No {report_type} report found"
        )
    
    return ReportResponse(
        id=report.id,
        report_type=report.report_type.value,
        report_date=report.report_date.isoformat(),
        title=report.title,
        summary_markdown=report.summary_markdown,
        analysis_markdown=report.analysis_markdown,
        content_json=getattr(report, "content_json", None),
        article_count=report.article_count,
        created_at=report.created_at.isoformat()
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report_by_id(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定ID的报告
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportResponse(
        id=report.id,
        report_type=report.report_type.value,
        report_date=report.report_date.isoformat(),
        title=report.title,
        summary_markdown=report.summary_markdown,
        analysis_markdown=report.analysis_markdown,
        content_json=getattr(report, "content_json", None),
        article_count=report.article_count,
        created_at=report.created_at.isoformat()
    )

