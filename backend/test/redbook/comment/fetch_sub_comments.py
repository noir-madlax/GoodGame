#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小红书子评论获取脚本

功能:
1. 获取指定评论的子评论
2. 增量保存：每获取完一个评论的子评论就保存
3. 断点续传：已获取的不重复获取
4. 支持并发获取（不同评论的子评论可以并发）
5. 完整记录请求和响应体
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading


# 线程锁，用于安全写入文件
file_lock = threading.Lock()


def load_config() -> Dict[str, Any]:
    """从 config.json 加载配置"""
    config_path = Path(__file__).parent / "params" / "config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_api_key() -> str:
    """从环境变量加载 TikHub API Key"""
    backend_dir = Path(__file__).parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError("环境变量 tikhub_API_KEY 未设置")
    
    return api_key


def load_sub_progress(output_dir: Path, note_id: str) -> Dict[str, Any]:
    """加载子评论获取进度"""
    progress_file = output_dir / f"sub_progress_{note_id}.json"
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'note_id': note_id,
        'completed_comment_ids': [],  # 已完成获取子评论的评论 ID
        'in_progress': {},  # 正在获取中的评论 {comment_id: last_cursor}
        'last_update': None
    }


def save_sub_progress(output_dir: Path, note_id: str, progress: Dict[str, Any]) -> None:
    """保存子评论获取进度"""
    with file_lock:
        progress_file = output_dir / f"sub_progress_{note_id}.json"
        progress['last_update'] = datetime.now().isoformat()
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)


def load_sub_comments_data(output_dir: Path, note_id: str) -> Dict[str, Any]:
    """加载子评论数据"""
    data_file = output_dir / f"sub_comments_{note_id}.json"
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'note_id': note_id,
        'sub_comments': {}  # {comment_id: [sub_comments]}
    }


def save_sub_comments_data(output_dir: Path, note_id: str, data: Dict[str, Any]) -> None:
    """保存子评论数据"""
    with file_lock:
        data_file = output_dir / f"sub_comments_{note_id}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def append_sub_api_log(output_dir: Path, note_id: str, log_entry: Dict[str, Any]) -> None:
    """追加子评论 API 日志"""
    with file_lock:
        log_file = output_dir / f"sub_api_log_{note_id}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def save_sub_raw_response(output_dir: Path, note_id: str, comment_id: str, page: int, response_data: Dict[str, Any]) -> None:
    """保存子评论原始响应"""
    raw_dir = output_dir / "raw" / "sub"
    raw_dir.mkdir(parents=True, exist_ok=True)
    # 使用 comment_id 和 page 作为文件名，避免覆盖
    raw_file = raw_dir / f"sub_{comment_id}_page{page}.json"
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)


def get_sub_comments_api(
    api_key: str,
    note_id: str,
    comment_id: str,
    cursor: str = ""
) -> Dict[str, Any]:
    """
    获取子评论 API
    
    使用 App API: /api/v1/xiaohongshu/app/get_sub_comments
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
    
    if cursor:
        params['start'] = cursor
    
    request_info = {
        'url': url,
        'method': 'GET',
        'params': params.copy(),
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response_info = {
            'status_code': response.status_code,
            'timestamp': datetime.now().isoformat(),
            'success': response.status_code == 200,
            'error': None
        }
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'data': result,
                'request': request_info,
                'response': response_info
            }
        else:
            response_info['error'] = response.text[:500]
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text[:200]}",
                'request': request_info,
                'response': response_info
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'request': request_info,
            'response': {
                'status_code': None,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            }
        }


def extract_sub_comment_info(sub: Dict[str, Any]) -> Dict[str, Any]:
    """提取子评论关键信息"""
    user = sub.get('user', {})
    target = sub.get('target_comment', {})
    target_user = target.get('user', {}) if target else {}
    
    return {
        'id': sub.get('id'),
        'content': sub.get('content', ''),
        'time': sub.get('time'),
        'user_nickname': user.get('nickname', ''),
        'user_id': user.get('userid', ''),
        'like_count': sub.get('like_count', 0),
        'reply_to_nickname': target_user.get('nickname', ''),
        'reply_to_user_id': target_user.get('userid', ''),
        'ip_location': sub.get('ip_location', '')
    }


def fetch_single_comment_subs(
    api_key: str,
    note_id: str,
    comment_id: str,
    expected_count: int,
    output_dir: Path,
    progress: Dict[str, Any],
    sub_data: Dict[str, Any],
    max_pages: int = 50,
    request_delay: float = 0.3
) -> int:
    """
    获取单个评论的所有子评论
    
    Returns:
        获取到的子评论数量
    """
    # 检查是否已完成
    if comment_id in progress.get('completed_comment_ids', []):
        existing = sub_data.get('sub_comments', {}).get(comment_id, [])
        print(f"   ⏭️  评论 {comment_id[:12]}... 已完成，跳过 (已有 {len(existing)} 条)")
        return len(existing)
    
    # 获取已有的子评论和游标
    existing_subs = sub_data.get('sub_comments', {}).get(comment_id, [])
    existing_ids = set(s['id'] for s in existing_subs)
    cursor = progress.get('in_progress', {}).get(comment_id, '')
    
    print(f"   📥 评论 {comment_id[:12]}... (预期 {expected_count} 条，已有 {len(existing_ids)} 条)")
    
    page = 0
    new_count = 0
    
    while page < max_pages:
        page += 1
        
        # 调用 API
        result = get_sub_comments_api(api_key, note_id, comment_id, cursor=cursor)
        
        # 记录 API 日志
        log_entry = {
            'comment_id': comment_id,
            'page': page,
            'cursor_used': cursor,
            'request': result['request'],
            'response': result['response']
        }
        append_sub_api_log(output_dir, note_id, log_entry)
        
        if not result['success']:
            print(f"      ❌ 第 {page} 页失败: {result['error']}")
            # 保存进度，下次可以继续
            progress['in_progress'][comment_id] = cursor
            save_sub_progress(output_dir, note_id, progress)
            break
        
        # 保存原始响应
        save_sub_raw_response(output_dir, note_id, comment_id, page, result['data'])
        
        # 解析响应 (App API 结构)
        # 检查 code 字段
        if result['data'].get('code') != 200:
            print(f"      ❌ 第 {page} 页 API 返回错误: {result['data'].get('message', 'Unknown')}")
            break
        
        api_data = result['data'].get('data', {})
        inner_data = api_data.get('data', {})
        comments = inner_data.get('comments', [])
        
        if not comments:
            break
        
        # 处理子评论
        page_new = 0
        for sub in comments:
            sub_id = sub.get('id')
            if sub_id and sub_id not in existing_ids:
                sub_info = extract_sub_comment_info(sub)
                existing_subs.append(sub_info)
                existing_ids.add(sub_id)
                page_new += 1
                new_count += 1
        
        # 更新数据
        if comment_id not in sub_data['sub_comments']:
            sub_data['sub_comments'][comment_id] = []
        sub_data['sub_comments'][comment_id] = existing_subs
        
        # 使用最后一条评论的 ID 作为游标
        new_cursor = comments[-1].get('id', '') if comments else ''
        cursor = new_cursor
        progress['in_progress'][comment_id] = cursor
        
        # App API 每页返回约 5 条，如果返回数量少于 5 条说明没有更多了
        # 或者已获取数量达到预期数量
        has_more = len(comments) >= 5 and len(existing_subs) < expected_count
        
        # 立即保存
        save_sub_comments_data(output_dir, note_id, sub_data)
        save_sub_progress(output_dir, note_id, progress)
        
        if not has_more:
            break
        
        time.sleep(request_delay)
    
    # 标记完成
    if comment_id not in progress['completed_comment_ids']:
        progress['completed_comment_ids'].append(comment_id)
    if comment_id in progress.get('in_progress', {}):
        del progress['in_progress'][comment_id]
    save_sub_progress(output_dir, note_id, progress)
    
    total = len(existing_subs)
    print(f"      ✅ 完成，新增 {new_count} 条，共 {total}/{expected_count} 条")
    
    return total


def fetch_all_sub_comments(
    api_key: str,
    note_id: str,
    output_dir: Path,
    min_sub_count: int = 5,
    max_concurrent: int = 5,
    request_delay: float = 0.3
) -> None:
    """
    获取所有符合条件的子评论
    """
    # 加载主评论数据
    main_comments_file = output_dir / f"main_comments_{note_id}.json"
    if not main_comments_file.exists():
        print(f"❌ 未找到主评论文件: {main_comments_file}")
        return
    
    with open(main_comments_file, 'r', encoding='utf-8') as f:
        main_data = json.load(f)
    
    # 筛选需要获取子评论的评论
    comments_to_fetch = [
        c for c in main_data['comments']
        if c.get('sub_comment_count', 0) >= min_sub_count
    ]
    
    # 按子评论数降序排序
    comments_to_fetch.sort(key=lambda x: x['sub_comment_count'], reverse=True)
    
    print(f"\n{'='*60}")
    print(f"📥 获取子评论")
    print(f"{'='*60}")
    print(f"   笔记 ID: {note_id}")
    print(f"   子评论数阈值: >= {min_sub_count}")
    print(f"   符合条件的评论数: {len(comments_to_fetch)}")
    print(f"   预计子评论总数: {sum(c['sub_comment_count'] for c in comments_to_fetch)}")
    
    # 加载进度和数据
    progress = load_sub_progress(output_dir, note_id)
    sub_data = load_sub_comments_data(output_dir, note_id)
    
    completed = set(progress.get('completed_comment_ids', []))
    to_fetch = [c for c in comments_to_fetch if c['id'] not in completed]
    
    print(f"   已完成: {len(completed)} 个评论")
    print(f"   待获取: {len(to_fetch)} 个评论")
    print(f"{'='*60}")
    
    if not to_fetch:
        print("✅ 所有子评论已获取完成")
        # 统计总数
        total_subs = sum(len(subs) for subs in sub_data.get('sub_comments', {}).values())
        print(f"   子评论总数: {total_subs}")
        return
    
    # 串行获取（因为要保证进度正确保存）
    for i, comment in enumerate(comments_to_fetch, 1):
        comment_id = comment['id']
        expected = comment['sub_comment_count']
        
        print(f"\n[{i}/{len(comments_to_fetch)}] 处理评论: {comment['content'][:30]}...")
        
        fetch_single_comment_subs(
            api_key=api_key,
            note_id=note_id,
            comment_id=comment_id,
            expected_count=expected,
            output_dir=output_dir,
            progress=progress,
            sub_data=sub_data,
            request_delay=request_delay
        )
    
    # 最终统计
    print(f"\n{'='*60}")
    print(f"📊 获取完成")
    total_subs = sum(len(subs) for subs in sub_data.get('sub_comments', {}).values())
    print(f"   子评论总数: {total_subs}")
    print(f"{'='*60}")


def main():
    import sys
    
    print("=" * 60)
    print("小红书子评论获取工具")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    api_key = load_api_key()
    
    # 设置输出目录
    script_dir = Path(__file__).parent
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 获取目标帖子 ID
    note_ids = config.get('目标帖子', {}).get('note_ids', [])
    if not note_ids:
        print("❌ 未配置目标帖子 ID")
        return
    
    # 支持命令行参数指定帖子索引或 ID
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.startswith('--index='):
            index = int(arg.split('=')[1])
            if index >= len(note_ids):
                print(f"❌ 索引 {index} 超出范围，共 {len(note_ids)} 个帖子")
                return
            note_id = note_ids[index]
        elif arg.startswith('--id='):
            note_id = arg.split('=')[1]
        else:
            note_id = arg
    else:
        note_id = note_ids[0]
    
    # 获取配置参数
    min_sub_count = config.get('子评论获取', {}).get('sub_comment_threshold', 5)
    max_concurrent = config.get('并发设置', {}).get('max_concurrent', 5)
    request_delay = config.get('请求间隔', {}).get('request_delay', 0.3)
    
    # 开始获取
    fetch_all_sub_comments(
        api_key=api_key,
        note_id=note_id,
        output_dir=output_dir,
        min_sub_count=min_sub_count,
        max_concurrent=max_concurrent,
        request_delay=request_delay
    )


if __name__ == "__main__":
    main()
