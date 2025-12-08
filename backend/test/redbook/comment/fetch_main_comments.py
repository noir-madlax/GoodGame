#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小红书主评论获取脚本

功能:
1. 只获取一级评论（不获取子评论）
2. 增量保存：每获取一页评论就保存
3. 断点续传：已保存的内容不重复获取
4. 完整记录请求和响应体
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import time


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


def load_progress(output_dir: Path, note_id: str) -> Dict[str, Any]:
    """加载进度文件"""
    progress_file = output_dir / f"main_progress_{note_id}.json"
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'note_id': note_id,
        'last_cursor': '',
        'total_fetched': 0,
        'fetched_comment_ids': [],
        'completed': False,
        'last_update': None
    }


def save_progress(output_dir: Path, note_id: str, progress: Dict[str, Any]) -> None:
    """保存进度文件"""
    progress_file = output_dir / f"main_progress_{note_id}.json"
    progress['last_update'] = datetime.now().isoformat()
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_comments(output_dir: Path, note_id: str) -> Dict[str, Any]:
    """加载已保存的评论"""
    comments_file = output_dir / f"main_comments_{note_id}.json"
    if comments_file.exists():
        with open(comments_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'note_id': note_id,
        'total_count': 0,
        'comments': []
    }


def save_comments(output_dir: Path, note_id: str, data: Dict[str, Any]) -> None:
    """保存评论数据"""
    comments_file = output_dir / f"main_comments_{note_id}.json"
    with open(comments_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_api_log(output_dir: Path, note_id: str, log_entry: Dict[str, Any]) -> None:
    """追加 API 日志"""
    log_file = output_dir / f"main_api_log_{note_id}.jsonl"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def save_raw_response(output_dir: Path, note_id: str, page: int, response_data: Dict[str, Any]) -> None:
    """保存原始响应"""
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    raw_file = raw_dir / f"main_raw_page{page}_{note_id}.json"
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)


def get_note_comments(
    api_key: str,
    note_id: str,
    cursor: str = "",
    sort_strategy: str = "latest_v2"
) -> Dict[str, Any]:
    """
    获取笔记评论
    
    使用 Web API: /api/v1/xiaohongshu/web/get_note_comments
    """
    url = "https://api.tikhub.io/api/v1/xiaohongshu/web/get_note_comments"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    params = {
        'note_id': note_id,
        'sort_strategy': sort_strategy
    }
    
    if cursor:
        params['lastCursor'] = cursor
    
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


def extract_comment_info(comment: Dict[str, Any]) -> Dict[str, Any]:
    """提取评论关键信息"""
    user = comment.get('user', {})
    return {
        'id': comment.get('id'),
        'content': comment.get('content', ''),
        'time': comment.get('time'),
        'user_nickname': user.get('nickname', ''),
        'user_id': user.get('userid', ''),
        'like_count': comment.get('like_count', 0),
        'sub_comment_count': comment.get('sub_comment_count', 0),
        'ip_location': comment.get('ip_location', '')
    }


def fetch_all_main_comments(
    api_key: str,
    note_id: str,
    output_dir: Path,
    max_pages: int = 500,
    request_delay: float = 0.5
) -> None:
    """
    获取所有主评论
    
    Args:
        api_key: TikHub API Key
        note_id: 笔记 ID
        output_dir: 输出目录
        max_pages: 最大页数限制
        request_delay: 请求间隔（秒）
    """
    # 加载进度
    progress = load_progress(output_dir, note_id)
    comments_data = load_comments(output_dir, note_id)
    
    # 检查是否已完成
    if progress.get('completed'):
        print(f"✅ 笔记 {note_id} 的主评论已全部获取完成")
        print(f"   总计: {progress['total_fetched']} 条")
        return
    
    # 已获取的评论 ID 集合
    existing_ids = set(progress.get('fetched_comment_ids', []))
    cursor = progress.get('last_cursor', '')
    
    print(f"\n{'='*60}")
    print(f"📥 获取笔记 {note_id} 的主评论")
    print(f"{'='*60}")
    print(f"   已有: {len(existing_ids)} 条")
    print(f"   游标: {cursor[:20]}..." if cursor else "   游标: (从头开始)")
    
    page = 0
    new_count = 0
    
    while page < max_pages:
        page += 1
        print(f"\n📄 第 {page} 页...", flush=True)
        
        # 调用 API
        result = get_note_comments(api_key, note_id, cursor=cursor)
        
        # 记录 API 日志
        log_entry = {
            'page': page,
            'cursor_used': cursor,
            'request': result['request'],
            'response': result['response']
        }
        append_api_log(output_dir, note_id, log_entry)
        
        if not result['success']:
            print(f"   ❌ 请求失败: {result['error']}")
            break
        
        # 保存原始响应
        save_raw_response(output_dir, note_id, page, result['data'])
        
        # 解析响应
        api_data = result['data'].get('data', {})
        inner_data = api_data.get('data', {})
        comments = inner_data.get('comments', [])
        has_more = inner_data.get('has_more', False)
        raw_cursor = inner_data.get('cursor', '')
        total_l1 = inner_data.get('comment_count_l1', 0)
        
        # 处理 cursor：可能是字符串或 JSON 对象
        if isinstance(raw_cursor, dict):
            new_cursor = raw_cursor.get('cursor', '')
        elif isinstance(raw_cursor, str) and raw_cursor.startswith('{'):
            try:
                cursor_obj = json.loads(raw_cursor)
                new_cursor = cursor_obj.get('cursor', raw_cursor)
            except:
                new_cursor = raw_cursor
        else:
            new_cursor = raw_cursor
        
        print(f"   一级评论总数: {total_l1}")
        
        if not comments:
            print(f"   没有更多评论")
            progress['completed'] = True
            save_progress(output_dir, note_id, progress)
            break
        
        # 处理评论
        page_new = 0
        for comment in comments:
            comment_id = comment.get('id')
            if comment_id and comment_id not in existing_ids:
                comment_info = extract_comment_info(comment)
                comments_data['comments'].append(comment_info)
                existing_ids.add(comment_id)
                progress['fetched_comment_ids'].append(comment_id)
                page_new += 1
                new_count += 1
        
        # 更新进度
        cursor = new_cursor
        progress['last_cursor'] = cursor
        progress['total_fetched'] = len(existing_ids)
        comments_data['total_count'] = len(existing_ids)
        
        # 立即保存
        save_progress(output_dir, note_id, progress)
        save_comments(output_dir, note_id, comments_data)
        
        print(f"   ✅ 本页 {len(comments)} 条，新增 {page_new} 条")
        print(f"   📊 累计: {len(existing_ids)}/{total_l1} 条")
        
        if not has_more:
            print(f"\n✅ 已获取全部主评论")
            progress['completed'] = True
            save_progress(output_dir, note_id, progress)
            break
        
        # 请求间隔
        time.sleep(request_delay)
    
    print(f"\n{'='*60}")
    print(f"📊 获取完成")
    print(f"   新增: {new_count} 条")
    print(f"   总计: {len(existing_ids)} 条")
    print(f"{'='*60}")


def main():
    import sys
    
    print("=" * 60)
    print("小红书主评论获取工具")
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
            # 直接传入 note_id
            note_id = arg
    else:
        note_id = note_ids[0]  # 默认处理第一个
    
    print(f"\n目标帖子: {note_id}")
    
    # 获取配置参数
    max_pages = config.get('一级评论获取', {}).get('max_pages', 100)
    request_delay = config.get('请求间隔', {}).get('request_delay', 0.5)
    
    print(f"最大页数: {max_pages}")
    print(f"请求间隔: {request_delay}s")
    
    # 开始获取
    fetch_all_main_comments(
        api_key=api_key,
        note_id=note_id,
        output_dir=output_dir,
        max_pages=max_pages,
        request_delay=request_delay
    )


if __name__ == "__main__":
    main()
