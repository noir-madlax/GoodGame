#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整的视频数据量化分析 - 包含所有核心指标

功能：
1. 数据概况统计（KOL数量、视频数量、视频类型分布、平均指标）
2. 核心量化指标分布（播放量、点赞、评论、分享、转发、收藏、赞评比等）
3. 热门视频热度评估指标（完播率替代指标、互动率、传播力等）
"""

import json
import os
from pathlib import Path
from collections import defaultdict, Counter
import statistics

def comprehensive_analysis():
    base_dir = Path(__file__).parent.parent / "kol-video-fetcher" / "output"
    ids_file = Path(__file__).parent.parent / "kol-video-fetcher" / "output" / "kol_video_ids.json"
    details_file = base_dir / "final_video_details.json"
    
    if not ids_file.exists() or not details_file.exists():
        print("❌ 缺少数据文件")
        return

    # 1. 加载数据
    with open(ids_file, 'r', encoding='utf-8') as f:
        kol_structure = json.load(f)
        
    with open(details_file, 'r', encoding='utf-8') as f:
        video_details_list = json.load(f)
    
    video_map = {v['aweme_id']: v for v in video_details_list if v.get('aweme_id')}
    
    # 2. 整合数据
    merged_data = []
    kol_count = 0
    video_type_count = Counter()
    
    for kol in kol_structure:
        kol_name = kol.get('kol_name', 'Unknown')
        video_details_db = kol.get('video_details', {})
        has_video = False
        
        for v_type, details_db in video_details_db.items():
            if not details_db: continue
            
            vid = details_db.get('item_id')
            if not vid: continue
            
            api_details = video_map.get(vid)
            if not api_details: continue
            
            has_video = True
            video_type_count[v_type] += 1
            
            # 播放量
            play_count = details_db.get('vv', 0)
            
            # 互动数据
            stats = api_details.get('statistics', {})
            digg = stats.get('digg_count', 0)
            comment = stats.get('comment_count', 0)
            share = stats.get('share_count', 0)
            collect = stats.get('collect_count', 0)
            forward = stats.get('forward_count', 0)
            
            # 视频时长 (毫秒)
            raw_data = api_details.get('raw_video_data', {})
            duration_ms = raw_data.get('duration', 0)
            duration_sec = duration_ms / 1000 if duration_ms else 0
            
            # 计算衍生指标
            safe_digg = max(digg, 1)
            safe_play = max(play_count, 1)
            
            # 赞评比
            lc_ratio = digg / max(comment, 1)
            
            # 互动率 (基于点赞)
            interaction_rate = (comment + share + collect) / safe_digg
            
            # 综合参与度
            engagement_rate = (comment + share + collect + forward) / safe_digg
            
            # 分享占比
            share_ratio = share / safe_digg
            
            # 收藏占比
            collect_ratio = collect / safe_digg
            
            # 转发占比
            forward_ratio = forward / safe_digg
            
            # 热度指数 (基于播放量的互动转化)
            # 热度指数 = (总互动 / 播放量) * 1000
            total_interaction = digg + comment + share + collect + forward
            heat_index = (total_interaction / safe_play) * 1000
            
            # 传播力指数 (分享+转发相对于点赞)
            virality_score = (share + forward) / safe_digg * 100
            
            # 完播率替代指标: 播赞比 (播放量/点赞数)
            # 通常，完播率高的视频，点赞转化率也高，即播赞比低（10-30之间较好）
            play_like_ratio = play_count / safe_digg
            
            merged_data.append({
                'kol_name': kol_name,
                'video_type': v_type,
                'play_count': play_count,
                'digg': digg,
                'comment': comment,
                'share': share,
                'collect': collect,
                'forward': forward,
                'duration_sec': duration_sec,
                'lc_ratio': lc_ratio,
                'interaction_rate': interaction_rate,
                'engagement_rate': engagement_rate,
                'share_ratio': share_ratio,
                'collect_ratio': collect_ratio,
                'forward_ratio': forward_ratio,
                'heat_index': heat_index,
                'virality_score': virality_score,
                'play_like_ratio': play_like_ratio
            })
            
        if has_video:
            kol_count += 1
            
    total_videos = len(merged_data)
    
    print("=" * 80)
    print("护肤垂类达人视频数据深度量化分析报告")
    print("=" * 80)
    
    # ===== 1. 数据概况 =====
    print("\n### 1. 数据概况")
    print(f"\n**样本规模**:")
    print(f"- KOL 数量: {kol_count} 位")
    print(f"- 视频样本总数: {total_videos} 条")
    print(f"- 平均每位 KOL 视频数: {total_videos/kol_count:.2f} 条")
    
    print(f"\n**视频类型分布**:")
    type_mapping = {
        'masterpiece': '爆款视频 (Tag 3)',
        'hot': '热门视频 (Tag 5)',
        'newest': '最新视频 (Tag 6)'
    }
    for v_type in ['masterpiece', 'hot', 'newest']:
        count = video_type_count.get(v_type, 0)
        pct = count / total_videos * 100
        print(f"- {type_mapping[v_type]}: {count} 条 ({pct:.1f}%)")
    
    print(f"\n**核心数据指标（平均值）**:")
    avg_play = statistics.mean([d['play_count'] for d in merged_data])
    avg_digg = statistics.mean([d['digg'] for d in merged_data])
    avg_comment = statistics.mean([d['comment'] for d in merged_data])
    avg_share = statistics.mean([d['share'] for d in merged_data])
    avg_collect = statistics.mean([d['collect'] for d in merged_data])
    avg_forward = statistics.mean([d['forward'] for d in merged_data])
    avg_duration = statistics.mean([d['duration_sec'] for d in merged_data if d['duration_sec'] > 0])
    
    print(f"- 平均播放量: {avg_play:,.0f}")
    print(f"- 平均点赞数: {avg_digg:,.0f}")
    print(f"- 平均评论数: {avg_comment:,.0f}")
    print(f"- 平均分享数: {avg_share:,.0f}")
    print(f"- 平均收藏数: {avg_collect:,.0f}")
    print(f"- 平均转发数: {avg_forward:,.0f}")
    print(f"- 平均视频时长: {avg_duration:.1f} 秒")
    
    # ===== 2. 核心量化指标分布 =====
    print("\n### 2. 核心量化指标分布")
    
    def print_dist(name, key, bins, labels):
        values = [d[key] for d in merged_data]
        counts = [0] * len(labels)
        for v in values:
            for i, b in enumerate(bins[:-1]):
                if bins[i] <= v < bins[i+1]:
                    counts[i] += 1
                    break
                elif i == len(bins) - 2 and v >= bins[i+1]:
                    counts[i] += 1
                    break
        
        print(f"\n**{name}**:")
        for i, label in enumerate(labels):
            pct = counts[i] / total_videos * 100
            print(f"- {label}: {counts[i]} 条 ({pct:.1f}%)")
            
    # 播放量
    print_dist("播放量分布", "play_count", 
               [0, 10000, 100000, 500000, 1000000, float('inf')],
               ['< 1万', '1万 - 10万', '10万 - 50万', '50万 - 100万', '> 100万'])
               
    # 点赞数
    print_dist("点赞数分布", "digg",
               [0, 100, 1000, 10000, 100000, float('inf')],
               ['< 100', '100 - 1千', '1千 - 1万', '1万 - 10万', '> 10万'])
               
    # 评论数
    print_dist("评论数分布", "comment",
               [0, 10, 100, 500, 1000, float('inf')],
               ['< 10', '10 - 100', '100 - 500', '500 - 1千', '> 1千'])
               
    # 分享数
    print_dist("分享数分布", "share",
               [0, 1, 10, 50, 100, float('inf')],
               ['0', '1 - 10', '10 - 50', '50 - 100', '> 100'])
               
    # 转发数
    print_dist("转发数分布", "forward",
               [0, 1, 10, 50, 100, float('inf')],
               ['0', '1 - 10', '10 - 50', '50 - 100', '> 100'])
               
    # 收藏数
    print_dist("收藏数分布", "collect",
               [0, 10, 100, 1000, 10000, float('inf')],
               ['< 10', '10 - 100', '100 - 1千', '1千 - 1万', '> 1万'])
               
    # 赞评比
    print_dist("赞评比分布", "lc_ratio",
               [0, 10, 30, 50, 100, float('inf')],
               ['< 10', '10 - 30', '30 - 50', '50 - 100', '> 100'])
               
    # 收藏占比
    print_dist("收藏占比分布 (收藏/点赞)", "collect_ratio",
               [0, 0.01, 0.05, 0.1, float('inf')],
               ['< 1%', '1% - 5%', '5% - 10%', '> 10%'])
    
    # ===== 3. 视频热度评估指标分布 =====
    print("\n### 3. 视频热度评估指标分布")
    
    # 热度指数 (基于播放量的互动转化率)
    print_dist("热度指数分布 (互动/播放量*1000)", "heat_index",
               [0, 1, 5, 10, 50, float('inf')],
               ['< 1 (冷门)', '1 - 5 (一般)', '5 - 10 (热门)', '10 - 50 (爆款)', '> 50 (超级爆款)'])
    
    # 传播力指数
    print_dist("传播力指数分布 ((分享+转发)/点赞*100)", "virality_score",
               [0, 1, 5, 10, 20, float('inf')],
               ['< 1% (弱传播)', '1% - 5% (一般)', '5% - 10% (强传播)', '10% - 20% (病毒传播)', '> 20% (超强病毒)'])
    
    # 播赞比 (完播率替代指标)
    print_dist("播赞比分布 (播放/点赞) - 完播率替代指标", "play_like_ratio",
               [0, 10, 30, 100, 500, float('inf')],
               ['< 10 (极高转化)', '10 - 30 (优秀)', '30 - 100 (良好)', '100 - 500 (一般)', '> 500 (较差)'])
    
    # ===== 4. 热门视频排行 =====
    print("\n### 4. 热门视频量化分析 (Top 10 综合热度)")
    print("\n综合热度 = 播放量 × 热度指数，反映绝对影响力")
    
    # 计算综合热度
    for d in merged_data:
        d['comprehensive_heat'] = d['play_count'] * d['heat_index']
    
    sorted_by_heat = sorted(merged_data, key=lambda x: x['comprehensive_heat'], reverse=True)[:10]
    
    print("\n| 排名 | 达人 | 类型 | 播放量 | 点赞 | 评论 | 收藏 | 赞评比 | 热度指数 | 综合热度 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for i, v in enumerate(sorted_by_heat, 1):
        print(f"| {i} | {v['kol_name'][:15]} | {v['video_type']} | {v['play_count']:,} | {v['digg']:,} | {v['comment']:,} | {v['collect']:,} | {v['lc_ratio']:.1f} | {v['heat_index']:.2f} | {v['comprehensive_heat']:,.0f} |")
    
    # ===== 5. 高价值内容排行 =====
    print("\n### 5. 高价值内容分析 (Top 10 收藏占比)")
    print("\n筛选条件: 播放量 > 1万")
    
    high_value = [v for v in merged_data if v['play_count'] > 10000]
    sorted_by_collect = sorted(high_value, key=lambda x: x['collect_ratio'], reverse=True)[:10]
    
    print("\n| 排名 | 达人 | 类型 | 播放量 | 收藏数 | 点赞数 | 收藏占比 | 赞评比 |")
    print("|---|---|---|---|---|---|---|---|")
    for i, v in enumerate(sorted_by_collect, 1):
        print(f"| {i} | {v['kol_name'][:15]} | {v['video_type']} | {v['play_count']:,} | {v['collect']:,} | {v['digg']:,} | {v['collect_ratio']*100:.1f}% | {v['lc_ratio']:.1f} |")
    
    # ===== 6. 指标说明 =====
    print("\n### 6. 核心量化指标说明")
    
    metrics_doc = {
        "基础互动指标": [
            ("digg_count", "点赞数", "用户对内容的基本认可"),
            ("comment_count", "评论数", "用户的深度参与意愿"),
            ("share_count", "分享数", "内容的口碑传播能力"),
            ("collect_count", "收藏数", "内容的实用价值和收藏意愿"),
            ("forward_count", "转发数", "内容的二次传播能力"),
        ],
        "衍生效率指标": [
            ("like_comment_ratio", "赞评比", "点赞÷评论，>50 为高质量内容"),
            ("interaction_rate", "互动率", "(评论+分享+收藏)÷点赞，>0.08 为强互动"),
            ("engagement_rate", "综合参与度", "(评论+分享+收藏+转发)÷点赞"),
            ("share_ratio", "分享占比", "分享÷点赞，>0.02 为易传播"),
            ("collect_ratio", "收藏占比", "收藏÷点赞，>0.05 为高价值"),
        ],
        "热度评估指标": [
            ("heat_index", "热度指数", "(总互动÷播放量)×1000，>10 为爆款"),
            ("virality_score", "传播力指数", "(分享+转发)÷点赞×100，>5% 为强传播"),
            ("play_like_ratio", "播赞比", "播放÷点赞，10-30 为优秀（完播率替代）"),
        ]
    }
    
    for category, metrics in metrics_doc.items():
        print(f"\n**{category}**:")
        for field, name, desc in metrics:
            print(f"- **{name}** (`{field}`): {desc}")
    
    # 保存数据
    report_data = {
        'summary': {
            'kol_count': kol_count,
            'total_videos': total_videos,
            'avg_videos_per_kol': total_videos / kol_count,
            'video_type_distribution': dict(video_type_count),
            'avg_metrics': {
                'play_count': avg_play,
                'digg': avg_digg,
                'comment': avg_comment,
                'share': avg_share,
                'collect': avg_collect,
                'forward': avg_forward,
                'duration_sec': avg_duration
            }
        },
        'top_videos_by_heat': sorted_by_heat,
        'high_value_videos': sorted_by_collect,
        'all_videos': merged_data
    }
    
    output_file = base_dir / "comprehensive_analysis_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n\n💾 详细数据已保存: {output_file}")

if __name__ == "__main__":
    comprehensive_analysis()

