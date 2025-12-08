#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小红书评论获取脚本

用途:
- 获取笔记的评论列表
- 获取评论的子评论（回复）
- 汇总输出评论内容

接口文档:
- 获取笔记评论: https://docs.tikhub.io/310965840e0
- 获取子评论: https://docs.tikhub.io/310965841e0
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
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


def get_note_comments(
    api_key: str,
    note_id: str,
    start: str = "",
    sort_strategy: int = 1
) -> Dict[str, Any]:
    """
    获取笔记评论
    
    Args:
        api_key: TikHub API Key
        note_id: 笔记ID
        start: 翻页游标
        sort_strategy: 排序策略 (1: 默认排序, 2: 最新评论)
    
    Returns:
        API 响应数据
    """
    url = "https://api.tikhub.io/api/v1/xiaohongshu/app/get_note_comments"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    params = {
        'note_id': note_id,
        'sort_strategy': sort_strategy
    }
    
    if start:
        params['start'] = start
    
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


def get_sub_comments(
    api_key: str,
    note_id: str,
    comment_id: str,
    start: str = ""
) -> Dict[str, Any]:
    """
    获取子评论（回复）
    
    Args:
        api_key: TikHub API Key
        note_id: 笔记ID
        comment_id: 一级评论ID
        start: 翻页游标
    
    Returns:
        API 响应数据
    """
    url = "https://api.tikhub.io/api/v1/xiaohongshu/app/get_sub_comments"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    params = {
        'note_id': note_id,
        'comment_id': comment_id
    }
    
    if start:
        params['start'] = start
    
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


def fetch_all_comments(
    api_key: str,
    note_id: str,
    max_pages: int = 5,
    fetch_sub_comments: bool = True,
    max_sub_pages: int = 3
) -> Dict[str, Any]:
    """
    获取笔记的所有评论（包括子评论）
    
    Args:
        api_key: TikHub API Key
        note_id: 笔记ID
        max_pages: 最大获取页数
        fetch_sub_comments: 是否获取子评论
        max_sub_pages: 子评论最大获取页数
    
    Returns:
        包含所有评论的字典
    """
    all_comments = []
    cursor = ""
    page = 0
    total_count = 0
    
    print(f"\n📥 开始获取笔记 {note_id} 的评论...")
    
    while page < max_pages:
        page += 1
        print(f"   获取评论第 {page} 页...")
        
        result = get_note_comments(api_key, note_id, start=cursor)
        
        if result.get('code') != 200:
            print(f"   ❌ 获取评论失败: {result}")
            break
        
        # 解析响应
        data = result.get('data', {})
        inner_data = data.get('data', {})
        comments = inner_data.get('comments', [])
        has_more = inner_data.get('has_more', False)
        cursor = inner_data.get('cursor', '')
        
        if page == 1:
            total_count = inner_data.get('total', 0)
            print(f"   📊 总评论数: {total_count}")
        
        if not comments:
            print(f"   没有更多评论")
            break
        
        print(f"   ✅ 获取 {len(comments)} 条评论")
        
        # 处理每条评论
        for comment in comments:
            # 用户信息可能在 user 或 user_info 字段
            user_info = comment.get('user') or comment.get('user_info', {})
            # 时间可能在 time 或 create_time 字段
            create_time = comment.get('time') or comment.get('create_time')
            # 点赞数可能在 like_count 或 interact_info.liked_count
            like_count = comment.get('like_count', 0)
            if not like_count:
                interact_info = comment.get('interact_info', {})
                like_count = interact_info.get('liked_count', 0)
            
            comment_data = {
                'id': comment.get('id'),
                'content': comment.get('content', ''),
                'create_time': create_time,
                'user_info': user_info,
                'interact_info': {'liked_count': like_count},
                'sub_comment_count': comment.get('sub_comment_count', 0),
                'sub_comments': []
            }
            
            # 获取子评论
            if fetch_sub_comments and comment_data['sub_comment_count'] > 0:
                print(f"      获取子评论 (共 {comment_data['sub_comment_count']} 条)...", flush=True)
                sub_cursor = ""
                sub_page = 0
                
                while sub_page < max_sub_pages:
                    sub_page += 1
                    
                    sub_result = get_sub_comments(
                        api_key, 
                        note_id, 
                        comment_data['id'],
                        start=sub_cursor
                    )
                    
                    if sub_result.get('code') != 200:
                        print(f"      ❌ 获取子评论失败", flush=True)
                        break
                    
                    sub_data = sub_result.get('data', {})
                    sub_inner = sub_data.get('data', {})
                    sub_comments = sub_inner.get('comments', [])
                    
                    if not sub_comments:
                        break
                    
                    print(f"      ✅ 获取 {len(sub_comments)} 条子评论", flush=True)
                    
                    for sub in sub_comments:
                        # 子评论的用户信息
                        sub_user = sub.get('user') or sub.get('user_info', {})
                        sub_time = sub.get('time') or sub.get('create_time')
                        comment_data['sub_comments'].append({
                            'id': sub.get('id'),
                            'content': sub.get('content', ''),
                            'create_time': sub_time,
                            'user_info': sub_user,
                            'target_comment': sub.get('target_comment', {})
                        })
                    
                    # 获取下一页子评论的游标
                    if sub_comments:
                        sub_cursor = sub_comments[-1].get('id', '')
                    
                    # 检查是否还有更多
                    if len(sub_comments) < 10:  # 假设每页10条
                        break
                    
                    time.sleep(0.3)
            
            all_comments.append(comment_data)
        
        if not has_more:
            print(f"   已获取全部评论")
            break
        
        time.sleep(0.5)
    
    return {
        'note_id': note_id,
        'total_count': total_count,
        'fetched_count': len(all_comments),
        'comments': all_comments
    }


def format_timestamp(ts: int) -> str:
    """格式化时间戳"""
    if not ts:
        return "未知时间"
    try:
        # 小红书时间戳可能是毫秒
        if ts > 10000000000:
            ts = ts // 1000
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return "未知时间"


def generate_summary_file(
    note_info: Dict[str, Any],
    comments_data: Dict[str, Any],
    output_path: str
) -> None:
    """
    生成评论汇总文件（类似小红书帖子格式）
    
    Args:
        note_info: 笔记信息
        comments_data: 评论数据
        output_path: 输出文件路径
    """
    lines = []
    
    # 帖子信息
    lines.append("=" * 60)
    lines.append(f"📝 小红书帖子评论汇总")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"【帖子信息】")
    lines.append(f"ID: {note_info.get('id', 'N/A')}")
    lines.append(f"标题: {note_info.get('title', '无标题')}")
    lines.append(f"作者: {note_info.get('author', 'N/A')}")
    lines.append(f"点赞数: {note_info.get('liked_count', 0)}")
    lines.append(f"评论数: {note_info.get('comments_count', 0)}")
    lines.append(f"收藏数: {note_info.get('collected_count', 0)}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("")
    
    # 评论统计
    total_comments = len(comments_data.get('comments', []))
    total_sub_comments = sum(
        len(c.get('sub_comments', [])) 
        for c in comments_data.get('comments', [])
    )
    
    lines.append(f"【评论统计】")
    lines.append(f"获取的一级评论数: {total_comments}")
    lines.append(f"获取的子评论数: {total_sub_comments}")
    lines.append(f"评论总数: {total_comments + total_sub_comments}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("💬 评论详情")
    lines.append("=" * 60)
    lines.append("")
    
    # 评论详情
    for i, comment in enumerate(comments_data.get('comments', []), 1):
        user_info = comment.get('user_info', {})
        nickname = user_info.get('nickname', '匿名用户')
        content = comment.get('content', '')
        create_time = format_timestamp(comment.get('create_time', 0))
        interact_info = comment.get('interact_info', {})
        liked_count = interact_info.get('liked_count', 0)
        sub_count = comment.get('sub_comment_count', 0)
        
        lines.append(f"【{i}楼】{nickname}")
        lines.append(f"   {content}")
        lines.append(f"   ❤️ {liked_count}  💬 {sub_count}  🕐 {create_time}")
        
        # 子评论
        sub_comments = comment.get('sub_comments', [])
        if sub_comments:
            for j, sub in enumerate(sub_comments, 1):
                sub_user = sub.get('user_info', {})
                sub_nickname = sub_user.get('nickname', '匿名用户')
                sub_content = sub.get('content', '')
                sub_time = format_timestamp(sub.get('create_time', 0))
                
                # 检查是否回复其他子评论
                target = sub.get('target_comment', {})
                target_user = target.get('user_info', {}) if target else {}
                target_nickname = target_user.get('nickname', '')
                
                if target_nickname:
                    lines.append(f"   └─ {sub_nickname} 回复 {target_nickname}: {sub_content}")
                else:
                    lines.append(f"   └─ {sub_nickname}: {sub_content}")
                lines.append(f"      🕐 {sub_time}")
        
        lines.append("")
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"💾 评论汇总已保存: {output_path}")


def main():
    import sys
    print("=" * 60, flush=True)
    print("小红书评论获取工具", flush=True)
    print("=" * 60, flush=True)
    
    api_key = load_api_key()
    
    # 设置输出目录
    script_dir = Path(__file__).parent
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 读取 Top3 帖子信息
    search_output_dir = script_dir.parent / "search" / "output"
    top3_file = search_output_dir / "top3_notes.json"
    
    if not top3_file.exists():
        print(f"❌ 未找到 Top3 帖子文件: {top3_file}")
        print("请先运行 fetch_all_pages.py 获取帖子列表")
        return
    
    with open(top3_file, 'r', encoding='utf-8') as f:
        top3_notes = json.load(f)
    
    print(f"\n📋 将获取以下 {len(top3_notes)} 个帖子的评论:")
    for i, note in enumerate(top3_notes, 1):
        print(f"   {i}. {note['title'][:40]}... (评论数: {note['comments_count']})")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 获取每个帖子的评论
    for i, note in enumerate(top3_notes, 1):
        note_id = note['id']
        
        print(f"\n{'='*60}")
        print(f"📖 处理帖子 {i}/{len(top3_notes)}: {note['title'][:40]}...")
        print(f"{'='*60}")
        
        # 获取评论（限制页数以控制 API 调用）
        # 由于评论数很多，我们只获取前几页作为示例
        comments_data = fetch_all_comments(
            api_key,
            note_id,
            max_pages=2,  # 限制为2页
            fetch_sub_comments=True,
            max_sub_pages=1  # 子评论限制1页
        )
        
        # 保存原始评论数据
        raw_file = output_dir / f"comments_raw_{note_id}_{timestamp}.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(comments_data, f, ensure_ascii=False, indent=2)
        print(f"💾 原始数据已保存: {raw_file}")
        
        # 生成汇总文件
        summary_file = output_dir / f"comments_summary_{note_id}_{timestamp}.txt"
        generate_summary_file(note, comments_data, str(summary_file))
        
        # 避免请求过快
        if i < len(top3_notes):
            print("\n⏳ 等待 2 秒后继续...")
            time.sleep(2)
    
    print(f"\n{'='*60}")
    print("✅ 所有帖子评论获取完成！")
    print(f"{'='*60}")
    print(f"输出目录: {output_dir}")


if __name__ == "__main__":
    main()
