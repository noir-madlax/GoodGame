from __future__ import annotations
from typing import Protocol, Optional, Dict, Any, runtime_checkable, List
from datetime import datetime

from .orm.models import PlatformPost, PlatformComment


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

class DouyinCommentAdapter:
    """抖音评论数据 -> PlatformComment 适配器"""

    @staticmethod
    def to_comment(raw: Dict[str, Any], post_id: int) -> PlatformComment:
        user = (raw.get('user') or {})
        avatar = (user.get('avatar_thumb') or {})
        url_list = avatar.get('url_list') or []
        avatar_url = url_list[0] if url_list else None

        published_at = None
        ts = raw.get('create_time')
        if isinstance(ts, (int, float)):
            try:
                published_at = datetime.fromtimestamp(ts)
            except Exception:
                published_at = None

        return PlatformComment(
            post_id=post_id,
            platform="douyin",
            platform_comment_id=str(raw.get('cid', '')),
            parent_comment_id=None,
            parent_platform_comment_id=None,
            author_id=str(user.get('uid', '') or ''),
            author_name=str(user.get('nickname', '') or ''),
            author_avatar_url=avatar_url,
            content=str(raw.get('text', '') or ''),
            like_count=int(raw.get('digg_count') or 0),
            reply_count=int(raw.get('reply_comment_total') or 0),
            published_at=published_at,
        )

    @staticmethod
    def to_comment_list(raw_list: List[Dict[str, Any]], post_id: int) -> List[PlatformComment]:
        out: List[PlatformComment] = []
        for raw in (raw_list or []):
            try:
                out.append(DouyinCommentAdapter.to_comment(raw, post_id))
            except Exception:
                continue
        return out

    @staticmethod
    def to_reply_list(raw_list: List[Dict[str, Any]], post_id: int, top_cid: str,
                      id_map: Dict[str, int]) -> List[PlatformComment]:
        """将楼中楼回复列表映射为 PlatformComment，并尽力绑定父级关系。
        - parent_platform_comment_id: 对 "0" 使用顶层 cid；否则用 reply_to_reply_id
        - parent_comment_id: 如果 id_map 里已经有父，则绑定；否则置 None，后续再补
        """
        out: List[PlatformComment] = []
        for raw in (raw_list or []):
            try:
                user = (raw.get('user') or {})
                avatar = (user.get('avatar_thumb') or {})
                url_list = avatar.get('url_list') or []
                avatar_url = url_list[0] if url_list else None

                published_at = None
                ts = raw.get('create_time')
                if isinstance(ts, (int, float)):
                    try:
                        published_at = datetime.fromtimestamp(ts)
                    except Exception:
                        published_at = None

                cid = str(raw.get('cid', ''))
                reply_to_reply_id = str(raw.get('reply_to_reply_id', '') or '0')
                parent_platform_cid = top_cid if reply_to_reply_id == '0' else reply_to_reply_id
                parent_db_id = id_map.get(parent_platform_cid)

                out.append(PlatformComment(
                    post_id=post_id,
                    platform="douyin",
                    platform_comment_id=cid,
                    parent_comment_id=parent_db_id,
                    parent_platform_comment_id=parent_platform_cid,
                    author_id=str(user.get('uid', '') or ''),
                    author_name=str(user.get('nickname', '') or ''),
                    author_avatar_url=avatar_url,
                    content=str(raw.get('text', '') or ''),
                    like_count=int(raw.get('digg_count') or 0),
                    reply_count=int(raw.get('comment_reply_total') or 0),
                    published_at=published_at,
                ))
            except Exception:
                continue
        return out
