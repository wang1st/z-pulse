#!/usr/bin/env python3
"""
生成12月25日的晨报并发送给所有订阅用户（带PDF附件）
"""

import sys
from pathlib import Path
from datetime import date

# 确保容器内可 import shared（项目根目录 /app）
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from shared.utils import get_logger
from app.workers.ai_generate import AIWorker

logger = get_logger("generate_and_send_daily_2025_12_25")


def main():
    target_date = date(2025, 12, 25)
    logger.info(f"开始生成并发送 {target_date} 的晨报...")
    
    try:
        worker = AIWorker()
        # 生成晨报并自动发送邮件（send_emails=True）
        worker.generate_daily_report(target_date=target_date, send_emails=True)
        logger.info(f"✅ {target_date} 晨报生成并发送完成")
    except Exception as e:
        logger.error(f"❌ 失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

