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

# 模块级默认下载根目录
DEFAULT_BASE_DOWNLOAD_DIR = "downloads"



from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class WorkflowOptions:
    # 四步可选，默认与原有逻辑一致：全部开启
    sync_details: bool = True
    sync_comments: bool = True
    sync_danmaku: bool = True
    download_video: bool = True
    # 其他控制项
    force_refresh: bool = False
    page_size: int = 20


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
    platform: str,
    video_id: str,
    options: WorkflowOptions = WorkflowOptions(),
) -> WorkflowReport:
    """
    统一视频工作流：可选择性执行 详情入库 / 评论同步 / 弹幕保存 / 视频下载。
    默认行为与原 download_video_complete 保持一致（全部开启）。

    Returns: WorkflowReport（结构化每步信息）
    """
    print(f"🎬 开始处理 {platform} 视频: {video_id}")

    report = WorkflowReport(platform=platform, video_id=video_id)

    # 1. 平台校验
    if platform not in get_supported_platforms():
        err = f"不支持的平台: {platform}，支持的平台: {get_supported_platforms()}"
        print(f"❌ {err}")
        report.steps["details"] = StepResult(ok=False, error=err)
        return report

    # 2. 构造 fetcher
    fetcher = create_fetcher(platform)

    # 3. 目录
    video_dir = os.path.join(DEFAULT_BASE_DOWNLOAD_DIR, platform, video_id)
    report.video_dir = video_dir

    unified_post = None

    # Step A: 详情 + 入库
    if options.sync_details:
        a_res = _step_sync_details_and_upsert(fetcher, video_id)
        report.steps["details"] = a_res
        if a_res.ok:
            report.post_id = a_res.output.get("post_id")
            unified_post = a_res.output.get("unified_post")
        else:
            # 原逻辑：详情是前置，为保证行为一致，如果详情失败，后续依赖 post_id 的步骤会被跳过
            pass
    else:
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

    # Step C: 弹幕
    if options.sync_danmaku:
        try:
            try:
                from .capabilities import DanmakuProvider
            except Exception:
                from tikhub_api.capabilities import DanmakuProvider
            if isinstance(fetcher, DanmakuProvider):
                os.makedirs(video_dir, exist_ok=True)
                c_res = _step_sync_danmaku(fetcher, video_id, video_dir)
                report.steps["danmaku"] = c_res
            else:
                report.steps["danmaku"] = StepResult(ok=True, skipped=True, error="平台不支持弹幕能力")
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
        print(f"🎉 完成：{report.file_path}")
    else:
        print("⚠️ 工作流未成功下载文件（如已跳过下载则忽略）")

    return report



# ===== 步骤实现 =====

def _step_sync_details_and_upsert(fetcher, video_id: str) -> StepResult:
    try:
        unified_post = fetcher.get_platform_post(video_id)
        if unified_post is None:
            return StepResult(ok=False, error="未能生成统一领域模型 PlatformPost")
        saved = PostRepository.upsert_post(unified_post)
        print(f"🧩 统一模型已入库: id={saved.id} platform={saved.platform} item={saved.platform_item_id}")
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
        print("💬 开始同步顶层评论...")
        while True:
            page = fetcher.get_video_comments(video_id, cursor, page_size) or {}
            comments = page.get("comments") or []
            next_cursor = int(page.get("cursor") or 0)
            has_more = int(page.get("has_more") or 0)

            if not comments:
                print("📭 本页无评论，结束顶层评论同步。")
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
                    print(f"⚠️ 顶层评论入库失败: {e}")
            total_top += len(models)
            print(f"💬 顶层评论累计入库: {total_top}")

            if has_more == 1 and next_cursor != cursor:
                cursor = next_cursor
                continue
            else:
                break

        return StepResult(ok=True, output={"top_count": total_top})
    except Exception as e:
        return StepResult(ok=False, error=f"评论同步失败: {e}")


def _step_sync_danmaku(fetcher, video_id: str, video_dir: str) -> StepResult:
    try:
        video_details = fetcher.get_video_details(video_id) or {}
        _fetch_and_save_danmaku(fetcher, video_id, video_details, video_dir)
        return StepResult(ok=True)
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

        print(f"🔗 找到 {len(download_urls)} 个下载链接")
        video_filename = f"{video_id}.mp4"
        downloader = VideoDownloader(video_dir)
        file_path = _download_with_multiple_urls(downloader, download_urls, video_filename)
        if file_path:
            print(f"🎉 视频下载完成: {file_path}")
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
        print(f"🔗 尝试第 {i}/{len(download_urls)} 个下载链接...")
        url_str = str(url)
        print(f"   链接: {url_str[:80]}...")

        try:
            # 尝试下载
            file_path = downloader.download_video_with_retry(url_str, filename, max_retries=2)

            if file_path:
                print(f"✅ 第 {i} 个链接下载成功！")
                return file_path
            else:
                print(f"❌ 第 {i} 个链接下载失败，尝试下一个...")

        except Exception as e:
            print(f"❌ 第 {i} 个链接下载异常: {str(e)}")
            continue

    print("❌ 所有下载链接都尝试失败")
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
        print("🎭 正在获取弹幕信息...")

        # 从视频详细信息中获取视频时长
        aweme_detail = video_details.get('aweme_detail', {})
        video_info = aweme_detail.get('video', {})
        duration = video_info.get('duration', 0)  # 时长单位为毫秒

        if duration <= 0:
            print("⚠️ 无法获取视频时长，跳过弹幕获取")
            return

        print(f"📏 视频时长: {duration / 1000:.1f} 秒")

        # 获取弹幕信息
        danmaku_data = fetcher.get_video_danmaku(video_id, duration)

        if danmaku_data:
            # 保存弹幕信息到 danmaku.json 文件
            danmaku_file_path = os.path.join(video_dir, "danmaku.json")
            with open(danmaku_file_path, 'w', encoding='utf-8') as f:
                json.dump(danmaku_data, f, ensure_ascii=False, indent=2)
            print(f"🎭 弹幕信息已保存: {danmaku_file_path}")
        else:
            print("⚠️ 未获取到弹幕信息")

    except Exception as e:
        print(f"⚠️ 获取弹幕信息时出错: {str(e)}")



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
                    print(f"⚠️ 楼中楼入库失败: {e}")

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
                    print(f"⚠️ 楼中楼父子修正失败: {e}")

            if has_more == 1 and next_cursor != cursor:
                cursor = next_cursor
                continue
            else:
                break
        print(f"💬 顶层 {top_cid} 的楼中楼同步完成：页数={page_count}，新增/更新={synced}")
    except Exception as e:
        print(f"⚠️ 同步楼中楼失败(top={top_cid}): {e}")


# 可选：提供一个便捷函数，按默认全流程执行抖音
# 如不需要保留也可删除

def run_douyin_full_workflow(aweme_id: str) -> WorkflowReport:
    return run_video_workflow(
        platform="douyin",
        video_id=aweme_id,
        options=WorkflowOptions(
            sync_details=True,
            sync_comments=True,
            sync_danmaku=True,
            download_video=True,
        ),
    )


def main():
    """主函数示例"""
    print("=== 多平台视频下载工具 ===")
    print(f"支持的平台: {get_supported_platforms()}")

    # 示例视频 ID
    test_cases = [
        ("douyin", "7383012850161241385"),
        ("douyin", "7499608775142608186"),
        ("douyin", "7505583378596646180"),
        ("douyin", "7497155954375494950"),
        ("xiaohongshu", "685752ea000000000d01b8b2"),
    ]

    print("\n=== 完整下载流程示例（包含弹幕获取）===")
    report = run_video_workflow(
        platform="douyin",
        video_id="7497155954375494950",
        options=WorkflowOptions(
            sync_details=True,
            sync_comments=False,
            sync_danmaku=False,
            download_video=False,
        ),
    )

    print("\n☑️ 任务完成！")


if __name__ == "__main__":
    main()
