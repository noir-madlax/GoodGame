#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据导入脚本：将搜索结果和评论数据导入数据库

导入目标表：
1. gg_redbook_pillow_project - 抱枕项目汇总表
2. gg_platform_post - 通用帖子表
3. gg_platform_post_comments - 通用评论表

特性：
- 增量导入：已存在的记录不重复插入
- 批次处理：每批次处理后打印进度
- 进度显示：实时显示导入进度
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# 配置
BATCH_SIZE = 100  # 每批次处理数量
PROJECT_ID = '7ee2f0b2-de5a-4156-b52e-344fae7f499d'  # 抱枕评论分析项目


def load_env() -> tuple:
    """加载环境变量"""
    backend_dir = Path(__file__).parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("SUPABASE_URL 或 SUPABASE_KEY 未设置")
    
    return url, key


def get_supabase_client() -> Client:
    """获取 Supabase 客户端"""
    url, key = load_env()
    return create_client(url, key)


def load_search_results(search_dir: Path) -> list:
    """加载搜索结果（从 page_*.json 文件）"""
    all_notes = []
    seen_ids = set()
    
    for i in range(1, 10):
        page_files = list(search_dir.glob(f"page_{i}_*.json"))
        if not page_files:
            break
        
        for page_file in page_files:
            with open(page_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            items = data.get('data', {}).get('data', {}).get('items', [])
            keyword = data.get('params', {}).get('keyword', '抱枕')
            
            for item in items:
                if item.get('model_type') != 'note':
                    continue
                
                note = item.get('note', {})
                note_id = note.get('id')
                
                if not note_id or note_id in seen_ids:
                    continue
                
                seen_ids.add(note_id)
                
                user = note.get('user', {})
                images_list = note.get('images_list', [])
                cover_url = images_list[0].get('url_size_large', '') if images_list else ''
                
                all_notes.append({
                    'note_id': note_id,
                    'title': note.get('title', ''),
                    'content': note.get('desc', ''),
                    'author_id': user.get('userid', ''),
                    'author_name': user.get('nickname', ''),
                    'note_type': note.get('type', 'normal'),
                    'cover_url': cover_url,
                    'liked_count': note.get('liked_count', 0),
                    'comments_count': note.get('comments_count', 0),
                    'collected_count': note.get('collected_count', 0),
                    'shared_count': note.get('shared_count', 0),
                    'note_timestamp': note.get('timestamp'),
                    'search_keyword': keyword,
                    'raw_data': note
                })
    
    return all_notes


def get_existing_comment_ids(supabase: Client, post_id: int) -> set:
    """获取已存在的评论 ID"""
    existing_ids = set()
    offset = 0
    limit = 1000
    
    while True:
        result = supabase.table('gg_platform_post_comments').select('platform_comment_id').eq('post_id', post_id).range(offset, offset + limit - 1).execute()
        
        if not result.data:
            break
        
        for row in result.data:
            existing_ids.add(row['platform_comment_id'])
        
        if len(result.data) < limit:
            break
        
        offset += limit
    
    return existing_ids


def import_comments_batch(supabase: Client, post_id: int, comments: list, existing_ids: set, is_sub: bool = False) -> int:
    """批量导入评论"""
    inserted = 0
    batch = []
    
    for comment in comments:
        comment_id = comment.get('id') or comment.get('platform_comment_id')
        if not comment_id or comment_id in existing_ids:
            continue
        
        # 转换时间戳
        published_at = None
        if comment.get('time'):
            try:
                ts = comment['time']
                if ts > 10000000000:
                    ts = ts // 1000
                published_at = datetime.fromtimestamp(ts).isoformat()
            except:
                pass
        
        insert_data = {
            'post_id': post_id,
            'platform': 'xiaohongshu',
            'platform_comment_id': comment_id,
            'author_id': comment.get('user_id'),
            'author_name': comment.get('user_nickname'),
            'content': comment.get('content', ''),
            'like_count': comment.get('like_count', 0),
            'reply_count': comment.get('sub_comment_count', 0) if not is_sub else 0,
            'published_at': published_at
        }
        
        # 子评论添加父评论信息
        if is_sub and comment.get('parent_comment_id'):
            insert_data['parent_platform_comment_id'] = comment.get('parent_comment_id')
        
        batch.append(insert_data)
        existing_ids.add(comment_id)
        
        # 批量插入
        if len(batch) >= BATCH_SIZE:
            try:
                supabase.table('gg_platform_post_comments').insert(batch).execute()
                inserted += len(batch)
                print(f"      📦 批次插入 {len(batch)} 条，累计 {inserted} 条", flush=True)
            except Exception as e:
                print(f"      ❌ 批次插入失败: {e}", flush=True)
            batch = []
    
    # 插入剩余的
    if batch:
        try:
            supabase.table('gg_platform_post_comments').insert(batch).execute()
            inserted += len(batch)
            print(f"      📦 最后批次插入 {len(batch)} 条，累计 {inserted} 条", flush=True)
        except Exception as e:
            print(f"      ❌ 最后批次插入失败: {e}", flush=True)
    
    return inserted


def import_first_note_comments(supabase: Client, note_id: str, post_id: int, comments_dir: Path) -> tuple:
    """导入第一个帖子的评论"""
    main_file = comments_dir / f"main_comments_{note_id}.json"
    sub_file = comments_dir / f"sub_comments_{note_id}.json"
    
    if not main_file.exists():
        print(f"   ❌ 主评论文件不存在: {main_file}")
        return 0, 0
    
    # 获取已存在的评论 ID
    print(f"   📊 检查已存在的评论...", flush=True)
    existing_ids = get_existing_comment_ids(supabase, post_id)
    print(f"   📊 已存在 {len(existing_ids)} 条评论", flush=True)
    
    # 加载主评论
    print(f"   📂 加载主评论文件...", flush=True)
    with open(main_file, 'r', encoding='utf-8') as f:
        main_data = json.load(f)
    
    main_comments = main_data.get('comments', [])
    print(f"   📊 主评论文件中有 {len(main_comments)} 条", flush=True)
    
    # 导入主评论
    print(f"   📥 导入主评论...", flush=True)
    main_count = import_comments_batch(supabase, post_id, main_comments, existing_ids, is_sub=False)
    
    # 加载并导入子评论
    sub_count = 0
    if sub_file.exists():
        print(f"   📂 加载子评论文件...", flush=True)
        with open(sub_file, 'r', encoding='utf-8') as f:
            sub_data = json.load(f)
        
        sub_comments_dict = sub_data.get('sub_comments', {})
        total_subs = sum(len(subs) for subs in sub_comments_dict.values())
        print(f"   📊 子评论文件中有 {total_subs} 条", flush=True)
        
        # 转换为列表格式
        all_subs = []
        for parent_id, subs in sub_comments_dict.items():
            for sub in subs:
                sub['parent_comment_id'] = parent_id
                all_subs.append(sub)
        
        print(f"   📥 导入子评论...", flush=True)
        sub_count = import_comments_batch(supabase, post_id, all_subs, existing_ids, is_sub=True)
    
    return main_count, sub_count


def get_or_create_platform_post(supabase: Client, note_id: str, note_info: dict) -> int:
    """获取或创建 platform_post 记录"""
    # 检查是否已存在
    existing = supabase.table('gg_platform_post').select('id').eq('platform', 'xiaohongshu').eq('platform_item_id', note_id).execute()
    
    if existing.data:
        return existing.data[0]['id']
    
    # 插入数据
    insert_data = {
        'platform': 'xiaohongshu',
        'platform_item_id': note_id,
        'title': note_info.get('title', ''),
        'content': note_info.get('content', ''),
        'post_type': 'note' if note_info.get('note_type') == 'normal' else 'video',
        'like_count': note_info.get('liked_count', 0),
        'comment_count': note_info.get('comments_count', 0),
        'share_count': note_info.get('shared_count', 0),
        'cover_url': note_info.get('cover_url'),
        'author_id': note_info.get('author_id'),
        'author_name': note_info.get('author_name'),
        'analysis_status': 'init',
        'raw_details': note_info.get('raw_data'),
        'project_id': PROJECT_ID
    }
    
    result = supabase.table('gg_platform_post').insert(insert_data).execute()
    return result.data[0]['id'] if result.data else None


def update_pillow_project_status(supabase: Client, note_id: str, main_count: int, sub_count: int):
    """更新抱枕项目状态"""
    # 先获取当前值
    current = supabase.table('gg_redbook_pillow_project').select('main_comments_fetched, sub_comments_fetched').eq('note_id', note_id).execute()
    
    if current.data:
        current_main = current.data[0].get('main_comments_fetched', 0) or 0
        current_sub = current.data[0].get('sub_comments_fetched', 0) or 0
        new_main = current_main + main_count
        new_sub = current_sub + sub_count
    else:
        new_main = main_count
        new_sub = sub_count
    
    supabase.table('gg_redbook_pillow_project').update({
        'main_comments_fetched': new_main,
        'sub_comments_fetched': new_sub,
        'fetch_status': 'completed',
        'fetch_completed_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }).eq('note_id', note_id).execute()


def main():
    print("=" * 60, flush=True)
    print("数据导入工具", flush=True)
    print("=" * 60, flush=True)
    print(f"批次大小: {BATCH_SIZE}", flush=True)
    print(f"项目 ID: {PROJECT_ID}", flush=True)
    
    # 初始化
    print("\n🔌 连接数据库...", flush=True)
    supabase = get_supabase_client()
    print("   ✅ 连接成功", flush=True)
    
    script_dir = Path(__file__).parent
    search_dir = script_dir / "search" / "output"
    comments_dir = script_dir / "comment" / "output"
    
    # 1. 加载搜索结果
    print("\n📂 加载搜索结果...", flush=True)
    notes = load_search_results(search_dir)
    print(f"   共加载 {len(notes)} 个帖子", flush=True)
    
    # 2. 支持命令行参数指定帖子
    import sys
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.startswith('--id='):
            target_note_id = arg.split('=')[1]
        elif arg.startswith('--index='):
            # 从数据库获取待处理帖子
            pending = supabase.table('gg_redbook_pillow_project').select('note_id').eq('fetch_status', 'pending').order('comments_count', desc=True).execute()
            index = int(arg.split('=')[1])
            if index >= len(pending.data):
                print(f"❌ 索引 {index} 超出范围，共 {len(pending.data)} 个待处理帖子")
                return
            target_note_id = pending.data[index]['note_id']
        else:
            target_note_id = arg
    else:
        # 默认处理第一个待处理的帖子
        pending = supabase.table('gg_redbook_pillow_project').select('note_id').eq('fetch_status', 'pending').order('comments_count', desc=True).limit(1).execute()
        if pending.data:
            target_note_id = pending.data[0]['note_id']
        else:
            print("✅ 没有待处理的帖子")
            return
    
    target_note = next((n for n in notes if n['note_id'] == target_note_id), None)
    
    if target_note:
        print(f"\n{'='*60}", flush=True)
        print(f"📥 导入帖子评论数据", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"   帖子 ID: {target_note_id}", flush=True)
        print(f"   标题: {target_note['title'][:40]}...", flush=True)
        
        # 获取或创建 platform_post
        print(f"\n   📝 检查/创建 platform_post...", flush=True)
        post_id = get_or_create_platform_post(supabase, target_note_id, target_note)
        print(f"   ✅ post_id: {post_id}", flush=True)
        
        if post_id:
            # 导入评论
            main_count, sub_count = import_first_note_comments(supabase, target_note_id, post_id, comments_dir)
            
            print(f"\n   📊 本次导入结果:", flush=True)
            print(f"      主评论: {main_count} 条", flush=True)
            print(f"      子评论: {sub_count} 条", flush=True)
            
            # 更新项目状态（使用实际获取的数量）
            # 从文件读取实际数量
            main_file = comments_dir / f"main_comments_{target_note_id}.json"
            sub_file = comments_dir / f"sub_comments_{target_note_id}.json"
            
            actual_main = 0
            actual_sub = 0
            if main_file.exists():
                with open(main_file, 'r', encoding='utf-8') as f:
                    actual_main = len(json.load(f).get('comments', []))
            if sub_file.exists():
                with open(sub_file, 'r', encoding='utf-8') as f:
                    sub_data = json.load(f).get('sub_comments', {})
                    actual_sub = sum(len(subs) for subs in sub_data.values())
            
            # 更新状态
            supabase.table('gg_redbook_pillow_project').update({
                'main_comments_fetched': actual_main,
                'sub_comments_fetched': actual_sub,
                'fetch_status': 'completed',
                'fetch_completed_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).eq('note_id', target_note_id).execute()
            print(f"   ✅ 项目状态已更新", flush=True)
    else:
        print(f"❌ 未找到帖子 {target_note_id} 的信息")
        return
    
    # 3. 查询最终状态
    print(f"\n{'='*60}", flush=True)
    print(f"📊 最终状态", flush=True)
    print(f"{'='*60}", flush=True)
    
    # 查询抱枕项目表
    pillow_result = supabase.table('gg_redbook_pillow_project').select('note_id, title, comments_count, main_comments_fetched, sub_comments_fetched, fetch_status').eq('note_id', target_note_id).execute()
    
    if pillow_result.data:
        row = pillow_result.data[0]
        print(f"   帖子: {row['title'][:30]}...", flush=True)
        print(f"   API 评论数: {row['comments_count']}", flush=True)
        print(f"   已获取主评论: {row['main_comments_fetched']}", flush=True)
        print(f"   已获取子评论: {row['sub_comments_fetched']}", flush=True)
        print(f"   状态: {row['fetch_status']}", flush=True)
    
    # 查询评论表
    comments_result = supabase.table('gg_platform_post_comments').select('id', count='exact').eq('post_id', post_id).execute()
    print(f"   数据库中评论总数: {comments_result.count}", flush=True)
    
    print(f"\n{'='*60}", flush=True)
    print("✅ 数据导入完成", flush=True)
    print(f"{'='*60}", flush=True)


if __name__ == "__main__":
    main()
