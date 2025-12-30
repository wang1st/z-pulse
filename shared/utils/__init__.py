"""
工具函数模块
"""
from .logger import get_logger
from .redis_client import get_redis_client

# MinIO客户端（可选，仅在需要时导入）
try:
    from .minio_client import get_minio_client
    __all__ = [
        "get_logger",
        "get_redis_client",
        "get_minio_client",
    ]
except ImportError:
    # MinIO未安装时，提供一个占位函数
    def get_minio_client():
        raise ImportError("minio package is not installed. Install it with: pip install minio")
    
    __all__ = [
        "get_logger",
        "get_redis_client",
        "get_minio_client",
    ]

