"""
多平台视频下载工作流：获取视频信息并下载视频到指定目录结构
支持抖音、小红书等多个平台
"""

import os
import json
import sys

# 添加当前目录到 Python 路径，支持直接运行
if __name__ == "__main__":
    # 将项目根目录加入路径，确保以包方式导入，避免相对导入报错
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from tikhub_api.fetchers import create_fetcher, get_supported_platforms
    from tikhub_api.video_downloader import VideoDownloader
    from tikhub_api.orm.post_repository import PostRepository
else:
    # 作为模块导入时使用相对导入
    from .fetchers import create_fetcher, get_supported_platforms
    from .video_downloader import VideoDownloader
    from .orm.post_repository import PostRepository

from jobs.logger import get_logger

# 模块级默认下载根目录
DEFAULT_BASE_DOWNLOAD_DIR = "downloads"

log = get_logger(__name__)

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class WorkflowOptions:
    # 步骤开关（默认与原有逻辑一致）
    sync_details: bool = False
    sync_comments: bool = False
    sync_danmaku: bool = False
    download_video: bool = False
    # 其他控制项
    force_refresh: bool = False
    page_size: int = 20  # 评论分页等用途
    # 批处理控制
    batch_size: int = 20  # 搜索结果按批落库大小
    concurrency: int = 1  # 处理并发：当前按 1 顺序处理，后续只需改数字即可


@dataclass
class StepResult:
    ok: bool
    skipped: bool = False
    error: Optional[str] = None
    output: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowReport:
    platform: str
    video_id: str
    post_id: Optional[int] = None
    video_dir: Optional[str] = None
    file_path: Optional[str] = None
    steps: Dict[str, StepResult] = field(default_factory=dict)

    def succeeded(self) -> bool:
        dl = self.steps.get("download")
        return bool(dl and dl.ok)


def run_video_workflow(
    unified_post,  # PlatformPost 对象
    options: WorkflowOptions = WorkflowOptions(),
) -> WorkflowReport:
    """
    统一视频工作流：基于已有 PlatformPost，执行 评论同步 / 弹幕保存 / 视频下载。
    不再执行"详情获取+入库"步骤。

    Args:
        unified_post: PlatformPost 对象（已包含 platform_item_id、platform 等信息）
        options: 工作流选项

    Returns: WorkflowReport（结构化每步信息）
    """
    platform = unified_post.platform
    video_id = unified_post.platform_item_id
    log.info("开始处理视频：平台=%s，视频ID=%s", platform, video_id)

    report = WorkflowReport(platform=platform, video_id=video_id)

    # 1. 平台校验
    if platform not in get_supported_platforms():
        err = f"不支持的平台: {platform}，支持的平台: {get_supported_platforms()}"
        log.error("%s", err)
        report.steps["details"] = StepResult(ok=False, error=err)
        return report

    # 2. 构造 fetcher
    fetcher = create_fetcher(platform)

    # 3. 目录
    video_dir = os.path.join(DEFAULT_BASE_DOWNLOAD_DIR, platform, video_id)
    report.video_dir = video_dir

    # Step A: 外部负责详情获取与可选入库；此处仅记录已有 post_id（若已入库过）
    report.post_id = getattr(unified_post, "id", None)
    report.steps["details"] = StepResult(ok=True, skipped=True)

    # Step B: 评论
    if options.sync_comments:
        if report.post_id is None:
            report.steps["comments"] = StepResult(ok=False, skipped=True, error="缺少 post_id 或详情未入库")
        else:
            b_res = _step_sync_comments(fetcher, video_id, int(report.post_id), options.page_size)
            report.steps["comments"] = b_res
    else:
        report.steps["comments"] = StepResult(ok=True, skipped=True)

    # Step C: 弹幕（优先使用已知时长，避免重复详情请求）
    if options.sync_danmaku:
        try:
            c_res = _step_sync_danmaku_from_post(fetcher, unified_post, video_id, video_dir)
            report.steps["danmaku"] = c_res
        except Exception as e:
            report.steps["danmaku"] = StepResult(ok=False, error=str(e))
    else:
        report.steps["danmaku"] = StepResult(ok=True, skipped=True)

    # Step D: 下载
    if options.download_video:
        os.makedirs(video_dir, exist_ok=True)
        d_res = _step_download_video(fetcher, unified_post, video_id, video_dir)
        report.steps["download"] = d_res
        if d_res.ok:
            report.file_path = d_res.output.get("file_path")
    else:
        report.steps["download"] = StepResult(ok=True, skipped=True)

    # 结束
    if report.succeeded():
        log.info("视频处理完成，文件已保存：%s", report.file_path)
    else:
        log.warning("工作流未成功下载文件（如已跳过下载则忽略）")

    return report



# ===== 步骤实现 =====

def _step_sync_details_and_upsert(fetcher, video_id: str) -> StepResult:
    try:
        unified_post = fetcher.get_platform_post(video_id)
        if unified_post is None:
            return StepResult(ok=False, error="未能生成统一领域模型 PlatformPost")
        saved = PostRepository.upsert_post(unified_post)
        log.info("统一模型已入库：post_id=%s，平台=%s，视频ID=%s", saved.id, saved.platform, saved.platform_item_id)
        return StepResult(ok=True, output={
            "post_id": getattr(saved, "id", None),
            "unified_post": unified_post,
        })
    except Exception as e:
        return StepResult(ok=False, error=f"入库统一领域模型出错: {e}")


def _step_sync_comments(fetcher, video_id: str, post_id: int, page_size: int = 20) -> StepResult:
    try:
        # 动态导入
        try:
            from .capabilities import CommentsProvider
            from .adapters import DouyinCommentAdapter
            from .orm.comment_repository import CommentRepository
        except Exception:
            from tikhub_api.capabilities import CommentsProvider
            from tikhub_api.adapters import DouyinCommentAdapter
            from tikhub_api.orm.comment_repository import CommentRepository

        if not isinstance(fetcher, CommentsProvider):
            return StepResult(ok=True, skipped=True, error="平台未提供评论能力")

        cursor = 0
        total_top = 0
        id_map: dict[str, int] = {}
        log.info("开始同步顶层评论：视频ID=%s，post_id=%s", video_id, post_id)
        while True:
            page = fetcher.get_video_comments(video_id, cursor, page_size) or {}
            comments = page.get("comments") or []
            next_cursor = int(page.get("cursor") or 0)
            has_more = int(page.get("has_more") or 0)

            if not comments:
                log.info("本页无评论，视频ID=%s，post_id=%s，结束顶层评论同步：cursor=%s",video_id, post_id ,cursor)
                break

            models = DouyinCommentAdapter.to_comment_list(comments, post_id)
            for c in models:
                try:
                    saved_c = CommentRepository.upsert_comment(c)
                    if getattr(saved_c, "platform_comment_id", None) and getattr(saved_c, "id", None):
                        id_map[str(saved_c.platform_comment_id)] = int(saved_c.id)
                    if int(getattr(saved_c, "reply_count", 0) or 0) > 0:
                        _sync_replies_for_top_comment(fetcher, video_id, str(saved_c.platform_comment_id), int(post_id), id_map)
                except Exception as e:
                    log.warning("视频ID=%s，post_id=%s，顶层评论入库失败：%s",video_id, post_id, e)
            total_top += len(models)
            log.info("视频ID=%s，post_id=%s，顶层评论累计入库：%s 条",video_id, post_id, total_top)

            if has_more == 1 and next_cursor != cursor:
                cursor = next_cursor
                continue
            else:
                break

        return StepResult(ok=True, output={"top_count": total_top})
    except Exception as e:
        return StepResult(ok=False, error=f"评论同步失败: {e}")



def sync_comments_for_post_id(post_id: int, page_size: int = 20) -> StepResult:
    """公开方法：按 post_id 同步评论，成功后将 analysis_status 置为 pending。
    封装 _step_sync_comments 以及状态回写逻辑，供 worker/CLI 复用。
    """
    try:
        # 延迟导入，兼容作为模块或脚本运行
        try:
            from .orm.post_repository import PostRepository
            from .orm.enums import AnalysisStatus
        except Exception:
            from tikhub_api.orm.post_repository import PostRepository
            from tikhub_api.orm.enums import AnalysisStatus

        post = PostRepository.get_by_id(int(post_id))
        if not post:
            return StepResult(ok=False, error=f"post not found: id={post_id}")
        platform = getattr(post, "platform", None)
        video_id = getattr(post, "platform_item_id", None)
        if not platform or not video_id:
            return StepResult(ok=False, error="missing platform or platform_item_id")

        # 创建对应平台 fetcher 并调用内部实现
        fetcher = create_fetcher(str(platform))
        res = _step_sync_comments(fetcher, str(video_id), int(post_id), page_size=page_size)

        # 成功且未跳过时，写回 analysis_status=pending；失败则写回 comments_failed
        if getattr(res, "ok", False) and not getattr(res, "skipped", False):
            try:
                PostRepository.update_analysis_status(int(post_id), AnalysisStatus.PENDING.value)
            except Exception:
                # 状态写回失败不影响主流程结果
                pass
        elif not getattr(res, "ok", False):
            try:
                PostRepository.update_analysis_status(int(post_id), AnalysisStatus.COMMENTS_FAILED.value)
            except Exception:
                # 状态写回失败不影响主流程结果
                pass
        return res
    except Exception as e:
        try:
            # 异常时也标记为 comments_failed（使用局部别名避免遮蔽外层导入）
            try:
                from .orm.post_repository import PostRepository as _PR
                from .orm.enums import AnalysisStatus as _AS
            except Exception:
                from tikhub_api.orm.post_repository import PostRepository as _PR
                from tikhub_api.orm.enums import AnalysisStatus as _AS
            _PR.update_analysis_status(int(post_id), _AS.COMMENTS_FAILED.value)
        except Exception:
            pass
        return StepResult(ok=False, error=f"sync_comments_for_post_id failed: {e}")


def _step_sync_danmaku(fetcher, video_id: str, video_dir: str) -> StepResult:
    try:
        video_details = fetcher.get_video_details(video_id) or {}
        _fetch_and_save_danmaku(fetcher, video_id, video_details, video_dir)
        return StepResult(ok=True)
    except Exception as e:
        return StepResult(ok=False, error=f"弹幕处理失败: {e}")


# 基于已知 PlatformPost 的弹幕处理，避免重复详情请求
def _step_sync_danmaku_from_post(fetcher, unified_post, video_id: str, video_dir: str) -> StepResult:
    try:
        # 优先使用 PlatformPost.duration_ms
        duration = int(getattr(unified_post, "duration_ms", 0) or 0)
        if duration <= 0:
            # 尝试从 raw_details 中取
            raw = getattr(unified_post, "raw_details", {}) or {}
            if isinstance(raw, dict):
                aweme_detail = raw.get("aweme_detail", {}) or {}
                video = aweme_detail.get("video", {}) or {}
                duration = int(video.get("duration") or 0)
        if duration <= 0:
            # 兜底：调一次详情拿时长
            try:
                details = fetcher.get_video_details(video_id) or {}
                aweme_detail = details.get("aweme_detail", {}) or {}
                video = aweme_detail.get("video", {}) or {}
                duration = int(video.get("duration") or 0)
            except Exception:
                duration = 0
        if duration <= 0:
            return StepResult(ok=True, skipped=True, error="缺少视频时长，跳过弹幕")

        try:
            from .capabilities import DanmakuProvider
        except Exception:
            from tikhub_api.capabilities import DanmakuProvider
        if not isinstance(fetcher, DanmakuProvider):
            return StepResult(ok=True, skipped=True, error="平台不支持弹幕能力")

        os.makedirs(video_dir, exist_ok=True)
        data = fetcher.get_video_danmaku(video_id, duration)
        if data:
            danmaku_file_path = os.path.join(video_dir, "danmaku.json")
            with open(danmaku_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return StepResult(ok=True)
        return StepResult(ok=False, error="未获取到弹幕")
    except Exception as e:
        return StepResult(ok=False, error=f"弹幕处理失败: {e}")




def _step_download_video(fetcher, unified_post, video_id: str, video_dir: str) -> StepResult:
    try:
        # 获取下载链接
        download_urls: List[str] = []
        if unified_post and getattr(unified_post, "video_url", None):
            download_urls = [str(unified_post.video_url)]
        else:
            urls = fetcher.get_download_urls(video_id) or []
            download_urls = [str(u) for u in urls if u]

        if not download_urls:
            return StepResult(ok=False, error="未找到下载链接")

        log.info("找到下载链接：共 %s 个", len(download_urls))
        video_filename = f"{video_id}.mp4"
        downloader = VideoDownloader(video_dir)
        file_path = _download_with_multiple_urls(downloader, download_urls, video_filename)
        if file_path:
            log.info("视频下载完成：路径=%s", file_path)
            return StepResult(ok=True, output={"file_path": file_path})
        return StepResult(ok=False, error="所有下载链接都失败了")
    except Exception as e:
        return StepResult(ok=False, error=f"下载步骤异常: {e}")


def _download_with_multiple_urls(downloader, download_urls: list, filename: str) -> str:
    """
    使用多个URL尝试下载视频

    Args:
        downloader: VideoDownloader 实例
        download_urls (list): 下载链接列表
        filename (str): 文件名

    Returns:
        str: 下载成功返回文件路径，失败返回 None
    """
    for i, url in enumerate(download_urls, 1):
        log.info("尝试第 %s/%s 个下载链接", i, len(download_urls))
        url_str = str(url)
        log.info("下载链接预览（前80字符）：%s...", url_str[:80])

        try:
            # 尝试下载
            file_path = downloader.download_video_with_retry(url_str, filename, max_retries=2)

            if file_path:
                log.info("第 %s 个链接下载成功", i)
                return file_path
            else:
                log.warning("第 %s 个链接下载失败，尝试下一个", i)

        except Exception as e:
            log.warning("第 %s 个链接下载异常：%s", i, e)
            continue

    log.error("所有下载链接都尝试失败")
    return None





def _fetch_and_save_danmaku(fetcher, video_id: str, video_details: dict, video_dir: str) -> None:
    """
    获取并保存弹幕信息到 danmaku.json 文件

    Args:
        fetcher: 视频获取器实例
        video_id (str): 视频 ID
        video_details (dict): 视频详细信息
        video_dir (str): 视频保存目录
    """
    try:
        log.info("开始获取弹幕：视频ID=%s", video_id)

        # 从视频详细信息中获取视频时长
        aweme_detail = video_details.get('aweme_detail', {})
        video_info = aweme_detail.get('video', {})
        duration = video_info.get('duration', 0)  # 时长单位为毫秒

        if duration <= 0:
            log.warning("无法获取视频时长，跳过弹幕获取：视频ID=%s", video_id)
            return

        log.info("视频时长：%.1f 秒", duration / 1000)

        # 获取弹幕信息
        danmaku_data = fetcher.get_video_danmaku(video_id, duration)

        if danmaku_data:
            # 保存弹幕信息到 danmaku.json 文件
            danmaku_file_path = os.path.join(video_dir, "danmaku.json")
            with open(danmaku_file_path, 'w', encoding='utf-8') as f:
                json.dump(danmaku_data, f, ensure_ascii=False, indent=2)
            log.info("弹幕信息已保存：%s", danmaku_file_path)
        else:
            log.warning("未获取到弹幕信息：视频ID=%s", video_id)

    except Exception as e:
        log.error("获取弹幕信息出错：视频ID=%s，错误=%s", video_id, e)



def _sync_replies_for_top_comment(fetcher, aweme_id: str, top_cid: str, video_post_id: int, id_map: dict[str, int]):
    """为一个顶层评论同步其所有楼中楼回复（分页拉取，无节流）。"""
    try:
        # 动态导入适配器与仓库
        try:
            from .adapters import DouyinCommentAdapter
            from .orm.comment_repository import CommentRepository
        except Exception:
            from tikhub_api.adapters import DouyinCommentAdapter
            from tikhub_api.orm.comment_repository import CommentRepository

        cursor = 0
        page_size = 20
        page_count = 0
        synced = 0
        while True:
            page = fetcher.get_video_comment_replies(aweme_id, top_cid, cursor, page_size) or {}
            replies = page.get("comments") or []
            next_cursor = int(page.get("cursor") or 0)
            has_more = int(page.get("has_more") or 0)
            page_count += 1

            if not replies:
                break

            # 第一趟：基础 upsert，尽力绑定父级
            models = DouyinCommentAdapter.to_reply_list(replies, video_post_id, top_cid, id_map)
            for m in models:
                try:
                    saved = CommentRepository.upsert_comment(m)
                    if getattr(saved, "platform_comment_id", None) and getattr(saved, "id", None):
                        id_map[str(saved.platform_comment_id)] = int(saved.id)
                    synced += 1
                except Exception as e:
                    log.warning("楼中楼入库失败：top_cid=%s，错误=%s", top_cid, e)

            # 第二趟：对 reply_to_reply_id != '0' 的项尝试修正 parent_comment_id
            for raw in replies:
                try:
                    reply_to_reply_id = str(raw.get('reply_to_reply_id', '') or '0')
                    if reply_to_reply_id == '0':
                        continue
                    child_cid = str(raw.get('cid', ''))
                    parent_db = id_map.get(reply_to_reply_id)
                    child_db = id_map.get(child_cid)
                    if parent_db and child_db:
                        # 仅更新父子关联，避免触碰 content 非空约束
                        CommentRepository.update_parent_link(
                            platform="douyin",
                            platform_comment_id=child_cid,
                            parent_comment_id=parent_db,
                            parent_platform_comment_id=reply_to_reply_id,
                            post_id=video_post_id,
                        )
                except Exception as e:
                    log.warning("楼中楼父子修正失败：top_cid=%s，错误=%s", top_cid, e)

            if has_more == 1 and next_cursor != cursor:
                cursor = next_cursor
                continue
            else:
                break
        log.info("视频ID=%s，post_id=%s，顶层评论回复同步完成：top_cid=%s，页数=%s，新增/更新=%s", aweme_id, video_post_id,top_cid, page_count, synced)
    except Exception as e:
        log.error("同步楼中楼失败：top_cid=%s，错误=%s", top_cid, e)

# 便捷：按视频ID完整执行（详情获取+入库+公共流程）
def run_video_full_by_id(platform: str, video_id: str, options: WorkflowOptions = WorkflowOptions()) -> WorkflowReport:
    try:
        f = create_fetcher(platform)
        # 先落地详情（统一模型 + 入库）
        details_res = _step_sync_details_and_upsert(f, video_id)
        if not details_res.ok:
            return WorkflowReport(platform=platform, video_id=video_id, steps={"details": details_res})

        unified_post = details_res.output.get("unified_post")
        post_id = details_res.output.get("post_id")
        if unified_post is None:
            return WorkflowReport(platform=platform, video_id=video_id, steps={"details": StepResult(ok=False, error="获取 PlatformPost 失败")})
        # 将入库后的 id 回写到对象，便于后续评论落库
        try:
            if post_id is not None and getattr(unified_post, "id", None) is None:
                setattr(unified_post, "id", post_id)
        except Exception:
            pass

        report = run_video_workflow(unified_post, options)
        # 覆盖 details 步为真实执行结果，并确保 post_id
        if report is not None:
            if report.post_id is None and post_id is not None:
                report.post_id = post_id
            report.steps["details"] = details_res
        return report
    except Exception as e:
        r = WorkflowReport(platform=platform, video_id=video_id)
        r.steps["details"] = StepResult(ok=False, error=str(e))
        return r


# 渠道入口（仅查询并落库）：按批抓取→适配→批量 upsert，不触发后续工作流
# 返回处理的帖子总数（尽力统计）
def run_channel_search_and_upsert(channel: str, keyword: str) -> int:
    try:
        log.info("run_channel_search_and_upsert: channel=%s, keyword=%s", channel, keyword)
        fetcher = create_fetcher(channel)

        total = 0
        # 由 BaseFetcher.iter_search_posts 负责组装领域模型并批量 upsert
        for saved_batch in fetcher.iter_search_posts(keyword, batch_size=20):
            batch_n = len(saved_batch) if isinstance(saved_batch, list) else 0
            total += batch_n
            log.info("本批已落库：size=%s，累计=%s", batch_n, total)
        log.info("完成：channel=%s, keyword=%s，总计=%s", channel, keyword, total)
        return total
    except Exception as e:
        log.error("run_channel_search_and_upsert 失败：channel=%s，keyword=%s，错误=%s", channel, keyword, e)
        return 0



def main():
    log.info("启动多平台视频下载工具")

    run_channel_search_and_upsert("douyin", "火锅")

    log.info("任务完成")


if __name__ == "__main__":
    main()
