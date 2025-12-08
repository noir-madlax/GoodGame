#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小红书搜索笔记接口测试脚本

用途:
- 调用 TikHub 的小红书搜索笔记接口
- 根据筛选条件搜索笔记
- 记录完整的请求和响应

支持两个接口版本:
1. V1 接口: /xiaohongshu/app/search_notes (已验证可用)
2. V2 接口: /xiaohongshu/app/search_notes_v2 (文档: https://docs.tikhub.io/384045852e0)

V1 接口参数说明:
- keyword: 搜索关键词
- page: 页码，默认为1
- sort_type: 排序方式
    - general: 综合排序（默认）
    - popularity_descending: 最热排序
    - time_descending: 最新排序
- filter_note_type: 笔记类型
    - 不限: 综合笔记（默认）
    - 视频: 视频笔记
    - 图文: 图文笔记
- filter_note_time: 发布时间
    - 不限: 不限（默认）
    - 一天内: 一天内
    - 一周内: 一周内
    - 半年内: 半年内

V2 接口参数说明:
- keyword: 搜索关键词
- page: 页码，默认为1
- sort: 排序方式
    - general: 综合排序（默认）
    - popularity_descending: 最热排序
    - time_descending: 最新排序
    - comment_descending: 最多评论
    - collect_descending: 最多收藏
- noteType: 笔记类型
    - _0: 综合笔记（默认）
    - _1: 视频笔记
    - _2: 图文笔记
    - _3: 直播
- noteTime: 发布时间
    - "": 不限（默认）
    - 一天内: 一天内
    - 一周内: 一周内
    - 半年内: 半年内
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional


def load_api_key() -> str:
    """
    从环境变量加载 TikHub API Key
    """
    # 定位到 backend/.env 文件
    backend_dir = Path(__file__).parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 从 {env_path} 加载环境变量")
    else:
        print(f"⚠️ 未找到 .env 文件: {env_path}")
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置，请在 {env_path} 文件中配置")
    
    return api_key


def search_notes_v1(
    api_key: str,
    keyword: str,
    page: int = 1,
    sort_type: str = "general",
    filter_note_type: str = "不限",
    filter_note_time: str = "不限"
) -> Dict[str, Any]:
    """
    调用小红书搜索笔记 V1 接口（已验证可用）
    
    Args:
        api_key: TikHub API Key
        keyword: 搜索关键词
        page: 页码，默认为1
        sort_type: 排序方式
            - general: 综合排序（默认）
            - popularity_descending: 最热排序
            - time_descending: 最新排序
        filter_note_type: 笔记类型
            - 不限: 综合笔记（默认）
            - 视频: 视频笔记
            - 图文: 图文笔记
        filter_note_time: 发布时间
            - 不限: 不限（默认）
            - 一天内: 一天内
            - 一周内: 一周内
            - 半年内: 半年内
    
    Returns:
        API 响应数据
    """
    url = "https://api.tikhub.io/api/v1/xiaohongshu/app/search_notes"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    params = {
        'keyword': keyword,
        'page': page,
        'sort_type': sort_type,
        'filter_note_type': filter_note_type,
        'filter_note_time': filter_note_time
    }
    
    print(f"\n{'='*60}")
    print("📡 发送请求")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"请求参数:")
    print(json.dumps(params, ensure_ascii=False, indent=2))
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"\nHTTP 状态码: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ HTTP 请求失败: {response.text[:500]}")
            return {
                "error": f"HTTP {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return {"error": str(e)}


def save_result(
    data: Dict[str, Any],
    output_dir: str,
    filename: str
) -> str:
    """
    保存结果到文件
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 结果已保存: {filepath}")
    return filepath


def analyze_response(result: Dict[str, Any]) -> None:
    """
    分析响应数据结构
    """
    print(f"\n{'='*60}")
    print("📊 响应分析")
    print(f"{'='*60}")
    
    # 顶层字段
    print("\n【顶层字段】")
    for key in result.keys():
        value = result[key]
        if isinstance(value, dict):
            print(f"  - {key}: <dict> (包含 {len(value)} 个字段)")
        elif isinstance(value, list):
            print(f"  - {key}: <list> (包含 {len(value)} 个元素)")
        elif isinstance(value, str) and len(value) > 100:
            print(f"  - {key}: <str> (长度 {len(value)})")
        else:
            print(f"  - {key}: {value}")
    
    # 检查 data 字段
    if 'data' in result:
        data = result['data']
        print("\n【data 字段结构】")
        if isinstance(data, dict):
            for key in data.keys():
                value = data[key]
                if isinstance(value, dict):
                    print(f"  - data.{key}: <dict> (包含 {len(value)} 个字段)")
                elif isinstance(value, list):
                    print(f"  - data.{key}: <list> (包含 {len(value)} 个元素)")
                elif isinstance(value, str) and len(value) > 100:
                    print(f"  - data.{key}: <str> (长度 {len(value)})")
                else:
                    print(f"  - data.{key}: {value}")
            
            # 检查 data.data 字段（嵌套结构）
            if 'data' in data:
                inner_data = data['data']
                print("\n【data.data 字段结构】")
                if isinstance(inner_data, dict):
                    for key in inner_data.keys():
                        value = inner_data[key]
                        if isinstance(value, dict):
                            print(f"  - data.data.{key}: <dict> (包含 {len(value)} 个字段)")
                        elif isinstance(value, list):
                            print(f"  - data.data.{key}: <list> (包含 {len(value)} 个元素)")
                        elif isinstance(value, str) and len(value) > 100:
                            print(f"  - data.data.{key}: <str> (长度 {len(value)})")
                        else:
                            print(f"  - data.data.{key}: {value}")
                    
                    # 分析 items 列表
                    if 'items' in inner_data:
                        items = inner_data['items']
                        print(f"\n【items 列表分析】")
                        print(f"  总数量: {len(items)}")
                        
                        if items:
                            # 分析第一个 item 的结构
                            first_item = items[0]
                            print(f"\n  第一个 item 的字段:")
                            if isinstance(first_item, dict):
                                for key in first_item.keys():
                                    value = first_item[key]
                                    if isinstance(value, dict):
                                        print(f"    - {key}: <dict> (包含 {len(value)} 个字段)")
                                    elif isinstance(value, list):
                                        print(f"    - {key}: <list> (包含 {len(value)} 个元素)")
                                    elif isinstance(value, str) and len(value) > 50:
                                        print(f"    - {key}: <str> (长度 {len(value)})")
                                    else:
                                        print(f"    - {key}: {value}")
                                
                                # 如果有 note 字段，分析其结构
                                if 'note' in first_item:
                                    note = first_item['note']
                                    print(f"\n  第一个 item.note 的字段:")
                                    if isinstance(note, dict):
                                        for key in note.keys():
                                            value = note[key]
                                            if isinstance(value, dict):
                                                print(f"    - note.{key}: <dict> (包含 {len(value)} 个字段)")
                                            elif isinstance(value, list):
                                                print(f"    - note.{key}: <list> (包含 {len(value)} 个元素)")
                                            elif isinstance(value, str) and len(value) > 50:
                                                print(f"    - note.{key}: <str> (长度 {len(value)})")
                                            else:
                                                print(f"    - note.{key}: {value}")


def print_notes_summary(result: Dict[str, Any]) -> None:
    """
    打印笔记摘要信息
    """
    print(f"\n{'='*60}")
    print("📝 笔记摘要")
    print(f"{'='*60}")
    
    try:
        data = result.get('data', {})
        inner_data = data.get('data', {})
        items = inner_data.get('items', [])
        
        if not items:
            print("未找到笔记数据")
            return
        
        # 统计笔记类型
        type_counts = {}
        for item in items:
            note = item.get('note', {})
            note_type = note.get('type', 'unknown')
            type_counts[note_type] = type_counts.get(note_type, 0) + 1
        
        print(f"\n【笔记类型统计】")
        for t, c in type_counts.items():
            print(f"  - {t}: {c} 条")
        
        for i, item in enumerate(items[:10], 1):  # 显示前10条
            note = item.get('note', {})
            user = note.get('user', {})
            
            # 获取发布时间
            corner_tags = note.get('corner_tag_info', [])
            publish_time = "N/A"
            for tag in corner_tags:
                if tag.get('type') == 'publish_time':
                    publish_time = tag.get('text', 'N/A')
                    break
            
            print(f"\n【笔记 {i}】")
            print(f"  ID: {note.get('id', 'N/A')}")
            print(f"  标题: {note.get('title', note.get('display_title', 'N/A'))[:50]}")
            print(f"  类型: {note.get('type', 'N/A')}")
            print(f"  作者: {user.get('nickname', 'N/A')} (userid: {user.get('userid', 'N/A')})")
            print(f"  点赞数: {note.get('liked_count', 'N/A')}")
            print(f"  评论数: {note.get('comments_count', 'N/A')}")
            print(f"  收藏数: {note.get('collected_count', 'N/A')}")
            print(f"  分享数: {note.get('shared_count', 'N/A')}")
            print(f"  发布时间: {publish_time}")
            
            # 如果是视频，显示视频信息
            video_info = note.get('video_info_v2', {})
            if video_info:
                media = video_info.get('media', {})
                video = media.get('video', {})
                print(f"  视频时长: {video.get('duration', 'N/A')} 秒")
                print(f"  视频尺寸: {video.get('width', 'N/A')}x{video.get('height', 'N/A')}")
            
        if len(items) > 10:
            print(f"\n... 还有 {len(items) - 10} 条笔记未显示")
            
    except Exception as e:
        print(f"解析笔记数据失败: {e}")


def main():
    print("=" * 60)
    print("小红书搜索笔记 V2 接口测试")
    print("=" * 60)
    
    try:
        api_key = load_api_key()
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # 设置输出目录
    script_dir = Path(__file__).parent
    output_dir = script_dir / "output"
    input_dir = script_dir / "input"
    
    # 搜索参数（根据截图中的筛选条件）
    # 截图显示: 关键词=抱枕, 排序=最多评论, 笔记类型=不限, 发布时间=半年内
    # 注意: V1 接口不支持"最多评论"排序，使用综合排序代替
    search_params = {
        "keyword": "抱枕",           # 搜索关键词
        "page": 1,                   # 第一页
        "sort_type": "general",      # 综合排序（V1不支持comment_descending）
        "filter_note_type": "不限",   # 不限（综合笔记）
        "filter_note_time": "半年内"  # 半年内
    }
    
    # 保存请求参数
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_result(
        search_params,
        str(input_dir),
        f"request_params_{timestamp}.json"
    )
    
    # 调用 V1 API
    result = search_notes_v1(
        api_key,
        keyword=search_params["keyword"],
        page=search_params["page"],
        sort_type=search_params["sort_type"],
        filter_note_type=search_params["filter_note_type"],
        filter_note_time=search_params["filter_note_time"]
    )
    
    # 保存完整响应
    save_result(
        result,
        str(output_dir),
        f"response_{search_params['keyword']}_{timestamp}.json"
    )
    
    # 分析响应结构
    if result.get('code') == 200:
        print("\n✅ 接口调用成功")
        analyze_response(result)
        print_notes_summary(result)
    else:
        print(f"\n❌ API 返回错误:")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
