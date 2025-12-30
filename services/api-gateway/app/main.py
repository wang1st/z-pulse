"""
API网关主入口
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session

from shared.database import get_db, init_db
from shared.config import settings
from shared.utils import get_logger
from .routers import auth, accounts, articles, reports, subscriptions

logger = get_logger("api-gateway")

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url=f"{settings.API_PREFIX}/docs",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["认证"])
app.include_router(accounts.router, prefix=f"{settings.API_PREFIX}/accounts", tags=["公众号"])
app.include_router(articles.router, prefix=f"{settings.API_PREFIX}/articles", tags=["文章"])
app.include_router(reports.router, prefix=f"{settings.API_PREFIX}/reports", tags=["报告"])
app.include_router(subscriptions.router, prefix=f"{settings.API_PREFIX}/subscriptions", tags=["订阅"])


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    init_db()
    logger.info("Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("Shutting down...")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

