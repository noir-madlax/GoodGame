"""
多平台视频下载工作流：获取视频信息并下载视频到指定目录结构
支持抖音、小红书等多个平台
"""

import os
import json
import sys

# 添加当前目录到 Python 路径，支持直接运行
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    from fetchers import create_fetcher, get_supported_platforms
    from video_downloader import VideoDownloader
else:
    # 作为模块导入时使用相对导入
    from .fetchers import create_fetcher, get_supported_platforms
    from .video_downloader import VideoDownloader


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

        # 2. 创建目录结构: downloads/{platform}/{视频ID}/
        video_dir = os.path.join(base_download_dir, platform, video_id)
        os.makedirs(video_dir, exist_ok=True)
        print(f"📁 创建目录: {video_dir}")

        # 3. 获取完整视频信息
        print("📡 正在获取视频信息...")
        fetcher = create_fetcher(platform)
        full_video_info = fetcher.fetch_video_info(video_id)

        if not full_video_info or not fetcher._check_api_response(full_video_info):
            print("❌ 获取视频信息失败")
            return None

        # 4. 保存完整视频信息到 JSON 文件
        json_file_path = os.path.join(video_dir, "video_info.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(full_video_info, f, ensure_ascii=False, indent=2)
        print(f"💾 视频信息已保存: {json_file_path}")

        # 5. 获取下载链接
        download_urls = fetcher.get_download_urls(video_id)

        if not download_urls:
            print("❌ 未找到下载链接")
            return None

        print(f"🔗 找到 {len(download_urls)} 个下载链接")

        # 6. 显示视频基本信息
        video_details = fetcher.get_video_details(video_id)
        if video_details:
            _display_video_info(platform, video_details)

        # 7. 设置视频文件名: {视频ID}.mp4
        video_filename = f"{video_id}.mp4"

        # 8. 尝试下载视频（多URL重试）
        print("⬇️ 开始下载视频...")
        downloader = VideoDownloader(video_dir)
        file_path = _download_with_multiple_urls(downloader, download_urls, video_filename)

        if file_path:
            print(f"🎉 视频下载完成: {file_path}")
            print(f"📋 视频信息文件: {json_file_path}")
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
        print(f"   链接: {url[:80]}...")

        try:
            # 尝试下载
            file_path = downloader.download_video_with_retry(url, filename, max_retries=2)

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


def _display_video_info(platform: str, video_details: dict) -> None:
    """
    显示视频基本信息

    Args:
        platform (str): 平台名称
        video_details (dict): 视频详细信息
    """
    try:
        if platform == "douyin":
            aweme_detail = video_details.get('aweme_detail', {})
            video_info = aweme_detail.get('video', {})
            author_info = aweme_detail.get('author', {})

            print(f"📝 视频标题: {aweme_detail.get('desc', '无标题')}")
            print(f"👤 作者: {author_info.get('nickname', '未知')}")
            print(f"⏱️ 时长: {video_info.get('duration', 0) / 1000:.1f} 秒")

        elif platform == "xiaohongshu":
            note_detail = video_details.get('note_detail', {})
            author_info = note_detail.get('author', {})

            print(f"📝 笔记标题: {note_detail.get('title', '无标题')}")
            print(f"📄 笔记描述: {note_detail.get('desc', '无描述')}")
            print(f"👤 作者: {author_info.get('nickname', '未知')}")

        else:
            print(f"📋 {platform} 平台视频信息显示功能待实现")

    except Exception as e:
        print(f"⚠️ 显示视频信息时出错: {str(e)}")


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
        ("xiaohongshu", "test_note_id_123"),
    ]

    for platform, video_id in test_cases:
        print(f"\n=== {platform.upper()} 平台测试 ===")

        try:
            # 创建获取器实例
            fetcher = create_fetcher(platform)
            print(f"✅ 成功创建 {platform} 获取器: {fetcher}")

            # 获取完整的 API 响应
            full_response = fetcher.fetch_video_info(video_id)
            print(f"API 状态码: {full_response.get('code')}")

            # 获取视频详细信息
            video_details = fetcher.get_video_details(video_id)
            if video_details:
                _display_video_info(platform, video_details)

        except Exception as e:
            print(f"❌ {platform} 平台测试失败: {e}")

    print("\n=== 完整下载流程示例 ===")
    # 执行完整的下载流程（仅测试抖音）
    download_path = download_video_complete("douyin", "7383012850161241385", "downloads")

    if download_path:
        print(f"\n✅ 任务完成！视频已保存到: {download_path}")
    else:
        print("\n❌ 任务失败！")


if __name__ == "__main__":
    main()
