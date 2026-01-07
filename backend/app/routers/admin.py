"""
管理后台路由
"""
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Response, BackgroundTasks
from fastapi.responses import RedirectResponse
import time
import re
import html as _html
import httpx
from urllib.parse import urlencode
import os
import threading
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from pydantic import BaseModel, EmailStr
import pandas as pd
import io

from shared.database import (
    get_db,
    SessionLocal,
    OfficialAccount,
    Article,
    Report,
    ReportJob,
    Subscriber,
    User,
    ArticleStatus,
    ReportType,
    ReportJobType,
    ReportJobStatus,
    ArticleCollectionJob,
    ArticleCollectionJobStatus,
)
from shared.auth import get_current_active_user
from shared.config import settings
from shared.utils import get_logger

router = APIRouter(tags=["管理后台"])
logger = get_logger("api.admin")
_ARTICLE_COLLECT_LOCK = threading.Lock()


_WERSS_TOKEN_CACHE: dict[str, Any] = {"token": None, "exp_ts": 0.0}


def _iso_utc(dt: datetime | None) -> str:
    """Return ISO string with explicit UTC timezone (+00:00)."""
    if not dt:
        return ""
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except Exception:
        # fallback: best-effort
        return str(dt)

def _looks_like_placeholder_text(s: str) -> bool:
    if not isinstance(s, str):
        return True
    t = s.strip()
    if not t:
        return True
    # common wechat/rss placeholder texts
    if "欢迎关注" in t and len(t) < 80:
        return True
    if t in ("图片", "image", "Image"):
        return True
    return len(t) < 120

def _to_visible_text(raw: str) -> str:
    """Convert HTML-ish content to user-visible plain text."""
    if not raw:
        return ""
    s = raw
    try:
        s = _html.unescape(s)
    except Exception:
        pass
    if "<" in s and ">" in s:
        try:
            from lxml import html as lxml_html
            doc = lxml_html.fromstring(s)
            for bad in doc.xpath("//script|//style|//noscript"):
                bad.drop_tree()
            s = doc.text_content()
        except Exception:
            s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    lines = []
    for line in s.split("\n"):
        t = line.strip()
        if not t:
            continue
        if t in ("图片", "image", "Image"):
            continue
        lines.append(t)
    s = "\n".join(lines)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s

async def _get_werss_token(base_url: str) -> Optional[str]:
    """Login to weRSS and cache a short-lived token for internal fetches."""
    now = time.time()
    if _WERSS_TOKEN_CACHE.get("token") and float(_WERSS_TOKEN_CACHE.get("exp_ts") or 0) > now + 30:
        return _WERSS_TOKEN_CACHE["token"]
    username = os.getenv("WERSS_ADMIN_USERNAME") or "admin"
    password = os.getenv("WERSS_ADMIN_PASSWORD") or "admin@123"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{base_url}/api/v1/wx/auth/login",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            token = (data.get("data") or {}).get("access_token")
            if token:
                # token expiry is managed by weRSS; cache for 30 minutes conservatively
                _WERSS_TOKEN_CACHE["token"] = token
                _WERSS_TOKEN_CACHE["exp_ts"] = now + 30 * 60
            return token
    except Exception as e:
        logger.warning(f"Failed to login to weRSS for fulltext fetch: {e}")
        return None

async def _fetch_fulltext_from_werss(article_url: str) -> Optional[str]:
    """
    Fetch full article content from weRSS using its internal fetcher (Playwright+session).
    Requires weRSS admin auth.
    """
    base_url = settings.RSS_BRIDGE_URL.rstrip("/")  # e.g. http://rss-bridge:8001
    token = await _get_werss_token(base_url)
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            # this endpoint is POST with query param 'url'
            url = f"{base_url}/api/v1/wx/mps/by_article?{urlencode({'url': article_url})}"
            resp = await client.post(url, headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()
            payload = resp.json()
            info = payload.get("data") or {}
            raw = info.get("content") or ""
            txt = _to_visible_text(raw)
            return txt or None
    except Exception as e:
        logger.warning(f"Failed to fetch fulltext from weRSS: {e}")
        return None


# ==================== 公众号管理 ====================

class OfficialAccountCreate(BaseModel):
    """公众号创建模型"""
    name: str
    wechat_id: str | None = None
    werss_feed_id: str | None = None
    is_active: bool = True


class OfficialAccountUpdate(BaseModel):
    """公众号更新模型"""
    name: str | None = None
    wechat_id: str | None = None
    werss_feed_id: str | None = None
    is_active: bool | None = None


class OfficialAccountResponse(BaseModel):
    """公众号响应模型"""
    id: int
    name: str
    wechat_id: str | None
    werss_feed_id: str | None
    is_active: bool
    total_articles: int
    last_collection_time: datetime | None
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/accounts/export")
async def export_accounts(
    template: Optional[str] = Query(default=None, description="是否导出模板文件，传'true'导出模板"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """导出公众号列表为CSV，或导出模板文件"""
    from fastapi.responses import Response
    
    # 处理template参数：支持字符串"true"/"false"
    is_template = False
    if template is not None and template:
        is_template = str(template).lower() in ('true', '1', 'yes', 'on')
    
    if is_template:
        # 导出模板文件（带说明）
        # 使用多行字符串，第一行是说明，后面是数据
        template_lines = [
            "说明：第一行是说明文字，导入前请删除第一行。所有字段都是必填项：werss_feed_id（Feed ID）、name（公众号名称）、is_active（是否启用，填写1表示启用，0表示停用）、wechat_id（微信ID）。列名必须保留在第一行（删除说明后的第一行）。",
            "werss_feed_id,name,is_active,wechat_id",
            "feed_123,示例公众号,1,example_wechat_id"
        ]
        template_content = "\n".join(template_lines)
        return Response(
            content=template_content,
            media_type='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename="accounts_template.csv"'
            }
        )
    
    # 导出实际数据
    accounts = db.query(OfficialAccount).all()
    
    # 构建DataFrame（导出时按新顺序：werss_feed_id, name, is_active, wechat_id，is_active 使用 0/1 格式）
    data = []
    for account in accounts:
        data.append({
            'werss_feed_id': account.werss_feed_id or '',
            'name': account.name,
            'is_active': 1 if account.is_active else 0,  # 导出时使用 0/1 格式
            'wechat_id': account.wechat_id or '',
        })
    
    df = pd.DataFrame(data)
    
    # 确保列顺序：werss_feed_id, name, is_active, wechat_id
    column_order = ['werss_feed_id', 'name', 'is_active', 'wechat_id']
    df = df[column_order]
    
    # 转换为CSV
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    return Response(
        content=output.getvalue(),
        media_type='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename="accounts_export.csv"'
        }
    )


@router.get("/accounts", response_model=List[OfficialAccountResponse])
async def list_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取公众号列表"""
    query = db.query(OfficialAccount)
    
    if is_active is not None:
        query = query.filter(OfficialAccount.is_active == is_active)
    
    accounts = query.order_by(desc(OfficialAccount.created_at)).offset(skip).limit(limit).all()
    return accounts


@router.post("/accounts", response_model=OfficialAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: OfficialAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建公众号"""
    # 检查wechat_id是否已存在
    if account_data.wechat_id:
        existing = db.query(OfficialAccount).filter(
            OfficialAccount.wechat_id == account_data.wechat_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="WeChat ID already exists"
            )
    
    account = OfficialAccount(
        name=account_data.name,
        wechat_id=account_data.wechat_id,
        # level, region, department 字段已废弃，不再使用
        werss_feed_id=account_data.werss_feed_id,
        werss_sync_method='rss',  # 固定为 rss
        is_active=account_data.is_active,
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    logger.info(f"Account created: {account.name} by {current_user.username}")
    
    return account


@router.get("/accounts/{account_id}", response_model=OfficialAccountResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取公众号详情"""
    account = db.query(OfficialAccount).filter(OfficialAccount.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    return account


@router.put("/accounts/{account_id}", response_model=OfficialAccountResponse)
async def update_account(
    account_id: int,
    account_data: OfficialAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新公众号"""
    account = db.query(OfficialAccount).filter(OfficialAccount.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # 更新字段
    update_data = account_data.model_dump(exclude_unset=True)
    # level, region, department 字段已废弃，不再处理
    
    for field, value in update_data.items():
        setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    
    logger.info(f"Account updated: {account.name} by {current_user.username}")
    
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除公众号"""
    account = db.query(OfficialAccount).filter(OfficialAccount.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    db.delete(account)
    db.commit()
    
    logger.info(f"Account deleted: {account.name} by {current_user.username}")


@router.post("/accounts/import")
async def import_accounts(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    批量导入公众号（支持CSV和Excel）
    
    CSV/Excel格式要求：
    - 必需列：name（名称）
    - 可选列：wechat_id（微信ID）、werss_feed_id（Feed ID）、is_active（是否启用，默认true）
    """
    try:
        # 读取文件内容
        contents = await file.read()
        
        # 根据文件扩展名选择读取方式
        file_ext = file.filename.split('.')[-1].lower() if file.filename else 'csv'
        
        if file_ext in ['xlsx', 'xls']:
            # Excel文件
            df = pd.read_excel(io.BytesIO(contents))
        else:
            # CSV文件 - 尝试读取，如果第一行是说明行则跳过
            try:
                # 先读取第一行检查是否是说明行
                first_line = contents.split(b'\n')[0].decode('utf-8', errors='ignore')
                # 检查是否包含说明关键词
                if '说明' in first_line or '第一行是说明' in first_line or '导入前请删除' in first_line or '请务必' in first_line:
                    # 跳过说明行（第一行），从第二行开始读取（第二行应该是列名）
                    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8', skiprows=1)
                    logger.info("检测到说明行，已自动跳过第一行")
                else:
                    # 没有说明行，正常读取
                    df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except Exception as e:
                # 如果出错，尝试正常读取
                logger.warning(f"CSV解析出错，尝试正常读取: {str(e)}")
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
        
        # 验证必需列（所有字段都是必填的）
        required_columns = ['werss_feed_id', 'name', 'is_active', 'wechat_id']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"缺少必需列: {', '.join(missing_columns)}。请确保CSV文件包含所有列：werss_feed_id, name, is_active, wechat_id"
            )
        
        # 处理数据
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 获取数据，所有字段都是必填的（按新顺序：werss_feed_id, name, is_active, wechat_id）
                werss_feed_id = str(row['werss_feed_id']).strip() if pd.notna(row.get('werss_feed_id')) else None
                if not werss_feed_id:
                    errors.append(f"第{index+2}行: Feed ID为空（必填）")
                    error_count += 1
                    continue
                
                name = str(row['name']).strip()
                if not name:
                    errors.append(f"第{index+2}行: 名称为空（必填）")
                    error_count += 1
                    continue
                
                # is_active 字段处理（只接受 0 或 1）
                is_active_raw = row.get('is_active')
                if pd.isna(is_active_raw):
                    errors.append(f"第{index+2}行: is_active为空（必填，填写1表示启用，0表示停用）")
                    error_count += 1
                    continue
                
                # 转换为字符串并去除空格
                is_active_str = str(is_active_raw).strip()
                if is_active_str == '1':
                    is_active = True
                elif is_active_str == '0':
                    is_active = False
                else:
                    errors.append(f"第{index+2}行: is_active值无效（必须是0或1，1表示启用，0表示停用）")
                    error_count += 1
                    continue
                
                wechat_id = str(row['wechat_id']).strip() if pd.notna(row.get('wechat_id')) else None
                if not wechat_id:
                    errors.append(f"第{index+2}行: 微信ID为空（必填）")
                    error_count += 1
                    continue
                
                # 检查是否已存在（通过wechat_id或name）
                if wechat_id:
                    existing = db.query(OfficialAccount).filter(
                        OfficialAccount.wechat_id == wechat_id
                    ).first()
                    if existing:
                        errors.append(f"第{index+2}行: 微信ID {wechat_id} 已存在")
                        error_count += 1
                        continue
                
                # 创建公众号（所有字段都已验证为必填）
                account = OfficialAccount(
                    name=name,
                    wechat_id=wechat_id,
                    werss_feed_id=werss_feed_id,
                    werss_sync_method='rss',
                    is_active=is_active,
                )
                
                db.add(account)
                success_count += 1
                
            except Exception as e:
                errors.append(f"第{index+2}行: {str(e)}")
                error_count += 1
                continue
        
        # 提交所有更改
        db.commit()
        
        logger.info(f"Imported {success_count} accounts by {current_user.username}")
        
        return {
            "success": True,
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors[:20],  # 最多返回20个错误
            "message": f"成功导入 {success_count} 个公众号，失败 {error_count} 个"
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件为空"
        )
    except Exception as e:
        logger.error(f"Import error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"导入失败: {str(e)}"
        )


# ==================== 订阅管理 ====================

class SubscriberResponse(BaseModel):
    """订阅者响应模型"""
    id: int
    email: str
    is_active: bool
    subscribe_daily: bool
    subscribe_weekly: bool
    regions: dict | None
    total_sent: int
    last_sent_at: datetime | None
    created_at: datetime
    activated_at: datetime | None
    
    class Config:
        from_attributes = True


@router.get("/subscribers", response_model=List[SubscriberResponse])
async def list_subscribers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取订阅者列表"""
    query = db.query(Subscriber)
    
    if is_active is not None:
        query = query.filter(Subscriber.is_active == is_active)
    
    subscribers = query.order_by(desc(Subscriber.created_at)).offset(skip).limit(limit).all()
    return subscribers


@router.get("/subscribers/{subscriber_id}", response_model=SubscriberResponse)
async def get_subscriber(
    subscriber_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取订阅者详情"""
    subscriber = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscriber not found"
        )
    return subscriber


@router.delete("/subscribers/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscriber(
    subscriber_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除订阅者"""
    subscriber = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscriber not found"
        )
    
    db.delete(subscriber)
    db.commit()
    
    logger.info(f"Subscriber deleted: {subscriber.email} by {current_user.username}")


# ==================== 文章管理 ====================

class ArticleResponse(BaseModel):
    """文章响应模型"""
    id: int
    account_id: int
    account_name: Optional[str] = None
    title: str
    content: Optional[str]
    article_url: str
    published_at: str
    status: str
    collected_at: str
    
    class Config:
        from_attributes = True


@router.get("/articles", response_model=List[ArticleResponse])
async def list_articles(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    date: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取文章列表（管理后台）"""
    # Join to avoid N+1 queries for account name (this endpoint is used by admin UI).
    query = db.query(Article, OfficialAccount.name).join(
        OfficialAccount, OfficialAccount.id == Article.account_id
    )
    
    if status:
        query = query.filter(Article.status == ArticleStatus(status))
    
    if date:
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            tomorrow = target_date + timedelta(days=1)
            query = query.filter(
                Article.published_at >= target_date,
                Article.published_at < tomorrow
            )
        except ValueError:
            pass
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Article.title.ilike(search_pattern)) |
            (Article.content.ilike(search_pattern))
        )
    
    total = query.count()
    response.headers["X-Total-Count"] = str(total)

    rows = query.order_by(desc(Article.published_at)).offset(skip).limit(limit).all()
    
    # 构建响应，包含公众号名称
    result = []
    for article, account_name in rows:
        # list page should be fast: only send a short preview; full text is available via /articles/{id}
        preview = article.content
        if isinstance(preview, str) and len(preview) > 800:
            preview = preview[:800]
        result.append(ArticleResponse(
            id=article.id,
            account_id=article.account_id,
            account_name=account_name,
            title=article.title,
            content=preview,
            article_url=article.article_url,
            published_at=_iso_utc(article.published_at),
            status=article.status.value if hasattr(article.status, 'value') else str(article.status),
            collected_at=_iso_utc(article.collected_at),
        ))
    
    return result


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取单篇文章详情（管理后台，返回完整纯文本内容）"""
    row = (
        db.query(Article, OfficialAccount.name)
        .join(OfficialAccount, OfficialAccount.id == Article.account_id)
        .filter(Article.id == article_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Article not found")
    article, account_name = row
    # If stored content is clearly a placeholder/summary, try fetching full text from weRSS on-demand.
    if _looks_like_placeholder_text(article.content or "") and article.article_url:
        fulltext = await _fetch_fulltext_from_werss(article.article_url)
        if fulltext and len(fulltext) > len((article.content or "").strip()) + 80:
            article.content = fulltext
            db.add(article)
            db.commit()
    return ArticleResponse(
        id=article.id,
        account_id=article.account_id,
        account_name=account_name,
        title=article.title,
        content=article.content,
        article_url=article.article_url,
        published_at=_iso_utc(article.published_at),
        status=article.status.value if hasattr(article.status, 'value') else str(article.status),
        collected_at=_iso_utc(article.collected_at),
    )


@router.post("/articles/collect", status_code=status.HTTP_202_ACCEPTED)
async def trigger_article_collection(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    手动触发文章采集
    
    立即采集所有活跃公众号的最新文章
    """
    try:
        logger.info(f"Article collection triggered by {current_user.username}")

        # Prevent stacking multiple collections if user clicks repeatedly.
        if _ARTICLE_COLLECT_LOCK.locked():
            return {
                "status": "accepted",
                "message": "已有采集任务在运行中（不会重复启动）。",
            }

        job = ArticleCollectionJob(
            status=ArticleCollectionJobStatus.PENDING,
            requested_by=current_user.username,
            mode="sqlite" if os.getenv("USE_WERSS_DB", "True").lower() == "true" else "rss",
            total_accounts=0,
            processed_accounts=0,
            new_articles=0,
            skipped_articles=0,
            error_count=0,
            details={"accounts": [], "errors": []},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        def _run_collection(job_id: int) -> None:
            from app.workers.ingest import IngestionWorker
            import time

            # Prevent stacking multiple collections if user clicks repeatedly.
            if not _ARTICLE_COLLECT_LOCK.acquire(blocking=False):
                logger.info("Article collection already running; skip starting another one.")
                return
            try:
                worker = IngestionWorker()
                s = SessionLocal()
                try:
                    job_row = s.query(ArticleCollectionJob).filter(ArticleCollectionJob.id == job_id).first()
                    if not job_row:
                        return
                    job_row.status = ArticleCollectionJobStatus.RUNNING
                    job_row.started_at = datetime.utcnow()

                    accounts = (
                        s.query(OfficialAccount)
                        .filter(OfficialAccount.is_active == True)
                        .order_by(OfficialAccount.id.asc())
                        .all()
                    )
                    job_row.total_accounts = len(accounts)
                    s.commit()

                    total_new = 0
                    total_skipped = 0
                    error_count = 0
                    details_accounts: list[dict[str, Any]] = []
                    details_errors: list[dict[str, Any]] = []

                    for idx, account in enumerate(accounts, start=1):
                        t0 = time.time()
                        new_count = 0
                        err: str | None = None
                        try:
                            # collect_feed may use sqlite (preferred) or fallback to HTTP RSS.
                            new_count = worker.collect_feed(s, account)
                        except Exception as e:
                            err = str(e)
                            error_count += 1
                            job_row.last_error = f"{account.name}: {err}"
                            details_errors.append({"account": account.name, "error": err})
                            logger.error(f"Failed to collect from {account.name}: {err}")

                        # Heuristic skipped count: if no new articles and feed has entries, it's likely all existed.
                        # We don't have exact skipped count here; keep as best-effort.
                        if new_count == 0 and not err:
                            total_skipped += 1
                        total_new += int(new_count or 0)

                        details_accounts.append(
                            {
                                "account": account.name,
                                "new": int(new_count or 0),
                                "ok": err is None,
                                "ms": int((time.time() - t0) * 1000),
                            }
                        )

                        job_row.processed_accounts = idx
                        job_row.new_articles = total_new
                        job_row.skipped_articles = total_skipped
                        job_row.error_count = error_count
                        job_row.details = {"accounts": details_accounts[-100:], "errors": details_errors[-50:]}
                        s.commit()

                    job_row.status = ArticleCollectionJobStatus.SUCCESS if error_count == 0 else ArticleCollectionJobStatus.FAILED
                    job_row.finished_at = datetime.utcnow()
                    s.commit()
                finally:
                    try:
                        s.close()
                    except Exception:
                        pass
                logger.info("Article collection finished.")
            except Exception as e:
                logger.error(f"Background article collection failed: {e}")
                try:
                    s2 = SessionLocal()
                    job_row = s2.query(ArticleCollectionJob).filter(ArticleCollectionJob.id == job_id).first()
                    if job_row:
                        job_row.status = ArticleCollectionJobStatus.FAILED
                        job_row.last_error = str(e)
                        job_row.finished_at = datetime.utcnow()
                        s2.commit()
                    s2.close()
                except Exception:
                    pass
            finally:
                try:
                    _ARTICLE_COLLECT_LOCK.release()
                except Exception:
                    pass

        background_tasks.add_task(_run_collection, job.id)

        return {
            "status": "accepted",
            "message": "已在后台开始采集（不会阻塞页面）。可查看进度或稍后刷新列表。",
            "job_id": job.id,
        }
    except Exception as e:
        logger.error(f"Failed to trigger article collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发文章采集失败: {str(e)}"
        )


class ArticleCollectionJobResponse(BaseModel):
    id: int
    status: str
    requested_by: str | None = None
    mode: str | None = None
    total_accounts: int
    processed_accounts: int
    new_articles: int
    skipped_articles: int
    error_count: int
    last_error: str | None = None
    details: Dict[str, Any] | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


@router.get("/articles/collect/status", response_model=ArticleCollectionJobResponse | None)
async def get_article_collection_status(
    job_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取采集任务状态（默认返回最新任务；也可指定 job_id）"""
    q = db.query(ArticleCollectionJob)
    if job_id is not None:
        q = q.filter(ArticleCollectionJob.id == job_id)
    else:
        q = q.order_by(ArticleCollectionJob.created_at.desc())
    job = q.first()
    if not job:
        return None
    return ArticleCollectionJobResponse(
        id=job.id,
        status=job.status.value if hasattr(job.status, "value") else str(job.status),
        requested_by=job.requested_by,
        mode=job.mode,
        total_accounts=job.total_accounts or 0,
        processed_accounts=job.processed_accounts or 0,
        new_articles=job.new_articles or 0,
        skipped_articles=job.skipped_articles or 0,
        error_count=job.error_count or 0,
        last_error=job.last_error,
        details=job.details,
        created_at=job.created_at.isoformat() if job.created_at else "",
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
    )


@router.get("/articles/collect/jobs", response_model=list[ArticleCollectionJobResponse])
async def list_article_collection_jobs(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """列出最近的采集任务"""
    jobs = db.query(ArticleCollectionJob).order_by(ArticleCollectionJob.created_at.desc()).limit(limit).all()
    out: list[ArticleCollectionJobResponse] = []
    for job in jobs:
        out.append(
            ArticleCollectionJobResponse(
                id=job.id,
                status=job.status.value if hasattr(job.status, "value") else str(job.status),
                requested_by=job.requested_by,
                mode=job.mode,
                total_accounts=job.total_accounts or 0,
                processed_accounts=job.processed_accounts or 0,
                new_articles=job.new_articles or 0,
                skipped_articles=job.skipped_articles or 0,
                error_count=job.error_count or 0,
                last_error=job.last_error,
                details=job.details,
                created_at=job.created_at.isoformat() if job.created_at else "",
                started_at=job.started_at.isoformat() if job.started_at else None,
                finished_at=job.finished_at.isoformat() if job.finished_at else None,
            )
        )
    return out


@router.post("/articles/clear", status_code=status.HTTP_200_OK)
async def clear_all_articles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """清空所有文章（管理后台）"""
    try:
        # Use TRUNCATE for speed; also reset official account counters.
        db.execute(text("TRUNCATE TABLE scraped_articles RESTART IDENTITY"))
        db.execute(text("UPDATE official_accounts SET total_articles=0, last_collection_time=NULL"))
        db.commit()
        logger.warning(f"All articles cleared by {current_user.username}")
        return {"status": "success", "message": "已清空所有文章"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to clear all articles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空文章失败: {str(e)}"
        )


# ==================== 报告管理 ====================

class ReportResponse(BaseModel):
    """报告响应模型"""
    id: int
    report_type: str
    report_date: str
    title: str
    summary_markdown: str
    analysis_markdown: str | None
    content_json: Dict[str, Any] | None = None
    article_count: int
    view_count: int
    sent_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/reports", response_model=List[ReportResponse])
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    report_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取报告列表（管理后台）"""
    query = db.query(Report)
    
    if report_type:
        query = query.filter(Report.report_type == ReportType(report_type))
    
    reports = query.order_by(desc(Report.report_date)).offset(skip).limit(limit).all()
    
    # 显式转换枚举值为字符串
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
            view_count=r.view_count,
            sent_count=r.sent_count,
            created_at=r.created_at
        )
        for r in reports
    ]


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取报告详情（管理后台）"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # 增加查看次数
    report.view_count += 1
    db.commit()
    
    # 显式转换枚举值为字符串
    return ReportResponse(
        id=report.id,
        report_type=report.report_type.value,
        report_date=report.report_date.isoformat(),
        title=report.title,
        summary_markdown=report.summary_markdown,
        analysis_markdown=report.analysis_markdown,
        content_json=getattr(report, "content_json", None),
        article_count=report.article_count,
        view_count=report.view_count,
        sent_count=report.sent_count,
        created_at=report.created_at
    )


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除报告"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    db.delete(report)
    db.commit()
    
    logger.info(f"Report deleted: {report.title} by {current_user.username}")


@router.post("/reports/{report_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    重新生成指定报告
    
    根据报告日期重新生成日报。
    注意：为了避免 report_id 变化导致前端引用失效，日报会“原地更新”。
    """
    from app.workers.ai_generate import AIWorker
    
    # 获取原报告信息
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # 只支持重新生成日报
    if report.report_type != ReportType.DAILY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="目前只支持重新生成日报"
        )
    
    # 为了避免阻塞 API（生成可能要几分钟），这里改为“入队任务”，由 ai-worker 异步执行
    target_date = report.report_date
    return await _enqueue_regenerate_daily_job(db=db, target_date=target_date, requested_by=current_user.username)


@router.post("/reports/daily/{report_date}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_daily_report_by_date(
    report_date: str,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    按日期重新生成日报（推荐）

    - 避免前端拿到旧 report_id 导致 404
    - 日报会“原地更新”（如果该日期已存在日报）
    """
    from app.workers.ai_generate import AIWorker
    from datetime import date, timedelta

    try:
        target_date = date.fromisoformat(report_date)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="report_date 格式错误，需为 YYYY-MM-DD"
        )

    tomorrow = target_date + timedelta(days=1)
    article_count = db.query(Article).filter(
        Article.published_at >= target_date,
        Article.published_at < tomorrow
    ).count()
    if article_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法重新生成：{target_date} 没有文章数据。请检查文章采集是否正常，或该日期确实没有发布文章。"
        )

    return await _enqueue_regenerate_daily_job(
        db=db,
        target_date=target_date,
        requested_by=current_user.username,
        force=force,
    )


async def _enqueue_regenerate_daily_job(db: Session, target_date, requested_by: str, force: bool = False):
    """创建/复用一个 pending/running 的日报再生成任务（非阻塞）"""
    tomorrow = target_date + timedelta(days=1)
    article_count = db.query(Article).filter(
        Article.published_at >= target_date,
        Article.published_at < tomorrow
    ).count()
    if article_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法重新生成：{target_date} 没有文章数据。请检查文章采集是否正常，或该日期确实没有发布文章。"
        )

    existing = db.query(ReportJob).filter(
        ReportJob.job_type == ReportJobType.REGENERATE_DAILY,
        ReportJob.target_date == target_date,
        ReportJob.status.in_([ReportJobStatus.PENDING, ReportJobStatus.RUNNING])
    ).order_by(ReportJob.created_at.desc()).first()

    # 如果已有任务：支持 force 强制重新入队；以及回收“卡死”的 RUNNING（worker 重启后会永远卡住）
    if existing:
        stale_minutes = int(os.getenv("REPORT_JOB_STALE_MINUTES", "60"))
        is_running = existing.status == ReportJobStatus.RUNNING
        is_stale_running = bool(
            is_running
            and existing.started_at is not None
            and (datetime.utcnow() - existing.started_at) > timedelta(minutes=stale_minutes)
            and existing.finished_at is None
        )

        if force or is_stale_running:
            # 标记旧任务失败（避免永远拦截）
            existing.status = ReportJobStatus.FAILED
            existing.finished_at = datetime.utcnow()
            if force:
                existing.error_message = f"Superseded by forced requeue by {requested_by}"
            else:
                existing.error_message = f"Stale RUNNING reclaimed after {stale_minutes} minutes (worker may have restarted)"
            db.commit()
            logger.warning(
                f"Requeue allowed (force={force}, stale={is_stale_running}): "
                f"old_job_id={existing.id} date={target_date} by {requested_by}"
            )
        else:
            logger.info(f"Regen job already queued/running: job_id={existing.id} date={target_date} by {requested_by}")
            return {
                "status": "queued",
                "message": f"已存在进行中的任务（job_id={existing.id}），请稍后刷新或在系统日志查看进度。"
                           f"（如需强制重跑，可带参数 force=true）",
                "job_id": existing.id,
                "target_date": str(target_date),
            }

    job = ReportJob(
        job_type=ReportJobType.REGENERATE_DAILY,
        status=ReportJobStatus.PENDING,
        target_date=target_date,
        requested_by=requested_by,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(f"Queued regen job: job_id={job.id} date={target_date} by {requested_by}")
    return {
        "status": "queued",
        "message": f"已提交后台任务（job_id={job.id}），生成期间系统不会卡死。可在“系统日志”查看进度。",
        "job_id": job.id,
        "target_date": str(target_date),
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    job = db.query(ReportJob).filter(ReportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {
        "id": job.id,
        "job_type": job.job_type.value,
        "status": job.status.value,
        "target_date": str(job.target_date),
        "report_id": job.report_id,
        "requested_by": job.requested_by,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_message": job.error_message or "",
    }


@router.get("/jobs", status_code=status.HTTP_200_OK)
async def list_report_jobs(
    limit: int = 50,
    job_type: str | None = None,
    status_: str | None = None,
    target_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    任务管理：列出最近的报告任务（用于后台“报告管理-任务管理”）
    - 默认按 created_at 倒序（最新在前）
    - 可按 job_type/status/target_date 过滤
    """
    limit = max(1, min(int(limit or 50), 200))

    q = db.query(ReportJob)

    if job_type:
        try:
            jt = ReportJobType(job_type)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid job_type: {job_type}")
        q = q.filter(ReportJob.job_type == jt)

    if status_:
        try:
            st = ReportJobStatus(status_)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status_}")
        q = q.filter(ReportJob.status == st)

    if target_date:
        try:
            td = date.fromisoformat(target_date)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_date 格式错误，需为 YYYY-MM-DD")
        q = q.filter(ReportJob.target_date == td)

    jobs = q.order_by(ReportJob.created_at.desc()).limit(limit).all()

    stale_minutes = int(os.getenv("REPORT_JOB_STALE_MINUTES", "60"))
    now_utc = datetime.utcnow()

    def _to_utc_iso(dt: datetime | None) -> str | None:
        if not dt:
            return None
        # DB stores naive UTC; return timezone-aware ISO for frontend conversion
        return dt.replace(tzinfo=timezone.utc).isoformat()

    items = []
    for j in jobs:
        is_stale = bool(
            j.status == ReportJobStatus.RUNNING
            and j.started_at is not None
            and j.finished_at is None
            and (now_utc - j.started_at) > timedelta(minutes=stale_minutes)
        )
        items.append(
            {
                "id": j.id,
                "job_type": j.job_type.value,
                "status": j.status.value,
                "target_date": str(j.target_date),
                "report_id": j.report_id,
                "requested_by": j.requested_by,
                "created_at": _to_utc_iso(j.created_at),
                "started_at": _to_utc_iso(j.started_at),
                "finished_at": _to_utc_iso(j.finished_at),
                "error_message": j.error_message or "",
                "is_stale": is_stale,
            }
        )
    return {"items": items, "stale_minutes": stale_minutes}


@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_report_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    取消任务：
    - 仅支持取消 PENDING（RUNNING 无法安全中断，只能“回收卡死”）
    """
    job = db.query(ReportJob).filter(ReportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status != ReportJobStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Only PENDING can be cancelled, got: {job.status.value}")

    job.status = ReportJobStatus.FAILED
    job.finished_at = datetime.utcnow()
    job.error_message = f"Cancelled by {current_user.username}"
    db.commit()
    return {"status": "ok", "id": job.id, "new_status": job.status.value}


@router.post("/jobs/{job_id}/reclaim", status_code=status.HTTP_200_OK)
async def reclaim_stale_running_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    回收卡死 RUNNING：
    - 将 RUNNING 标记为 FAILED，从而允许重新入队
    """
    job = db.query(ReportJob).filter(ReportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status != ReportJobStatus.RUNNING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Only RUNNING can be reclaimed, got: {job.status.value}")

    job.status = ReportJobStatus.FAILED
    job.finished_at = datetime.utcnow()
    job.error_message = f"Reclaimed by {current_user.username} (worker restart/crash suspected)"
    db.commit()
    return {"status": "ok", "id": job.id, "new_status": job.status.value}


# ==================== 统计信息 ====================

class DashboardStats(BaseModel):
    """仪表板统计信息"""
    total_accounts: int
    active_accounts: int
    total_articles: int
    pending_articles: int
    total_subscribers: int
    active_subscribers: int
    total_reports: int
    daily_reports: int
    weekly_reports: int


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取仪表板统计信息"""
    total_accounts = db.query(OfficialAccount).count()
    active_accounts = db.query(OfficialAccount).filter(OfficialAccount.is_active == True).count()
    
    total_articles = db.query(Article).count()
    pending_articles = db.query(Article).filter(Article.status == ArticleStatus.PENDING).count()
    
    total_subscribers = db.query(Subscriber).count()
    active_subscribers = db.query(Subscriber).filter(Subscriber.is_active == True).count()
    
    total_reports = db.query(Report).count()
    daily_reports = db.query(Report).filter(Report.report_type == ReportType.DAILY).count()
    weekly_reports = db.query(Report).filter(Report.report_type == ReportType.WEEKLY).count()
    
    return DashboardStats(
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        total_articles=total_articles,
        pending_articles=pending_articles,
        total_subscribers=total_subscribers,
        active_subscribers=active_subscribers,
        total_reports=total_reports,
        daily_reports=daily_reports,
        weekly_reports=weekly_reports,
    )


# ==================== 报告生成控制 ====================

@router.post("/reports/generate/daily", status_code=status.HTTP_202_ACCEPTED)
async def trigger_daily_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    手动触发日报生成
    
    注意：这是一个异步任务，会在后台执行
    """
    from app.workers.ai_generate import AIWorker
    
    try:
        worker = AIWorker()
        worker.generate_daily_report()
        
        logger.info(f"Daily report generation triggered by {current_user.username}")
        
        return {
            "status": "success",
            "message": "日报生成任务已启动，请查看日志了解进度"
        }
    except Exception as e:
        logger.error(f"Failed to trigger daily report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发日报生成失败: {str(e)}"
        )


@router.post("/reports/generate/weekly", status_code=status.HTTP_202_ACCEPTED)
async def trigger_weekly_report(
    background_tasks: BackgroundTasks,
    end_date: Optional[str] = Query(default=None, description="指定周报结束日期（YYYY-MM-DD），按该日往前7天生成"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    手动触发周报生成
    
    注意：这是一个异步任务，会在后台执行
    """
    from app.workers.ai_generate import AIWorker
    
    try:
        # Parse end_date if provided
        target_dt: date | None = None
        if end_date:
            try:
                target_dt = date.fromisoformat(end_date)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="end_date 格式错误，需为 YYYY-MM-DD"
                )

        def _run_weekly() -> None:
            try:
                worker = AIWorker()
                worker.generate_weekly_report(target_date=target_dt)
            except Exception as e:
                logger.error(f"Background weekly generation failed: {e}")

        background_tasks.add_task(_run_weekly)
        logger.info(f"Weekly report generation triggered by {current_user.username}")
        return {
            "status": "accepted",
            "message": "已在后台开始生成（不会阻塞页面）。请稍后刷新或查看系统日志。",
            "target_date": str(target_dt) if target_dt else None,
        }
    except Exception as e:
        logger.error(f"Failed to trigger weekly report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发周报生成失败: {str(e)}"
        )
