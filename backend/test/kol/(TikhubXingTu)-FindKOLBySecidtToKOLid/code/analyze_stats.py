#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统计分析 check_kol_status.py 的运行结果
"""

import json
import os
from pathlib import Path

def analyze_results():
    # 路径
    base_dir = Path(__file__).resolve().parents[5]
    detail_dir = base_dir / "backend/test/kol/secidtToKOL/detail"
    
    if not detail_dir.exists():
        print(f"Detail dir not found: {detail_dir}")
        return

    files = list(detail_dir.glob("kol_check_*.json"))
    total_files = len(files)
    
    xingtu_kol_count = 0
    non_kol_count = 0
    error_count = 0
    
    # 原始返回字段检查
    has_raw_data_count = 0
    
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
                if data.get('is_kol'):
                    xingtu_kol_count += 1
                elif data.get('error'):
                    error_count += 1
                else:
                    non_kol_count += 1
                    
                # 检查是否有 api_response.data (原始返回)
                if 'api_response' in data and 'data' in data['api_response']:
                    has_raw_data_count += 1
                    
        except Exception as e:
            print(f"Error reading {f}: {e}")

    print(f"📊 统计结果 (Total Files: {total_files})")
    print(f"✅ 星图 KOL: {xingtu_kol_count} ({xingtu_kol_count/total_files*100:.1f}%)")
    print(f"⚠️ 非 KOL: {non_kol_count} ({non_kol_count/total_files*100:.1f}%)")
    print(f"❌ 错误: {error_count}")
    print(f"💾 包含原始返回(api_response.data): {has_raw_data_count}/{total_files}")

if __name__ == "__main__":
    analyze_results()

