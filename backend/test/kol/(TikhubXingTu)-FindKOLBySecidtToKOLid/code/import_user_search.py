#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
临时脚本：导入72位KOL用户到 gg_douyin_user_search 表

使用方法:
    python import_user_search.py

依赖:
    pip install python-dotenv supabase
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# 加载环境变量
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / '.env')

# Supabase配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("错误: 未找到SUPABASE_URL或SUPABASE_KEY环境变量")
    sys.exit(1)

# 创建Supabase客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数"""
    if value is None or value == '':
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def parse_user_search_data(kol_file: Path) -> Optional[Dict]:
    """
    从KOL检查文件中解析用户搜索数据

    Args:
        kol_file: KOL检查JSON文件路径

    Returns:
        解析后的用户数据字典，如果解析失败返回None
    """
    try:
        with open(kol_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        user_info = data.get('user_info', {})
        api_response = data.get('api_response', {})

        # 提取api_response中的data部分作为raw_data
        api_data = api_response.get('data', {})

        return {
            'uid': user_info.get('uid'),
            'sec_uid': user_info.get('sec_uid'),
            'nickname': user_info.get('nickname'),
            'follower_count': safe_int(user_info.get('follower_count')),
            'raw_data': api_response,  # 保存完整的API响应
            'search_keyword': '皮肤好 专家',  # 从文件名推断的搜索关键词
            'search_date': datetime.now().date().isoformat(),  # 当前日期
        }

    except Exception as e:
        print(f"❌ 解析文件 {kol_file.name} 失败: {str(e)}")
        return None


def import_user_search_batch(user_data_list: List[Dict]) -> Dict[str, int]:
    """
    批量导入用户搜索数据

    Args:
        user_data_list: 用户数据列表

    Returns:
        统计信息字典
    """
    stats = {
        'total': len(user_data_list),
        'success': 0,
        'error': 0,
        'duplicates': 0
    }

    for idx, user_data in enumerate(user_data_list, 1):
        uid = user_data.get('uid')
        nickname = user_data.get('nickname', '未知')

        print(f"  [{idx}/{len(user_data_list)}] 导入用户: {nickname} (UID: {uid})")

        try:
            # 使用upsert确保不重复插入
            result = supabase.table('gg_douyin_user_search').upsert(
                user_data,
                on_conflict='uid'
            ).execute()

            stats['success'] += 1
            print(f"    ✅ 已导入")

        except Exception as e:
            error_msg = str(e)
            if 'duplicate key value' in error_msg.lower():
                stats['duplicates'] += 1
                print(f"    ⚠️ 重复数据，已跳过")
            else:
                stats['error'] += 1
                print(f"    ❌ 导入失败: {error_msg}")

    return stats


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 抖音用户搜索数据导入工具")
    print("=" * 80)

    # 数据目录
    detail_dir = Path(__file__).parent.parent / 'detail'

    if not detail_dir.exists():
        print(f"❌ 数据目录不存在: {detail_dir}")
        return

    # 获取所有KOL检查文件
    kol_files = list(detail_dir.glob('kol_check_*.json'))

    if not kol_files:
        print("❌ 未找到KOL检查文件")
        return

    print(f"\n📊 找到 {len(kol_files)} 个KOL检查文件")

    # 分批处理，每批20个用户
    batch_size = 20
    total_stats = {
        'total': 0,
        'success': 0,
        'error': 0,
        'duplicates': 0
    }

    for i in range(0, len(kol_files), batch_size):
        batch_files = kol_files[i:i + batch_size]
        batch_data = []

        print(f"\n🔄 处理第 {i//batch_size + 1} 批 (文件 {i+1}-{min(i+batch_size, len(kol_files))})")

        # 解析这一批的数据
        for kol_file in batch_files:
            user_data = parse_user_search_data(kol_file)
            if user_data:
                batch_data.append(user_data)

        if batch_data:
            # 导入这一批数据
            batch_stats = import_user_search_batch(batch_data)

            # 累加统计
            for key in total_stats:
                total_stats[key] += batch_stats[key]

            print(f"  📊 本批统计: 成功 {batch_stats['success']}, 失败 {batch_stats['error']}, 重复 {batch_stats['duplicates']}")
        else:
            print("  ⚠️ 本批无有效数据")

    # 打印汇总统计
    print("\n" + "=" * 80)
    print("📈 导入统计汇总")
    print("=" * 80)
    print(f"总文件数: {len(kol_files)}")
    print(f"解析成功: {total_stats['total']}")
    print(f"✅ 导入成功: {total_stats['success']}")
    print(f"❌ 导入失败: {total_stats['error']}")
    print(f"⚠️ 重复数据: {total_stats['duplicates']}")
    print("=" * 80)


if __name__ == '__main__':
    main()
