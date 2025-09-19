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

