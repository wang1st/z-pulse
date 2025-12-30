"""
采集器模块
"""
from .base import BaseCollector
from .wechat import WechatCollector
from .rss import RSSCollector
from .web import WebCollector

__all__ = [
    "BaseCollector",
    "WechatCollector",
    "RSSCollector",
    "WebCollector",
]

