"""
TikHub API 客户端包
用于调用 TikHub 的各种 API 接口
支持多平台视频获取和下载
"""

# 视频下载组件
from .video_downloader import VideoDownloader, download_video_from_url

# 获取器模块 - 从 fetchers 子包导入
from .fetchers import (
    # 基础组件
    BaseFetcher,

    # 平台特定获取器
    DouyinVideoFetcher,
    fetch_douyin_video,
    XiaohongshuFetcher,
    fetch_xiaohongshu_video,

    # 工厂模式组件
    FetcherFactory,
    Platform,
    create_fetcher,
    get_supported_platforms,
)

# 工作流组件（避免导入循环，此处不直接导出 workflow 内符号）

__all__ = [
    # 基础组件
    'BaseFetcher',
    'VideoDownloader',
    'download_video_from_url',

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
