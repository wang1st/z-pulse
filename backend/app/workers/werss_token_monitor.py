#!/usr/bin/env python3
"""
WeRSS Token监控Worker

定期检查微信公众号token状态，在即将过期时发送提醒邮件
建议：每天运行一次（通过cron或celery beat）
"""
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from shared.utils import get_logger
from backend.app.services.werss_monitor import monitor_tokens

logger = get_logger("werss-token-monitor-worker")


def run_monitor():
    """执行一次监控检查"""
    logger.info("=" * 60)
    logger.info("WeRSS Token Monitor Worker Started")
    logger.info(f"Time: {datetime.now().isoformat()}")

    try:
        expiring_count = monitor_tokens()

        if expiring_count > 0:
            logger.warning(f"⚠️ Found {expiring_count} tokens expiring soon, alerts sent")
        else:
            logger.info("✅ All tokens are healthy, no alerts needed")

        return expiring_count

    except Exception as e:
        logger.exception(f"Error in token monitor: {e}")
        return -1


def main():
    """Main函数"""
    import argparse

    parser = argparse.ArgumentParser(description="WeRSS Token Monitor Worker")
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (default)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=3600,
        help='Interval in seconds for continuous mode (default: 3600)'
    )

    args = parser.parse_args()

    if args.once or True:  # 默认运行一次
        logger.info("Running in single-shot mode")
        expiring_count = run_monitor()
        sys.exit(0 if expiring_count >= 0 else 1)
    else:
        # 持续模式（用于开发测试）
        logger.info(f"Running in continuous mode, interval: {args.interval}s")
        try:
            while True:
                run_monitor()
                logger.info(f"Sleeping for {args.interval} seconds...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            sys.exit(0)


if __name__ == "__main__":
    main()
