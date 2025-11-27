#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音星图 KOL 搜索关键词对比脚本

用途:
对比不同关键词在相同筛选条件下的搜索结果：
1. 关键词: "护肤" (基准)
2. 关键词: "" (空)
3. 关键词: "护肤达人"

筛选条件:
- 粉丝范围: 10万-100万 (followerRange='100000-1000000')
- 内容标签: 美妆 + 护肤保养 (contentTag=['tag-1', 'tag_level_two-4'])

输出:
- 每个关键词的搜索结果 JSON
- 简单的对比报告 (总数、部分达人示例)
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List

# 标签定义
TAG_BEAUTY = "tag-1"
TAG_SKINCARE = "tag_level_two-4"

def load_api_key():
    # 定位到 backend/.env 文件
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError("环境变量 tikhub_API_KEY 未设置")
    return api_key

def search_kol_v2(api_key: str, keyword: str, page: int = 1, count: int = 20):
    url = "https://api.tikhub.io/api/v1/douyin/xingtu/search_kol_v2"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    content_tags = [TAG_SKINCARE]
    
    # 根据之前成功的请求参数配置
    # followerRange 使用 '10-100' (表示 10万-100万)
    params = {
        'keyword': keyword,
        'page': page,
        'count': count,
        'followerRange': '10-100',
        'contentTag': content_tags
    }
    
    print(f"\n📡 搜索关键词: '{keyword}'")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text[:100]}")
            return {"error": f"HTTP {response.status_code}", "message": response.text}
    except Exception as e:
        print(f"   ❌ 请求异常: {str(e)}")
        return {"error": str(e)}

def save_result(data: Dict[str, Any], output_dir: str, filename: str):
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"   💾 保存: {filepath}")

def analyze_result(data: Dict[str, Any], keyword: str) -> Dict[str, Any]:
    if data.get('code') != 200 and data.get('code') != 0:
        return {'keyword': keyword, 'status': 'failed', 'total_count': 0, 'authors': []}
    
    pagination = data.get('data', {}).get('pagination', {})
    total_count = pagination.get('total_count', 0)
    
    # 兼容不同的字段名 (authors / kol_list)
    authors_list = data.get('data', {}).get('authors', []) or data.get('data', {}).get('kol_list', [])
    
    authors_summary = []
    for author in authors_list[:5]: # 只取前5个做示例
        attr = author.get('attribute_datas', {})
        authors_summary.append({
            'nickname': attr.get('nick_name', 'Unknown'),
            'follower': attr.get('follower', 0),
            'tags': attr.get('tags_relation', '{}')
        })
    
    return {
        'keyword': keyword,
        'status': 'success',
        'total_count': total_count,
        'authors_count': len(authors_list),
        'authors_sample': authors_summary
    }

def main():
    print("=" * 60)
    print("抖音星图 KOL 搜索关键词对比测试")
    print("=" * 60)
    
    try:
        api_key = load_api_key()
    except ValueError as e:
        print(f"❌ {e}")
        return

    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "output"
    
    keywords = ["护肤保养"]
    results = []
    
    for kw in keywords:
        # 1. 搜索
        resp = search_kol_v2(api_key, kw)
        
        # 2. 保存
        safe_kw = "EMPTY" if kw == "" else kw
        filename = f"compare_v2_{safe_kw}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_result(resp, str(output_dir), filename)
        
        # 3. 分析
        analysis = analyze_result(resp, kw)
        results.append(analysis)
        
        # 避免过于频繁请求
        time.sleep(1)

    # 4. 输出对比报告
    print("\n" + "=" * 60)
    print("📊 对比报告")
    print("=" * 60)
    
    for res in results:
        kw_display = f"'{res['keyword']}'" if res['keyword'] else "[空字符串]"
        print(f"\n关键词: {kw_display}")
        if res['status'] == 'success':
            print(f"  ✅ 状态: 成功")
            print(f"  🔢 Total Count (总数): {res['total_count']}")
            print(f"  📥 本页返回: {res['authors_count']}")
            print(f"  👤 示例达人:")
            for author in res['authors_sample']:
                print(f"     - {author['nickname']} (粉丝: {author['follower']})")
        else:
            print(f"  ❌ 状态: 失败")

if __name__ == "__main__":
    main()

