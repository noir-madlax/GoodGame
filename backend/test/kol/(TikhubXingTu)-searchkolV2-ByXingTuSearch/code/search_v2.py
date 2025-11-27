#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音星图 KOL 搜索接口 V2 调用脚本

用途:
高级搜索kol V2，支持粉丝范围和内容标签筛选
筛选10-100万的粉丝，筛选一级标签是美妆，二级标签是护肤保养的达人。
搜索关键词是 护肤

参考: backend/test/kol/(TikhubXingTu)-searchkol-ByXingTuSearch/code/fetch_and_analyze_kol_v2.py
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# 标签定义
# tag-1: 美妆
# tag_level_two-4: 护肤保养
TAG_BEAUTY = "tag-1"
TAG_SKINCARE = "tag_level_two-4"

def load_api_key():
    """
    从环境变量加载 TikHub API Key
    """
    # 定位到 backend/.env 文件
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
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

def search_kol_v2(api_key: str, keyword: str, page: int = 1, count: int = 20):
    """
    调用 search_kol_v2 接口
    """
    url = "https://api.tikhub.io/api/v1/douyin/xingtu/search_kol_v2"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 构建参数
    # 筛选10-100万的粉丝 -> followerRange: "10-100"
    # 二级标签护肤保养 (tag_level_two-4)
    # 经测试，仅传递二级标签即可，传递多个标签可能会导致 400 错误
    content_tags = [TAG_SKINCARE]
    
    params = {
        'keyword': keyword,
        'page': page,
        'count': count,
        'followerRange': '10-100',
        'contentTag': content_tags, 
        # 'platformSource': '_1',     # V2 接口可能不需要或不支持
        # 'sort_type': 1
    }
    
    print(f"\n📡 发送请求: 第 {page} 页...")
    print(f"   URL: {url}")
    print(f"   关键词: {keyword}")
    print(f"   粉丝范围: {params['followerRange']}")
    print(f"   内容标签: {content_tags}")
    
    try:
        # requests 自动处理列表参数为多个同名 key
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"   HTTP 状态码: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"   ❌ HTTP 请求失败: {response.text[:200]}")
            return {
                "error": f"HTTP {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        print(f"   ❌ 请求异常: {str(e)}")
        return {"error": str(e)}

def save_result(data: Dict[str, Any], output_dir: str, filename_prefix: str = "search_result"):
    """
    保存结果到文件
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{filename_prefix}_{timestamp}.json'
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 结果已保存: {filepath}")
    return filepath

def main():
    print("=" * 60)
    print("抖音星图 KOL 搜索 V2 测试")
    print("=" * 60)
    
    try:
        api_key = load_api_key()
    except ValueError as e:
        print(f"❌ {e}")
        return

    # 设置输出目录
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "output"
    
    # 搜索关键词
    keyword = "护肤保养"
    # keyword = "美妆"
    
    # 调用 API
    result = search_kol_v2(api_key, keyword)
    
    # 保存结果
    # 不做任何过滤，直接保存原始返回
    save_result(result, str(output_dir), f"search_v2_{keyword}")
    
    if result.get('code') == 200 or result.get('code') == 0:
        print("✅ 接口调用成功，原始数据已保存。")
        data = result.get('data', {})
        # 兼容可能的返回结构
        kol_list = data.get('kol_list') or data.get('authors') or []
        print(f"   返回达人数量: {len(kol_list)}")
    else:
        print(f"❌ API 返回错误: {result}")

if __name__ == "__main__":
    main()
