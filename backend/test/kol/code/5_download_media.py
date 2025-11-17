#!/usr/bin/env python3
"""
脚本名称: 5_download_media.py
功能描述: 下载搜索结果中的视频和图片到本地，用于后续Gemini分析
输入: ../output/2_parsed_result_*.json
输出: ../output/file/{aweme_id}/目录下的视频和图片文件
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def load_env_vars():
    """加载环境变量"""
    project_root = Path(__file__).resolve().parents[4]
    backend_env = project_root / "backend/.env"
    
    if load_dotenv and backend_env.exists():
        load_dotenv(backend_env)


def find_latest_parsed_result():
    """查找最新的解析结果文件"""
    output_dir = Path(__file__).resolve().parent.parent / "output"
    
    parsed_files = list(output_dir.glob("2_parsed_result_*.json"))
    if not parsed_files:
        raise RuntimeError("未找到解析结果文件")
    
    latest_file = max(parsed_files, key=lambda f: f.stat().st_mtime)
    return latest_file


def ensure_file_dir(aweme_id: str) -> Path:
    """创建文件存储目录"""
    output_dir = Path(__file__).resolve().parent.parent / "output" / "file" / aweme_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def download_file(url: str, save_path: Path, timeout: int = 60) -> bool:
    """下载文件到本地
    
    参数:
        url: 下载链接
        save_path: 保存路径
        timeout: 超时时间（秒）
        
    返回:
        是否下载成功
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
        if resp.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            print(f"  ✗ HTTP {resp.status_code}: {url[:80]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"  ✗ 下载失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 未知错误: {e}")
        return False


def try_download_with_fallback(urls: list, save_path: Path, file_type: str) -> bool:
    """尝试多个URL下载，直到成功
    
    参数:
        urls: URL列表
        save_path: 保存路径
        file_type: 文件类型（video/image）
        
    返回:
        是否有任一URL下载成功
    """
    for idx, url in enumerate(urls):
        print(f"  尝试 {file_type} URL #{idx+1}/{len(urls)}")
        if download_file(url, save_path):
            print(f"  ✓ {file_type} 下载成功: {save_path.name}")
            return True
    
    print(f"  ✗ 所有 {file_type} URL 均下载失败")
    return False


def download_video(item: dict, file_dir: Path) -> Optional[Path]:
    """下载视频文件
    
    参数:
        item: 帖子数据（包含video_urls）
        file_dir: 存储目录
        
    返回:
        视频文件路径（如果下载成功）
    """
    video_urls = item.get("video_urls")
    if not video_urls:
        return None
    
    # 优先使用 play_urls，其次 download_urls
    play_urls = video_urls.get("play_urls", [])
    download_urls = video_urls.get("download_urls", [])
    
    all_urls = play_urls + download_urls
    if not all_urls:
        return None
    
    # 保存为 video.mp4
    video_path = file_dir / "video.mp4"
    
    if try_download_with_fallback(all_urls, video_path, "视频"):
        return video_path
    
    return None


def download_images(item: dict, file_dir: Path) -> list[Path]:
    """下载所有图片文件
    
    参数:
        item: 帖子数据（包含image_urls）
        file_dir: 存储目录
        
    返回:
        成功下载的图片路径列表
    """
    image_urls = item.get("image_urls")
    if not image_urls:
        return []
    
    downloaded_images = []
    
    # 图片URL是一个列表，每4个URL为一组（不同格式的同一张图）
    # 我们按组处理，每组取第一个成功下载的
    total_urls = len(image_urls)
    
    # 根据URL模式推断：通常是 [heic, jpeg, webp, jpeg] 这样的4个一组
    # 我们简化处理：每4个URL尝试下载第一个成功的
    group_size = 4
    num_images = total_urls // group_size
    
    for img_idx in range(num_images):
        start_idx = img_idx * group_size
        end_idx = start_idx + group_size
        url_group = image_urls[start_idx:end_idx]
        
        # 扩展名优先级：jpeg > webp > heic
        sorted_urls = []
        for url in url_group:
            if '.jpeg' in url.lower() or '.jpg' in url.lower():
                sorted_urls.insert(0, url)
            elif '.webp' in url.lower():
                sorted_urls.insert(len(sorted_urls)//2 if sorted_urls else 0, url)
            else:
                sorted_urls.append(url)
        
        # 确定文件扩展名
        ext = ".jpg"
        first_url = sorted_urls[0] if sorted_urls else ""
        if ".png" in first_url.lower():
            ext = ".png"
        elif ".webp" in first_url.lower():
            ext = ".webp"
        
        image_path = file_dir / f"image_{img_idx:03d}{ext}"
        
        print(f"  下载图片 {img_idx + 1}/{num_images}")
        if try_download_with_fallback(sorted_urls, image_path, "图片"):
            downloaded_images.append(image_path)
    
    return downloaded_images


def process_item(item: dict) -> dict:
    """处理单个帖子，下载媒体文件
    
    参数:
        item: 帖子数据
        
    返回:
        包含下载结果的字典
    """
    aweme_id = item.get("aweme_id")
    content_type = item.get("content_type")
    
    print(f"\n处理帖子: {aweme_id} ({content_type})")
    
    # 创建存储目录
    file_dir = ensure_file_dir(aweme_id)
    
    # 保存帖子元数据
    metadata = {
        "aweme_id": aweme_id,
        "content_type": content_type,
        "desc": item.get("desc"),
        "author": item.get("author"),
        "statistics": item.get("statistics"),
    }
    
    metadata_path = file_dir / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    result = {
        "aweme_id": aweme_id,
        "content_type": content_type,
        "file_dir": str(file_dir),
        "metadata_path": str(metadata_path),
    }
    
    # 根据内容类型下载
    if content_type == "视频":
        video_path = download_video(item, file_dir)
        result["video_path"] = str(video_path) if video_path else None
        result["success"] = video_path is not None
    elif content_type == "图文":
        image_paths = download_images(item, file_dir)
        result["image_paths"] = [str(p) for p in image_paths]
        result["image_count"] = len(image_paths)
        result["success"] = len(image_paths) > 0
    else:
        result["success"] = False
        result["error"] = f"未知内容类型: {content_type}"
    
    return result


def main() -> None:
    print("=" * 80)
    print("媒体文件下载脚本")
    print("=" * 80)
    
    # 加载环境变量
    load_env_vars()
    
    # 查找最新的解析结果文件
    print("\n[1/4] 查找解析结果文件...")
    parsed_file = find_latest_parsed_result()
    print(f"✓ 找到文件: {parsed_file.name}")
    
    # 读取解析结果
    print("\n[2/4] 读取解析结果...")
    with open(parsed_file, 'r', encoding='utf-8') as f:
        parsed_data = json.load(f)
    
    items = parsed_data.get("items", [])
    print(f"✓ 共 {len(items)} 个帖子待处理")
    
    # 处理每个帖子
    print("\n[3/4] 下载媒体文件...")
    results = []
    success_count = 0
    
    for idx, item in enumerate(items, 1):
        print(f"\n进度: {idx}/{len(items)}")
        result = process_item(item)
        results.append(result)
        
        if result.get("success"):
            success_count += 1
    
    # 保存下载结果
    print("\n[4/4] 保存下载结果...")
    output_dir = Path(__file__).resolve().parent.parent / "output"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    result_file = output_dir / f"5_download_result_{stamp}.json"
    
    summary = {
        "download_time": stamp,
        "source_file": str(parsed_file),
        "total_items": len(items),
        "success_count": success_count,
        "failed_count": len(items) - success_count,
        "results": results
    }
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 下载结果已保存: {result_file}")
    
    # 打印统计信息
    print("\n" + "=" * 80)
    print("下载统计")
    print("=" * 80)
    print(f"总帖子数: {len(items)}")
    print(f"成功下载: {success_count}")
    print(f"下载失败: {len(items) - success_count}")
    print(f"成功率: {success_count/len(items)*100:.1f}%")


if __name__ == "__main__":
    main()

