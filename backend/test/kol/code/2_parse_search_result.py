#!/usr/bin/env python3
"""
脚本名称: 2_parse_search_result.py
功能描述: 解析搜索结果，提取核心信息（视频/图文、URL、作者等）
输入: ../output/1_search_result_*.json
输出: ../output/2_parsed_result_{timestamp}.json
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def find_latest_search_result():
    """查找最新的搜索结果文件"""
    output_dir = Path(__file__).resolve().parent.parent / "output"
    
    search_files = list(output_dir.glob("1_search_result_*.json"))
    if not search_files:
        raise RuntimeError("未找到搜索结果文件")
    
    # 按修改时间排序，取最新的
    latest_file = max(search_files, key=lambda f: f.stat().st_mtime)
    return latest_file


def extract_video_urls(video_data: dict) -> dict:
    """提取视频的所有下载URL"""
    urls = {
        "play_urls": [],  # 播放地址
        "download_urls": [],  # 下载地址
        "cover_urls": []  # 封面地址
    }
    
    try:
        video = video_data.get("video", {})
        
        # 播放地址
        play_addr = video.get("play_addr", {})
        if play_addr:
            urls["play_urls"] = play_addr.get("url_list", [])
        
        # 下载地址
        download_addr = video.get("download_addr", {})
        if download_addr:
            urls["download_urls"] = download_addr.get("url_list", [])
        
        # 封面地址
        cover = video.get("cover", {})
        if cover:
            urls["cover_urls"] = cover.get("url_list", [])
        
        # 动态封面
        dynamic_cover = video.get("dynamic_cover", {})
        if dynamic_cover:
            dynamic_urls = dynamic_cover.get("url_list", [])
            if dynamic_urls:
                urls["cover_urls"].extend(dynamic_urls)
    
    except Exception as e:
        print(f"  警告: 提取视频URL失败 - {e}")
    
    return urls


def extract_image_urls(images_data: list) -> list:
    """提取图文的所有图片URL"""
    all_urls = []
    
    try:
        for img in images_data:
            if not isinstance(img, dict):
                continue
            
            # 提取所有可能的URL字段
            url_list = img.get("url_list", [])
            download_url_list = img.get("download_url_list", [])
            
            all_urls.extend(url_list)
            all_urls.extend(download_url_list)
    
    except Exception as e:
        print(f"  警告: 提取图片URL失败 - {e}")
    
    return all_urls


def parse_aweme_item(item: dict) -> dict:
    """解析单个抖音内容项"""
    aweme_info = item.get("aweme_info", {})
    
    # 基础信息
    aweme_id = aweme_info.get("aweme_id", "")
    desc = aweme_info.get("desc", "")
    create_time = aweme_info.get("create_time", 0)
    
    # 作者信息
    author = aweme_info.get("author", {})
    author_info = {
        "uid": author.get("uid", ""),
        "sec_uid": author.get("sec_uid", ""),
        "nickname": author.get("nickname", ""),
        "signature": author.get("signature", ""),
        "follower_count": author.get("follower_count", 0),
        "total_favorited": author.get("total_favorited", 0),
        "aweme_count": author.get("aweme_count", 0),
    }
    
    # 统计信息
    statistics = aweme_info.get("statistics", {})
    stats = {
        "digg_count": statistics.get("digg_count", 0),
        "comment_count": statistics.get("comment_count", 0),
        "share_count": statistics.get("share_count", 0),
        "play_count": statistics.get("play_count", 0),
        "collect_count": statistics.get("collect_count", 0),
    }
    
    # 判断内容类型
    aweme_type = aweme_info.get("aweme_type", 0)
    images = aweme_info.get("images", [])
    
    if images and len(images) > 0:
        content_type = "图文"
        media_urls = extract_image_urls(images)
        video_urls = {}
    else:
        content_type = "视频"
        video_urls = extract_video_urls(aweme_info)
        media_urls = []
    
    return {
        "aweme_id": aweme_id,
        "content_type": content_type,
        "desc": desc,
        "create_time": create_time,
        "create_time_readable": datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S") if create_time > 0 else "",
        "author": author_info,
        "statistics": stats,
        "video_urls": video_urls if content_type == "视频" else None,
        "image_urls": media_urls if content_type == "图文" else None,
        "aweme_type": aweme_type,
        "has_full_details": bool(aweme_info.get("video") or aweme_info.get("images"))
    }


def parse_search_result(search_file: Path) -> dict:
    """解析搜索结果"""
    print(f"正在解析: {search_file.name}")
    
    with search_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 提取搜索结果列表
    response_data = data.get("data", {}).get("data", {})
    items = response_data.get("data", [])
    
    print(f"找到 {len(items)} 个结果")
    
    parsed_items = []
    ai_result = None
    
    for idx, item in enumerate(items, 1):
        item_type = item.get("type")
        
        # type=999 是AI生成的回答
        if item_type == 999:
            print(f"[{idx}] AI生成内容 (type=999)")
            # 提取AI回答中的达人名称
            try:
                raw_data = item.get("dynamic_patch", {}).get("raw_data", "")
                if raw_data:
                    ai_result = {
                        "type": "AI回答",
                        "raw_data": raw_data
                    }
            except:
                pass
            continue
        
        # type=1 是视频
        elif item_type == 1:
            try:
                parsed = parse_aweme_item(item)
                parsed_items.append(parsed)
                
                print(f"[{idx}] {parsed['content_type']} - {parsed['author']['nickname']} - {parsed['desc'][:50]}...")
                print(f"      粉丝: {parsed['author']['follower_count']:,} | 点赞: {parsed['statistics']['digg_count']:,}")
                
            except Exception as e:
                print(f"[{idx}] 解析失败: {e}")
                continue
        
        # type=6 是商品
        elif item_type == 6:
            print(f"[{idx}] 商品 (type=6) - 跳过")
            continue
        
        else:
            print(f"[{idx}] 未知类型 (type={item_type}) - 跳过")
            continue
    
    return {
        "parse_time": datetime.now().isoformat(),
        "source_file": str(search_file),
        "total_items": len(items),
        "parsed_video_count": len(parsed_items),
        "ai_result": ai_result,
        "items": parsed_items
    }


def save_parsed_result(parsed_data: dict):
    """保存解析结果"""
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_file = output_dir / f"2_parsed_result_{timestamp}.json"
    
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(parsed_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 解析结果已保存: {output_file}")
    
    # 生成需要获取详情的aweme_id列表
    aweme_ids = [item["aweme_id"] for item in parsed_data["items"] if not item["has_full_details"]]
    
    if aweme_ids:
        ids_file = output_dir / f"2_aweme_ids_for_detail_{timestamp}.txt"
        with ids_file.open("w", encoding="utf-8") as f:
            f.write("\n".join(aweme_ids))
        
        print(f"✓ 需要获取详情的ID列表已保存: {ids_file}")
        print(f"  共 {len(aweme_ids)} 个视频需要获取详情")
    else:
        print("✓ 所有内容都包含完整详情，无需额外获取")
    
    return str(output_file)


def generate_author_summary(parsed_data: dict):
    """生成作者汇总信息"""
    items = parsed_data["items"]
    
    # 按粉丝数排序
    sorted_by_followers = sorted(items, key=lambda x: x["author"]["follower_count"], reverse=True)
    
    print("\n" + "="*80)
    print("达人排行榜（按粉丝数）")
    print("="*80)
    
    for idx, item in enumerate(sorted_by_followers[:20], 1):
        author = item["author"]
        stats = item["statistics"]
        
        print(f"\n[{idx}] {author['nickname']}")
        print(f"    - 粉丝数: {author['follower_count']:,}")
        print(f"    - 获赞数: {author['total_favorited']:,}")
        print(f"    - 作品数: {author['aweme_count']:,}")
        print(f"    - 本视频点赞: {stats['digg_count']:,}")
        print(f"    - UID: {author['uid']}")
        print(f"    - 签名: {author['signature'][:50]}..." if len(author['signature']) > 50 else f"    - 签名: {author['signature']}")


def main():
    """主函数"""
    print("="*80)
    print("搜索结果解析脚本")
    print("="*80)
    
    try:
        # 1. 查找最新搜索结果
        print("\n[1/3] 查找搜索结果文件...")
        search_file = find_latest_search_result()
        print(f"✓ 找到文件: {search_file.name}")
        
        # 2. 解析结果
        print("\n[2/3] 解析搜索结果...")
        parsed_data = parse_search_result(search_file)
        
        # 3. 保存结果
        print("\n[3/3] 保存解析结果...")
        output_file = save_parsed_result(parsed_data)
        
        # 4. 生成作者汇总
        generate_author_summary(parsed_data)
        
        print("\n" + "="*80)
        print("✓ 解析完成！")
        print("="*80)
        print(f"\n输出文件: {output_file}")
        print("\n后续步骤:")
        print("  - 运行 3_fetch_video_details.py 获取视频详情")
        print("  - 分析达人信息，确定要调研的20位达人")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

