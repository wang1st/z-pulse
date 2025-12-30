"""
日志工具
"""
import sys
import os
from pathlib import Path
from loguru import logger

from ..config import settings


def get_logger(name: str):
    """
    获取logger实例
    
    Args:
        name: logger名称
    
    Returns:
        logger实例
    """
    # 只在首次调用时配置 handler，避免多次 get_logger() 互相 remove 导致日志丢失
    if not getattr(get_logger, "_configured", False):
        # 移除默认handler
        logger.remove()

        # 根据配置添加 stdout handler
        if settings.LOG_FORMAT == "json":
            logger.add(
                sys.stdout,
                format="{time} | {level} | {name}:{function}:{line} | {message}",
                level=settings.LOG_LEVEL,
                serialize=True,
            )
        else:
            logger.add(
                sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
                level=settings.LOG_LEVEL,
                colorize=True,
            )

        # 选择日志目录：
        # - 优先使用 LOG_DIR 环境变量
        # - 其次使用项目根目录下的 backend/logs（本仓库约定）
        # - 最后回退到 ./logs
        project_root = Path(__file__).resolve().parents[2]
        env_log_dir = os.getenv("LOG_DIR")
        if env_log_dir:
            log_dir = Path(env_log_dir)
        else:
            candidate = project_root / "backend" / "logs"
            log_dir = candidate if candidate.exists() else (project_root / "logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # 添加文件 handler（按 logger name 分文件）
        logger.add(
            str(log_dir / f"{name}.log"),
            rotation="500 MB",
            retention="10 days",
            level=settings.LOG_LEVEL,
            compression="zip",
        )

        get_logger._configured = True
    
    return logger.bind(name=name)

