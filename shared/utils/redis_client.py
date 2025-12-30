"""
Redis客户端
"""
import redis
from typing import Optional

from ..config import settings


_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    获取Redis客户端（单例模式）
    
    Returns:
        Redis客户端实例
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    
    return _redis_client


def close_redis_client():
    """关闭Redis客户端"""
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None

