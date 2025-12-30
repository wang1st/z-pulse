"""
报告管理路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from shared.database import get_db, Report, ReportType, User
from ..security import get_current_active_user

router = APIRouter()


class ReportResponse(BaseModel):
    """报告响应模型"""
    id: int
    title: str
    report_type: str
    summary: Optional[str]
    article_count: int
    start_date: datetime
    end_date: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReportDetailResponse(ReportResponse):
    """报告详情响应模型"""
    content: str


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    report_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取报告列表
    """
    query = db.query(Report)
    
    if report_type:
        query = query.filter(Report.report_type == ReportType(report_type))
    
    reports = query.order_by(
        Report.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return reports


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取报告详情
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report


@router.get("/latest/{report_type}", response_model=ReportDetailResponse)
async def get_latest_report(
    report_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取最新的报告
    """
    report = db.query(Report).filter(
        Report.report_type == ReportType(report_type)
    ).order_by(Report.created_at.desc()).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="No report found")
    
    return report

