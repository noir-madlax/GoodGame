from __future__ import annotations
from typing import Protocol, Optional, Dict, Any, runtime_checkable, List
from datetime import datetime

from .orm.enums import Channel

from .orm.models import PlatformPost, PlatformComment, Author
from .orm import PostType
from .utils.url_validator import filter_valid_video_urls

from common.request_context import get_project_id
from jobs.logger import get_logger

log = get_logger(__name__)


# ===== 评论适配器协议 =====

@runtime_checkable
class CommentAdapter(Protocol):
    """将平台原始评论数据转换为统一领域模型 PlatformComment 的适配器协议。"""

    @staticmethod
    def to_comment(raw: Dict[str, Any], post_id: int) -> PlatformComment:
        """将单条原始评论转换为 PlatformComment"""
        ...

    @staticmethod
    def to_comment_list(raw_list: List[Dict[str, Any]], post_id: int) -> List[PlatformComment]:
        """将评论列表转换为 PlatformComment 列表"""
        ...

    @staticmethod
    def to_reply_list(raw_list: List[Dict[str, Any]], post_id: int, top_comment_id: str,
                      id_map: Dict[str, int]) -> List[PlatformComment]:
        """将楼中楼回复列表转换为 PlatformComment 列表"""
        ...

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

        # 调试日志：检查 details 和 aweme_detail 的内容
        if not aweme_detail:
            log.warning("[DouyinVideoAdapter] aweme_detail 为空，details keys: %s", list(details.keys()))

        # 兼容多种位置的 aweme_id，必要时回退到 group_id/id
        platform_item_id = (
            details.get('aweme_id')
            or aweme_detail.get('aweme_id')
            or (aweme_detail.get('statistics') or {}).get('aweme_id')
            or (aweme_detail.get('status') or {}).get('aweme_id')
            or details.get('group_id')
            or aweme_detail.get('group_id')
            or details.get('id')
            or aweme_detail.get('id')
        )

        # 调试日志：检查 platform_item_id 提取结果
        if not platform_item_id:
            log.error("[DouyinVideoAdapter] 无法提取 platform_item_id，aweme_detail keys: %s", list(aweme_detail.keys()) if aweme_detail else "None")

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
        # 现在存储所有有效的 URL，而不是只取第一个
        download_addr = video.get('download_addr') or {}
        url_list = download_addr.get('url_list') or []
        valid_urls = filter_valid_video_urls(url_list)
        video_url = valid_urls if valid_urls else None

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
        author_id = str(author.get('sec_uid') or '') or None
        author_name = str(author.get('nickname') or '') or None
        share_count = int((aweme_detail.get('statistics') or {}).get('share_count') or statistics.get('share_count') or 0)
        duration_ms = int(aweme_detail.get('duration') or 0)

        return PlatformPost(
            project_id=get_project_id(),
            platform="douyin",
            platform_item_id=platform_item_id,
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

        # 帖子类型：根据 type 字段判断（normal=图文, video=视频）
        note_type = str(raw.get("type") or "").lower()
        post_type = PostType.VIDEO if note_type == "video" else PostType.IMAGE

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
            # 存储所有有效的 URL
            video_url = valid_urls if valid_urls else None

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
            # 存储所有有效的 URL
            video_url = valid_urls if valid_urls else None

        # 提取图片列表（图文笔记）
        image_urls = None
        images = raw.get("images_list") or []
        if isinstance(images, list) and images:
            # 提取封面（第一张图）
            first = images[0] or {}
            if isinstance(first, dict):
                cover_url = first.get("url_size_large") or first.get("url") or first.get("original") or first.get("thumb")

            # 提取所有图片 URL（优先 url_size_large，其次 url，再次 original）
            img_candidates: List[str] = []
            for img in images:
                if not isinstance(img, dict):
                    continue
                # 优先级：url_size_large > url > original > thumb
                img_url = img.get("url_size_large") or img.get("url") or img.get("original") or img.get("thumb")
                if isinstance(img_url, str) and img_url.strip():
                    img_candidates.append(img_url.strip())

            # 过滤出有效的 HTTP/HTTPS URL
            if img_candidates:
                valid_img_urls = [
                    url for url in img_candidates
                    if url.lower().startswith(("http://", "https://"))
                ]
                image_urls = valid_img_urls if valid_img_urls else None

        # 封面兜底：若没有从图片列表获取到，尝试从视频字段兜底
        if not cover_url and isinstance(video.get("thumbnail_dim"), str):
            cover_url = video.get("thumbnail_dim")

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

        # 仅接受绝对 URL，避免 Pydantic 校验报错
        if isinstance(cover_url, str) and not cover_url.strip().lower().startswith(("http://", "https://")):
            cover_url = None
        # video_url 现在是列表，过滤掉非绝对 URL
        if isinstance(video_url, list):
            video_url = [
                url for url in video_url
                if isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))
            ]
            if not video_url:
                video_url = None

        return PlatformPost(
            project_id=get_project_id(),
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
            image_urls=image_urls,
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

        # 帖子类型：根据 type 字段判断（normal=图文, video=视频）
        note_type = str(raw.get("type") or "").lower()
        post_type = PostType.VIDEO if note_type == "video" else PostType.IMAGE

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
            # 存储所有有效的 URL
            video_url = valid_urls if valid_urls else None

            # 封面兜底（如 videoInfo 存在缩略图字段）
            for k in ("coverUrl", "thumbnail", "thumb", "poster"):
                if not cover_url and isinstance(video_info.get(k), str):
                    cover_url = video_info.get(k)

        # 提取图片列表（图文笔记）
        image_urls = None
        if isinstance(images_list, list) and images_list:
            # 提取封面（第一张图）
            if not cover_url:
                first = images_list[0] or {}
                if isinstance(first, dict):
                    cover_url = first.get("url_size_large") or first.get("url") or first.get("original") or first.get("thumb")

            # 提取所有图片 URL（优先 url_size_large，其次 url，再次 original）
            img_candidates: List[str] = []
            for img in images_list:
                if not isinstance(img, dict):
                    continue
                # 优先级：url_size_large > url > original > thumb
                img_url = img.get("url_size_large") or img.get("url") or img.get("original") or img.get("thumb")
                if isinstance(img_url, str) and img_url.strip():
                    img_candidates.append(img_url.strip())

            # 过滤出有效的 HTTP/HTTPS URL
            if img_candidates:
                valid_img_urls = [
                    url for url in img_candidates
                    if url.lower().startswith(("http://", "https://"))
                ]
                image_urls = valid_img_urls if valid_img_urls else None

        # 发布时间：优先 time.createTime (毫秒)，其次尝试顶层 createTime(字符串)忽略
        published_at = None
        t = raw.get("time") or {}
        ts = t.get("createTime")
        if isinstance(ts, (int, float)) and ts > 0:
            try:
                published_at = datetime.fromtimestamp(ts / 1000.0 if ts > 10**12 else ts)
            except Exception:
                published_at = None

        # 仅接受绝对 URL，避免 Pydantic 校验报错
        if isinstance(cover_url, str) and not cover_url.strip().lower().startswith(("http://", "https://")):
            cover_url = None
        # video_url 现在是列表，过滤掉非绝对 URL
        if isinstance(video_url, list):
            video_url = [
                url for url in video_url
                if isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))
            ]
            if not video_url:
                video_url = None

        return PlatformPost(
            project_id=get_project_id(),
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
            image_urls=image_urls,
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
            author_id=str(user.get('sec_uid', '') or ''),
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
                    author_id=str(user.get('sec_uid', '') or ''),
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


# ===== 作者适配器协议 =====

@runtime_checkable
class AuthorAdapter(Protocol):
    """将平台原始作者数据转换为统一领域模型 Author 的适配器协议。"""

    @staticmethod
    def to_author(raw: Dict[str, Any]) -> Author:
        """将单条原始作者数据转换为 Author"""
        ...


class DouyinAuthorAdapter:
    """抖音作者数据 -> Author 适配器"""

    @staticmethod
    def to_author(raw: Dict[str, Any]) -> Author:
        """
        将抖音作者原始报文转换为 Author 模型。
        兼容以下输入：
        - 顶层 response（含 data.user）
        - 仅 data 容器（含 user）
        - 直接 user 字典（含 uid/sec_uid/nickname 等）
        """
        if not isinstance(raw, dict):
            raise ValueError("raw 必须是字典类型")

        # 归一化：提取 user 字典
        user: Optional[Dict[str, Any]] = None
        u = raw.get('user') if isinstance(raw, dict) else None
        if isinstance(u, dict):
            user = u
        if user is None and isinstance(raw.get('data'), dict):
            data_obj = raw.get('data')
            if isinstance(data_obj.get('user'), dict):
                user = data_obj.get('user')  # type: ignore[assignment]
            elif isinstance(data_obj.get('data'), dict) and isinstance(data_obj.get('data').get('user'), dict):
                user = data_obj.get('data').get('user')  # type: ignore[assignment]
        if user is None and any(k in raw for k in ('uid', 'sec_uid', 'nickname')):
            user = raw  # type: ignore[assignment]
        if not isinstance(user, dict):
            raise ValueError("无法从传入数据中解析出抖音 user 对象")

        # 头像：优先使用 avatar_larger -> avatar_medium -> avatar_thumb -> avatar_300x300
        avatar_url = None
        for avatar_key in ('avatar_larger', 'avatar_medium', 'avatar_thumb', 'avatar_300x300'):
            avatar_obj = user.get(avatar_key) or {}
            if isinstance(avatar_obj, dict):
                url_list = avatar_obj.get('url_list') or []
                if url_list and isinstance(url_list, list):
                    # 优先选择 jpeg 格式的 URL
                    for url in url_list:
                        if isinstance(url, str) and '.jpeg' in url:
                            avatar_url = url
                            break
                    if not avatar_url and url_list:
                        avatar_url = url_list[0]
                    if avatar_url:
                        break

        # 分享链接
        share_url = None
        share_info = user.get('share_info') or {}
        if isinstance(share_info, dict):
            share_url_raw = share_info.get('share_url')
            if isinstance(share_url_raw, str) and share_url_raw:
                share_url = share_url_raw if share_url_raw.startswith('http') else f"https://{share_url_raw}"

        # 地理位置
        location = None
        ip_location = user.get('ip_location')
        if isinstance(ip_location, str) and ip_location:
            # 去掉 "IP属地：" 前缀
            location = ip_location.replace('IP属地：', '').strip()
        if not location:
            # 尝试其他位置字段
            for loc_key in ('location', 'city', 'province'):
                loc_val = user.get(loc_key)
                if isinstance(loc_val, str) and loc_val.strip():
                    location = loc_val.strip()
                    break

        # 认证信息：允许为 dict 或 str
        account_cert_info = user.get('account_cert_info')
        if isinstance(account_cert_info, dict):
            import json as _json
            account_cert_info = _json.dumps(account_cert_info, ensure_ascii=False)
        elif not isinstance(account_cert_info, str):
            account_cert_info = None

        return Author(
            platform=Channel.DOUYIN,
            platform_author_id=str(user.get('uid', '')),
            sec_uid=str(user.get('sec_uid', '') or ''),
            nickname=str(user.get('nickname', '') or ''),
            avatar_url=avatar_url,
            share_url=share_url,
            follower_count=int(user.get('follower_count') or 0),
            signature=str(user.get('signature', '') or '') or None,
            location=location,
            account_cert_info=account_cert_info,
            verification_type=int(user.get('verification_type') or 0),
            raw_response=user,
        )


class XiaohongshuAuthorAdapter:
    """小红书作者数据 -> Author 适配器

    适配多种原始形态：
    - 直接传入用户字典（含 userid/red_id 等）
    - 传入带有 user 字段的字典（如 data.user）
    - 传入 TikHub 顶层响应或 data 容器（如 response.data.data）
    该适配器会内部解析并规整为统一字段后再输出 Author。
    """

    @staticmethod
    def to_author(raw: Dict[str, Any]) -> Author:
        """将小红书作者信息转换为 Author 模型（在适配器内部抹平结构差异）"""
        if not isinstance(raw, Dict):  # type: ignore[arg-type]
            raise ValueError("raw 必须是字典类型")

        # 1) 归一化：从可能的多种层级中提取到“用户字典” user
        user: Optional[Dict[str, Any]] = None

        # a. 顶层就有 user
        u = raw.get("user") if isinstance(raw, dict) else None
        if isinstance(u, dict):
            user = u

        # b. 顶层的 data 容器
        if user is None:
            data_obj = raw.get("data") if isinstance(raw, dict) else None
            if isinstance(data_obj, dict):
                # data.user
                if isinstance(data_obj.get("user"), dict):
                    user = data_obj.get("user")  # type: ignore[assignment]
                # data.data（TikHub 小红书 user_info 的用户体直挂在这里）
                inner = data_obj.get("data")
                if user is None and isinstance(inner, dict):
                    # 通过关键字段判断像不像用户对象
                    if any(k in inner for k in ("userid", "red_id", "nickname", "images", "imageb")):
                        user = inner  # type: ignore[assignment]

        # c. 若原对象本身看起来就是用户对象
        if user is None and isinstance(raw, dict):
            if any(k in raw for k in ("userid", "red_id", "nickname", "images", "imageb")):
                user = raw

        # d. 兜底：data 看起来像用户对象
        if user is None and isinstance(raw.get("data"), dict):
            data_obj2 = raw.get("data")
            if any(k in data_obj2 for k in ("userid", "red_id", "nickname")):
                user = data_obj2  # type: ignore[assignment]

        if not isinstance(user, dict):
            raise ValueError("无法从传入数据中解析出小红书用户对象")

        # 2) 字段映射
        # 头像：优先大图 imageb，其次 images
        avatar_url = None
        for k in ("imageb", "images"):
            v = user.get(k)
            if isinstance(v, str) and v.strip():
                avatar_url = v.strip()
                break

        # 主页分享链接
        share_url = None
        share_link = user.get("share_link")
        if isinstance(share_link, str) and share_link.strip():
            share_url = share_link.strip()

        # 粉丝数：优先 fans 字段；回落到 interactions 中 type=="fans" 或 name=="粉丝"
        follower_count = 0
        fans_val = user.get("fans")
        if isinstance(fans_val, (int, float)):
            follower_count = int(fans_val)
        else:
            interactions = user.get("interactions") or []
            if isinstance(interactions, list):
                for it in interactions:
                    if not isinstance(it, dict):
                        continue
                    t = str(it.get("type") or "").lower()
                    n = str(it.get("name") or "")
                    if t == "fans" or n == "粉丝":
                        c = it.get("count")
                        if isinstance(c, (int, float)):
                            follower_count = int(c)
                            break

        # 个性签名
        signature = None
        desc_val = user.get("desc")
        if isinstance(desc_val, str) and desc_val.strip():
            signature = desc_val.strip()
        else:
            user_desc_info = user.get("user_desc_info") or {}
            if isinstance(user_desc_info, dict):
                d = user_desc_info.get("desc")
                if isinstance(d, str) and d.strip():
                    signature = d.strip()

        # 位置：优先 ip_location，其次 location
        location = None
        ip_loc = user.get("ip_location")
        if isinstance(ip_loc, str) and ip_loc.strip():
            location = ip_loc.strip()
        else:
            loc = user.get("location")
            if isinstance(loc, str) and loc.strip():
                location = loc.strip()

        # 认证信息：整理为 JSON 字符串
        account_cert_info = None
        try:
            import json as _json
            cert = {
                "red_official_verified": bool(user.get("red_official_verified")),
                "red_official_verify_type": user.get("red_official_verify_type"),
                "red_official_verify_content": user.get("red_official_verify_content"),
            }
            account_cert_info = _json.dumps(cert, ensure_ascii=False)
        except Exception:
            account_cert_info = None

        # 认证类型：映射到统一字段 verification_type
        verification_type = None
        vt = user.get("red_official_verify_type")
        if isinstance(vt, (int, float)):
            verification_type = int(vt)

        # 基础 ID/昵称
        platform_author_id = str(user.get("userid") or user.get("red_id") or "")
        if not platform_author_id:
            raise ValueError("缺少必要的 userid/red_id 作为平台作者 ID")
        nickname = user.get("nickname")
        nickname = str(nickname).strip() if isinstance(nickname, str) else None

        return Author(
            platform=Channel.XIAOHONGSHU,
            platform_author_id=platform_author_id,
            sec_uid=None,
            nickname=nickname,
            avatar_url=avatar_url,
            share_url=share_url,
            follower_count=follower_count,
            signature=signature,
            location=location,
            account_cert_info=account_cert_info,
            verification_type=verification_type,
            raw_response=user,
        )


class XiaohongshuCommentAdapter:
    """小红书评论数据 -> PlatformComment 适配器"""

    @staticmethod
    def to_comment(raw: Dict[str, Any], post_id: int) -> PlatformComment:
        """将小红书单条评论转换为 PlatformComment

        小红书评论结构示例（来自 /api/v1/xiaohongshu/app/get_note_comments）：
        {
            "id": "68ca3d92000000000b0177c7",
            "content": "我靠我正在体检，费用都交了…[石化R]",
            "time": 1758084499,  # 秒级时间戳
            "like_count": 0,
            "sub_comment_count": 7,
            "sub_comment_cursor": "{\"cursor\":\"...\",\"index\":1}",
            "user": {
                "userid": "605a02d3000000000101f12d",
                "nickname": "胡八一爱倒斗",
                "images": "https://...",
                "red_id": "2656540724"
            },
            "ip_location": "河南",
            "status": 0
        }
        """
        user = raw.get('user') or {}

        # 小红书时间戳是秒级
        published_at = None
        ts = raw.get('time')
        if isinstance(ts, (int, float)):
            try:
                published_at = datetime.fromtimestamp(ts)
            except Exception:
                published_at = None

        return PlatformComment(
            post_id=post_id,
            platform="xiaohongshu",
            platform_comment_id=str(raw.get('id', '')),
            parent_comment_id=None,
            parent_platform_comment_id=None,
            author_id=str(user.get('userid', '') or ''),
            author_name=str(user.get('nickname', '') or ''),
            author_avatar_url=user.get('images') or '',
            content=str(raw.get('content', '') or ''),
            like_count=int(raw.get('like_count') or 0),
            reply_count=int(raw.get('sub_comment_count') or 0),
            published_at=published_at,
        )

    @staticmethod
    def to_comment_list(raw_list: List[Dict[str, Any]], post_id: int) -> List[PlatformComment]:
        out: List[PlatformComment] = []
        for raw in (raw_list or []):
            try:
                out.append(XiaohongshuCommentAdapter.to_comment(raw, post_id))
            except Exception:
                continue
        return out

    @staticmethod
    def to_reply_list(raw_list: List[Dict[str, Any]], post_id: int, top_comment_id: str,
                      id_map: Dict[str, int]) -> List[PlatformComment]:
        """将小红书楼中楼回复列表映射为 PlatformComment

        小红书子评论结构示例（从顶层评论的 sub_comments 字段获取）：
        {
            "id": "68ca3dca0000000002000609",
            "content": "我面的大张长申国际店安保岗位，不知道咋样",
            "time": 1758084555,
            "like_count": 0,
            "user": {
                "userid": "605a02d3000000000101f12d",
                "nickname": "胡八一爱倒斗",
                "images": "https://..."
            },
            "target_comment": {
                "id": "68ca3d92000000000b0177c7",  # 被回复的评论ID
                "user": {...}
            }
        }
        """
        out: List[PlatformComment] = []
        for raw in (raw_list or []):
            try:
                user = raw.get('user') or {}

                published_at = None
                ts = raw.get('time')
                if isinstance(ts, (int, float)):
                    try:
                        published_at = datetime.fromtimestamp(ts)
                    except Exception:
                        published_at = None

                comment_id = str(raw.get('id', ''))

                # 确定父评论ID
                target_comment = raw.get('target_comment') or {}
                target_id = str(target_comment.get('id', '') or '')

                # 如果没有 target_id 或 target_id 等于顶层评论ID，则父评论是顶层评论
                if not target_id or target_id == top_comment_id:
                    parent_platform_cid = top_comment_id
                else:
                    parent_platform_cid = target_id

                parent_db_id = id_map.get(parent_platform_cid)

                out.append(PlatformComment(
                    post_id=post_id,
                    platform="xiaohongshu",
                    platform_comment_id=comment_id,
                    parent_comment_id=parent_db_id,
                    parent_platform_comment_id=parent_platform_cid,
                    author_id=str(user.get('userid', '') or ''),
                    author_name=str(user.get('nickname', '') or ''),
                    author_avatar_url=user.get('images') or '',
                    content=str(raw.get('content', '') or ''),
                    like_count=int(raw.get('like_count') or 0),
                    reply_count=int(raw.get('sub_comment_count') or 0),
                    published_at=published_at,
                ))
            except Exception:
                continue
        return out
