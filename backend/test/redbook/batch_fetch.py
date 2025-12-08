#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量获取评论脚本

按顺序处理所有待处理的帖子：
1. 获取主评论
2. 获取子评论
3. 导入数据库
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client


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


def get_pending_notes(supabase: Client) -> list:
    """获取待处理的帖子列表"""
    result = supabase.table('gg_redbook_pillow_project').select(
        'note_id, title, comments_count'
    ).eq('fetch_status', 'pending').order('comments_count', desc=True).execute()
    
    return result.data


def run_command(cmd: list, description: str) -> bool:
    """运行命令并返回是否成功"""
    print(f"\n   🔧 {description}...", flush=True)
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=600  # 10 分钟超时
        )
        
        # 打印输出的最后几行
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines[-10:]:
            if line.strip():
                print(f"      {line}", flush=True)
        
        if result.returncode != 0:
            print(f"      ❌ 错误: {result.stderr[-200:] if result.stderr else '未知错误'}", flush=True)
            return False
        
        return True
    except subprocess.TimeoutExpired:
        print(f"      ❌ 超时", flush=True)
        return False
    except Exception as e:
        print(f"      ❌ 异常: {e}", flush=True)
        return False


def process_note(note_id: str, title: str, index: int, total: int) -> dict:
    """处理单个帖子"""
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent.parent
    
    print(f"\n{'='*60}", flush=True)
    print(f"[{index}/{total}] 处理帖子: {title[:30]}...", flush=True)
    print(f"   ID: {note_id}", flush=True)
    print(f"{'='*60}", flush=True)
    
    result = {
        'note_id': note_id,
        'title': title,
        'main_comments': False,
        'sub_comments': False,
        'import_db': False
    }
    
    # 1. 获取主评论
    cmd = [
        sys.executable,
        str(script_dir / 'comment' / 'fetch_main_comments.py'),
        f'--id={note_id}'
    ]
    result['main_comments'] = run_command(cmd, "获取主评论")
    
    if not result['main_comments']:
        print(f"   ⚠️ 主评论获取失败，跳过后续步骤", flush=True)
        return result
    
    # 2. 获取子评论
    cmd = [
        sys.executable,
        str(script_dir / 'comment' / 'fetch_sub_comments.py'),
        f'--id={note_id}'
    ]
    result['sub_comments'] = run_command(cmd, "获取子评论")
    
    # 3. 导入数据库
    cmd = [
        sys.executable,
        str(script_dir / 'import_to_db.py'),
        f'--id={note_id}'
    ]
    result['import_db'] = run_command(cmd, "导入数据库")
    
    return result


def main():
    print("=" * 60, flush=True)
    print("批量评论获取工具", flush=True)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 60, flush=True)
    
    # 获取待处理帖子
    supabase = get_supabase_client()
    pending_notes = get_pending_notes(supabase)
    
    print(f"\n📋 待处理帖子: {len(pending_notes)} 个", flush=True)
    
    if not pending_notes:
        print("✅ 没有待处理的帖子", flush=True)
        return
    
    # 显示待处理列表
    print("\n待处理列表:", flush=True)
    for i, note in enumerate(pending_notes[:10]):
        print(f"   {i+1}. {note['title'][:30]}... ({note['comments_count']} 评论)", flush=True)
    if len(pending_notes) > 10:
        print(f"   ... 还有 {len(pending_notes) - 10} 个", flush=True)
    
    # 处理每个帖子
    results = []
    for i, note in enumerate(pending_notes):
        result = process_note(
            note_id=note['note_id'],
            title=note['title'],
            index=i + 1,
            total=len(pending_notes)
        )
        results.append(result)
        
        # 每处理完一个，打印进度
        completed = sum(1 for r in results if r['import_db'])
        failed = sum(1 for r in results if not r['main_comments'])
        print(f"\n📊 进度: {i+1}/{len(pending_notes)} | 成功: {completed} | 失败: {failed}", flush=True)
    
    # 最终统计
    print(f"\n{'='*60}", flush=True)
    print("📊 最终统计", flush=True)
    print(f"{'='*60}", flush=True)
    
    success = sum(1 for r in results if r['import_db'])
    failed = sum(1 for r in results if not r['main_comments'])
    partial = len(results) - success - failed
    
    print(f"   总计: {len(results)} 个帖子", flush=True)
    print(f"   成功: {success} 个", flush=True)
    print(f"   部分成功: {partial} 个", flush=True)
    print(f"   失败: {failed} 个", flush=True)
    
    # 保存结果
    result_file = Path(__file__).parent / 'batch_result.json'
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total': len(results),
            'success': success,
            'failed': failed,
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {result_file}", flush=True)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)


if __name__ == "__main__":
    main()
