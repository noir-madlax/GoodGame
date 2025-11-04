#!/usr/bin/env python3
"""
抖音视频抓取脚本 - 独立版本
从指定的抖音视频 URL 获取视频信息和下载视频文件
"""
import os
import sys
import json
import time
import re
from pathlib import Path
import requests
from typing import Optional, Tuple
from urllib.parse import urlparse


# TikHub API 配置
TIKHUB_API_KEY = os.getenv("tikhub_API_KEY", "")  # 从环境变量获取
TIKHUB_BASE_URL = "https://api.tikhub.io/api/v1"  # 正确的 API 路径


class SimpleLogger:
    """简化的日志类"""
    def info(self, msg):
        print(f"[INFO] {msg}")
    
    def error(self, msg, exc_info=False):
        print(f"[ERROR] {msg}")
        if exc_info:
            import traceback
            traceback.print_exc()


log = SimpleLogger()


def load_api_key_from_env() -> str:
    """从 .env 文件加载 API Key"""
    # 尝试从多个位置查找 .env 文件
    env_paths = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]
    
    api_key = os.getenv("tikhub_API_KEY", "")
    if api_key:
        return api_key
    
    # 手动解析 .env 文件
    for env_path in env_paths:
        if not env_path.exists():
            continue
        
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        if key.strip() == "tikhub_API_KEY":
                            return value.strip().strip('"\'')
        except Exception as e:
            log.error(f"读取 .env 文件失败: {e}")
    
    return ""


def extract_video_id_from_url(url: str) -> str:
    """从 URL 中提取视频 ID
    
    支持格式:
    - https://www.douyin.com/jingxuan/search/...?modal_id=7521959446235548985&type=general
    - https://www.douyin.com/video/7499608775142608186
    """
    # 尝试从 modal_id 参数提取
    modal_id_match = re.search(r'modal_id=(\d+)', url)
    if modal_id_match:
        return modal_id_match.group(1)
    
    # 尝试从路径提取
    path_match = re.search(r'/(?:video|note)/(\d+)', url)
    if path_match:
        return path_match.group(1)
    
    raise ValueError(f"无法从 URL 提取视频 ID: {url}")


class DouyinVideoFetcher:
    """抖音视频获取器 - 独立实现"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = TIKHUB_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def fetch_video_info(self, aweme_id: str) -> dict:
        """获取视频详细信息
        
        尝试多个端点:
        1. /douyin/app/v3/fetch_one_video (V3 API)
        2. /douyin/web/fetch_one_video (Web API)
        """
        endpoints = [
            f"{self.base_url}/douyin/app/v3/fetch_one_video",
            f"{self.base_url}/douyin/web/fetch_one_video",
        ]
        
        last_error = None
        for url in endpoints:
            try:
                params = {"aweme_id": aweme_id}
                log.info(f"尝试端点: {url}")
                
                response = requests.get(url, params=params, headers=self.headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                # 检查 API 返回状态
                if result.get("code") == 200:
                    log.info(f"✓ 端点成功: {url}")
                    return result.get("data")
                else:
                    log.info(f"API 返回错误: {result.get('message', '未知错误')}")
                    last_error = RuntimeError(f"API 返回错误: {result.get('message', '未知错误')}")
            
            except requests.RequestException as e:
                log.info(f"端点失败: {url} - {e}")
                last_error = e
                continue
        
        if last_error:
            raise RuntimeError(f"所有端点都失败: {last_error}")
        
        raise RuntimeError("无法获取视频信息")


class VideoDownloader:
    """视频下载器 - 独立实现"""
    
    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def download_video(self, url: str, filename: str) -> Optional[str]:
        """下载视频文件"""
        file_path = self.download_dir / filename
        
        try:
            # 发送 HEAD 请求获取文件信息
            head_response = requests.head(url, headers=self.headers, timeout=30)
            content_length = head_response.headers.get('Content-Length')
            file_size = int(content_length) if content_length else 0
            
            log.info(f"开始下载视频: {filename}")
            if file_size > 0:
                log.info(f"文件大小: {file_size / (1024 * 1024):.2f} MB")
            
            # 下载文件
            response = requests.get(url, headers=self.headers, stream=True, timeout=60)
            response.raise_for_status()
            
            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 显示下载进度
                        if file_size > 0:
                            progress = (downloaded_size / file_size) * 100
                            print(f"\r下载进度: {progress:.1f}% ({downloaded_size / (1024 * 1024):.2f}/{file_size / (1024 * 1024):.2f} MB)", end='')
            
            print()  # 换行
            log.info(f"下载完成: {file_path}")
            return str(file_path)
        
        except Exception as e:
            log.error(f"下载失败: {e}")
            return None


def fetch_video_info(video_id: str, api_key: str) -> dict:
    """获取视频详细信息"""
    log.info(f"正在获取视频信息: {video_id}")
    
    fetcher = DouyinVideoFetcher(api_key)
    video_details = fetcher.fetch_video_info(video_id)
    
    if not video_details:
        raise RuntimeError(f"无法获取视频 {video_id} 的详细信息")
    
    return video_details


def download_video_file(video_id: str, video_details: dict, output_dir: Path) -> str:
    """下载视频文件到指定目录"""
    log.info(f"正在下载视频文件: {video_id}")

    # 从视频详情中提取下载链接
    aweme_detail = video_details.get("aweme_detail", {})
    video_info = aweme_detail.get("video", {})

    # 优先选择可用的下载链接（根据用户反馈）
    # 尝试 play_addr_265 中的第一个链接（通常是 api-play.amemv.com 域名）
    play_addr_265 = video_info.get("play_addr_265", {})
    url_list = play_addr_265.get("url_list", [])

    download_url = None
    if url_list:
        # 优先选择 api-play.amemv.com 域名的链接
        for url in url_list:
            if "api-play.amemv.com" in url and "is_play_url=1" in url:
                download_url = url
                break

        # 如果没有找到，尝试其他链接
        if not download_url:
            download_url = url_list[0]

    # 如果没找到，尝试其他字段
    if not download_url:
        play_addr = video_info.get("play_addr", {})
        url_list = play_addr.get("url_list", [])
        if url_list:
            download_url = url_list[0]

    if not download_url:
        raise RuntimeError(f"无法找到视频 {video_id} 的下载链接")

    log.info(f"下载链接: {download_url}")
    
    # 创建下载器并下载视频
    video_dir = output_dir / video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    
    downloader = VideoDownloader(download_dir=str(video_dir))
    filename = f"{video_id}.mp4"
    
    file_path = downloader.download_video(download_url, filename=filename)
    
    if not file_path:
        raise RuntimeError(f"视频 {video_id} 下载失败")
    
    return file_path


def save_video_info(video_details: dict, output_dir: Path, video_id: str):
    """保存视频信息到 JSON 文件"""
    video_dir = output_dir / video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    
    info_file = video_dir / "video_info.json"
    
    with info_file.open("w", encoding="utf-8") as f:
        json.dump(video_details, f, ensure_ascii=False, indent=2)
    
    log.info(f"视频信息已保存到: {info_file}")
    return str(info_file)


def create_summary(video_details: dict, video_id: str, output_dir: Path):
    """创建视频摘要信息"""
    aweme_detail = video_details.get("aweme_detail", {})
    
    # 提取关键信息
    desc = aweme_detail.get("desc", "")
    author = aweme_detail.get("author", {})
    nickname = author.get("nickname", "未知")
    statistics = aweme_detail.get("statistics", {})
    
    summary = {
        "video_id": video_id,
        "title": desc,
        "author": nickname,
        "author_id": author.get("uid", ""),
        "create_time": aweme_detail.get("create_time", 0),
        "duration": aweme_detail.get("duration", 0),
        "statistics": {
            "digg_count": statistics.get("digg_count", 0),  # 点赞数
            "comment_count": statistics.get("comment_count", 0),  # 评论数
            "share_count": statistics.get("share_count", 0),  # 分享数
            "play_count": statistics.get("play_count", 0),  # 播放量
        }
    }
    
    video_dir = output_dir / video_id
    summary_file = video_dir / "summary.json"
    
    with summary_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    log.info(f"视频摘要已保存到: {summary_file}")
    
    # 打印摘要信息到控制台
    print("\n" + "=" * 60)
    print("视频信息摘要:")
    print("=" * 60)
    print(f"视频ID: {video_id}")
    print(f"标题: {desc}")
    print(f"作者: {nickname}")
    print(f"时长: {summary['duration']/1000:.1f}秒")
    print(f"点赞数: {summary['statistics']['digg_count']:,}")
    print(f"评论数: {summary['statistics']['comment_count']:,}")
    print(f"分享数: {summary['statistics']['share_count']:,}")
    print("=" * 60 + "\n")
    
    return summary


def verify_video_file(video_path: str) -> dict:
    """验证视频文件是否可用"""
    path = Path(video_path)
    
    if not path.exists():
        return {"valid": False, "error": "文件不存在"}
    
    file_size = path.stat().st_size
    
    # 检查文件大小（至少应该大于 100KB）
    if file_size < 100 * 1024:
        return {"valid": False, "error": f"文件过小: {file_size} bytes"}
    
    # 检查文件扩展名
    if path.suffix.lower() != ".mp4":
        return {"valid": False, "error": f"文件格式错误: {path.suffix}"}
    
    return {
        "valid": True,
        "file_size": file_size,
        "file_size_mb": file_size / (1024 * 1024),
    }


def main():
    """主函数"""
    # 目标视频 URL（从截图提取）
    video_url = "https://www.douyin.com/jingxuan/search/%E5%8D%97%E9%9F%B3%E5%86%8D%E8%AE%B8?aid=da4233b4-fdd7-4760-b96f-485fc33a045e&modal_id=7523787273016839434&type=general"
    
    # 输出目录
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 加载 API Key
    api_key = load_api_key_from_env()
    if not api_key:
        print("错误: 未找到 tikhub_API_KEY")
        print("请在 .env 文件中设置 tikhub_API_KEY=your_api_key")
        sys.exit(1)
    
    print(f"\n开始处理视频: {video_url}\n")
    print(f"API Key: {api_key[:20]}..." if len(api_key) > 20 else f"API Key: {api_key}")
    print()
    
    try:
        # 1. 提取视频 ID
        print("步骤 1: 提取视频 ID...")
        video_id = extract_video_id_from_url(video_url)
        print(f"✓ 视频 ID: {video_id}\n")
        
        # 2. 获取视频信息
        print("步骤 2: 获取视频详细信息...")
        video_details = fetch_video_info(video_id, api_key)
        print("✓ 视频信息获取成功\n")
        
        # 3. 保存视频信息
        print("步骤 3: 保存视频信息...")
        info_file = save_video_info(video_details, output_dir, video_id)
        print(f"✓ 视频信息已保存: {info_file}\n")
        
        # 4. 创建摘要
        print("步骤 4: 创建视频摘要...")
        summary = create_summary(video_details, video_id, output_dir)
        print("✓ 视频摘要已创建\n")
        
        # 5. 下载视频文件
        print("步骤 5: 下载视频文件...")
        video_file_path = download_video_file(video_id, video_details, output_dir)
        print(f"✓ 视频文件已下载: {video_file_path}\n")
        
        # 6. 验证视频文件
        print("步骤 6: 验证视频文件...")
        verification = verify_video_file(video_file_path)
        
        if verification["valid"]:
            print("✓ 视频文件验证通过")
            print(f"  - 文件大小: {verification['file_size_mb']:.2f} MB")
            
            # 检查视频时长是否满足要求（至少15秒）
            duration_sec = summary.get("duration", 0) / 1000
            if duration_sec >= 15:
                print(f"  - 视频时长: {duration_sec:.1f}秒 ✓")
            else:
                print(f"  - ⚠️  视频时长: {duration_sec:.1f}秒 (少于15秒)")
        else:
            print(f"✗ 视频文件验证失败: {verification['error']}")
        
        print("\n" + "=" * 60)
        print("任务完成! 所有文件已保存到:")
        print(f"  {output_dir / video_id}")
        print("=" * 60 + "\n")
        
        # 返回结果路径
        return {
            "video_id": video_id,
            "video_file": video_file_path,
            "info_file": info_file,
            "output_dir": str(output_dir / video_id),
            "verification": verification,
        }
        
    except Exception as e:
        log.error(f"处理失败: {e}", exc_info=True)
        print(f"\n✗ 错误: {e}\n")
        raise


if __name__ == "__main__":
    result = main()
