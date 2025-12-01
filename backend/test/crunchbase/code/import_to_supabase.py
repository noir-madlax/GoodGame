#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 Crunchbase 公司数据到 Supabase 数据库

读取所有解析好的JSON文件，批量导入到 gg_crunchbase_company 表。
使用 upsert 机制避免重复插入（以 organization_name 为唯一键）。

使用方法:
    cd backend
    source .venv/bin/activate
    python test/crunchbase/code/import_to_supabase.py
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# 添加 backend 目录到路径，以便导入项目模块
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from supabase import create_client, Client


def load_env():
    """加载环境变量"""
    env_path = backend_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("请在 .env 文件中配置 SUPABASE_URL 和 SUPABASE_KEY")
    
    return supabase_url, supabase_key


def get_supabase_client() -> Client:
    """获取 Supabase 客户端"""
    url, key = load_env()
    return create_client(url, key)


def find_json_files(base_dir: Path) -> dict[str, list[Path]]:
    """
    查找所有目录下的JSON文件
    
    返回:
        字典，key为目录名（source_category），value为该目录下的JSON文件列表
    """
    # 目标目录列表
    target_dirs = [
        'ai-a-2025',
        'ai-Seed-2025', 
        'ai-b-2025',
        'board-a-2025'
    ]
    
    result = {}
    
    for dir_name in target_dirs:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            json_files = sorted(
                [f for f in dir_path.glob('div*.json')],
                key=lambda x: int(x.stem.replace('div', '')) if x.stem.replace('div', '').isdigit() else 999
            )
            if json_files:
                result[dir_name] = json_files
    
    return result


def load_companies_from_json(json_file: Path, source_category: str) -> list[dict]:
    """
    从JSON文件加载公司数据
    
    参数:
        json_file: JSON文件路径
        source_category: 数据来源分类
        
    返回:
        公司数据列表，每个元素已添加 source_category 字段
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    companies = data.get('companies', [])
    
    # 为每个公司添加 source_category
    for company in companies:
        company['source_category'] = source_category
    
    return companies


def import_companies(supabase: Client, companies: list[dict]) -> dict:
    """
    批量导入公司数据到数据库
    
    使用 upsert 机制，以 organization_name 为唯一键，
    已存在的公司会被更新，新公司会被插入。
    
    参数:
        supabase: Supabase 客户端
        companies: 公司数据列表
        
    返回:
        导入统计信息
    """
    stats = {
        'total': len(companies),
        'success': 0,
        'skipped': 0,
        'errors': []
    }
    
    if not companies:
        return stats
    
    # 准备数据，确保字段名匹配数据库列名
    records = []
    for company in companies:
        # 跳过没有公司名的记录
        if not company.get('organization_name'):
            stats['skipped'] += 1
            continue
            
        record = {
            'organization_name': company.get('organization_name'),
            'industries': company.get('industries'),  # JSONB 字段直接传数组
            'last_funding_type': company.get('last_funding_type'),
            'last_funding_date': company.get('last_funding_date'),
            'headquarters_location': company.get('headquarters_location'),
            'description': company.get('description'),
            'source_category': company.get('source_category')
        }
        records.append(record)
    
    if not records:
        return stats
    
    try:
        # 使用 upsert，以 organization_name 为冲突键
        # on_conflict 指定冲突时更新的列
        result = supabase.table('gg_crunchbase_company').upsert(
            records,
            on_conflict='organization_name'  # 唯一约束字段
        ).execute()
        
        stats['success'] = len(result.data) if result.data else 0
        
    except Exception as e:
        stats['errors'].append(str(e))
        # 如果批量失败，尝试单条插入
        print(f"    批量插入失败，尝试单条插入: {str(e)[:100]}")
        for record in records:
            try:
                supabase.table('gg_crunchbase_company').upsert(
                    record,
                    on_conflict='organization_name'
                ).execute()
                stats['success'] += 1
            except Exception as e2:
                stats['errors'].append(f"{record.get('organization_name')}: {str(e2)[:50]}")
    
    return stats


def main():
    """主函数"""
    print("=" * 60)
    print("Crunchbase 公司数据导入工具")
    print("=" * 60)
    
    # 获取 Supabase 客户端
    print("\n正在连接数据库...")
    try:
        supabase = get_supabase_client()
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        sys.exit(1)
    
    # 查找所有JSON文件
    crunchbase_dir = Path(__file__).parent.parent
    json_files_by_category = find_json_files(crunchbase_dir)
    
    total_files = sum(len(files) for files in json_files_by_category.values())
    print(f"\n找到 {len(json_files_by_category)} 个目录，共 {total_files} 个JSON文件")
    
    # 统计信息
    all_stats = {
        'total_companies': 0,
        'total_imported': 0,
        'total_skipped': 0,
        'categories': {}
    }
    
    # 按目录处理
    for source_category, json_files in json_files_by_category.items():
        print(f"\n{'='*60}")
        print(f"处理目录: {source_category} ({len(json_files)} 个文件)")
        print('='*60)
        
        category_stats = {
            'companies': 0,
            'imported': 0,
            'skipped': 0
        }
        
        for json_file in json_files:
            # 加载公司数据
            companies = load_companies_from_json(json_file, source_category)
            
            if not companies:
                print(f"  [跳过] {json_file.name} (无数据)")
                continue
            
            # 导入数据库
            stats = import_companies(supabase, companies)
            
            print(f"  [完成] {json_file.name}: {stats['success']}/{len(companies)} 条")
            
            if stats['errors']:
                for err in stats['errors'][:3]:  # 只显示前3个错误
                    print(f"         错误: {err[:80]}")
            
            category_stats['companies'] += len(companies)
            category_stats['imported'] += stats['success']
            category_stats['skipped'] += stats['skipped']
        
        all_stats['categories'][source_category] = category_stats
        all_stats['total_companies'] += category_stats['companies']
        all_stats['total_imported'] += category_stats['imported']
        all_stats['total_skipped'] += category_stats['skipped']
    
    # 打印总结
    print("\n" + "=" * 60)
    print("导入完成! 汇总统计:")
    print("=" * 60)
    print(f"  总公司数: {all_stats['total_companies']}")
    print(f"  成功导入: {all_stats['total_imported']}")
    print(f"  跳过记录: {all_stats['total_skipped']}")
    
    print("\n各目录统计:")
    for category, stats in all_stats['categories'].items():
        print(f"  {category}: {stats['imported']}/{stats['companies']} 条")
    
    # 查询数据库中的总记录数
    try:
        result = supabase.table('gg_crunchbase_company').select('id', count='exact').execute()
        print(f"\n数据库当前总记录数: {result.count}")
    except Exception as e:
        print(f"\n查询总数失败: {e}")
    
    return all_stats


if __name__ == '__main__':
    main()

