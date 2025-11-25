#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析粉丝数量分布
按照每10%一档统计粉丝数量分布情况

作者: AI Agent
创建时间: 2025-11-24
"""

import json
import os
from pathlib import Path
import numpy as np

def extract_follower_counts(file_paths):
    """从JSON文件中提取所有粉丝数量"""
    follower_counts = []

    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'data' in data and 'data' in data['data']:
                videos = data['data']['data']

                for video in videos:
                    if 'aweme_info' in video and 'author' in video['aweme_info']:
                        author = video['aweme_info']['author']
                        follower_count = author.get('follower_count', 0)
                        if follower_count > 0:
                            follower_counts.append(follower_count)

        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")

    return follower_counts

def calculate_percentile_distribution(follower_counts):
    """计算每10%的粉丝数量分布"""
    if not follower_counts:
        return {}

    # 排序粉丝数量
    sorted_counts = sorted(follower_counts)

    # 计算百分位数
    percentiles = {}
    for p in range(0, 101, 10):
        if p == 0:
            percentiles[p] = sorted_counts[0]
        elif p == 100:
            percentiles[p] = sorted_counts[-1]
        else:
            index = int(len(sorted_counts) * p / 100)
            percentiles[p] = sorted_counts[index - 1]  # 百分位数计算

    return percentiles

def format_number(num):
    """格式化数字显示"""
    if num >= 10000:
        return f"{num/10000:.1f}万"
    elif num >= 1000:
        return f"{num/1000:.1f}k"
    else:
        return str(num)

def main():
    # 文件路径
    current_dir = Path(__file__).parent
    output_dir = current_dir.parent / "output" / "keyword_护肤保养" / "detail"

    file_paths = [
        output_dir / "video_search_page_0_20251124_134103.json",
        output_dir / "video_search_page_1_20251124_134103.json",
        output_dir / "video_search_page_2_20251124_134103.json"
    ]

    # 提取粉丝数量
    follower_counts = extract_follower_counts(file_paths)
    print(f"📊 总共提取到 {len(follower_counts)} 个粉丝数量数据")

    if not follower_counts:
        print("❌ 未找到粉丝数量数据")
        return

    # 计算百分位数分布
    percentiles = calculate_percentile_distribution(follower_counts)

    print("\n📈 粉丝数量百分位数分布 (每10%一档):")
    print("=" * 60)

    for p in range(0, 101, 10):
        count = percentiles[p]
        print("4")

    # 额外统计信息
    print("\n📊 详细统计信息:")
    print("=" * 60)
    print(f"最小粉丝数: {format_number(min(follower_counts))}")
    print(f"最大粉丝数: {format_number(max(follower_counts))}")
    print(f"平均粉丝数: {format_number(int(np.mean(follower_counts)))}")
    print(f"中位数粉丝数: {format_number(int(np.median(follower_counts)))}")

    # 按数量级统计
    ranges = [
        (0, 1000, "1k以下"),
        (1000, 10000, "1k-1万"),
        (10000, 100000, "1万-10万"),
        (100000, 1000000, "10万-100万"),
        (1000000, 10000000, "100万-1000万"),
        (10000000, float('inf'), "1000万以上")
    ]

    print("
📊 粉丝数量区间分布:"    print("=" * 60)

    for min_val, max_val, label in ranges:
        count = sum(1 for f in follower_counts if min_val <= f < max_val)
        percentage = count / len(follower_counts) * 100
        print("6")

if __name__ == "__main__":
    main()
