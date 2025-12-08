#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小红书评论获取脚本 V2

优化点:
1. 增量保存：每获取一页评论就保存，避免中断丢失
2. 断点续传：已保存的内容不重复获取
3. 并发获取子评论：使用线程池并发
4. 先统计子评论数量：让用户决定是否获取
5. 所有参数从配置文件读取

接口文档:
- 获取笔记评论: https://docs.tikhub.io/310965840e0
- 获取子评论: https://docs.tikhub.io/310965841e0

配置文件: params/config.json
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import sys


# ============================================================
# 配置加载
# ============================================================

def load_config() -> Dict[str, Any]:
    """从配置文件加载参数"""
    config_path = Path(__file__).parent / "params" / "config.json"
    
    # 默认配置
    default_config = {
        "max_concurrent": 5,
        "request_delay": 0.3,
        "max_pages": 100,
        "sub_comment_threshold": 5,
        "max_sub_pages": 10,
        "note_ids": []
    }
    
    if not config_path.exists():
        print(f"⚠️ 配置文件不存在: {config_path}", flush=True)
        print(f"   使用默认配置", flush=True)
        return default_config
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = json.load(f)
        
        # 解析配置
        config = {
            "max_concurrent": raw_config.get("并发设置", {}).get("max_concurrent", default_config["max_concurrent"]),
            "request_delay": raw_config.get("请求间隔", {}).get("request_delay", default_config["request_delay"]),
            "max_pages": raw_config.get("一级评论获取", {}).get("max_pages", default_config["max_pages"]),
            "sub_comment_threshold": raw_config.get("子评论获取", {}).get("sub_comment_threshold", default_config["sub_comment_threshold"]),
            "max_sub_pages": raw_config.get("子评论获取", {}).get("max_sub_pages", default_config["max_sub_pages"]),
            "note_ids": raw_config.get("目标帖子", {}).get("note_ids", default_config["note_ids"])
        }
        
        return config
    except Exception as e:
        print(f"⚠️ 配置文件解析失败: {e}", flush=True)
        print(f"   使用默认配置", flush=True)
        return default_config


# 加载配置（全局）
CONFIG = load_config()


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
    """获取笔记评论"""
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
            # 返回更详细的错误信息
            try:
                error_json = response.json()
                return {"error": f"HTTP {response.status_code}", "code": response.status_code, "detail": error_json}
            except:
                return {"error": f"HTTP {response.status_code}", "code": response.status_code, "message": response.text[:500]}
    except Exception as e:
        return {"error": str(e)}


def get_sub_comments(
    api_key: str,
    note_id: str,
    comment_id: str,
    start: str = ""
) -> Dict[str, Any]:
    """获取子评论"""
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
            return {"error": f"HTTP {response.status_code}", "message": response.text[:200]}
    except Exception as e:
        return {"error": str(e)}


def load_existing_comments(output_dir: Path, note_id: str) -> Dict[str, Any]:
    """加载已保存的评论数据"""
    comments_file = output_dir / f"comments_{note_id}.json"
    if comments_file.exists():
        with open(comments_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'note_id': note_id,
        'comments': {},  # 使用 dict，key 为 comment_id
        'fetched_comment_ids': [],  # 已获取的评论 ID 列表
        'last_cursor': '',  # 上次的游标
        'sub_comments_fetched': set(),  # 已获取子评论的评论 ID
    }


def save_comments(output_dir: Path, note_id: str, data: Dict[str, Any]) -> None:
    """保存评论数据"""
    comments_file = output_dir / f"comments_{note_id}.json"
    # 转换 set 为 list 以便 JSON 序列化
    save_data = data.copy()
    if isinstance(save_data.get('sub_comments_fetched'), set):
        save_data['sub_comments_fetched'] = list(save_data['sub_comments_fetched'])
    
    with open(comments_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)


def fetch_comments_only(
    api_key: str,
    note_id: str,
    output_dir: Path,
    max_pages: int = None
) -> Dict[str, Any]:
    """
    只获取一级评论（不获取子评论）
    增量保存，支持断点续传
    
    参数:
        max_pages: 最大获取页数，默认从配置文件读取
    """
    # 使用配置文件的值
    if max_pages is None:
        max_pages = CONFIG["max_pages"]
    
    request_delay = CONFIG["request_delay"]
    
    # 加载已有数据
    data = load_existing_comments(output_dir, note_id)
    
    # 转换 sub_comments_fetched 为 set
    if isinstance(data.get('sub_comments_fetched'), list):
        data['sub_comments_fetched'] = set(data['sub_comments_fetched'])
    elif not isinstance(data.get('sub_comments_fetched'), set):
        data['sub_comments_fetched'] = set()
    
    existing_ids = set(data.get('fetched_comment_ids', []))
    cursor = data.get('last_cursor', '')
    
    # 检查是否已完成获取
    fetch_completed = data.get('fetch_completed', False)
    if fetch_completed and len(existing_ids) > 0:
        print(f"\n📥 笔记 {note_id} 的一级评论已全部获取完成", flush=True)
        print(f"   已有 {len(existing_ids)} 条评论，跳过获取", flush=True)
        return data
    
    print(f"\n📥 获取笔记 {note_id} 的一级评论...", flush=True)
    print(f"   已有 {len(existing_ids)} 条评论", flush=True)
    print(f"   最大获取页数: {max_pages}", flush=True)
    
    page = 0
    new_count = 0
    retry_without_cursor = False
    
    while page < max_pages:
        page += 1
        print(f"   获取第 {page}/{max_pages} 页...", flush=True)
        
        result = get_note_comments(api_key, note_id, start=cursor)
        
        # 检查是否是 HTTP 错误
        if 'error' in result and result.get('code') in [400, 401, 403]:
            # 如果有 cursor 且是 400 错误，可能是 cursor 过期，尝试从头开始
            if cursor and result.get('code') == 400 and not retry_without_cursor:
                print(f"   ⚠️ cursor 可能已过期，尝试从头获取...", flush=True)
                cursor = ""
                data['last_cursor'] = ""
                save_comments(output_dir, note_id, data)
                retry_without_cursor = True
                page -= 1  # 重试当前页
                continue
            print(f"   ❌ 获取失败: {result.get('error', result)}", flush=True)
            if result.get('detail'):
                print(f"   详情: {result.get('detail')}", flush=True)
            break
        
        if result.get('code') != 200:
            print(f"   ❌ 获取失败: {result.get('error', result)}", flush=True)
            break
        
        # 解析响应
        api_data = result.get('data', {})
        inner_data = api_data.get('data', {})
        comments = inner_data.get('comments', [])
        has_more = inner_data.get('has_more', False)
        cursor = inner_data.get('cursor', '')
        
        if not comments:
            print(f"   没有更多评论", flush=True)
            data['fetch_completed'] = True
            save_comments(output_dir, note_id, data)
            break
        
        # 处理评论
        page_new = 0
        for comment in comments:
            comment_id = comment.get('id')
            if comment_id and comment_id not in existing_ids:
                # 提取用户信息
                user = comment.get('user', {})
                data['comments'][comment_id] = {
                    'id': comment_id,
                    'content': comment.get('content', ''),
                    'time': comment.get('time'),
                    'user_nickname': user.get('nickname', ''),
                    'user_id': user.get('userid', ''),
                    'like_count': comment.get('like_count', 0),
                    'sub_comment_count': comment.get('sub_comment_count', 0),
                    'ip_location': comment.get('ip_location', ''),
                    'sub_comments': []
                }
                existing_ids.add(comment_id)
                data['fetched_comment_ids'].append(comment_id)
                page_new += 1
                new_count += 1
        
        # 保存游标
        data['last_cursor'] = cursor
        
        # 立即保存
        save_comments(output_dir, note_id, data)
        print(f"   ✅ 本页 {len(comments)} 条，新增 {page_new} 条，已保存", flush=True)
        
        if not has_more:
            print(f"   ✅ 已获取全部一级评论", flush=True)
            data['fetch_completed'] = True
            save_comments(output_dir, note_id, data)
            break
        
        time.sleep(request_delay)
    
    print(f"   📊 共获取 {new_count} 条新评论，总计 {len(existing_ids)} 条一级评论", flush=True)
    return data


def analyze_sub_comments(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    分析子评论情况，返回需要获取子评论的评论列表
    """
    comments_with_subs = []
    
    for comment_id, comment in data.get('comments', {}).items():
        sub_count = comment.get('sub_comment_count', 0)
        if sub_count > 0:
            # 检查是否已获取
            already_fetched = comment_id in data.get('sub_comments_fetched', set())
            fetched_count = len(comment.get('sub_comments', []))
            
            comments_with_subs.append({
                'comment_id': comment_id,
                'content': comment.get('content', '')[:50],
                'sub_comment_count': sub_count,
                'already_fetched': already_fetched,
                'fetched_count': fetched_count
            })
    
    # 按子评论数排序
    comments_with_subs.sort(key=lambda x: x['sub_comment_count'], reverse=True)
    return comments_with_subs


def fetch_single_sub_comments(
    api_key: str,
    note_id: str,
    comment_id: str,
    max_pages: int = None
) -> List[Dict[str, Any]]:
    """
    获取单个评论的所有子评论
    
    参数:
        max_pages: 最大获取页数，默认从配置文件读取
    """
    # 使用配置文件的值
    if max_pages is None:
        max_pages = CONFIG["max_sub_pages"]
    
    request_delay = CONFIG["request_delay"]
    
    all_subs = []
    cursor = ""
    page = 0
    
    while page < max_pages:
        page += 1
        result = get_sub_comments(api_key, note_id, comment_id, start=cursor)
        
        if result.get('code') != 200:
            break
        
        sub_data = result.get('data', {})
        inner = sub_data.get('data', {})
        comments = inner.get('comments', [])
        
        if not comments:
            break
        
        for sub in comments:
            user = sub.get('user', {})
            target = sub.get('target_comment', {})
            target_user = target.get('user', {}) if target else {}
            
            all_subs.append({
                'id': sub.get('id'),
                'content': sub.get('content', ''),
                'time': sub.get('time'),
                'user_nickname': user.get('nickname', ''),
                'user_id': user.get('userid', ''),
                'reply_to_nickname': target_user.get('nickname', ''),
                'ip_location': sub.get('ip_location', '')
            })
        
        # 使用最后一条的 ID 作为游标
        cursor = comments[-1].get('id', '')
        
        # 如果返回数量少于预期，说明没有更多了
        if len(comments) < 10:
            break
        
        time.sleep(request_delay)
    
    return all_subs


def fetch_sub_comments_concurrent(
    api_key: str,
    note_id: str,
    output_dir: Path,
    data: Dict[str, Any],
    comment_ids: List[str],
    max_concurrent: int = None
) -> None:
    """
    并发获取多个评论的子评论
    
    参数:
        max_concurrent: 最大并发数，默认从配置文件读取
    """
    # 使用配置文件的值
    if max_concurrent is None:
        max_concurrent = CONFIG["max_concurrent"]
    
    # 确保 sub_comments_fetched 是 set
    if isinstance(data.get('sub_comments_fetched'), list):
        data['sub_comments_fetched'] = set(data['sub_comments_fetched'])
    elif not isinstance(data.get('sub_comments_fetched'), set):
        data['sub_comments_fetched'] = set()
    
    # 过滤掉已获取的
    to_fetch = [cid for cid in comment_ids if cid not in data['sub_comments_fetched']]
    
    if not to_fetch:
        print("   ✅ 所有子评论已获取，无需重复获取", flush=True)
        return
    
    print(f"\n📥 并发获取 {len(to_fetch)} 个评论的子评论 (并发数: {max_concurrent})...", flush=True)
    
    completed = 0
    total_subs = 0
    
    def fetch_one(comment_id: str):
        return comment_id, fetch_single_sub_comments(api_key, note_id, comment_id)
    
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {executor.submit(fetch_one, cid): cid for cid in to_fetch}
        
        for future in as_completed(futures):
            comment_id = futures[future]
            try:
                cid, subs = future.result()
                
                # 更新数据
                if cid in data['comments']:
                    data['comments'][cid]['sub_comments'] = subs
                    data['sub_comments_fetched'].add(cid)
                
                completed += 1
                total_subs += len(subs)
                
                # 每完成一个就保存（增量保存，防止中断丢失）
                save_comments(output_dir, note_id, data)
                
                sub_count = data['comments'].get(cid, {}).get('sub_comment_count', 0)
                print(f"   ✅ [{completed}/{len(to_fetch)}] 评论 {cid[:8]}... 获取 {len(subs)}/{sub_count} 条子评论，已保存", flush=True)
                
            except Exception as e:
                print(f"   ❌ 评论 {comment_id[:8]}... 获取失败: {e}", flush=True)
    
    print(f"   📊 完成 {completed}/{len(to_fetch)} 个评论的子评论获取，共 {total_subs} 条子评论", flush=True)


def format_timestamp(ts: int) -> str:
    """格式化时间戳"""
    if not ts:
        return "未知时间"
    try:
        if ts > 10000000000:
            ts = ts // 1000
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return "未知时间"


def generate_summary(
    note_info: Dict[str, Any],
    data: Dict[str, Any],
    output_path: str
) -> None:
    """生成评论汇总文件"""
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
    
    # 统计
    comments = data.get('comments', {})
    total_comments = len(comments)
    total_subs = sum(len(c.get('sub_comments', [])) for c in comments.values())
    
    lines.append("")
    lines.append(f"【评论统计】")
    lines.append(f"一级评论数: {total_comments}")
    lines.append(f"子评论数: {total_subs}")
    lines.append(f"总计: {total_comments + total_subs}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("💬 评论详情")
    lines.append("=" * 60)
    lines.append("")
    
    # 评论详情
    for i, (cid, comment) in enumerate(comments.items(), 1):
        nickname = comment.get('user_nickname', '匿名用户')
        content = comment.get('content', '')
        create_time = format_timestamp(comment.get('time', 0))
        like_count = comment.get('like_count', 0)
        sub_count = comment.get('sub_comment_count', 0)
        location = comment.get('ip_location', '')
        
        lines.append(f"【{i}楼】{nickname} ({location})")
        lines.append(f"   {content}")
        lines.append(f"   ❤️ {like_count}  💬 {sub_count}  🕐 {create_time}")
        
        # 子评论
        for sub in comment.get('sub_comments', []):
            sub_nickname = sub.get('user_nickname', '匿名用户')
            sub_content = sub.get('content', '')
            sub_time = format_timestamp(sub.get('time', 0))
            reply_to = sub.get('reply_to_nickname', '')
            sub_location = sub.get('ip_location', '')
            
            if reply_to:
                lines.append(f"   └─ {sub_nickname} 回复 {reply_to}: {sub_content}")
            else:
                lines.append(f"   └─ {sub_nickname}: {sub_content}")
            lines.append(f"      ({sub_location}) 🕐 {sub_time}")
        
        lines.append("")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"💾 评论汇总已保存: {output_path}", flush=True)


def main():
    print("=" * 60, flush=True)
    print("小红书评论获取工具 V2", flush=True)
    print("=" * 60, flush=True)
    
    # 显示当前配置
    print(f"\n📋 当前配置 (来自 params/config.json):", flush=True)
    print(f"   并发数: {CONFIG['max_concurrent']}", flush=True)
    print(f"   请求间隔: {CONFIG['request_delay']}秒", flush=True)
    print(f"   一级评论最大页数: {CONFIG['max_pages']}", flush=True)
    print(f"   子评论阈值: >= {CONFIG['sub_comment_threshold']} 条才获取", flush=True)
    print(f"   子评论最大页数: {CONFIG['max_sub_pages']}", flush=True)
    
    api_key = load_api_key()
    
    # 设置输出目录
    script_dir = Path(__file__).parent
    output_dir = script_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 确定要处理的帖子
    note_ids = CONFIG.get("note_ids", [])
    
    if note_ids:
        # 从配置文件读取帖子 ID
        print(f"\n📋 从配置文件读取 {len(note_ids)} 个帖子 ID", flush=True)
        
        # 尝试从 top3_notes.json 获取帖子详情
        search_output_dir = script_dir.parent / "search" / "output"
        top3_file = search_output_dir / "top3_notes.json"
        
        notes_info = {}
        if top3_file.exists():
            with open(top3_file, 'r', encoding='utf-8') as f:
                top3_notes = json.load(f)
                for note in top3_notes:
                    notes_info[note['id']] = note
        
        # 构建帖子列表
        top3_notes = []
        for nid in note_ids:
            if nid in notes_info:
                top3_notes.append(notes_info[nid])
            else:
                # 如果没有详情，创建基本信息
                top3_notes.append({
                    'id': nid,
                    'title': f'帖子 {nid[:8]}...',
                    'comments_count': 0,
                    'liked_count': 0,
                    'collected_count': 0,
                    'author': '未知'
                })
    else:
        # 从 top3_notes.json 读取
        search_output_dir = script_dir.parent / "search" / "output"
        top3_file = search_output_dir / "top3_notes.json"
        
        if not top3_file.exists():
            print(f"❌ 未找到 Top3 帖子文件: {top3_file}", flush=True)
            print(f"   请在配置文件中指定 note_ids 或确保 top3_notes.json 存在", flush=True)
            return
        
        with open(top3_file, 'r', encoding='utf-8') as f:
            top3_notes = json.load(f)
    
    print(f"\n📋 将处理以下 {len(top3_notes)} 个帖子:", flush=True)
    for i, note in enumerate(top3_notes, 1):
        title = note.get('title', '无标题')[:40]
        comments = note.get('comments_count', 0)
        print(f"   {i}. {title}... (评论数: {comments})", flush=True)
    
    # 第一步：获取所有一级评论
    print(f"\n{'='*60}", flush=True)
    print("📌 第一步：获取一级评论（增量获取，已有数据不重复获取）", flush=True)
    print(f"{'='*60}", flush=True)
    
    all_data = {}
    for note in top3_notes:
        note_id = note['id']
        data = fetch_comments_only(api_key, note_id, output_dir)
        all_data[note_id] = data
    
    # 第二步：分析子评论情况
    print(f"\n{'='*60}", flush=True)
    print("📌 第二步：子评论统计", flush=True)
    print(f"{'='*60}", flush=True)
    
    sub_comment_threshold = CONFIG["sub_comment_threshold"]
    
    for note in top3_notes:
        note_id = note['id']
        data = all_data[note_id]
        
        title = note.get('title', '无标题')[:30]
        print(f"\n【{title}...】", flush=True)
        
        subs_analysis = analyze_sub_comments(data)
        
        if not subs_analysis:
            print("   没有子评论", flush=True)
            continue
        
        # 统计
        total_sub_count = sum(s['sub_comment_count'] for s in subs_analysis)
        already_fetched = sum(1 for s in subs_analysis if s['already_fetched'])
        need_fetch = sum(1 for s in subs_analysis 
                        if s['sub_comment_count'] >= sub_comment_threshold and not s['already_fetched'])
        
        print(f"   有子评论的评论数: {len(subs_analysis)}", flush=True)
        print(f"   子评论总数（预估）: {total_sub_count}", flush=True)
        print(f"   已获取子评论的评论数: {already_fetched}", flush=True)
        print(f"   待获取（子评论数 >= {sub_comment_threshold}）: {need_fetch}", flush=True)
        
        # 显示前10个
        print(f"\n   子评论数量 Top 10:", flush=True)
        print(f"   {'评论ID':<26} {'子评论数':<10} {'已获取':<10} {'内容'}", flush=True)
        print(f"   {'-'*70}", flush=True)
        
        for s in subs_analysis[:10]:
            status = "✅" if s['already_fetched'] else "❌"
            content = s['content'][:30] if s['content'] else '(无内容)'
            print(f"   {s['comment_id']:<26} {s['sub_comment_count']:<10} {status:<10} {content}", flush=True)
    
    # 询问是否获取子评论
    print(f"\n{'='*60}", flush=True)
    print("💡 子评论获取说明:", flush=True)
    print(f"   - 只获取子评论数 >= {sub_comment_threshold} 的评论的子评论", flush=True)
    print("   - 每次 API 调用都会产生费用", flush=True)
    print("   - 已获取的子评论不会重复获取（断点续传）", flush=True)
    print("   - 每获取完一个评论的子评论就立即保存", flush=True)
    print(f"{'='*60}", flush=True)
    
    # 自动获取子评论（只获取子评论数 >= 阈值 的）
    print(f"\n📌 第三步：获取子评论 (子评论数 >= {sub_comment_threshold} 的评论)", flush=True)
    
    for note in top3_notes:
        note_id = note['id']
        data = all_data[note_id]
        
        title = note.get('title', '无标题')[:30]
        print(f"\n【{title}...】", flush=True)
        
        subs_analysis = analyze_sub_comments(data)
        
        # 只获取子评论数 >= 阈值 的
        to_fetch = [s['comment_id'] for s in subs_analysis 
                   if s['sub_comment_count'] >= sub_comment_threshold and not s['already_fetched']]
        
        if to_fetch:
            print(f"   需要获取 {len(to_fetch)} 个评论的子评论", flush=True)
            fetch_sub_comments_concurrent(api_key, note_id, output_dir, data, to_fetch)
        else:
            print("   ✅ 无需获取子评论（已全部获取或无符合条件的评论）", flush=True)
    
    # 第四步：生成汇总文件
    print(f"\n{'='*60}", flush=True)
    print("📌 第四步：生成汇总文件", flush=True)
    print(f"{'='*60}", flush=True)
    
    for note in top3_notes:
        note_id = note['id']
        # 重新加载最新数据
        data = load_existing_comments(output_dir, note_id)
        summary_file = output_dir / f"summary_{note_id}.txt"
        generate_summary(note, data, str(summary_file))
    
    # 最终统计
    print(f"\n{'='*60}", flush=True)
    print("📊 最终统计", flush=True)
    print(f"{'='*60}", flush=True)
    
    for note in top3_notes:
        note_id = note['id']
        data = load_existing_comments(output_dir, note_id)
        
        comments = data.get('comments', {})
        total_comments = len(comments)
        total_subs = sum(len(c.get('sub_comments', [])) for c in comments.values())
        
        title = note.get('title', '无标题')[:30]
        api_total = note.get('comments_count', 0)
        
        print(f"\n【{title}...】", flush=True)
        print(f"   搜索接口显示评论数: {api_total}", flush=True)
        print(f"   实际获取一级评论数: {total_comments}", flush=True)
        print(f"   实际获取子评论数: {total_subs}", flush=True)
        print(f"   实际获取总计: {total_comments + total_subs}", flush=True)
    
    print(f"\n{'='*60}", flush=True)
    print("✅ 完成！", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"输出目录: {output_dir}", flush=True)
    print(f"配置文件: {Path(__file__).parent / 'params' / 'config.json'}", flush=True)


if __name__ == "__main__":
    main()
