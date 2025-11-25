#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
达人视频量化指标分析框架

专业分析抖音/小红书等平台达人视频的量化指标，
基于行业标准和TikTok官方数据分析方法。
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple
import statistics
import math

def calculate_quantitative_metrics():
    """计算专业的达人视频量化指标"""

    output_dir = Path(__file__).parent / "output"
    data_file = Path(__file__).parent.parent / "kol-video-fetcher" / "output" / "final_video_details.json"

    if not data_file.exists():
        print(f"❌ 数据文件不存在: {data_file}")
        return

    print("📊 开始计算达人视频量化指标...")
    print("=" * 80)

    # 1. 加载数据
    with open(data_file, 'r', encoding='utf-8') as f:
        videos = json.load(f)

    print(f"📊 分析 {len(videos)} 个视频数据")
    print()

    # 2. 按作者分组
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

    print(f"👥 涉及 {len(author_videos)} 位达人")
    print()

    # 3. 计算每个达人的量化指标
    kol_metrics = {}

    for author_key, video_list in author_videos.items():
        if '_' in author_key:
            uid, nickname = author_key.split('_', 1)
        else:
            uid, nickname = 'unknown', author_key

        # 基础统计数据
        stats = calculate_author_statistics(video_list)

        # 计算专业量化指标
        metrics = calculate_professional_metrics(stats)

        kol_metrics[author_key] = {
            'basic_info': {
                'uid': uid,
                'nickname': nickname,
                'video_count': len(video_list)
            },
            'statistics': stats,
            'quantitative_metrics': metrics
        }

    # 4. 输出量化指标框架
    print("🎯 达人视频量化分析指标框架")
    print("=" * 80)

    print("📈 一级指标（核心评估）:")
    print("-" * 60)

    # 展示几个示例达人的指标
    sample_kols = list(kol_metrics.keys())[:3]

    for author_key in sample_kols:
        kol = kol_metrics[author_key]
        metrics = kol['quantitative_metrics']
        basic = kol['basic_info']

        print(f"\n👤 {basic['nickname'][:20]} ({basic['video_count']}个视频)")
        print(".2f")
        print(".1f")
        print(".1f")
        print(".1f")
        print(".3f")
        print(".1f")
    print()

    # 5. 指标分布分析
    print("📊 全量数据指标分布分析:")
    print("-" * 60)

    # 收集所有指标值
    all_like_comment_ratios = []
    all_interaction_rates = []
    all_engagement_rates = []
    all_content_quality_scores = []
    all_virality_scores = []

    for kol in kol_metrics.values():
        m = kol['quantitative_metrics']
        all_like_comment_ratios.append(m['like_comment_ratio'])
        all_interaction_rates.append(m['interaction_rate'])
        all_engagement_rates.append(m['engagement_rate'])
        all_content_quality_scores.append(m['content_quality_score'])
        all_virality_scores.append(m['virality_score'])

    # 赞评比分布
    print("赞评比分布:")
    ratio_ranges = analyze_distribution(all_like_comment_ratios,
                                      [0, 10, 30, 50, 100, 200, float('inf')],
                                      ['<10', '10-30', '30-50', '50-100', '100-200', '>200'])
    for range_name, count in ratio_ranges.items():
        pct = (count / len(all_like_comment_ratios)) * 100
        print("10")

    # 内容质量分数分布
    print("\n内容质量分数分布:")
    quality_ranges = analyze_distribution(all_content_quality_scores,
                                        [0, 0.3, 0.5, 0.7, 0.9, 1.0],
                                        ['<0.3', '0.3-0.5', '0.5-0.7', '0.7-0.9', '0.9-1.0'])
    for range_name, count in quality_ranges.items():
        pct = (count / len(all_content_quality_scores)) * 100
        print("10")

    # 6. 专业分析指标说明
    print("\n💡 专业量化指标详解:")
    print("-" * 60)

    metrics_explanation = {
        "1. 赞评比 (Like-Comment Ratio)": {
            "计算公式": "赞评比 = 总点赞数 / 总评论数",
            "意义": "衡量粉丝对内容的认同度，避免刷赞刷评",
            "优秀标准": ">50 (高质量内容), >100 (精品内容)",
            "行业参考": "头部达人通常>100, 腰部达人>30"
        },

        "2. 互动率 (Interaction Rate)": {
            "计算公式": "互动率 = (评论+分享+收藏) / 点赞数",
            "意义": "衡量粉丝参与度，内容传播意愿",
            "优秀标准": ">0.08 (8%), 表示强互动",
            "行业参考": "优质内容通常>0.05, 病毒内容>0.15"
        },

        "3. 综合参与度 (Engagement Rate)": {
            "计算公式": "综合参与度 = (评论+分享+收藏+转发) / 点赞数",
            "意义": "全方位衡量内容互动水平",
            "优秀标准": ">0.10 (10%), 强互动内容",
            "行业参考": "品牌合作达人通常>0.08"
        },

        "4. 内容质量分数 (Content Quality Score)": {
            "计算公式": "内容质量分数 = (赞评比/100 * 0.4) + (互动率/0.1 * 0.3) + (分享率/0.02 * 0.3)",
            "意义": "综合评估内容质量的量化分数",
            "优秀标准": ">0.7 (优质内容)",
            "行业参考": "0.8+ 为头部内容质量"
        },

        "5. 传播力分数 (Virality Score)": {
            "计算公式": "传播力分数 = (分享数/点赞数) * (收藏数/点赞数) * 100",
            "意义": "衡量内容的自传播能力",
            "优秀标准": ">2.0 (强传播)",
            "行业参考": "病毒内容通常>5.0"
        },

        "6. 平均点赞数 (Average Digg Count)": {
            "计算公式": "平均点赞数 = 总点赞数 / 视频数量",
            "意义": "衡量达人基础粉丝质量",
            "优秀标准": ">1000 (腰部达人), >5000 (头部达人)",
            "行业参考": "护肤领域腰部达人通常1000-5000"
        },

        "7. 分享占比 (Share Ratio)": {
            "计算公式": "分享占比 = 分享数 / 点赞数",
            "意义": "衡量内容的分享意愿，口碑传播能力",
            "优秀标准": ">0.02 (2%), 易于分享",
            "行业参考": "实用内容分享率更高"
        },

        "8. 收藏占比 (Collect Ratio)": {
            "计算公式": "收藏占比 = 收藏数 / 点赞数",
            "意义": "衡量内容的收藏价值，实用性",
            "优秀标准": ">0.05 (5%), 高价值内容",
            "行业参考": "教程类内容收藏率更高"
        }
    }

    for metric_name, details in metrics_explanation.items():
        print(f"\n{metric_name}")
        print(f"  公式: {details['计算公式']}")
        print(f"  意义: {details['意义']}")
        print(f"  标准: {details['优秀标准']}")
        print(f"  参考: {details['行业参考']}")

    # 7. 保存量化分析结果
    quantitative_analysis = {
        'summary': {
            'total_kols': len(kol_metrics),
            'total_videos': len(videos),
            'avg_videos_per_kol': len(videos) / len(kol_metrics),
            'metrics_distribution': {
                'like_comment_ratio': analyze_distribution(all_like_comment_ratios),
                'interaction_rate': analyze_distribution(all_interaction_rates),
                'engagement_rate': analyze_distribution(all_engagement_rates),
                'content_quality_score': analyze_distribution(all_content_quality_scores),
                'virality_score': analyze_distribution(all_virality_scores)
            }
        },
        'kol_quantitative_metrics': kol_metrics,
        'metrics_framework': metrics_explanation
    }

    report_file = output_dir / "quantitative_metrics_analysis.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(quantitative_analysis, f, ensure_ascii=False, indent=2)

    print(f"\n💾 量化指标分析报告已保存: {report_file}")
    print("=" * 80)
    print("✅ 量化指标分析完成!")

def calculate_author_statistics(video_list: List[Dict]) -> Dict[str, Any]:
    """计算达人的基础统计数据"""
    total_digg = sum(v.get('statistics', {}).get('digg_count', 0) for v in video_list)
    total_comment = sum(v.get('statistics', {}).get('comment_count', 0) for v in video_list)
    total_share = sum(v.get('statistics', {}).get('share_count', 0) for v in video_list)
    total_collect = sum(v.get('statistics', {}).get('collect_count', 0) for v in video_list)
    total_forward = sum(v.get('statistics', {}).get('forward_count', 0) for v in video_list)

    video_count = len(video_list)

    return {
        'total_digg': total_digg,
        'total_comment': total_comment,
        'total_share': total_share,
        'total_collect': total_collect,
        'total_forward': total_forward,
        'video_count': video_count,
        'avg_digg': total_digg / video_count if video_count > 0 else 0,
        'avg_comment': total_comment / video_count if video_count > 0 else 0,
        'avg_share': total_share / video_count if video_count > 0 else 0,
        'avg_collect': total_collect / video_count if video_count > 0 else 0
    }

def calculate_professional_metrics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """计算专业的量化指标"""

    # 基础数据
    total_digg = stats['total_digg']
    total_comment = stats['total_comment']
    total_share = stats['total_share']
    total_collect = stats['total_collect']
    total_forward = stats['total_forward']

    # 避免除零错误
    safe_digg = max(total_digg, 1)
    safe_comment = max(total_comment, 1)

    # 1. 赞评比 (Like-Comment Ratio)
    like_comment_ratio = total_digg / safe_comment

    # 2. 互动率 (Interaction Rate) - 评论+分享+收藏
    interaction_rate = (total_comment + total_share + total_collect) / safe_digg

    # 3. 综合参与度 (Engagement Rate) - 包含转发
    engagement_rate = (total_comment + total_share + total_collect + total_forward) / safe_digg

    # 4. 分享占比 (Share Ratio)
    share_ratio = total_share / safe_digg

    # 5. 收藏占比 (Collect Ratio)
    collect_ratio = total_collect / safe_digg

    # 6. 内容质量分数 (Content Quality Score)
    # 综合赞评比、互动率、分享率三个维度
    quality_score = (
        min(like_comment_ratio / 100, 1.0) * 0.4 +  # 赞评比贡献40%
        min(interaction_rate / 0.1, 1.0) * 0.3 +    # 互动率贡献30%
        min(share_ratio / 0.02, 1.0) * 0.3          # 分享率贡献30%
    )

    # 7. 传播力分数 (Virality Score)
    # 分享意愿 × 收藏意愿
    virality_score = (share_ratio * collect_ratio) * 100

    # 8. 平均点赞数
    avg_digg = stats['avg_digg']

    return {
        'like_comment_ratio': like_comment_ratio,
        'interaction_rate': interaction_rate,
        'engagement_rate': engagement_rate,
        'share_ratio': share_ratio,
        'collect_ratio': collect_ratio,
        'content_quality_score': quality_score,
        'virality_score': virality_score,
        'avg_digg': avg_digg,

        # 质量等级 (基于综合评分)
        'quality_level': get_quality_level(quality_score),
        'virality_level': get_virality_level(virality_score)
    }

def get_quality_level(score: float) -> str:
    """根据内容质量分数返回等级"""
    if score >= 0.8:
        return "S级 (头部内容)"
    elif score >= 0.7:
        return "A级 (优质内容)"
    elif score >= 0.5:
        return "B级 (良好内容)"
    elif score >= 0.3:
        return "C级 (一般内容)"
    else:
        return "D级 (需改进)"

def get_virality_level(score: float) -> str:
    """根据传播力分数返回等级"""
    if score >= 10.0:
        return "病毒级 (极强传播)"
    elif score >= 5.0:
        return "优秀级 (强传播)"
    elif score >= 2.0:
        return "良好级 (中传播)"
    elif score >= 0.5:
        return "一般级 (弱传播)"
    else:
        return "低传播"

def analyze_distribution(values: List[float], bins: List[float] = None,
                        labels: List[str] = None) -> Dict[str, int]:
    """分析数值分布"""
    if bins is None:
        # 默认分位数分析
        if len(values) >= 10:
            values.sort()
            bins = [
                0,
                values[int(len(values) * 0.25)],  # Q1
                values[int(len(values) * 0.5)],   # Q2
                values[int(len(values) * 0.75)],  # Q3
                float('inf')
            ]
            labels = ['Q1以下', 'Q1-Q2', 'Q2-Q3', 'Q3以上']
        else:
            return {}

    if labels is None:
        labels = [f'{bins[i]:.1f}-{bins[i+1]:.1f}' for i in range(len(bins)-1)]

    distribution = defaultdict(int)
    for value in values:
        for i, bin_edge in enumerate(bins[:-1]):
            if value <= bins[i+1]:
                distribution[labels[i]] += 1
                break

    return dict(distribution)

if __name__ == "__main__":
    calculate_quantitative_metrics()

