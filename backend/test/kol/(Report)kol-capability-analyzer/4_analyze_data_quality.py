#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析视频数据质量和结构
"""

import json
import os
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any

def analyze_video_data_quality():
    """分析视频数据的质量和结构"""

    output_dir = Path(__file__).parent / "output"
    data_file = Path(__file__).parent.parent / "kol-video-fetcher" / "output" / "final_video_details.json"

    if not data_file.exists():
        print(f"❌ 数据文件不存在: {data_file}")
        return

    print("🔍 开始分析视频数据质量...")
    print("=" * 60)

    # 1. 加载数据
    with open(data_file, 'r', encoding='utf-8') as f:
        videos = json.load(f)

    print(f"📊 总视频数: {len(videos)}")
    print()

    # 2. 检查基本字段存在性
    print("📋 字段存在性统计:")
    print("-" * 40)

    field_stats = defaultdict(int)
    total_videos = len(videos)

    for video in videos:
        for field in ['aweme_id', 'desc', 'statistics', 'author', 'video_url', 'cover_url']:
            if field in video and video[field]:
                field_stats[field] += 1

    for field, count in field_stats.items():
        percentage = (count / total_videos) * 100
        status = "✅" if percentage > 95 else "⚠️" if percentage > 80 else "❌"
        print("25")

    print()

    # 3. 分析统计数据
    print("📈 统计数据字段分析:")
    print("-" * 40)

    stat_fields = [
        'digg_count', 'comment_count', 'share_count', 'collect_count',
        'play_count', 'forward_count', 'admire_count', 'download_count',
        'exposure_count', 'live_watch_count', 'lose_count', 'lose_comment_count'
    ]

    stat_stats = defaultdict(lambda: {'present': 0, 'zero': 0, 'non_zero': 0, 'values': []})

    for video in videos:
        stats = video.get('statistics', {})
        for field in stat_fields:
            value = stats.get(field, 0)
            if field in stats:
                stat_stats[field]['present'] += 1
                if value == 0:
                    stat_stats[field]['zero'] += 1
                else:
                    stat_stats[field]['non_zero'] += 1
                    stat_stats[field]['values'].append(value)

    for field in stat_fields:
        if stat_stats[field]['present'] > 0:
            present_pct = (stat_stats[field]['present'] / total_videos) * 100
            zero_pct = (stat_stats[field]['zero'] / stat_stats[field]['present']) * 100 if stat_stats[field]['present'] > 0 else 0
            non_zero_count = stat_stats[field]['non_zero']
            values = stat_stats[field]['values']

            status = "✅" if present_pct > 95 else "⚠️" if present_pct > 80 else "❌"

            print("30")
            if non_zero_count > 0:
                print("20")
            print()

    # 4. 分析作者信息
    print("👤 作者信息分析:")
    print("-" * 40)

    author_uids = []
    author_nicknames = []
    unique_authors = set()

    for video in videos:
        author = video.get('author', {})
        if isinstance(author, dict):
            uid = author.get('uid')
            nickname = author.get('nickname')
            if uid:
                author_uids.append(uid)
            if nickname:
                author_nicknames.append(nickname)
                unique_authors.add((uid, nickname))
        elif isinstance(author, str):
            # 有些数据中 author 是字符串
            author_nicknames.append(author)
            unique_authors.add((None, author))

    print(f"作者 UID 数量: {len([x for x in author_uids if x])}")
    print(f"作者昵称数量: {len(author_nicknames)}")
    print(f"唯一作者数: {len(unique_authors)}")
    print()

    # 5. 分析视频描述
    print("📝 视频描述分析:")
    print("-" * 40)

    desc_lengths = []
    has_hashtags = 0
    has_at_mentions = 0

    for video in videos:
        desc = video.get('desc', '')
        if desc:
            desc_lengths.append(len(desc))
            if '#' in desc:
                has_hashtags += 1
            if '@' in desc:
                has_at_mentions += 1

    if desc_lengths:
        print("20")
        print(f"有话题标签的视频: {has_hashtags} ({has_hashtags/len(videos)*100:.1f}%)")
        print(f"有@提及的视频: {has_at_mentions} ({has_at_mentions/len(videos)*100:.1f}%)")
    print()

    # 6. 分析视频时长（如果有的话）
    print("⏱️  视频时长分析:")
    print("-" * 40)

    durations = []
    for video in videos:
        raw_data = video.get('raw_video_data', {})
        duration = raw_data.get('duration')
        if duration:
            durations.append(duration / 1000)  # 转换为秒

    if durations:
        print("20")
        print(f"时长分布: 平均 {sum(durations)/len(durations):.1f}秒, 范围 {min(durations):.1f}-{max(durations):.1f}秒")

        # 时长分布统计
        duration_ranges = {
            '< 15秒': len([d for d in durations if d < 15]),
            '15-30秒': len([d for d in durations if 15 <= d < 30]),
            '30-60秒': len([d for d in durations if 30 <= d < 60]),
            '1-3分钟': len([d for d in durations if 60 <= d < 180]),
            '> 3分钟': len([d for d in durations if d >= 180])
        }

        print("时长分布:")
        for range_name, count in duration_ranges.items():
            pct = (count / len(durations)) * 100
            print("15")
    print()

    # 7. 分析互动效率指标
    print("📊 互动效率指标预览:")
    print("-" * 40)

    # 计算赞评比等指标
    interaction_metrics = []

    for video in videos:
        stats = video.get('statistics', {})
        digg = stats.get('digg_count', 0)
        comment = stats.get('comment_count', 0)
        share = stats.get('share_count', 0)
        collect = stats.get('collect_count', 0)

        if digg > 0:  # 避免除零
            like_comment_ratio = digg / comment if comment > 0 else digg
            engagement_rate = (comment + share + collect) / digg if digg > 0 else 0

            interaction_metrics.append({
                'digg': digg,
                'comment': comment,
                'share': share,
                'collect': collect,
                'like_comment_ratio': like_comment_ratio,
                'engagement_rate': engagement_rate
            })

    if interaction_metrics:
        # 统计赞评比分布
        like_comment_ratios = [m['like_comment_ratio'] for m in interaction_metrics]

        print("25")
        print(f"赞评比分布: 平均 {sum(like_comment_ratios)/len(like_comment_ratios):.1f}")

        # 赞评比区间统计
        ratio_ranges = {
            '< 10': len([r for r in like_comment_ratios if r < 10]),
            '10-50': len([r for r in like_comment_ratios if 10 <= r < 50]),
            '50-100': len([r for r in like_comment_ratios if 50 <= r < 100]),
            '100-500': len([r for r in like_comment_ratios if 100 <= r < 500]),
            '> 500': len([r for r in like_comment_ratios if r >= 500])
        }

        print("赞评比分布:")
        for range_name, count in ratio_ranges.items():
            pct = (count / len(like_comment_ratios)) * 100
            print("15")

    # 8. 保存分析报告
    analysis_report = {
        'summary': {
            'total_videos': total_videos,
            'unique_authors': len(unique_authors),
            'data_completeness': {field: count/total_videos*100 for field, count in field_stats.items()},
            'statistics_fields': {field: stat_stats[field]['present']/total_videos*100 for field in stat_fields},
            'interaction_metrics_count': len(interaction_metrics)
        },
        'field_details': dict(field_stats),
        'statistics_details': dict(stat_stats),
        'author_distribution': {
            'uids_count': len([x for x in author_uids if x]),
            'nicknames_count': len(author_nicknames),
            'unique_authors': len(unique_authors)
        },
        'content_analysis': {
            'avg_desc_length': sum(desc_lengths)/len(desc_lengths) if desc_lengths else 0,
            'hashtags_ratio': has_hashtags/total_videos*100 if total_videos else 0,
            'mentions_ratio': has_at_mentions/total_videos*100 if total_videos else 0
        }
    }

    report_file = output_dir / "data_quality_analysis.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_report, f, ensure_ascii=False, indent=2)

    print(f"💾 详细分析报告已保存: {report_file}")
    print("=" * 60)
    print("✅ 数据质量分析完成!")

if __name__ == "__main__":
    analyze_video_data_quality()

