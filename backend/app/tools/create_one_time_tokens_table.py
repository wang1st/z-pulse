#!/usr/bin/env python3
"""
创建one_time_tokens表的迁移脚本
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database.database import engine
from shared.database.models import OneTimeToken
from shared.utils import get_logger

logger = get_logger("migration")

def create_table():
    """创建one_time_tokens表"""
    try:
        logger.info("Creating one_time_tokens table...")

        # 使用SQLAlchemy创建表
        OneTimeToken.__table__.create(engine, checkfirst=True)

        logger.info("✅ one_time_tokens table created successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create table: {e}")
        return False

if __name__ == "__main__":
    success = create_table()
    sys.exit(0 if success else 1)
