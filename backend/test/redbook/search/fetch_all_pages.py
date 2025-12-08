#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小红书搜索笔记 - 获取多页数据并统计评论数量

用途:
- 获取搜索结果的第1-5页
- 统计每个帖子的评论数量
- 找出评论最多的帖子
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List
import time


def load_api_key() -> str:
    """从环境变量加载 TikHub API Key"""
    backend_dir = Path(__file__).parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    
    return api_key


def search_notes(
    api_key: str,
    keyword: str,
    page: int = 1,
    sort_type: str = "general",
    filter_note_type: str = "不限",
    filter_note_time: str = "半年内",
    search_id: str = "",
    session_id: str = ""
) -> Dict[str, Any]:
    """调用小红书搜索笔记接口"""
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
    
    # 翻页时需要携带 search_id 和 session_id
    if search_id:
        params['search_id'] = search_id
    if session_id:
        params['session_id'] = session_id
    
    print(f"📡 请求第 {page} 页...")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {"error": str(e)}


def extract_notes_from_response(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从响应中提取笔记列表"""
    notes = []
    try:
        data = result.get('data', {})
        inner_data = data.get('data', {})
        items = inner_data.get('items', [])
        
        for item in items:
            if item.get('model_type') == 'note':
                note = item.get('note', {})
                if note:
                    notes.append(note)
    except Exception as e:
        print(f"解析笔记失败: {e}")
    
    return notes


def get_session_ids(result: Dict[str, Any]) -> tuple:
    """从响应中提取 searchId 和 sessionId"""
    data = result.get('data', {})
    search_id = data.get('searchId', '')
    session_id = data.get('sessionId', '')
    return search_id, session_id


def main():
    print("=" * 60)
    print("小红书搜索笔记 - 获取多页数据")
    print("=" * 60)
    
    api_key = load_api_key()
    
    # 设置输出目录
    script_dir = Path(__file__).parent
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 搜索参数
    keyword = "抱枕"
    all_notes = []
    search_id = ""
    session_id = ""
    
    # 获取第1-5页
    for page in range(1, 6):
        result = search_notes(
            api_key,
            keyword=keyword,
            page=page,
            filter_note_time="半年内",
            search_id=search_id,
            session_id=session_id
        )
        
        if result.get('code') == 200:
            # 提取 session IDs 用于翻页
            search_id, session_id = get_session_ids(result)
            
            # 提取笔记
            notes = extract_notes_from_response(result)
            all_notes.extend(notes)
            print(f"   ✅ 第 {page} 页获取 {len(notes)} 条笔记")
            
            # 保存每页的原始响应
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            with open(output_dir / f"page_{page}_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        else:
            print(f"   ❌ 第 {page} 页获取失败")
        
        # 避免请求过快
        if page < 5:
            time.sleep(1)
    
    print(f"\n📊 共获取 {len(all_notes)} 条笔记")
    
    # 统计评论数量并排序
    notes_with_comments = []
    for note in all_notes:
        note_id = note.get('id', 'N/A')
        title = note.get('title', note.get('display_title', '无标题'))
        comments_count = note.get('comments_count', 0) or 0
        liked_count = note.get('liked_count', 0) or 0
        collected_count = note.get('collected_count', 0) or 0
        note_type = note.get('type', 'unknown')
        user = note.get('user', {})
        nickname = user.get('nickname', 'N/A')
        
        notes_with_comments.append({
            'id': note_id,
            'title': title[:50] if title else '无标题',
            'comments_count': comments_count,
            'liked_count': liked_count,
            'collected_count': collected_count,
            'type': note_type,
            'author': nickname
        })
    
    # 按评论数排序
    notes_with_comments.sort(key=lambda x: x['comments_count'], reverse=True)
    
    # 打印统计结果
    print(f"\n{'='*80}")
    print("📝 帖子评论数量统计（按评论数降序）")
    print(f"{'='*80}")
    print(f"{'序号':<4} {'ID':<26} {'评论数':<8} {'点赞数':<8} {'收藏数':<8} {'类型':<8} {'标题'}")
    print("-" * 80)
    
    for i, note in enumerate(notes_with_comments, 1):
        print(f"{i:<4} {note['id']:<26} {note['comments_count']:<8} {note['liked_count']:<8} {note['collected_count']:<8} {note['type']:<8} {note['title'][:30]}")
    
    # 保存统计结果
    stats_file = output_dir / f"notes_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_notes': len(notes_with_comments),
            'keyword': keyword,
            'notes': notes_with_comments
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 统计结果已保存: {stats_file}")
    
    # 找出评论最多的3个帖子
    top3 = notes_with_comments[:3]
    print(f"\n{'='*60}")
    print("🏆 评论最多的 Top 3 帖子")
    print(f"{'='*60}")
    for i, note in enumerate(top3, 1):
        print(f"\n【Top {i}】")
        print(f"  ID: {note['id']}")
        print(f"  标题: {note['title']}")
        print(f"  评论数: {note['comments_count']}")
        print(f"  点赞数: {note['liked_count']}")
        print(f"  作者: {note['author']}")
    
    # 保存 Top3 ID 供后续使用
    top3_file = output_dir / "top3_notes.json"
    with open(top3_file, 'w', encoding='utf-8') as f:
        json.dump(top3, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Top3 帖子信息已保存: {top3_file}")


if __name__ == "__main__":
    main()
