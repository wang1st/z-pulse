"""
FastAPI主应用
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
# 在Docker中：/app/backend/app/main.py -> /app (向上3级)
# 在本地：backend/app/main.py -> 项目根目录 (向上3级)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from shared.database import init_db
from shared.utils import get_logger
from .routers import reports, subscriptions, health, auth, admin

logger = get_logger("api-backend")

app = FastAPI(
    title="Z-Pulse API Backend",
    description="财政信息AI日报系统 API",
    version="2.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])
app.include_router(reports.router, prefix="/api/reports", tags=["报告"])
app.include_router(subscriptions.router, prefix="/api/subscribe", tags=["订阅"])
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("Starting API backend...")
    init_db()
    logger.info("Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("Shutting down API backend...")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Z-Pulse API Backend",
        "version": "2.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

