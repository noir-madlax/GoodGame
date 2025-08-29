from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime

def _truncate(text: Optional[str], max_len: int = 600) -> str:
    if not text:
        return ""
    text = " ".join(str(text).split())
    return text[:max_len]

USER_TEMPLATE = (
    "请基于以下视频信息判断是否值得进一步分析，并输出 JSON（has_value, reason, explanation, signals[], confidence, suggested_status）。\n"
    "判定标准：\n"
    "- 若与品牌/机构/公众人物、社会热点、负面舆情、强情绪/争议、较高互动或潜在风险信号相关，则 has_value=true，suggested_status='pending'；\n"
    "- 否则 has_value=false，suggested_status='no_value'。\n"
    "- 无法判断时默认 false。\n\n"
    "请在 explanation 字段中用简洁中文给出 1-3 句理由说明，能具体到命中的线索（如品牌、情绪、风险信号或互动阈值）。\n\n"
    "视频信息：\n"
    "标题: {title}\n"
    "简介: {content}\n"
    "平台: {platform} | 作者: {author_name} | 发布时间: {published_at}\n"
    "互动: 播放={play_count}, 点赞={like_count}, 评论={comment_count}, 分享={share_count}\n"
    "其他: 类型={post_type}, 时长毫秒={duration_ms}\n"
)

SYSTEM_PROMPT = (
    "你是一名中文舆情分析师，只需判断是否值得进一步分析。严格输出 JSON，字段："
    "has_value(boolean), reason(string<=80字), explanation(string), signals(string[]), confidence(0-1), suggested_status('no_value'|'pending')。"
)

def build_user_msg(row: Dict[str, Any]) -> str:
    return USER_TEMPLATE.format(
        title=row.get("title") or "",
        content=_truncate(row.get("content")),
        platform=row.get("platform") or "",
        author_name=row.get("author_name") or "",
        published_at=row.get("published_at") or "",
        play_count=row.get("play_count") or 0,
        like_count=row.get("like_count") or 0,
        comment_count=row.get("comment_count") or 0,
        share_count=row.get("share_count") or 0,
        post_type=row.get("post_type") or "",
        duration_ms=row.get("duration_ms") or 0,
    )

