"""
视频获取器模块
包含所有平台的视频获取器实现和工厂类
"""

# 基础组件
from .base_fetcher import BaseFetcher

# 平台特定获取器
from .douyin_video_fetcher import DouyinVideoFetcher, fetch_douyin_video
from .xiaohongshu_fetcher import XiaohongshuFetcher, fetch_xiaohongshu_video

# 工厂模式组件
from .fetcher_factory import (
    FetcherFactory,
    Platform,
    create_fetcher,
    get_supported_platforms,
)

__all__ = [
    # 基础组件
    'BaseFetcher',
    
    # 平台特定获取器
    'DouyinVideoFetcher',
    'fetch_douyin_video',
    'XiaohongshuFetcher', 
    'fetch_xiaohongshu_video',
    
    # 工厂模式组件
    'FetcherFactory',
    'Platform',
    'create_fetcher',
    'get_supported_platforms',
]
