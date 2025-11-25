#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析达人视频能力评估指标

基于抖音/小红书等平台达人评估的常见指标：
1. 基础指标：粉丝数、作品数、平均播放量
2. 互动指标：点赞、评论、分享、收藏
3. 效率指标：赞评比、互动率、完播率
4. 内容质量：视频时长分布、内容标签
5. 商业化指标：带货视频占比、转化率
"""

import json
import os
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
import statistics

def analyze_kol_capability_metrics():
    """分析达人视频能力的各项评估指标"""

    output_dir = Path(__file__).parent / "output"
    data_file = Path(__file__).parent.parent / "kol-video-fetcher" / "output" / "final_video_details.json"

    if not data_file.exists():
        print(f"❌ 数据文件不存在: {data_file}")
        return

    print("🎯 开始分析达人视频能力指标...")
    print("=" * 70)

    # 1. 加载数据
    with open(data_file, 'r', encoding='utf-8') as f:
        videos = json.load(f)

    print(f"📊 总视频数: {len(videos)}")
    print()

    # 2. 按作者分组视频
    author_videos = defaultdict(list)
    for video in videos:
        author = video.get('author', {})
        if isinstance(author, dict):
            uid = author.get('uid', 'unknown')
            nickname = author.get('nickname', 'unknown')
            author_key = f"{uid}_{nickname}"
        else:
            author_key = str(author)

        author_videos[author_key].append(video)

    print(f"👥 唯一作者数: {len(author_videos)}")
    print()

    # 3. 计算每个作者的基础统计
    author_stats = {}

    for author_key, video_list in author_videos.items():
        if '_' in author_key:
            uid, nickname = author_key.split('_', 1)
        else:
            uid, nickname = 'unknown', author_key

        # 基础统计
        total_videos = len(video_list)

        # 统计数据聚合
        total_digg = sum(v.get('statistics', {}).get('digg_count', 0) for v in video_list)
        total_comment = sum(v.get('statistics', {}).get('comment_count', 0) for v in video_list)
        total_share = sum(v.get('statistics', {}).get('share_count', 0) for v in video_list)
        total_collect = sum(v.get('statistics', {}).get('collect_count', 0) for v in video_list)
        total_play = sum(v.get('statistics', {}).get('play_count', 0) for v in video_list)

        # 平均指标
        avg_digg = total_digg / total_videos if total_videos > 0 else 0
        avg_comment = total_comment / total_videos if total_videos > 0 else 0
        avg_share = total_share / total_videos if total_videos > 0 else 0
        avg_collect = total_collect / total_videos if total_videos > 0 else 0
        avg_play = total_play / total_videos if total_videos > 0 else 0

        # 赞评比
        like_comment_ratio = total_digg / total_comment if total_comment > 0 else total_digg

        # 互动率 (评论+分享+收藏)/点赞
        total_interactions = total_comment + total_share + total_collect
        interaction_rate = total_interactions / total_digg if total_digg > 0 else 0

        # 视频时长分析
        durations = []
        for v in video_list:
            raw_data = v.get('raw_video_data', {})
            duration = raw_data.get('duration')
            if duration:
                durations.append(duration / 1000)  # 秒

        avg_duration = statistics.mean(durations) if durations else 0

        # 内容特征
        has_hashtag = sum(1 for v in video_list if '#' in v.get('desc', ''))
        has_mention = sum(1 for v in video_list if '@' in v.get('desc', ''))

        author_stats[author_key] = {
            'uid': uid,
            'nickname': nickname,
            'video_count': total_videos,

            # 基础指标
            'total_digg': total_digg,
            'total_comment': total_comment,
            'total_share': total_share,
            'total_collect': total_collect,
            'total_play': total_play,

            # 平均指标
            'avg_digg': avg_digg,
            'avg_comment': avg_comment,
            'avg_share': avg_share,
            'avg_collect': avg_collect,
            'avg_play': avg_play,

            # 效率指标
            'like_comment_ratio': like_comment_ratio,
            'interaction_rate': interaction_rate,

            # 内容指标
            'avg_duration': avg_duration,
            'hashtag_ratio': has_hashtag / total_videos if total_videos > 0 else 0,
            'mention_ratio': has_mention / total_videos if total_videos > 0 else 0
        }

    # 4. 分析指标分布
    print("📊 达人能力指标分布分析:")
    print("-" * 50)

    # 作品数分布
    video_counts = [stats['video_count'] for stats in author_stats.values()]
    print("作品数分布:")
    count_ranges = {
        '1个视频': len([c for c in video_counts if c == 1]),
        '2个视频': len([c for c in video_counts if c == 2]),
        '3个视频': len([c for c in video_counts if c == 3])
    }
    for range_name, count in count_ranges.items():
        pct = (count / len(video_counts)) * 100
        print("10")

    print()

    # 平均点赞数分布
    avg_diggs = [stats['avg_digg'] for stats in author_stats.values()]
    if avg_diggs:
        print("平均点赞数分布:")
        digg_ranges = {
            '< 100': len([d for d in avg_diggs if d < 100]),
            '100-500': len([d for d in avg_diggs if 100 <= d < 500]),
            '500-1000': len([d for d in avg_diggs if 500 <= d < 1000]),
            '1000-5000': len([d for d in avg_diggs if 1000 <= d < 5000]),
            '> 5000': len([d for d in avg_diggs if d >= 5000])
        }
        for range_name, count in digg_ranges.items():
            pct = (count / len(avg_diggs)) * 100
            print("10")
    print()

    # 赞评比分布
    like_comment_ratios = [stats['like_comment_ratio'] for stats in author_stats.values()]
    if like_comment_ratios:
        print("赞评比分布:")
        ratio_ranges = {
            '< 10': len([r for r in like_comment_ratios if r < 10]),
            '10-50': len([r for r in like_comment_ratios if 10 <= r < 50]),
            '50-100': len([r for r in like_comment_ratios if 50 <= r < 100]),
            '100-500': len([r for r in like_comment_ratios if 100 <= r < 500]),
            '> 500': len([r for r in like_comment_ratios if r >= 500])
        }
        for range_name, count in ratio_ranges.items():
            pct = (count / len(like_comment_ratios)) * 100
            print("10")
    print()

    # 互动率分布
    interaction_rates = [stats['interaction_rate'] for stats in author_stats.values()]
    if interaction_rates:
        print("互动率分布:")
        interact_ranges = {
            '< 0.01': len([r for r in interaction_rates if r < 0.01]),
            '0.01-0.05': len([r for r in interaction_rates if 0.01 <= r < 0.05]),
            '0.05-0.1': len([r for r in interaction_rates if 0.05 <= r < 0.1]),
            '0.1-0.2': len([r for r in interaction_rates if 0.1 <= r < 0.2]),
            '> 0.2': len([r for r in interaction_rates if r >= 0.2])
        }
        for range_name, count in interact_ranges.items():
            pct = (count / len(interaction_rates)) * 100
            print("10")
    print()

    # 5. 识别高能力达人
    print("🏆 高能力达人识别:")
    print("-" * 50)

    # 按不同指标排序
    top_by_digg = sorted(author_stats.items(), key=lambda x: x[1]['avg_digg'], reverse=True)[:10]
    top_by_ratio = sorted(author_stats.items(), key=lambda x: x[1]['like_comment_ratio'], reverse=True)[:10]
    top_by_interaction = sorted(author_stats.items(), key=lambda x: x[1]['interaction_rate'], reverse=True)[:10]

    print("平均点赞数 TOP 10:")
    for i, (author_key, stats) in enumerate(top_by_digg, 1):
        print("5")

    print("\n赞评比 TOP 10:")
    for i, (author_key, stats) in enumerate(top_by_ratio, 1):
        print("5")

    print("\n互动率 TOP 10:")
    for i, (author_key, stats) in enumerate(top_by_interaction, 1):
        print("5")

    print()

    # 6. 评估带货能力指标说明
    print("💡 达人带货能力评估指标说明:")
    print("-" * 50)
    print("1. 基础指标:")
    print("   • 粉丝量级: 10万-100万为腰部达人")
    print("   • 作品数量: 稳定的内容输出能力")
    print("   • 平均播放量: 内容传播广度")
    print()
    print("2. 互动效率指标:")
    print("   • 赞评比: 点赞/评论, >50为优质，>100为优秀")
    print("   • 互动率: (评论+分享+收藏)/点赞, >0.05为活跃")
    print("   • 分享收藏比: 内容传播意愿")
    print()
    print("3. 内容质量指标:")
    print("   • 视频时长: 护肤内容通常15-60秒最佳")
    print("   • 话题标签使用率: 内容营销能力")
    print("   • @提及率: 品牌合作意愿")
    print()
    print("4. 商业化潜力:")
    print("   • 高赞评比 + 高互动率 = 内容质量好")
    print("   • 高平均点赞 = 粉丝基础扎实")
    print("   • 稳定的内容输出 = 商业合作可靠性")
    print()

    # 7. 保存详细分析结果
    capability_analysis = {
        'summary': {
            'total_authors': len(author_stats),
            'total_videos': len(videos),
            'avg_videos_per_author': len(videos) / len(author_stats),
            'avg_like_comment_ratio': statistics.mean(like_comment_ratios) if like_comment_ratios else 0,
            'avg_interaction_rate': statistics.mean(interaction_rates) if interaction_rates else 0
        },
        'author_stats': author_stats,
        'top_performers': {
            'by_avg_digg': top_by_digg,
            'by_like_comment_ratio': top_by_ratio,
            'by_interaction_rate': top_by_interaction
        },
        'distribution_analysis': {
            'video_counts': count_ranges,
            'digg_ranges': digg_ranges if 'digg_ranges' in locals() else {},
            'ratio_ranges': ratio_ranges if 'ratio_ranges' in locals() else {},
            'interaction_ranges': interact_ranges if 'interact_ranges' in locals() else {}
        }
    }

    report_file = output_dir / "kol_capability_analysis.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(capability_analysis, f, ensure_ascii=False, indent=2)

    print(f"💾 详细能力分析报告已保存: {report_file}")
    print("=" * 70)
    print("✅ 达人能力分析完成!")

if __name__ == "__main__":
    analyze_kol_capability_metrics()

