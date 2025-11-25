#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析批量获取的KOL视频数据，用于评估带货能力

功能：
1. 读取 final_video_details.json
2. 统计视频各项指标分布
3. 分析带货视频质量相关特征
4. 生成评估报告

目标：评估KOL是否能产出高质量带货视频
"""

import os
import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from dotenv import load_dotenv

def load_env():
    current_dir = Path(__file__).parent
    backend_dir = current_dir.parent.parent.parent
    env_path = backend_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)

def load_video_data():
    """加载视频数据"""
    current_dir = Path(__file__).parent
    data_file = current_dir / "output" / "final_video_details.json"

    if not data_file.exists():
        print(f"Error: {data_file} not found")
        return []

    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_video_metrics(videos):
    """分析视频各项指标"""
    print("=" * 80)
    print("📊 视频指标统计分析")
    print("=" * 80)

    metrics = {
        'play_count': [],
        'digg_count': [],
        'comment_count': [],
        'share_count': [],
        'collect_count': [],
        'video_duration': [],
        'video_width': [],
        'video_height': []
    }

    # 统计各项指标
    for video in videos:
        stats = video.get('statistics', {})

        # 播放量（play_count）
        play_count = stats.get('play_count', 0)
        if play_count and play_count > 0:
            metrics['play_count'].append(play_count)

        # 点赞数
        digg_count = stats.get('digg_count', 0)
        if digg_count and digg_count > 0:
            metrics['digg_count'].append(digg_count)

        # 评论数
        comment_count = stats.get('comment_count', 0)
        if comment_count is not None:
            metrics['comment_count'].append(comment_count)

        # 分享数
        share_count = stats.get('share_count', 0)
        if share_count is not None:
            metrics['share_count'].append(share_count)

        # 收藏数
        collect_count = stats.get('collect_count', 0)
        if collect_count is not None:
            metrics['collect_count'].append(collect_count)

        # 视频尺寸信息
        video_info = video.get('raw_video_data', {}).get('video', {})
        if video_info:
            width = video_info.get('width')
            height = video_info.get('height')
            if width: metrics['video_width'].append(width)
            if height: metrics['video_height'].append(height)

    # 输出统计结果
    for metric_name, values in metrics.items():
        if not values:
            print(f"\n{metric_name}: 无有效数据")
            continue

        print(f"\n{metric_name} ({len(values)} 个有效值):")
        print(f"  平均值: {sum(values) / len(values):.1f}")
        print(f"  中位数: {sorted(values)[len(values)//2]}")
        print(f"  最大值: {max(values)}")
        print(f"  最小值: {min(values)}")
        print(f"  分布区间:")

        # 分区间统计
        ranges = []
        if metric_name in ['play_count', 'digg_count', 'comment_count', 'share_count', 'collect_count']:
            if max(values) >= 10000:
                ranges = [(0, 1000), (1000, 10000), (10000, 100000), (100000, 1000000), (1000000, float('inf'))]
                range_labels = ['<1k', '1k-10k', '10k-100k', '100k-1M', '1M+']
            elif max(values) >= 1000:
                ranges = [(0, 100), (100, 1000), (1000, 10000), (10000, 100000), (100000, float('inf'))]
                range_labels = ['<100', '100-1k', '1k-10k', '10k-100k', '100k+']
            else:
                ranges = [(0, 10), (10, 100), (100, 1000), (1000, float('inf'))]
                range_labels = ['<10', '10-100', '100-1k', '1k+']
        else:
            ranges = [(0, 720), (720, 1080), (1080, 1440), (1440, float('inf'))]
            range_labels = ['<720p', '720-1080p', '1080-1440p', '1440p+']

        for (low, high), label in zip(ranges, range_labels):
            count = sum(1 for v in values if low <= v < high)
            if count > 0:
                print(f"    {label}: {count} 个 ({count/len(values)*100:.1f}%)")

def analyze_author_distribution(videos):
    """分析作者分布"""
    print("\n" + "=" * 80)
    print("👤 作者分布分析")
    print("=" * 80)

    authors = []
    author_stats = defaultdict(lambda: {'videos': 0, 'total_plays': 0, 'total_diggs': 0})

    for video in videos:
        author = video.get('author', {})
        if author.get('uid'):
            authors.append(author)
            uid = author['uid']
            stats = video.get('statistics', {})

            author_stats[uid]['videos'] += 1
            author_stats[uid]['total_plays'] += stats.get('play_count', 0)
            author_stats[uid]['total_diggs'] += stats.get('digg_count', 0)
            author_stats[uid]['nickname'] = author.get('nickname', 'N/A')
            author_stats[uid]['unique_id'] = author.get('unique_id', 'N/A')

    print(f"\n总作者数: {len(set(a['uid'] for a in authors if a.get('uid')))}")
    print(f"总视频数: {len(videos)}")

    # 按视频数排序
    sorted_authors = sorted(author_stats.items(),
                           key=lambda x: x[1]['videos'], reverse=True)

    print("
作者贡献排名 (按视频数):")
    for i, (uid, stats) in enumerate(sorted_authors[:20], 1):
        avg_plays = stats['total_plays'] / stats['videos'] if stats['videos'] > 0 else 0
        avg_diggs = stats['total_diggs'] / stats['videos'] if stats['videos'] > 0 else 0
        print(f"  {i:2d}. {stats['nickname']} (@{stats['unique_id']}) - {stats['videos']} 个视频 - 平均播放: {avg_plays:,.0f} - 平均点赞: {avg_diggs:,.0f}")

def analyze_content_features(videos):
    """分析内容特征"""
    print("\n" + "=" * 80)
    print("📝 内容特征分析")
    print("=" * 80)

    # 描述长度统计
    desc_lengths = []
    has_product_keywords = 0
    has_shopping_links = 0
    has_hashtags = 0

    product_keywords = ['购买', '链接', '购买', '价', '元', '产品', '商品', '推荐', '种草', '试用', '优惠', '折扣', '限时']

    for video in videos:
        desc = video.get('desc', '')
        if desc:
            desc_lengths.append(len(desc))

            # 检查产品相关关键词
            desc_lower = desc.lower()
            if any(keyword in desc_lower for keyword in product_keywords):
                has_product_keywords += 1

            # 检查是否有购物链接 (@符号后通常是品牌或产品)
            if '@' in desc:
                has_shopping_links += 1

            # 检查话题标签
            if '#' in desc:
                has_hashtags += 1

    if desc_lengths:
        print("
描述长度统计:")
        print(f"  平均长度: {sum(desc_lengths) / len(desc_lengths):.1f} 字符")
        print(f"  最长描述: {max(desc_lengths)} 字符")
        print(f"  最短描述: {min(desc_lengths)} 字符")

    print("
内容特征统计:")
    print(f"  包含产品关键词: {has_product_keywords}/{len(videos)} ({has_product_keywords/len(videos)*100:.1f}%)")
    print(f"  包含@符号(可能购物链接): {has_shopping_links}/{len(videos)} ({has_shopping_links/len(videos)*100:.1f}%)")
    print(f"  包含话题标签#: {has_hashtags}/{len(videos)} ({has_hashtags/len(videos)*100:.1f}%)")

def analyze_engagement_quality(videos):
    """分析互动质量"""
    print("\n" + "=" * 80)
    print("🔥 互动质量分析")
    print("=" * 80)

    engagement_data = []

    for video in videos:
        stats = video.get('statistics', {})
        plays = stats.get('play_count', 0)
        diggs = stats.get('digg_count', 0)
        comments = stats.get('comment_count', 0)
        shares = stats.get('share_count', 0)
        collects = stats.get('collect_count', 0)

        if plays > 0:
            engagement_rate = (diggs + comments * 10 + shares * 20 + collects * 15) / plays
            engagement_data.append({
                'plays': plays,
                'engagement_rate': engagement_rate,
                'digg_rate': diggs / plays,
                'comment_rate': comments / plays,
                'share_rate': shares / plays,
                'collect_rate': collects / plays
            })

    if engagement_data:
        print(f"\n总有效视频数: {len(engagement_data)}")

        # 按播放量分组分析互动率
        play_ranges = [
            (0, 10000),
            (10000, 100000),
            (100000, 1000000),
            (1000000, float('inf'))
        ]

        print("
按播放量区间分析互动质量:")
        for min_plays, max_plays in play_ranges:
            range_data = [d for d in engagement_data if min_plays <= d['plays'] < max_plays]

            if range_data:
                avg_engagement = sum(d['engagement_rate'] for d in range_data) / len(range_data)
                avg_digg_rate = sum(d['digg_rate'] for d in range_data) / len(range_data)
                avg_comment_rate = sum(d['comment_rate'] for d in range_data) / len(range_data)

                print(f"  {min_plays:,}-{max_plays if max_plays != float('inf') else '∞'}:")
                print(f"    视频数: {len(range_data)}")
                print(f"    平均互动率: {avg_engagement:.4f}")
                print(f"    平均点赞率: {avg_digg_rate:.4f}")
                print(f"    平均评论率: {avg_comment_rate:.4f}")

def generate_kol_ranking(videos):
    """生成KOL带货能力排名"""
    print("\n" + "=" * 80)
    print("🏆 KOL带货能力评估排名")
    print("=" * 80)

    kol_scores = defaultdict(lambda: {
        'videos': [],
        'total_plays': 0,
        'total_diggs': 0,
        'total_comments': 0,
        'total_shares': 0,
        'total_collects': 0,
        'avg_engagement': 0,
        'has_product_content': 0,
        'nickname': '',
        'unique_id': ''
    })

    for video in videos:
        author = video.get('author', {})
        uid = author.get('uid')
        if not uid:
            continue

        stats = video.get('statistics', {})
        plays = stats.get('play_count', 0)
        diggs = stats.get('digg_count', 0)
        comments = stats.get('comment_count', 0)
        shares = stats.get('share_count', 0)
        collects = stats.get('collect_count', 0)

        # 计算基础分数
        engagement_score = 0
        if plays > 0:
            engagement_score = (diggs/plays * 1 + comments/plays * 10 + shares/plays * 20 + collects/plays * 15)

        # 内容质量分数
        desc = video.get('desc', '').lower()
        content_score = 0
        if any(kw in desc for kw in ['购买', '链接', '价', '元', '产品', '推荐', '种草']):
            content_score += 1
        if '@' in desc:
            content_score += 1
        if '#' in desc:
            content_score += 1

        # 视频质量分数（基于播放量）
        quality_score = min(plays / 100000, 5)  # 最高5分

        # 总分数
        total_score = engagement_score * 0.4 + content_score * 0.3 + quality_score * 0.3

        kol_scores[uid]['videos'].append({
            'score': total_score,
            'plays': plays,
            'engagement': engagement_score
        })
        kol_scores[uid]['total_plays'] += plays
        kol_scores[uid]['total_diggs'] += diggs
        kol_scores[uid]['total_comments'] += comments
        kol_scores[uid]['total_shares'] += shares
        kol_scores[uid]['total_collects'] += collects
        kol_scores[uid]['nickname'] = author.get('nickname', 'N/A')
        kol_scores[uid]['unique_id'] = author.get('unique_id', 'N/A')

        # 检查是否有产品内容
        if content_score > 0:
            kol_scores[uid]['has_product_content'] += 1

    # 计算平均分数
    for uid, data in kol_scores.items():
        videos_data = data['videos']
        if videos_data:
            data['avg_score'] = sum(v['score'] for v in videos_data) / len(videos_data)
            data['avg_engagement'] = sum(v['engagement'] for v in videos_data) / len(videos_data)
            data['video_count'] = len(videos_data)
        else:
            data['avg_score'] = 0
            data['avg_engagement'] = 0
            data['video_count'] = 0

    # 排名
    ranking = sorted(kol_scores.items(),
                    key=lambda x: (x[1]['avg_score'], x[1]['video_count']),
                    reverse=True)

    print("\nKOL带货能力排名 (TOP 20):")
    print(f"{'排名':<4} {'昵称':<16} {'抖音号':<16} {'视频数':<6} {'平均分数':<8} {'总播放':<10} {'产品内容':<8}")
    print("-" * 120)

    for i, (uid, data) in enumerate(ranking[:20], 1):
        nickname = data['nickname'][:15]  # 限制长度
        unique_id = data['unique_id'][:15]
        video_count = data['video_count']
        avg_score = data['avg_score']
        total_plays = data['total_plays']
        has_product = data['has_product_content']

        print(f"{i:<4} {nickname:<16} {unique_id:<16} {video_count:<6} {avg_score:<8.2f} {total_plays:<10,} {has_product:<8}")

def save_analysis_report(videos):
    """保存分析报告"""
    current_dir = Path(__file__).parent
    output_dir = current_dir / "output"
    output_dir.mkdir(exist_ok=True)

    report = {
        'analysis_time': datetime.now().isoformat(),
        'total_videos': len(videos),
        'summary': {
            'avg_play_count': sum(v.get('statistics', {}).get('play_count', 0) for v in videos) / len(videos),
            'avg_digg_count': sum(v.get('statistics', {}).get('digg_count', 0) for v in videos) / len(videos),
            'avg_comment_count': sum(v.get('statistics', {}).get('comment_count', 0) for v in videos) / len(videos),
        },
        'recommendations': [
            "优先选择平均播放量>10万的KOL",
            "互动率>0.05的视频质量较好",
            "包含产品关键词和@链接的视频更适合带货",
            "粉丝基础好的KOL更容易产出高质量内容"
        ]
    }

    report_file = output_dir / "video_analysis_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n💾 分析报告已保存到: {report_file}")

def main():
    print("=" * 80)
    print("抖音KOL带货视频质量分析工具")
    print("=" * 80)

    # 加载数据
    videos = load_video_data()
    if not videos:
        print("❌ 未找到视频数据")
        return

    print(f"✅ 加载了 {len(videos)} 个视频数据")

    # 执行各项分析
    analyze_video_metrics(videos)
    analyze_author_distribution(videos)
    analyze_content_features(videos)
    analyze_engagement_quality(videos)
    generate_kol_ranking(videos)

    # 保存报告
    save_analysis_report(videos)

    print("\n" + "=" * 80)
    print("✅ 分析完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()

