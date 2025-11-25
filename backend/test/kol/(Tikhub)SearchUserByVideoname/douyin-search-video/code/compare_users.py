#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对比两个关键词搜索结果的人物重合度，并与数据库进行对比
1. 获取 "护肤保养" (13页数据) 的所有作者ID
2. 获取 "皮肤好 专家" (3页数据) 的所有作者ID
3. 计算重合度
4. 连接数据库，对比 gg_xingtu_kol_base_info 表中的作者ID

作者: AI Agent
创建时间: 2025-11-24
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

def load_env():
    """加载环境变量"""
    # 向上查找 .env
    backend_dir = Path(__file__).resolve().parents[5]
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    else:
        cwd_env = Path.cwd() / '.env'
        if cwd_env.exists():
            load_dotenv(cwd_env)

def get_db_connection():
    """获取数据库连接"""
    load_env()
    
    # 从 Supabase URL 解析连接信息
    # SUPABASE_URL=postgres://user:password@host:port/dbname
    db_url = os.getenv("SUPABASE_URL")
    
    if not db_url:
        print("⚠️ 未找到 SUPABASE_URL 环境变量，无法连接数据库")
        return None
        
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None

def extract_author_ids(directory):
    """从指定目录的JSON文件中提取作者ID"""
    author_ids = set()
    author_info = {} # id -> nickname
    
    files = list(Path(directory).glob("video_search_page_*.json"))
    print(f"📂 正在处理目录: {directory.name} (共 {len(files)} 个文件)")
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 根据 API 返回结构提取作者信息
            # 结构通常是 data.data[] 或者 data.aweme_list[]
            # 每个 item 包含 author 字段
            
            # 检查 data 结构
            api_data = data.get('data', [])
            items = []
            
            if isinstance(api_data, list):
                items = api_data
            elif isinstance(api_data, dict):
                # 尝试常见的列表字段名
                items = api_data.get('data') or api_data.get('aweme_list') or []
            
            for item in items:
                # 有些结构可能是 item['aweme_info']['author'] 或者直接 item['author']
                # 视频搜索返回的结构通常比较复杂，包含不同类型的卡片
                
                author = None
                
                # 情况1: 直接在 item 中
                if 'author' in item:
                    author = item['author']
                # 情况2: 在 aweme_info 中
                elif 'aweme_info' in item and 'author' in item['aweme_info']:
                    author = item['aweme_info']['author']
                
                if author:
                    uid = author.get('uid')
                    sec_uid = author.get('sec_uid') # sec_uid 往往更稳定，但这里先用 uid
                    nickname = author.get('nickname', 'Unknown')
                    
                    # 注意: 有时候 uid 是字符串，有时候是数字，统一转字符串
                    if uid:
                        uid_str = str(uid)
                        author_ids.add(uid_str)
                        author_info[uid_str] = nickname
                        
        except Exception as e:
            print(f"⚠️ 读取文件 {file_path.name} 失败: {e}")
            
    print(f"   ✅ 提取到 {len(author_ids)} 个唯一作者ID")
    return author_ids, author_info

def check_db_overlap(author_ids):
    """检查数据库中是否存在这些作者"""
    existing_ids = set()
    
    # 由于 author_ids 可能是字符串或数字，这里需要处理一下
    # 从 list_tables 知道，gg_platform_author 实际上是 gg_authors 表?
    # 用户之前提到 gg_platform_author，但 list_tables 显示有 gg_authors 和 gg_xingtu_kol_base_info
    # gg_authors 表有 platform_author_id 字段
    # gg_xingtu_kol_base_info 表有 kol_id 字段
    
    # 我们使用 MCP execute_sql 工具来查询，但当前脚本是在本地 Python 环境运行
    # 无法直接调用 MCP 工具。
    # 用户要求 "这次可以成功的用mcp结合数据库的kol也对比完成"
    # 意味着我们需要在 chat 中调用 MCP 工具获取数据，或者配置 Python 脚本连接数据库。
    # 但之前的 Python 脚本连接失败。
    
    # 既然用户在 chat 中，我作为 Assistant 可以调用 MCP。
    # 但是脚本本身无法调用 MCP。
    # 所以策略是：
    # 1. 脚本只负责文件层面的对比，并输出所有新作者 ID 列表到一个文件。
    # 2. Assistant 读取该文件，然后使用 MCP execute_sql 查询数据库。
    # 3. Assistant 生成最终报告。
    
    # 所以这里我们只返回空，或者修改逻辑让主流程知道需要外部协助。
    print("⚠️ 脚本无法直接连接数据库 (DSN错误)。将导出ID列表供 MCP 查询。")
    return existing_ids

def main():
    script_dir = Path(__file__).parent
    base_output_dir = script_dir.parent / 'output'
    
    # 1. 定义目录
    dir_hufu = base_output_dir / 'keyword_护肤保养' / 'detail'
    dir_new = base_output_dir / 'keyword_皮肤好_专家' / 'detail'
    
    # 2. 提取 "护肤保养" 的作者
    print(f"--- 分析 '护肤保养' 数据 ---")
    ids_hufu, info_hufu = extract_author_ids(dir_hufu)
    
    # 3. 提取 "皮肤好 专家" 的作者
    print(f"\n--- 分析 '皮肤好 专家' 数据 ---")
    ids_new, info_new = extract_author_ids(dir_new)
    
    # 4. 计算重合度
    overlap = ids_new.intersection(ids_hufu)
    overlap_rate = len(overlap) / len(ids_new) * 100 if ids_new else 0
    
    print(f"\n--- 对比结果 ---")
    print(f"护肤保养 (基准): {len(ids_hufu)} 人")
    print(f"皮肤好 专家 (新): {len(ids_new)} 人")
    print(f"重合人数: {len(overlap)} 人")
    print(f"重合率 (相对于新数据): {overlap_rate:.2f}%")
    
    if overlap:
        print("\n重合作者示例:")
        for uid in list(overlap)[:5]:
            print(f" - {info_new.get(uid)} (ID: {uid})")
            
    # 5. 导出待查询 ID 列表 (为了 MCP)
    ids_to_check = list(ids_new)
    id_list_file = dir_new / 'author_ids_to_check.json'
    with open(id_list_file, 'w', encoding='utf-8') as f:
        json.dump(ids_to_check, f)
    print(f"\n📋 已导出 {len(ids_to_check)} 个作者ID 到 {id_list_file.name}，请使用 MCP 查询数据库。")

    # 6. 保存初步结果 (不含数据库对比)
    result = {
        "keyword_base": "护肤保养",
        "keyword_new": "皮肤好 专家",
        "base_count": len(ids_hufu),
        "new_count": len(ids_new),
        "overlap_count": len(overlap),
        "overlap_rate_percent": overlap_rate,
        "overlap_authors": [
            {"id": uid, "nickname": info_new.get(uid)} for uid in overlap
        ],
        "new_unique_authors": [
            {"id": uid, "nickname": info_new.get(uid)} 
            for uid in ids_new - ids_hufu
        ]
    }
    
    output_file = dir_new / 'overlap_analysis_local.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ 初步分析结果已保存至: {output_file.name}")

if __name__ == '__main__':
    main()

