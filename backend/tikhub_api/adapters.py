from __future__ import annotations
from typing import Protocol, Optional, Dict, Any, runtime_checkable
from datetime import datetime

from .orm.models import PlatformPost


@runtime_checkable
class VideoAdapter(Protocol):
    """将平台原始数据转换为统一领域模型 PlatformPost 的适配器协议。"""

    def to_post(self, details: Dict[str, Any]) -> PlatformPost:  # type: ignore[name-defined]
        ...


class DouyinVideoAdapter:
    """抖音视频数据 -> PlatformPost 适配器"""

    def to_post(self, details: Dict[str, Any]) -> PlatformPost:
        aweme_detail = details.get('aweme_detail', {}) or {}
        video = aweme_detail.get('video', {}) or {}
        statistics = aweme_detail.get('statistics', {}) or {}

        # 取封面
        cover_url = None
        for key in ('origin_cover', 'dynamic_cover', 'cover'):
            cover = video.get(key) or {}
            urls = cover.get('url_list') or []
            if urls:
                cover_url = urls[0]
                break

        # 取下载直链（可能有防盗链/重定向，仅作占位）
        download_addr = video.get('download_addr') or {}
        url_list = download_addr.get('url_list') or []
        video_url = url_list[0] if url_list else None

        # 发布时间（抖音可能返回 create_time: epoch 秒）
        published_at = None
        create_time = aweme_detail.get('create_time')
        if isinstance(create_time, (int, float)):
            try:
                published_at = datetime.fromtimestamp(create_time)
            except Exception:
                published_at = None

        return PlatformPost(
            platform="douyin",
            platform_item_id=str(aweme_detail.get('aweme_id', '')),
            title=str(aweme_detail.get('desc', '') or '').strip() or '无标题',
            content=None,
            play_count=int(statistics.get('play_count') or 0),
            like_count=int(statistics.get('digg_count') or 0),
            comment_count=int(statistics.get('comment_count') or 0),
            cover_url=cover_url,
            video_url=video_url,
            published_at=published_at,
        )


class XiaohongshuVideoAdapter:
    """小红书视频数据 -> PlatformPost 适配器"""

    def to_post(self, details: Dict[str, Any]) -> PlatformPost:
        note_detail = details.get('note_detail', {}) or {}
        video = note_detail.get('video', {}) or {}

        download_addr = video.get('download_addr') or {}
        url_list = download_addr.get('url_list') or []
        video_url = url_list[0] if url_list else None

        # 小红书的统计字段与发布时间可能需要额外拉取，这里先做兼容
        return PlatformPost(
            platform="xiaohongshu",
            platform_item_id=str(note_detail.get('note_id', '')),
            title=str(note_detail.get('title', '') or '').strip() or '无标题',
            content=str(note_detail.get('desc', '') or None) or None,
            play_count=0,
            like_count=0,
            comment_count=0,
            cover_url=None,
            video_url=video_url,
            published_at=None,
        )

