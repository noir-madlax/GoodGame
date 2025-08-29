from __future__ import annotations
from typing import Dict, Any

# 可根据业务随时调整阈值
MIN_PLAY = 5000
MIN_LIKE = 50
MIN_COMMENT = 5

LOW_VALUE_KEYWORDS = (
    "广告",
    "引流",
    "合集",
    "日常记录",
)

def obviously_no_value(row: Dict[str, Any]) -> bool:
    title = (row.get("title") or "").strip()
    content = (row.get("content") or "").strip()
    if any(k in title for k in LOW_VALUE_KEYWORDS) or any(k in content for k in LOW_VALUE_KEYWORDS):
        return True
    pc = int(row.get("play_count") or 0)
    lc = int(row.get("like_count") or 0)
    cc = int(row.get("comment_count") or 0)
    if pc < MIN_PLAY and lc < MIN_LIKE and cc < MIN_COMMENT:
        return True
    return False

