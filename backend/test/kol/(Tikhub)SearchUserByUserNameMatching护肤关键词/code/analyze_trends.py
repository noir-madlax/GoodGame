#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析1-22页护肤达人数据的趋势变化
"""

import os
import json
from pathlib import Path
from collections import defaultdict


def categorize_user(follower_count):
    """根据粉丝数分类用户"""
    if follower_count > 1_000_000:
        return '头部达人 (>100万)'
    elif follower_count >= 100_000:
        return '腰部达人 (10万~100万)'
    elif follower_count >= 10_000:
        return '尾部达人 (1万~10万)'
    else:
        return '素人 (<1万)'


def main():
    """主函数：统计分析1-22页数据趋势"""
    
    print("=" * 60)
    print("护肤达人数据趋势分析（第1-22页）")
    print("=" * 60)
    
    # 定位到 detail 目录
    script_dir = Path(__file__).parent.parent
    detail_dir = script_dir / "output" / "detail"
    
    # 收集所有页面数据
    all_uids = set()
    page_stats = []
    global_duplicates = 0
    
    for page_num in range(1, 23):
        page_file = detail_dir / f'page_{page_num}_request_response.json'
        
        if not page_file.exists():
            print(f"⚠️ 第{page_num}页文件不存在，跳过")
            continue
        
        with open(page_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取用户列表
        response = data.get('response', {})
        response_data = response.get('data', {})
        inner_data = response_data.get('data', [])
        user_list = inner_data if isinstance(inner_data, list) else []
        
        # 统计本页
        page_categories = {
            '头部达人 (>100万)': 0,
            '腰部达人 (10万~100万)': 0,
            '尾部达人 (1万~10万)': 0,
            '素人 (<1万)': 0
        }
        
        page_duplicates = 0
        
        for user in user_list:
            user_info = user.get('user_info', {})
            uid = user_info.get('uid', '')
            follower_count = user_info.get('follower_count', 0)
            
            # 检查是否重复
            if uid in all_uids:
                page_duplicates += 1
                global_duplicates += 1
            else:
                if uid:
                    all_uids.add(uid)
            
            # 分类统计
            category = categorize_user(follower_count)
            page_categories[category] += 1
        
        # 保存本页统计
        total = len(user_list)
        page_stats.append({
            'page': page_num,
            'total': total,
            'new': total - page_duplicates,
            'duplicates': page_duplicates,
            'categories': page_categories,
            'percentages': {
                cat: (count / total * 100) if total > 0 else 0
                for cat, count in page_categories.items()
            }
        })
    
    # 打印统计结果
    print(f"\n📊 总体统计:")
    print(f"   总页数: {len(page_stats)}")
    print(f"   唯一用户数: {len(all_uids)}")
    print(f"   全局重复数: {global_duplicates}")
    
    # 分段统计（前、中、后）
    print(f"\n📈 分段趋势分析:")
    
    segments = [
        ("第1-7页（前段）", page_stats[0:7]),
        ("第8-15页（中段）", page_stats[7:15]),
        ("第16-22页（后段）", page_stats[15:22])
    ]
    
    for segment_name, segment_data in segments:
        if not segment_data:
            continue
        
        print(f"\n{segment_name}:")
        
        # 计算平均值
        avg_categories = defaultdict(float)
        avg_duplicates = 0
        
        for stat in segment_data:
            for cat, pct in stat['percentages'].items():
                avg_categories[cat] += pct
            avg_duplicates += stat['duplicates']
        
        pages_count = len(segment_data)
        for cat in avg_categories:
            avg_categories[cat] /= pages_count
        avg_duplicates /= pages_count
        
        print(f"  头部达人占比: {avg_categories['头部达人 (>100万)']:.1f}%")
        print(f"  腰部达人占比: {avg_categories['腰部达人 (10万~100万)']:.1f}%")
        print(f"  尾部达人占比: {avg_categories['尾部达人 (1万~10万)']:.1f}%")
        print(f"  素人占比: {avg_categories['素人 (<1万)']:.1f}%")
        print(f"  平均重复数: {avg_duplicates:.1f}")
    
    # 逐页详细统计
    print(f"\n📋 逐页详细统计:")
    print(f"{'页码':<6} {'总数':<6} {'新增':<6} {'重复':<6} {'头部%':<8} {'腰部%':<8} {'尾部%':<8} {'素人%':<8}")
    print("-" * 70)
    
    for stat in page_stats:
        pct = stat['percentages']
        print(f"{stat['page']:<6} {stat['total']:<6} {stat['new']:<6} {stat['duplicates']:<6} "
              f"{pct['头部达人 (>100万)']:<8.1f} {pct['腰部达人 (10万~100万)']:<8.1f} "
              f"{pct['尾部达人 (1万~10万)']:<8.1f} {pct['素人 (<1万)']:<8.1f}")
    
    # 趋势分析结论
    print(f"\n🔍 趋势分析结论:")
    
    # 比较前后段
    first_segment = segments[0][1]
    last_segment = segments[2][1]
    
    first_avg = defaultdict(float)
    last_avg = defaultdict(float)
    
    for stat in first_segment:
        for cat, pct in stat['percentages'].items():
            first_avg[cat] += pct
    for cat in first_avg:
        first_avg[cat] /= len(first_segment)
    
    for stat in last_segment:
        for cat, pct in stat['percentages'].items():
            last_avg[cat] += pct
    for cat in last_avg:
        last_avg[cat] /= len(last_segment)
    
    print(f"\n1. 头部达人（>100万粉丝）:")
    change = last_avg['头部达人 (>100万)'] - first_avg['头部达人 (>100万)']
    if change > 0:
        print(f"   ✅ 后段比前段增加了 {change:.1f}%，说明越往后头部达人越多")
    else:
        print(f"   ❌ 后段比前段减少了 {abs(change):.1f}%，说明越往后头部达人越少")
    
    print(f"\n2. 腰部达人（10万-100万粉丝）:")
    change = last_avg['腰部达人 (10万~100万)'] - first_avg['腰部达人 (10万~100万)']
    if change > 0:
        print(f"   ✅ 后段比前段增加了 {change:.1f}%，说明越往后腰部达人越多")
    else:
        print(f"   ❌ 后段比前段减少了 {abs(change):.1f}%，说明越往后腰部达人越少")
    
    print(f"\n3. 尾部达人（1万-10万粉丝）:")
    change = last_avg['尾部达人 (1万~10万)'] - first_avg['尾部达人 (1万~10万)']
    if change > 0:
        print(f"   ✅ 后段比前段增加了 {change:.1f}%，说明越往后尾部达人越多")
    else:
        print(f"   ❌ 后段比前段减少了 {abs(change):.1f}%，说明越往后尾部达人越少")
    
    print(f"\n4. 素人（<1万粉丝）:")
    change = last_avg['素人 (<1万)'] - first_avg['素人 (<1万)']
    if change > 0:
        print(f"   ✅ 后段比前段增加了 {change:.1f}%，说明越往后素人越多")
    else:
        print(f"   ❌ 后段比前段减少了 {abs(change):.1f}%，说明越往后素人越少")
    
    print(f"\n5. 重复数据:")
    first_dup = sum(s['duplicates'] for s in first_segment) / len(first_segment)
    last_dup = sum(s['duplicates'] for s in last_segment) / len(last_segment)
    if global_duplicates > 0:
        print(f"   ⚠️ 存在 {global_duplicates} 个重复用户（跨页重复）")
        print(f"   前段平均重复: {first_dup:.1f} 个/页")
        print(f"   后段平均重复: {last_dup:.1f} 个/页")
    else:
        print(f"   ✅ 没有重复数据")
    
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()

