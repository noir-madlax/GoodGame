#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从现有搜索数据中提取 author_id 和 note_id 用于测试

功能:
1. 读取 search/output 目录下的搜索结果
2. 提取 author_id (从 widgets_context JSON 中)
3. 提取 note_id (从 note.id 中)
4. 保存到 params/config.json 供后续测试使用
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any


def extract_ids_from_search_results(search_output_dir: Path) -> Dict[str, List[str]]:
    """
    从搜索结果中提取 author_id 和 note_id
    
    Returns:
        {
            "author_ids": [...],
            "note_ids": [...],
            "user_ids": [...]
        }
    """
    author_ids: Set[str] = set()
    note_ids: Set[str] = set()
    user_ids: Set[str] = set()
    
    # 遍历所有 JSON 文件
    json_files = list(search_output_dir.glob("*.json"))
    print(f"📂 找到 {len(json_files)} 个 JSON 文件")
    
    for json_file in json_files:
        print(f"  处理: {json_file.name}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理搜索结果格式
            items = []
            
            # 格式1: TikHub API 返回格式
            if 'data' in data and isinstance(data['data'], dict):
                inner_data = data['data'].get('data', {})
                if isinstance(inner_data, dict):
                    items = inner_data.get('items', [])
            
            # 格式2: 直接的 items 列表
            if not items and isinstance(data, list):
                items = data
            
            for item in items:
                # 提取 note_id
                note = item.get('note', item)  # 兼容两种格式
                if isinstance(note, dict):
                    note_id = note.get('id')
                    if note_id:
                        note_ids.add(note_id)
                    
                    # 从 user 字段提取 user_id
                    user = note.get('user', {})
                    if isinstance(user, dict):
                        user_id = user.get('userid') or user.get('user_id')
                        if user_id:
                            user_ids.add(user_id)
                
                # 从 widgets_context 提取 author_id
                widgets_context = item.get('widgets_context') or (note.get('widgets_context') if isinstance(note, dict) else None)
                if widgets_context and isinstance(widgets_context, str):
                    try:
                        ctx = json.loads(widgets_context)
                        author_id = ctx.get('author_id')
                        if author_id:
                            author_ids.add(author_id)
                    except json.JSONDecodeError:
                        pass
                
        except Exception as e:
            print(f"    ⚠️ 处理失败: {e}")
    
    result = {
        "author_ids": sorted(list(author_ids)),
        "note_ids": sorted(list(note_ids)),
        "user_ids": sorted(list(user_ids))
    }
    
    print(f"\n📊 提取结果:")
    print(f"  - author_ids: {len(result['author_ids'])} 个")
    print(f"  - note_ids: {len(result['note_ids'])} 个")
    print(f"  - user_ids: {len(result['user_ids'])} 个")
    
    return result


def update_config(config_path: Path, ids: Dict[str, List[str]]) -> None:
    """
    更新配置文件中的测试 ID
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 取前 5 个作为测试样本
    config['test_kol_ids'] = ids['author_ids'][:5]
    config['test_note_ids'] = ids['note_ids'][:5]
    config['test_user_ids'] = ids['user_ids'][:5] if ids['user_ids'] else ids['author_ids'][:5]
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 配置已更新: {config_path}")
    print(f"  test_kol_ids: {config['test_kol_ids']}")
    print(f"  test_note_ids: {config['test_note_ids']}")
    print(f"  test_user_ids: {config['test_user_ids']}")


def main():
    print("=" * 60)
    print("从搜索结果提取测试 ID")
    print("=" * 60)
    
    # 定位目录
    script_dir = Path(__file__).parent.parent
    search_output_dir = script_dir.parent / "search" / "output"
    config_path = script_dir / "params" / "config.json"
    
    print(f"\n搜索结果目录: {search_output_dir}")
    print(f"配置文件路径: {config_path}")
    
    if not search_output_dir.exists():
        print(f"❌ 搜索结果目录不存在: {search_output_dir}")
        return
    
    # 提取 ID
    ids = extract_ids_from_search_results(search_output_dir)
    
    # 保存提取结果
    output_path = script_dir / "output" / "extracted_ids.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)
    print(f"\n💾 完整 ID 列表已保存: {output_path}")
    
    # 更新配置
    if config_path.exists():
        update_config(config_path, ids)
    else:
        print(f"⚠️ 配置文件不存在: {config_path}")


if __name__ == "__main__":
    main()
