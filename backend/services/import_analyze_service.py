from __future__ import annotations

from jobs.logger import get_logger
from typing import Any, Dict

from tikhub_api.utils.url_parser import resolve_and_parse
from tikhub_api.fetchers.fetcher_factory import FetcherFactory
from tikhub_api.orm.post_repository import PostRepository
from tikhub_api.orm.enums import AnalysisStatus, RelevantStatus


logger = get_logger(__name__)


def analyze_and_import(url: str, trace_id: str | None = None) -> Dict[str, Any]:
    """
    解析 URL -> 拉取详情 -> 适配为 PlatformPost -> Upsert 落库 -> 返回摘要结果。
    返回字典可直接塞入 ImportAnalyzeResult(**dict)。
    """
    logger.info("【导入分析】开始处理 trace_id=%s url=%s", trace_id, url)

    platform, item_id, reason = resolve_and_parse(url)
    if not platform or not item_id:
        logger.info(
            "【导入分析】URL 解析失败 trace_id=%s 原因=%s url=%s",
            trace_id,
            reason,
            url,
        )
        return {
            "recognized": False,
            "platform": platform,
            "platform_item_id": item_id,
            "post_id": None,
            "raw_reason": reason or "未识别到平台或帖子ID",
        }

    logger.info(
        "【导入分析】URL 解析成功 trace_id=%s 平台=%s 帖子ID=%s",
        trace_id,
        getattr(platform, "value", str(platform)),
        item_id,
    )

    # 拉取原始详情 & 适配（通过工厂创建 fetcher）
    try:
        logger.info(
            "【导入分析】创建抓取器 trace_id=%s 平台=%s",
            trace_id,
            getattr(platform, "value", str(platform)),
        )
        fetcher = FetcherFactory.create_fetcher(getattr(platform, "value", str(platform)))
    except Exception as e:
        logger.warning(
            "【导入分析】创建抓取器失败 trace_id=%s 平台=%s 错误=%s",
            trace_id,
            getattr(platform, "value", str(platform)),
            e,
        )
        return {
            "recognized": False,
            "platform": platform,
            "platform_item_id": item_id,
            "post_id": None,
            "raw_reason": f"创建获取器失败: {e}",
        }

    details = fetcher.get_video_details(item_id)
    if not details:
        logger.warning(
            "【导入分析】拉取详情为空 trace_id=%s 平台=%s 帖子ID=%s",
            trace_id,
            getattr(platform, "value", str(platform)),
            item_id,
        )
        return {
            "recognized": True,
            "platform": platform,
            "platform_item_id": item_id,
            "post_id": None,
            "raw_reason": "拉取详情失败",
        }

    adapter = fetcher.get_adapter()
    post = adapter.to_post_single(details)  # type: ignore[attr-defined]
    
    # 人工导入：固定初始评估枚举
    post.analysis_status = AnalysisStatus.INIT
    post.relevant_status = RelevantStatus.MAYBE
    post.is_marked = True

    # 落库
    saved = PostRepository.upsert_post(post)
    logger.info(
        "【导入分析】落库成功 trace_id=%s post_id=%s 平台=%s 帖子ID=%s",
        trace_id,
        getattr(saved, "id", None),
        getattr(platform, "value", str(platform)),
        item_id,
    )

    # 组装返回
    post_type_val = str(getattr(saved.post_type, "value", saved.post_type))  # 兼容枚举/字符串
    original_url = str(saved.original_url) if getattr(saved, "original_url", None) else None
    cover_url = str(saved.cover_url) if getattr(saved, "cover_url", None) else None
    video_url = str(saved.video_url) if getattr(saved, "video_url", None) else None

    return {
        "recognized": True,
        "platform": platform,
        "platform_item_id": item_id,
        "post_id": saved.id,
        "title": saved.title,
        "post_type": post_type_val,
        "original_url": original_url,
        "cover_url": cover_url,
        "video_url": video_url,
    }

