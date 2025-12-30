#!/usr/bin/env python
"""
手动触发日报生成脚本
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.workers.ai_generate import AIWorker
from shared.utils import get_logger

logger = get_logger("trigger_daily_report")

def main():
    """主函数"""
    logger.info("开始手动触发日报生成...")
    
    try:
        worker = AIWorker()
        target_date = None
        if len(sys.argv) >= 2 and sys.argv[1]:
            try:
                target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
            except Exception:
                logger.error("❌ 日期参数格式错误，应为 YYYY-MM-DD，例如：2025-12-15")
                sys.exit(2)
        worker.generate_daily_report(target_date=target_date)
        logger.info("✅ 日报生成任务已完成")
    except Exception as e:
        logger.error(f"❌ 日报生成失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

