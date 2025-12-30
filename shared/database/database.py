"""
数据库连接和会话管理
"""
from typing import Generator

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from ..config import settings
from .models import Base


# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话
    
    使用方法:
        with get_db() as db:
            # 使用 db
            pass
    
    或在FastAPI中:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库
    创建所有表
    """
    Base.metadata.create_all(bind=engine)
    _ensure_schema_compat()


def _ensure_schema_compat() -> None:
    """
    轻量级“开发期迁移”：
    - 项目还在开发中，不引入 Alembic，缺列则自动补齐。
    """
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        # ai_generated_reports.content_json
        if "ai_generated_reports" in tables:
            cols = {c["name"] for c in inspector.get_columns("ai_generated_reports")}
            if "content_json" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE ai_generated_reports ADD COLUMN content_json JSON"))

        # report_jobs 表由 create_all 创建即可；这里不额外处理
    except Exception:
        # 迁移失败不应阻止服务启动（尤其是只读/测试环境）
        return


def drop_db() -> None:
    """
    删除所有表（危险操作，仅用于开发和测试）
    """
    Base.metadata.drop_all(bind=engine)

