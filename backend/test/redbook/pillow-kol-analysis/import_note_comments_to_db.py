"""
导入笔记评论数据到数据库

策略：
1. 已存在的笔记：仅更新 comment_num（其他字段不覆盖）
2. 不存在的笔记：插入新记录（仅6个月内的数据）
3. 增量模式：跳过已更新的记录
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# 加载环境变量
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# 目录配置
CURRENT_DIR = Path(__file__).parent
NOTE_COMMENTS_DIR = CURRENT_DIR / "output" / "note_comments"

# 时间限制：只导入6个月内的数据
SIX_MONTHS_AGO = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')


def get_supabase_client() -> Client:
    """获取 Supabase 客户端"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def load_new_notes_data() -> dict:
    """加载所有新获取的笔记数据，返回 {note_id: note_data} 字典"""
    all_notes = {}
    
    for file in NOTE_COMMENTS_DIR.glob("kol_*_notes.json"):
        kol_id = file.stem.replace("kol_", "").replace("_notes", "")
        
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for note in data.get('notes', []):
            note_id = note.get('id')
            if note_id:
                note['kol_id'] = kol_id
                all_notes[note_id] = note
    
    return all_notes


def get_existing_notes_info(supabase: Client) -> dict:
    """获取数据库中已存在的笔记信息，返回 {note_id: {'comment_num': x}} """
    existing = {}
    page_size = 1000
    offset = 0
    
    print("   获取数据库笔记信息...")
    while True:
        response = supabase.table('gg_pgy_kol_notes') \
            .select('note_id, comment_num') \
            .range(offset, offset + page_size - 1) \
            .execute()
        
        if not response.data:
            break
        
        for row in response.data:
            existing[row['note_id']] = {
                'comment_num': row.get('comment_num') or 0
            }
        
        print(f"   已获取 {len(existing)} 条...")
        
        if len(response.data) < page_size:
            break
        
        offset += page_size
    
    return existing


def import_notes_incremental():
    """增量导入笔记数据"""
    print("=" * 60)
    print("开始增量导入笔记评论数据到数据库")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    supabase = get_supabase_client()
    
    # 加载新数据
    print("\n1. 加载新获取的笔记数据...")
    new_notes = load_new_notes_data()
    print(f"   新数据笔记数: {len(new_notes)}")
    
    # 获取已存在的笔记信息（包括 comment_num）
    print("\n2. 获取数据库已有的笔记信息...")
    existing_notes = get_existing_notes_info(supabase)
    print(f"   数据库已有笔记数: {len(existing_notes)}")
    
    # 分类：区分需要更新和需要插入的
    to_update = []
    to_insert = []
    already_done = 0
    skipped_old = 0
    
    for note_id, note in new_notes.items():
        create_date = note.get('create_date', '')
        new_comment_num = note.get('comments_count', 0)
        
        # 检查是否超过6个月
        if create_date < SIX_MONTHS_AGO:
            skipped_old += 1
            continue
        
        if note_id in existing_notes:
            # 已存在：检查是否需要更新
            existing_comment = existing_notes[note_id]['comment_num']
            if existing_comment == 0 and new_comment_num > 0:
                # 需要更新
                to_update.append({
                    'note_id': note_id,
                    'comment_num': new_comment_num
                })
            else:
                # 已更新过或本身就是0
                already_done += 1
        else:
            # 不存在：需要插入
            to_insert.append({
                'note_id': note_id,
                'kol_id': note.get('kol_id'),
                'title': note.get('title', '')[:200] if note.get('title') else None,
                'is_video': note.get('type') == 'video',
                'like_num': note.get('likes', 0),
                'collect_num': note.get('collected_count', 0),
                'comment_num': new_comment_num,
                'share_num': note.get('share_count', 0),
                'publish_date': create_date if create_date else None,
                'raw_data': note,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
    
    print(f"\n3. 数据分类结果:")
    print(f"   需要更新评论数: {len(to_update)} 条")
    print(f"   需要插入新记录: {len(to_insert)} 条")
    print(f"   已完成(跳过): {already_done} 条")
    print(f"   超过6个月(跳过): {skipped_old} 条")
    
    # 执行更新
    if to_update:
        print(f"\n4. 执行更新操作 (共 {len(to_update)} 条)...")
        updated_count = 0
        update_errors = 0
        
        for i, item in enumerate(to_update):
            try:
                supabase.table('gg_pgy_kol_notes') \
                    .update({'comment_num': item['comment_num'], 'updated_at': datetime.now().isoformat()}) \
                    .eq('note_id', item['note_id']) \
                    .execute()
                updated_count += 1
                
                # 每50条打印一次进度
                if (i + 1) % 50 == 0:
                    print(f"   ✅ 更新进度: {i + 1}/{len(to_update)} ({(i+1)*100//len(to_update)}%)")
            except Exception as e:
                update_errors += 1
                if update_errors <= 3:
                    print(f"   ❌ 更新失败 {item['note_id']}: {e}")
        
        print(f"   更新完成: 成功 {updated_count}, 失败 {update_errors}")
    else:
        print("\n4. 无需更新（已全部完成）")
        updated_count = 0
        update_errors = 0
    
    # 执行插入
    if to_insert:
        print(f"\n5. 执行插入操作 (共 {len(to_insert)} 条)...")
        inserted_count = 0
        insert_errors = 0
        
        batch_size = 50
        for i in range(0, len(to_insert), batch_size):
            batch = to_insert[i:i + batch_size]
            try:
                supabase.table('gg_pgy_kol_notes').insert(batch).execute()
                inserted_count += len(batch)
                print(f"   ✅ 插入进度: {min(i + batch_size, len(to_insert))}/{len(to_insert)} ({min(i + batch_size, len(to_insert))*100//len(to_insert)}%)")
            except Exception as e:
                insert_errors += len(batch)
                print(f"   ❌ 插入批次失败: {e}")
        
        print(f"   插入完成: 成功 {inserted_count}, 失败 {insert_errors}")
    else:
        print("\n5. 无需插入新记录")
        inserted_count = 0
        insert_errors = 0
    
    # 汇总
    print("\n" + "=" * 60)
    print("导入完成！")
    print(f"  更新评论数: {updated_count} 条")
    print(f"  插入新记录: {inserted_count} 条")
    print(f"  已完成跳过: {already_done} 条")
    print(f"  总计处理: {updated_count + inserted_count + already_done} 条")
    print("=" * 60)
    
    return {
        'updated': updated_count,
        'inserted': inserted_count,
        'already_done': already_done,
        'update_errors': update_errors,
        'insert_errors': insert_errors
    }


if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ 未配置 SUPABASE_URL 或 SUPABASE_KEY")
    else:
        import_notes_incremental()
