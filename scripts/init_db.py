#!/usr/bin/env python
"""
数据库初始化脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database import init_db, engine
from shared.config import settings
from shared.utils import get_logger

logger = get_logger("init_db")


def main():
    """初始化数据库"""
    try:
        logger.info(f"Initializing database: {settings.DATABASE_URL}")
        
        # 创建所有表
        init_db()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

