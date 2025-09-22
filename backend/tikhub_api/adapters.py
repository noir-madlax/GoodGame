from __future__ import annotations
from typing import Protocol, Optional, Dict, Any, runtime_checkable, List
from datetime import datetime

from backend.tikhub_api.orm.enums import Channel

from .orm.models import PlatformPost, PlatformComment
from .orm import PostType
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
    def hi() -> str:
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
        post_type = PostType.VIDEO  # 抖音此接口以视频为主，后续如检测到图文可调整
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

    def to_post_single(self, details: Dict[str, Any]) -> PlatformPost:
        """
        单条/批量对抖音是兼容的，这里直接复用 to_post。
        """
        return self.to_post(details)


class XiaohongshuVideoAdapter:
    """小红书视频数据 -> PlatformPost 适配器（兼容 web_v2/fetch_feed_notes_v2 与 app/search_notes）"""

    def to_post(self, details: Dict[str, Any]) -> PlatformPost:
        # details 既可能是 web_v2 的 note_list[0]，也可能是 app/search_notes 的 note 对象
        raw = details or {}

        note_id = str(raw.get("id") or "")
        title = str(raw.get("title") or "").strip() or "无标题"
        content = raw.get("desc") or None

        # 原始分享链接（可能不存在于搜索结果）
        original_url = None
        share_info = raw.get("share_info") or {}
        if isinstance(share_info.get("link"), str) and share_info.get("link"):
            original_url = share_info.get("link")
        elif isinstance((raw.get("mini_program_info") or {}).get("webpage_url"), str):
            original_url = (raw.get("mini_program_info") or {}).get("webpage_url")

        # 作者信息
        user = raw.get("user") or {}
        author_id = str(user.get("userid") or user.get("id") or "") or None
        author_name = user.get("nickname") or user.get("name") or None

        # 互动数据
        play_count = int(raw.get("view_count") or 0)  # 搜索页通常没有播放量
        like_count = int(raw.get("liked_count") or 0)
        comment_count = int(raw.get("comments_count") or 0)
        share_count = int(raw.get("shared_count") or 0)

        # 解析视频/时长/封面
        video = raw.get("video") or {}
        video_info_v2 = raw.get("video_info_v2") or {}
        duration_ms = 0
        video_url = None
        cover_url = None

        # 优先从 app/search_notes 的 video_info_v2 中取（含多码率）
        if isinstance(video_info_v2, dict) and video_info_v2.get("media"):
            media = video_info_v2.get("media") or {}
            inner_video = media.get("video") or {}
            duration_val = inner_video.get("duration")
            if isinstance(duration_val, (int, float)):
                duration_ms = int(duration_val * 1000)

            # 组装候选直链（master_url 与 backup_urls）
            candidates: List[str] = []
            stream = media.get("stream") or {}
            for key in ("h264", "h265", "av1", "h266"):
                arr = stream.get(key) or []
                if isinstance(arr, list):
                    for it in arr:
                        if not isinstance(it, dict):
                            continue
                        url = it.get("master_url") or it.get("main_url") or it.get("url")
                        if isinstance(url, str) and url:
                            candidates.append(url)
                        backs = it.get("backup_urls") or []
                        if isinstance(backs, list):
                            for b in backs:
                                if isinstance(b, str) and b:
                                    candidates.append(b)
            valid_urls = filter_valid_video_urls(candidates)
            video_url = valid_urls[0] if valid_urls else None

        # 回落到 web_v2 结构：video.url_info_list / video.url
        if not video_url:
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

        # 封面：优先图文首图；若没有尝试从视频字段兜底
        images = raw.get("images_list") or []
        if isinstance(images, list) and images:
            first = images[0] or {}
            cover_url = first.get("url") or first.get("url_size_large") or first.get("original") or first.get("thumb")
        if not cover_url and isinstance(video.get("thumbnail_dim"), str):
            cover_url = video.get("thumbnail_dim")

        # 帖子类型：仅保留两类：video / image
        post_type = PostType.VIDEO if (video_info_v2 or video) else PostType.IMAGE

        # 发布时间：兼容 timestamp(秒)/time(秒)/update_time(毫秒)
        published_at = None
        ts = raw.get("timestamp") or raw.get("time") or raw.get("update_time")
        if isinstance(ts, (int, float)) and ts > 0:
            try:
                if ts > 10**12:  # 毫秒
                    published_at = datetime.fromtimestamp(ts / 1000.0)
                else:
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

    def to_post_single(self, details: Dict[str, Any]) -> PlatformPost:
        """将 /api/v1/xiaohongshu/app/get_note_info_v2 的 data.data 映射为 PlatformPost。
        典型结构字段（例）：
        - noteId, noteLink, userId
        - title, content, imagesList
        - videoInfo(可为 null)
        - time.createTime (毫秒)
        - likeNum, cmtNum, readNum/impNum, shareNum
        - userInfo.nickName/userId
        """
        raw = details or {}

        # 基本字段
        note_id = str(raw.get("noteId") or raw.get("id") or "")
        title = str(raw.get("title") or "").strip() or "无标题"
        content = raw.get("content") or None

        # 原始链接
        original_url = None
        if isinstance(raw.get("noteLink"), str) and raw.get("noteLink"):
            original_url = raw.get("noteLink")

        # 作者信息
        user_info = raw.get("userInfo") or {}
        author_id = str(user_info.get("userId") or raw.get("userId") or "") or None
        author_name = user_info.get("nickName") or raw.get("name") or None

        # 互动与计数
        play_count = int(raw.get("readNum") or raw.get("impNum") or 0)
        like_count = int(raw.get("likeNum") or 0)
        comment_count = int(raw.get("cmtNum") or 0)
        share_count = int(raw.get("shareNum") or 0)

        # 媒体信息
        video_info = raw.get("videoInfo") or {}
        images_list = raw.get("imagesList") or raw.get("images_list") or []

        duration_ms = 0
        video_url = None
        cover_url = None

        # 尝试从 videoInfo 中提取时长/直链（结构不稳定，尽量兼容）
        if isinstance(video_info, dict) and video_info:
            # duration: 可能为秒或毫秒
            dur = video_info.get("duration")
            if isinstance(dur, (int, float)):
                try:
                    duration_ms = int(dur if dur > 10**6 else dur * 1000)
                except Exception:
                    duration_ms = 0

            candidates: List[str] = []
            media = video_info.get("media") or {}
            stream = (media.get("stream") or {}) if isinstance(media, dict) else {}
            if isinstance(stream, dict):
                for key in ("h264", "h265", "av1", "h266"):
                    arr = stream.get(key) or []
                    if isinstance(arr, list):
                        for it in arr:
                            if not isinstance(it, dict):
                                continue
                            url = it.get("master_url") or it.get("main_url") or it.get("url")
                            if isinstance(url, str) and url:
                                candidates.append(url)
                            backs = it.get("backup_urls") or []
                            if isinstance(backs, list):
                                for b in backs:
                                    if isinstance(b, str) and b:
                                        candidates.append(b)
            # 一些实现直接挂在 videoInfo 上
            for k in ("master_url", "main_url", "url"):
                u = video_info.get(k)
                if isinstance(u, str) and u:
                    candidates.append(u)

            valid_urls = filter_valid_video_urls(candidates)
            video_url = valid_urls[0] if valid_urls else None

            # 封面兜底（如 videoInfo 存在缩略图字段）
            for k in ("coverUrl", "thumbnail", "thumb", "poster"):
                if not cover_url and isinstance(video_info.get(k), str):
                    cover_url = video_info.get(k)

        # 封面优先用首图；若没有再用上面 videoInfo 兜底
        if not cover_url and isinstance(images_list, list) and images_list:
            first = images_list[0] or {}
            if isinstance(first, dict):
                cover_url = first.get("url") or first.get("original") or first.get("thumb")

        # 帖子类型：videoInfo 存在则视为视频，否则为图文
        post_type = PostType.VIDEO if (isinstance(video_info, dict) and video_info) else PostType.IMAGE

        # 发布时间：优先 time.createTime (毫秒)，其次尝试顶层 createTime(字符串)忽略
        published_at = None
        t = raw.get("time") or {}
        ts = t.get("createTime")
        if isinstance(ts, (int, float)) and ts > 0:
            try:
                published_at = datetime.fromtimestamp(ts / 1000.0 if ts > 10**12 else ts)
            except Exception:
                published_at = None

        return PlatformPost(
            platform=Channel.XIAOHONGSHU,
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
