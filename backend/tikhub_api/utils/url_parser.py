from __future__ import annotations

import re
from typing import Optional, Tuple
from tikhub_api.orm.enums import Channel


DOUYIN_PATTERNS = [
    # https://www.douyin.com/video/7499608775142608186
    re.compile(r"https?://(?:www\.)?douyin\.com/(?:video|note)/(\d+)", re.IGNORECASE),
    # https://www.iesdouyin.com/share/video/7499608775142608186
    re.compile(r"https?://(?:www\.)?iesdouyin\.com/share/(?:video|item)/(\d+)", re.IGNORECASE),
]

XHS_PATTERNS = [
    # https://www.xiaohongshu.com/explore/{note_id}
    re.compile(r"https?://(?:www\.)?xiaohongshu\.com/explore/([0-9A-Za-z]+)", re.IGNORECASE),
    # https://www.xiaohongshu.com/discovery/item/{note_id}
    re.compile(r"https?://(?:www\.)?xiaohongshu\.com/discovery/item/([0-9A-Za-z]+)", re.IGNORECASE),
]

SHORT_LINK_HINT_SUBSTR = (
    "v.douyin.com",  # 抖音短链
    "xhslink.com",   # 小红书短链
)


def parse_platform_and_id(url: str) -> Tuple[Optional[Channel], Optional[str], Optional[str]]:
    """尝试从 URL 中解析平台与帖子/视频 ID。

    返回 (platform, platform_item_id, reason)。
    - platform: "douyin" | "xiaohongshu" | None
    - platform_item_id: 解析出的 aweme_id/note_id；未匹配时为 None
    - reason: 无法识别/需要解短链等提示；成功时为 None
    """
    if not isinstance(url, str) or not url.strip():
        return None, None, "URL 为空"

    raw = url.strip()

    # 短链提示（建议上游先做解短链再调用本函数）
    if any(s in raw for s in SHORT_LINK_HINT_SUBSTR):
        return None, None, "短链需先展开（v.douyin.com/xhslink.com）"

    for pat in DOUYIN_PATTERNS:
        m = pat.search(raw)
        if m:
            return Channel.DOUYIN, m.group(1), None

    for pat in XHS_PATTERNS:
        m = pat.search(raw)
        if m:
            return Channel.XIAOHONGSHU, m.group(1), None

    return None, None, "未匹配到已支持的 URL 格式"



# --- 短链解码与标准化 ---
import requests

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def is_short_link(url: str) -> bool:
    if not isinstance(url, str):
        return False
    raw = url.strip().lower()
    return any(host in raw for host in SHORT_LINK_HINT_SUBSTR)


def resolve_short_url(url: str, timeout: float = 5.0) -> tuple[str, Optional[str]]:
    """尝试解短链，返回 (expanded_url, error)。
    - 若不是短链，直接返回原 url, error=None
    - 若解短链失败，返回原 url, error=错误原因
    """
    if not is_short_link(url):
        return url, None
    try:
        headers = {"User-Agent": USER_AGENT}
        # HEAD 有些平台不支持，先尝试 GET 且禁止下载正文
        resp = requests.get(url, headers=headers, allow_redirects=True, timeout=(3, timeout), stream=True)
        final_url = resp.url or url
        try:
            # 立刻关闭连接，避免下载内容
            resp.close()
        except Exception:
            pass
        return final_url, None
    except Exception as e:
        return url, f"短链解码失败: {e}"


def normalize_url_for_parsing(url: str, timeout: float = 5.0) -> tuple[str, Optional[str]]:
    """若为短链则先解码，否则原样返回。返回 (normalized_url, error)。"""
    return resolve_short_url(url, timeout=timeout)



def resolve_and_parse(url: str, timeout: float = 5.0) -> Tuple[Optional[Channel], Optional[str], Optional[str]]:
    """
    总入口：若为短链则先尝试解码，再调用 parse_platform_and_id；否则直接解析。
    返回 (platform, platform_item_id, reason)。
    """
    if not isinstance(url, str) or not url.strip():
        return None, None, "URL 为空"
    if is_short_link(url):
        expanded, err = resolve_short_url(url, timeout=timeout)
        if err:
            return None, None, err
        return parse_platform_and_id(expanded)
    return parse_platform_and_id(url)

# 语义别名，便于调用方理解
analyze_url = resolve_and_parse
