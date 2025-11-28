#!/usr/bin/env python3
"""
获取单个抖音视频的最新详情
使用 TikHub API 获取指定 aweme_id 的视频信息
"""

import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

def load_env():
    """加载环境变量"""
    current_dir = Path(__file__).parent
    # 从 backend/test/kol/(Tikhub)GetKOLVideosBatchByVVID/code/ 往上找到 backend/
    backend_dir = current_dir.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    print(f"当前脚本目录: {current_dir}")
    print(f"backend目录: {backend_dir}")
    print(f".env文件路径: {env_path}")
    print(f".env文件存在: {env_path.exists()}")
    if env_path.exists():
        load_dotenv(env_path)
        print("✅ 已加载.env文件")
    else:
        print("❌ .env文件不存在")

def fetch_single_video(aweme_id: str, output_dir: str = None):
    """获取单个视频的详情"""

    if output_dir is None:
        output_dir = Path(__file__).parent / "(LLM)analysisVideoByLLM"

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    load_env()
    api_key = os.getenv("tikhub_API_KEY")
    if not api_key:
        print("Error: tikhub_API_KEY not set in .env")
        return None

    url = "https://api.tikhub.io/api/v1/douyin/app/v3/fetch_multi_video_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    # 单个视频ID的payload
    payload = [aweme_id]

    print(f"正在获取视频 {aweme_id} 的最新信息...")

    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"API响应状态码: {response.status_code}")

        resp_data = response.json()

        # 保存原始响应
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        resp_file = output_dir / f"video_{aweme_id}_response_{timestamp}.json"
        with open(resp_file, "w", encoding="utf-8") as f:
            json.dump(resp_data, f, ensure_ascii=False, indent=2)

        if response.status_code == 200 and resp_data.get("code") == 200:
            # 提取视频数据
            data_obj = resp_data.get("data", {})
            aweme_details = data_obj.get("aweme_details", [])

            if aweme_details:
                vid = aweme_details[0]  # 应该只有一个视频
                stats = vid.get("statistics", {})
                aid = stats.get("aweme_id") or vid.get("aweme_id")

                if aid == aweme_id:
                    # 提取播放地址
                    video_info = vid.get("video", {})
                    play_addr = video_info.get("play_addr", {}) or video_info.get("play_addr_h264", {})
                    url_list = play_addr.get("url_list", [])
                    video_url = url_list[0] if url_list else None

                    # 提取封面
                    cover_info = video_info.get("cover", {}) or video_info.get("origin_cover", {})
                    cover_url_list = cover_info.get("url_list", [])
                    cover_url = cover_url_list[0] if cover_url_list else None

                    # 提取作者信息
                    author_info = vid.get("author", {})

                    parsed = {
                        "aweme_id": aid,
                        "desc": vid.get("desc"),
                        "statistics": stats,
                        "author": {
                            "uid": author_info.get("uid"),
                            "nickname": author_info.get("nickname"),
                            "unique_id": author_info.get("unique_id")
                        },
                        "video_url": video_url,
                        "cover_url": cover_url,
                        "raw_video_data": vid,
                        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "api_response_file": str(resp_file)
                    }

                    # 保存解析后的数据
                    result_file = output_dir / f"video_{aweme_id}_details.json"
                    with open(result_file, "w", encoding="utf-8") as f:
                        json.dump(parsed, f, ensure_ascii=False, indent=2)

                    print(f"✅ 成功获取视频信息: {aid}")
                    print(f"📁 保存到: {result_file}")
                    print(f"🎬 视频URL: {video_url[:80]}..." if video_url else "❌ 无视频URL")

                    return parsed
                else:
                    print(f"❌ 返回的视频ID不匹配: 期望 {aweme_id}, 实际 {aid}")
            else:
                print("❌ API响应中没有视频详情数据")
        else:
            print(f"❌ API调用失败: {resp_data.get('message', '未知错误')}")

    except Exception as e:
        print(f"❌ 请求异常: {e}")

    return None

def download_video_from_details(video_details: dict, output_dir: str = None):
    """从视频详情中下载视频"""

    if output_dir is None:
        output_dir = Path(__file__).parent / "(LLM)analysisVideoByLLM"

    output_dir = Path(output_dir)

    aweme_id = video_details.get("aweme_id")
    video_url = video_details.get("video_url")

    if not video_url:
        print("❌ 无视频URL，无法下载")
        return False

    output_file = output_dir / f"{aweme_id}_540p_latest.mp4"

    print(f"🎬 开始下载视频: {aweme_id}")
    print(f"📂 保存路径: {output_file}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.douyin.com/"
    }

    try:
        response = requests.get(video_url, headers=headers, stream=True, timeout=60)

        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))

            with open(output_file, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(".1f", end='', flush=True)

            # 保存视频信息
            info_file = output_dir / f"{aweme_id}_info_latest.json"
            video_info = {
                "aweme_id": aweme_id,
                "title": video_details.get('desc', ''),
                "author": video_details.get('author', {}),
                "statistics": video_details.get('statistics', {}),
                "video_url": video_url,
                "download_path": str(output_file),
                "file_size": downloaded,
                "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(video_info, f, ensure_ascii=False, indent=2)

            print(f"\n✅ 下载完成! 文件大小: {downloaded} bytes")
            print(f"📄 信息文件: {info_file}")
            return True

        else:
            print(f"❌ 下载失败，HTTP状态码: {response.status_code}")
            print(f"📄 响应内容: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ 下载出错: {e}")
        return False

def main():
    aweme_id = "7509416656843902271"

    print("🔍 获取抖音视频最新详情")
    print("=" * 50)

    # 获取视频详情
    video_details = fetch_single_video(aweme_id)

    if video_details:
        print("\n📹 视频信息:")
        print(f"   ID: {video_details['aweme_id']}")
        print(f"   标题: {video_details['desc'][:50]}...")
        print(f"   作者: {video_details['author']['nickname']}")
        print(f"   播放量: {video_details['statistics'].get('play_count', 'N/A')}")

        # 下载视频
        print("\n⬇️  下载视频")
        print("=" * 50)
        success = download_video_from_details(video_details)

        if success:
            print("\n🎉 任务完成!")
        else:
            print("\n❌ 下载失败，请检查网络或CDN状态")
    else:
        print("❌ 无法获取视频详情")

if __name__ == "__main__":
    main()
