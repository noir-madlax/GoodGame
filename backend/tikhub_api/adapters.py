from __future__ import annotations
from typing import Protocol, Optional, Dict, Any, runtime_checkable, List
from datetime import datetime

from .orm.models import PlatformPost, PlatformComment
from .utils.url_validator import filter_valid_video_urls

# ===== 搜索结果 -> PlatformPost 列表适配器 =====

def to_posts_from_douyin_search(data: Dict[str, Any]) -> List[PlatformPost]:
    """
    将抖音搜索结果 data 转为 PlatformPost 列表。
    兼容以下结构：
    - 顶层 code=200, data={ status_code, data=[...] }
    - 直接传入 data={ status_code, data=[...] }
    - 直接传入 { data=[...] } 或 { aweme_list=[...] } 或 { items=[...] }
    仅处理 type==1（视频）。
    """
    out: List[PlatformPost] = []
    if not isinstance(data, dict):
        return out

    # 解析到最终的 items 列表（容错多种路径）
    items = None
    try:
        if isinstance(data.get("data"), dict) and isinstance(data["data"].get("data"), list):
            items = data["data"]["data"]
        elif isinstance(data.get("status_code"), (int, float)) and isinstance(data.get("data"), list):
            items = data["data"]
        elif isinstance(data.get("data"), list):
            items = data["data"]
        elif isinstance(data.get("aweme_list"), list):
            items = data["aweme_list"]
        elif isinstance(data.get("items"), list):
            items = data["items"]
    except Exception:
        items = None

    if not isinstance(items, list):
        return out

    adapter = DouyinVideoAdapter()
    for it in items:
        try:
            if not isinstance(it, dict):
                continue
            if int(it.get("type") or 0) != 1:
                continue
            aweme = it.get("aweme_info") or {}
            if not isinstance(aweme, dict):
                continue
            details_like = {"aweme_detail": aweme}
            post = adapter.to_post(details_like)
            # 保存原始以便弹幕/排查
            post.raw_details = details_like
            out.append(post)
        except Exception:
            continue
    return out


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

        # 取下载直链，并校验可用性（某些链接可能无法实际下载）
        download_addr = video.get('download_addr') or {}
        url_list = download_addr.get('url_list') or []
        valid_urls = filter_valid_video_urls(url_list)
        video_url = valid_urls[0] if valid_urls else None

        # 发布时间（抖音可能返回 create_time: epoch 秒）
        published_at = None
        create_time = aweme_detail.get('create_time')
        if isinstance(create_time, (int, float)):
            try:
                published_at = datetime.fromtimestamp(create_time)
            except Exception:
                published_at = None

        # 新增字段映射
        post_type = "video"  # 抖音此接口以视频为主，后续如检测到图文可调整
        original_url = aweme_detail.get('share_url') or (aweme_detail.get('share_info') or {}).get('share_url')
        author = aweme_detail.get('author', {}) or {}
        author_id = str(author.get('uid') or '') or None
        author_name = str(author.get('nickname') or '') or None
        share_count = int((aweme_detail.get('statistics') or {}).get('share_count') or statistics.get('share_count') or 0)
        duration_ms = int(aweme_detail.get('duration') or 0)

        return PlatformPost(
            platform="douyin",
            platform_item_id=str(aweme_detail.get('aweme_id', '')),
            title=str(aweme_detail.get('desc', '') or '').strip() or '无标题',
            content=None,
            post_type=post_type,
            original_url=original_url,
            author_id=author_id,
            author_name=author_name,
            share_count=share_count,
            duration_ms=duration_ms,
            play_count=int(statistics.get('play_count') or 0),
            like_count=int(statistics.get('digg_count') or 0),
            comment_count=int(statistics.get('comment_count') or 0),
            cover_url=cover_url,
            video_url=video_url,
            raw_details=details,
            published_at=published_at,
        )


class XiaohongshuVideoAdapter:
    """小红书视频数据 -> PlatformPost 适配器（适配 web_v2/fetch_feed_notes_v2）"""

    def to_post(self, details: Dict[str, Any]) -> PlatformPost:
        # details 为 XiaohongshuFetcher.get_video_details 返回的 note_list[0]
        raw = details or {}

        note_id = str(raw.get("id") or "")
        title = str(raw.get("title") or "").strip() or "无标题"
        content = raw.get("desc") or None
        post_type = str(raw.get("type") or "").lower() or ("video" if raw.get("video") else "image")
        original_url = None
        # 可从 share_info.link / mini_program_info/webpage_url 取分享链接
        share_info = raw.get("share_info") or {}
        if isinstance(share_info.get("link"), str) and share_info.get("link"):
            original_url = share_info.get("link")
        elif isinstance((raw.get("mini_program_info") or {}).get("webpage_url"), str):
            original_url = (raw.get("mini_program_info") or {}).get("webpage_url")

        user = raw.get("user") or {}
        author_id = str(user.get("userid") or user.get("id") or "") or None
        author_name = user.get("nickname") or user.get("name") or None

        play_count = int(raw.get("view_count") or 0)  # 有些返回为 0
        like_count = int(raw.get("liked_count") or 0)
        comment_count = int(raw.get("comments_count") or 0)
        share_count = int(raw.get("shared_count") or 0)

        video = raw.get("video") or {}
        duration_val = video.get("duration")
        duration_ms = int(duration_val * 1000) if isinstance(duration_val, (int, float)) else 0

        # 取视频直链：优先 url_info_list，并进行可用性校验
        video_url = None
        candidates: List[str] = []
        url_info_list = video.get("url_info_list") or []
        if isinstance(url_info_list, list) and url_info_list:
            for it in url_info_list:
                if isinstance(it, dict) and isinstance(it.get("url"), str) and it.get("url"):
                    candidates.append(it.get("url"))
        if isinstance(video.get("url"), str) and video.get("url"):
            candidates.append(video.get("url"))
        valid_urls = filter_valid_video_urls(candidates)
        video_url = valid_urls[0] if valid_urls else None

        # 取封面
        cover_url = None
        images = raw.get("images_list") or []
        if isinstance(images, list) and images:
            first = images[0] or {}
            # web_v2 返回的图片字段
            cover_url = first.get("url") or first.get("original") or first.get("thumb")
        if not cover_url and isinstance(video.get("thumbnail_dim"), str):
            cover_url = video.get("thumbnail_dim")

        # 发布时间（time 为 epoch 秒）
        published_at = None
        ts = raw.get("time")
        if isinstance(ts, (int, float)) and ts > 0:
            try:
                published_at = datetime.fromtimestamp(ts)
            except Exception:
                published_at = None

        return PlatformPost(
            platform="xiaohongshu",
            platform_item_id=note_id,
            title=title,
            content=content,
            post_type=post_type,
            original_url=original_url,
            author_id=author_id,
            author_name=author_name,
            share_count=share_count,
            duration_ms=duration_ms,
            play_count=play_count,
            like_count=like_count,
            comment_count=comment_count,
            cover_url=cover_url,
            video_url=video_url,
            raw_details=details,
            published_at=published_at,
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
