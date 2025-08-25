"""
抖音视频下载工作流：获取视频信息并下载视频到指定目录结构
"""

import os
import json
from douyin_video_fetcher import DouyinVideoFetcher
from video_downloader import VideoDownloader


def download_douyin_video_complete(aweme_id: str, base_download_dir: str = "downloads"):
    """
    完整的抖音视频下载流程：获取视频信息 -> 保存信息到JSON -> 下载视频
    保存结构: downloads/douyin/{视频ID}/{视频ID}.mp4 和 video_info.json

    Args:
        aweme_id (str): 抖音视频 ID
        base_download_dir (str): 基础下载目录，默认为 "downloads"

    Returns:
        Optional[str]: 下载成功返回文件路径，失败返回 None
    """
    print(f"🎬 开始处理抖音视频: {aweme_id}")

    try:
        # 1. 创建目录结构: downloads/douyin/{视频ID}/
        video_dir = os.path.join(base_download_dir, "douyin", aweme_id)
        os.makedirs(video_dir, exist_ok=True)
        print(f"📁 创建目录: {video_dir}")

        # 2. 获取完整视频信息
        print("📡 正在获取视频信息...")
        fetcher = DouyinVideoFetcher()
        full_video_info = fetcher.fetch_video_info(aweme_id)

        if not full_video_info or full_video_info.get('code') != 200:
            print("❌ 获取视频信息失败")
            return None

        # 3. 保存完整视频信息到 JSON 文件
        json_file_path = os.path.join(video_dir, "video_info.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(full_video_info, f, ensure_ascii=False, indent=2)
        print(f"💾 视频信息已保存: {json_file_path}")

        # 4. 解析视频基本信息
        video_details = full_video_info.get('data', {})
        aweme_detail = video_details.get('aweme_detail', {})
        video_info = aweme_detail.get('video', {})
        author_info = aweme_detail.get('author', {})

        print(f"📝 视频标题: {aweme_detail.get('desc', '无标题')}")
        print(f"👤 作者: {author_info.get('nickname', '未知')}")
        print(f"⏱️ 时长: {video_info.get('duration', 0) / 1000:.1f} 秒")

        # 5. 获取下载链接
        download_addr = video_info.get('download_addr', {})
        url_list = download_addr.get('url_list', [])

        if not url_list:
            print("❌ 未找到下载链接")
            return None

        # 取第一个下载链接
        download_url = url_list[0]
        print(f"🔗 下载链接: {download_url[:100]}...")

        # 6. 设置视频文件名: {视频ID}.mp4
        video_filename = f"{aweme_id}.mp4"

        # 7. 下载视频
        print("⬇️ 开始下载视频...")
        downloader = VideoDownloader(video_dir)
        file_path = downloader.download_video_with_retry(download_url, video_filename)

        if file_path:
            print(f"🎉 视频下载完成: {file_path}")
            print(f"📋 视频信息文件: {json_file_path}")
            return file_path
        else:
            print("❌ 视频下载失败")
            return None

    except Exception as e:
        print(f"❌ 处理过程中发生错误: {str(e)}")
        return None


def main():
    """主函数示例"""
    # 示例视频 ID
    aweme_id = "7383012850161241385"

    print("=== 抖音视频信息获取示例 ===")
    try:
        # 创建获取器实例
        fetcher = DouyinVideoFetcher()

        # 获取完整的 API 响应
        full_response = fetcher.fetch_video_info(aweme_id)
        print(f"API 状态码: {full_response.get('code')}")

        # 获取视频详细信息
        video_details = fetcher.get_video_details(aweme_id)
        if video_details:
            aweme_detail = video_details.get('aweme_detail', {})
            print(f"视频标题: {aweme_detail.get('desc', '无标题')}")
            print(f"作者昵称: {aweme_detail.get('author', {}).get('nickname', '未知')}")
            print(f"点赞数: {aweme_detail.get('statistics', {}).get('digg_count', 0)}")

    except Exception as e:
        print(f"错误: {e}")

    print("\n=== 完整下载流程示例 ===")
    # 执行完整的下载流程
    download_path = download_douyin_video_complete(aweme_id, "downloads")

    if download_path:
        print(f"\n✅ 任务完成！视频已保存到: {download_path}")
    else:
        print("\n❌ 任务失败！")


if __name__ == "__main__":
    main()
