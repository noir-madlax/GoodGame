from __future__ import annotations
from typing import Iterable, List, Optional
import logging
import requests

logger = logging.getLogger(__name__)

# 轻量级有效性校验：
# - 优先使用 HEAD
# - 若 HEAD 不允许或返回 405/403/4xx，但可能可直连，则尝试带 Range 的 GET（只取前 1 字节）
# - 认为有效的条件：HTTP 200/206，并且 Content-Type 看起来像视频或 application/octet-stream
# - 超时和错误都视为无效

_DEFAULT_TIMEOUT = 8  # seconds
_VIDEO_CT_KEYWORDS = (
    "video/",
    "application/octet-stream",
    "application/vnd.apple.mpegurl",
    "application/x-mpegURL",
)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/122.0.0.0 Safari/537.36"
    )
}


def _looks_like_media(content_type: Optional[str]) -> bool:
    if not content_type:
        # 某些直链不返回 CT，但仍可下载，略微放宽：允许 None 进入，只要状态码对
        return True
    ct = content_type.lower()
    return any(k in ct for k in _VIDEO_CT_KEYWORDS)


def _head_ok(url: str, timeout: int) -> bool:
    try:
        r = requests.head(url, headers=_DEFAULT_HEADERS, allow_redirects=True, timeout=timeout)
        if r.status_code in (200, 206):
            return _looks_like_media(r.headers.get("Content-Type"))
        # 有些源对 HEAD 返回 403/405，但 GET 可用
        return False
    except Exception:
        return False


def _range_get_ok(url: str, timeout: int) -> bool:
    try:
        headers = dict(_DEFAULT_HEADERS)
        headers["Range"] = "bytes=0-0"
        r = requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=timeout)
        if r.status_code in (200, 206):
            return _looks_like_media(r.headers.get("Content-Type"))
        return False
    except Exception:
        return False


def filter_valid_video_urls(urls: Iterable[Optional[str]], timeout: int = _DEFAULT_TIMEOUT) -> List[str]:
    """过滤可用的视频直链。

    参数:
      - urls: URL 可迭代，允许包含 None/空串
      - timeout: 单次请求超时秒数
    返回:
      - 仅包含验证通过的 URL 列表；若全无效则返回空列表
    """
    candidates: List[str] = []
    for u in urls or []:
        if isinstance(u, str) and u.strip():
            candidates.append(u.strip())

    valid: List[str] = []
    for u in candidates:
        if _head_ok(u, timeout) or _range_get_ok(u, timeout):
            valid.append(u)
    invalid_count = max(len(candidates) - len(valid), 0)
    logger.info("URL 有效性校验完成：输入=%d，判定无效=%d，有效=%d", len(candidates), invalid_count, len(valid))
    return valid

