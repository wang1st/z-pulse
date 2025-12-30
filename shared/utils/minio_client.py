"""
MinIO客户端（可选）
"""
from typing import Optional

try:
    from minio import Minio
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    Minio = None  # type: ignore

from ..config import settings


_minio_client: Optional[Minio] = None


def get_minio_client() -> Minio:
    """
    获取MinIO客户端（单例模式）
    
    Returns:
        MinIO客户端实例
    
    Raises:
        ImportError: 如果minio包未安装
    """
    if not MINIO_AVAILABLE:
        raise ImportError("minio package is not installed. Install it with: pip install minio")
    
    global _minio_client
    
    if _minio_client is None:
        _minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        
        # 确保bucket存在
        if not _minio_client.bucket_exists(settings.MINIO_BUCKET):
            _minio_client.make_bucket(settings.MINIO_BUCKET)
    
    return _minio_client

