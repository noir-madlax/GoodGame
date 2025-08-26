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


def download_video_complete(platform: str, video_id: str, base_download_dir: str = "downloads"):
    """
    完整的多平台视频下载流程：获取视频信息 -> 保存信息到JSON -> 下载视频
    保存结构: downloads/{platform}/{视频ID}/{视频ID}.mp4 和 video_info.json

    Args:
        platform (str): 平台名称 (douyin, xiaohongshu)
        video_id (str): 视频 ID
        base_download_dir (str): 基础下载目录，默认为 "downloads"

    Returns:
        Optional[str]: 下载成功返回文件路径，失败返回 None
    """
    print(f"🎬 开始处理 {platform} 视频: {video_id}")

    try:
        # 1. 验证平台支持
        if platform not in get_supported_platforms():
            print(f"❌ 不支持的平台: {platform}，支持的平台: {get_supported_platforms()}")
            return None

        # 2~5. 直接通过统一模型一步到位，并从统一模型中拿下载地址（必要时回退）
        print(" 正在获取统一领域模型并准备下载...")
        fetcher = create_fetcher(platform)

        # 6 获取统一领域模型 PlatformPost 并直接入库
        try:
            unified_post = fetcher.get_platform_post(video_id)
            if unified_post is not None:
                saved = PostRepository.upsert_post(unified_post)
                print(f"🧩 统一模型已入库: id={saved.id} platform={saved.platform} item={saved.platform_item_id}")
            else:
                print("❌ 未能生成统一领域模型 PlatformPost")
                return None
        except Exception as e:
            print(f"⚠️ 入库统一领域模型出错: {e}")
            return None

        # ===== 评论拉取与落库 =====
        try:
            try:
                # 优先相对导入（包内运行）
                from .capabilities import CommentsProvider
                from .adapters import DouyinCommentAdapter
                from .orm.comment_repository import CommentRepository
            except Exception:
                # 作为脚本运行时使用绝对导入
                from tikhub_api.capabilities import CommentsProvider
                from tikhub_api.adapters import DouyinCommentAdapter
                from tikhub_api.orm.comment_repository import CommentRepository

            if isinstance(fetcher, CommentsProvider) and getattr(saved, "id", None):
                post_id = saved.id
                cursor = 0
                page_size = 20
                total = 0
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

                    # 映射并入库顶层评论
                    models = DouyinCommentAdapter.to_comment_list(comments, post_id)
                    for c in models:
                        try:
                            saved_c = CommentRepository.upsert_comment(c)
                            # 维护平台CID到DB id的映射
                            if getattr(saved_c, "platform_comment_id", None) and getattr(saved_c, "id", None):
                                id_map[str(saved_c.platform_comment_id)] = int(saved_c.id)
                            # 如果该顶层有回复，继续同步该顶层的楼中楼
                            if int(getattr(saved_c, "reply_count", 0) or 0) > 0:
                                _sync_replies_for_top_comment(fetcher, video_id, str(saved_c.platform_comment_id), int(saved.id), id_map)
                        except Exception as e:
                            print(f"⚠️ 顶层评论入库失败: {e}")
                    total += len(models)
                    print(f"💬 顶层评论累计入库: {total}")

                    if has_more == 1 and next_cursor != cursor:
                        cursor = next_cursor
                        continue
                    else:
                        break
            else:
                print("💬 当前平台未提供评论能力或缺少 post_id，跳过评论同步")
        except Exception as e:
            print(f"⚠️ 评论同步失败: {e}")

         # 7.（可选）弹幕：仅在支持且能拿到时获取
        try:
            try:
                from .capabilities import DanmakuProvider  # 包内相对导入
            except Exception:
                from tikhub_api.capabilities import DanmakuProvider  # 脚本绝对导入
            if isinstance(fetcher, DanmakuProvider):
                # 需要视频详情中的时长，临时获取一次详情
                video_details = fetcher.get_video_details(video_id) or {}
                # 准备保存目录（若还未创建）
                video_dir = os.path.join(base_download_dir, platform, video_id)
                os.makedirs(video_dir, exist_ok=True)
                _fetch_and_save_danmaku(fetcher, video_id, video_details, video_dir)
            else:
                print("🎭 当前平台不支持弹幕能力，跳过")
        except Exception:
            print("🎭 弹幕能力检测失败或未提供，跳过")

        # 从统一模型中获取下载链接，若没有则回退到 fetcher.get_download_urls
        download_urls = []
        if getattr(unified_post, "video_url", None):
            download_urls = [unified_post.video_url]
        else:
            download_urls = fetcher.get_download_urls(video_id) or []

        # 规范化为字符串（避免 Pydantic HttpUrl 之类的不可切片对象）
        download_urls = [str(u) for u in download_urls if u]
        if not download_urls:
            print("❌ 未找到下载链接")
            return None

        print(f"🔗 找到 {len(download_urls)} 个下载链接")

        # 8. 设置视频文件名: {视频ID}.mp4，并准备保存目录
        video_filename = f"{video_id}.mp4"
        video_dir = os.path.join(base_download_dir, platform, video_id)
        os.makedirs(video_dir, exist_ok=True)

        # 9. 尝试下载视频（多URL重试）
        print("⬇️ 开始下载视频...")
        downloader = VideoDownloader(video_dir)
        file_path = _download_with_multiple_urls(downloader, download_urls, video_filename)

        if file_path:
            print(f"🎉 视频下载完成: {file_path}")

            return file_path
        else:
            print("❌ 所有下载链接都失败了")
            return None
            

    except Exception as e:
        print(f"❌ 处理过程中发生错误: {str(e)}")
        return None


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


# 为了向后兼容，保留原函数名
def download_douyin_video_complete(aweme_id: str, base_download_dir: str = "downloads"):
    """
    向后兼容函数：下载抖音视频

    Args:
        aweme_id (str): 抖音视频 ID
        base_download_dir (str): 基础下载目录

    Returns:
        Optional[str]: 下载成功返回文件路径，失败返回 None
    """
    return download_video_complete("douyin", aweme_id, base_download_dir)


def main():
    """主函数示例"""
    print("=== 多平台视频下载工具 ===")
    print(f"支持的平台: {get_supported_platforms()}")

    # 示例视频 ID
    test_cases = [
        ("douyin", "7383012850161241385"),
        ("douyin", "7499608775142608186"),
        ("douyin", "7505583378596646180"),
    ]

    print("\n=== 完整下载流程示例（包含弹幕获取）===")
    # 执行完整的下载流程（仅测试抖音）
    download_path = download_video_complete("douyin", "7505583378596646180", "downloads")

    if download_path:
        print(f"\n✅ 任务完成！视频已保存到: {download_path}")
    else:
        print("\n❌ 任务失败！")


if __name__ == "__main__":
    main()
