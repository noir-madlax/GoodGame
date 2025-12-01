#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量解析 Crunchbase DIV 文件

遍历指定目录下的所有div文件，调用parse_crunchbase_div.py进行解析，
输出JSON文件到同目录下。

使用方法:
    python batch_parse.py
"""

import os
import sys
from pathlib import Path

# 导入解析模块
from parse_crunchbase_div import parse_crunchbase_div

import json


def find_div_files(directory: Path) -> list[Path]:
    """
    查找目录下所有的div文件（不包括.json文件）
    
    参数:
        directory: 目标目录
        
    返回:
        div文件路径列表
    """
    div_files = []
    for item in directory.iterdir():
        # 只处理以div开头且不是json文件的文件
        if item.is_file() and item.name.startswith('div') and not item.suffix == '.json':
            div_files.append(item)
    
    # 按数字排序
    def sort_key(path):
        # 提取div后面的数字
        name = path.name
        if name.startswith('div'):
            try:
                return int(name[3:])
            except ValueError:
                return 999
        return 999
    
    return sorted(div_files, key=sort_key)


def process_directory(directory: Path) -> dict:
    """
    处理单个目录下的所有div文件
    
    参数:
        directory: 目标目录
        
    返回:
        处理统计信息
    """
    stats = {
        'directory': directory.name,
        'total_files': 0,
        'processed': 0,
        'skipped': 0,
        'total_companies': 0,
        'files': []
    }
    
    div_files = find_div_files(directory)
    stats['total_files'] = len(div_files)
    
    print(f"\n{'='*60}")
    print(f"处理目录: {directory.name}")
    print(f"找到 {len(div_files)} 个div文件")
    print('='*60)
    
    for div_file in div_files:
        json_file = div_file.with_suffix('.json')
        
        # 检查是否已经有对应的json文件
        if json_file.exists():
            print(f"  [跳过] {div_file.name} (已存在 {json_file.name})")
            stats['skipped'] += 1
            # 读取已存在的json统计公司数量
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    company_count = data.get('total_count', len(data.get('companies', [])))
                    stats['total_companies'] += company_count
                    stats['files'].append({
                        'file': div_file.name,
                        'companies': company_count,
                        'status': 'skipped'
                    })
            except:
                pass
            continue
        
        # 读取并解析div文件
        try:
            with open(div_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            companies = parse_crunchbase_div(content)
            
            # 保存为JSON
            result = {
                "total_count": len(companies),
                "source_file": div_file.name,
                "companies": companies
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"  [完成] {div_file.name} -> {json_file.name} ({len(companies)} 家公司)")
            stats['processed'] += 1
            stats['total_companies'] += len(companies)
            stats['files'].append({
                'file': div_file.name,
                'companies': len(companies),
                'status': 'processed'
            })
            
        except Exception as e:
            print(f"  [错误] {div_file.name}: {str(e)}")
            stats['files'].append({
                'file': div_file.name,
                'companies': 0,
                'status': f'error: {str(e)}'
            })
    
    return stats


def main():
    """主函数"""
    # 获取crunchbase目录
    code_dir = Path(__file__).parent
    crunchbase_dir = code_dir.parent
    
    # 要处理的子目录列表
    target_dirs = [
        'ai-a-2025',
        'ai-Seed-2025',
        'ai-b-2025',
        'board-a-2025'
    ]
    
    all_stats = []
    total_companies = 0
    total_processed = 0
    total_skipped = 0
    
    print("=" * 60)
    print("Crunchbase DIV 批量解析工具")
    print("=" * 60)
    
    for dir_name in target_dirs:
        target_path = crunchbase_dir / dir_name
        if target_path.exists() and target_path.is_dir():
            stats = process_directory(target_path)
            all_stats.append(stats)
            total_companies += stats['total_companies']
            total_processed += stats['processed']
            total_skipped += stats['skipped']
        else:
            print(f"\n[警告] 目录不存在: {dir_name}")
    
    # 打印总结
    print("\n" + "=" * 60)
    print("处理完成! 汇总统计:")
    print("=" * 60)
    print(f"  总目录数: {len(all_stats)}")
    print(f"  新处理文件: {total_processed}")
    print(f"  跳过文件: {total_skipped}")
    print(f"  公司总数: {total_companies}")
    
    print("\n各目录统计:")
    for stats in all_stats:
        print(f"  {stats['directory']}: {stats['total_companies']} 家公司 "
              f"({stats['processed']} 新处理, {stats['skipped']} 跳过)")
    
    return all_stats


if __name__ == '__main__':
    main()

