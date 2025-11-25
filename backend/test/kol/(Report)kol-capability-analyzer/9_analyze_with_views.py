#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
达人视频数据深度分析与报告生成

功能：
1. 整合视频播放量数据 (来自 kol_video_ids.json) 与 互动数据 (来自 final_video_details.json)
2. 计算核心量化指标（赞评比、互动率、分享占比、收藏占比等）
3. 生成详细的数据分析报告内容
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import statistics

def analyze_and_generate_content():
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
    
    # 建立映射
    video_map = {v['aweme_id']: v for v in video_details_list if v.get('aweme_id')}
    
    # 2. 整合数据
    merged_data = []
    
    for kol in kol_structure:
        kol_name = kol.get('kol_name', 'Unknown')
        video_details_db = kol.get('video_details', {})
        
        for v_type, details_db in video_details_db.items():
            if not details_db: continue
            
            vid = details_db.get('item_id')
            if not vid: continue
            
            api_details = video_map.get(vid)
            if not api_details: continue
            
            # 获取播放量 (数据库中的 vv)
            play_count = details_db.get('vv', 0)
            
            # 获取互动数据 (API 返回)
            stats = api_details.get('statistics', {})
            digg = stats.get('digg_count', 0)
            comment = stats.get('comment_count', 0)
            share = stats.get('share_count', 0)
            collect = stats.get('collect_count', 0)
            forward = stats.get('forward_count', 0)
            
            # 计算指标
            safe_digg = max(digg, 1)
            
            # 赞评比 (Like-Comment Ratio)
            lc_ratio = digg / max(comment, 1)
            
            # 互动率 (Interaction Rate) = (评+转+藏)/赞  -- 根据用户新的定义
            # 用户新定义: "interaction_rate - 互动率" (未给公式，但之前是 (评+分+藏)/赞)
            # 通常互动率是 (总互动)/播放 或 (总互动)/粉丝。
            # 但为了保持一致性，我们使用用户之前的逻辑：(评论+分享+收藏) / 点赞数
            interaction_rate = (comment + share + collect) / safe_digg
            
            # 综合参与度 (Engagement Rate)
            engagement_rate = (comment + share + collect + forward) / safe_digg
            
            # 分享占比 (Share Ratio)
            share_ratio = share / safe_digg
            
            # 收藏占比 (Collect Ratio)
            collect_ratio = collect / safe_digg
            
            merged_data.append({
                'kol_name': kol_name,
                'video_type': v_type,
                'play_count': play_count,
                'digg': digg,
                'comment': comment,
                'share': share,
                'collect': collect,
                'forward': forward,
                'lc_ratio': lc_ratio,
                'interaction_rate': interaction_rate,
                'engagement_rate': engagement_rate,
                'share_ratio': share_ratio,
                'collect_ratio': collect_ratio
            })
            
    print(f"✅ 成功整合 {len(merged_data)} 条视频数据")
    
    # 3. 生成分析内容
    
    # 3.1 数据概况
    total_videos = len(merged_data)
    total_views = sum(d['play_count'] for d in merged_data)
    avg_views = total_views / total_videos if total_videos else 0
    
    print("\n### 1. 数据概况")
    print(f"- **总视频样本**: {total_videos} 条")
    print(f"- **总播放量**: {total_views:,}")
    print(f"- **平均单条播放**: {avg_views:,.0f}")
    
    # 3.2 核心指标分布
    print("\n### 2. 核心量化指标分布")
    
    def print_dist(name, key, bins, labels):
        values = [d[key] for d in merged_data]
        counts = [0] * len(labels)
        for v in values:
            for i, b in enumerate(bins[:-1]):
                if v <= bins[i+1]:
                    counts[i] += 1
                    break
        
        print(f"\n**{name}分布**:")
        for i, label in enumerate(labels):
            pct = counts[i] / total_videos * 100
            print(f"- {label}: {counts[i]} ({pct:.1f}%)")
            
    # 播放量分布
    print_dist("播放量 (Play Count)", "play_count", 
               [0, 10000, 100000, 500000, 1000000, float('inf')],
               ['< 1万', '1万 - 10万', '10万 - 50万', '50万 - 100万', '> 100万'])
               
    # 赞评比分布
    print_dist("赞评比 (Like/Comment)", "lc_ratio",
               [0, 10, 30, 50, 100, float('inf')],
               ['< 10', '10 - 30', '30 - 50', '50 - 100', '> 100'])
               
    # 收藏占比分布
    print_dist("收藏占比 (Collect/Like)", "collect_ratio",
               [0, 0.01, 0.05, 0.1, float('inf')],
               ['< 1%', '1% - 5%', '5% - 10%', '> 10%'])

    # 3.3 热门视频量化分析 (Top 10 by Play Count)
    print("\n### 3. 热门视频量化分析 (Top 10 播放量)")
    
    sorted_by_play = sorted(merged_data, key=lambda x: x['play_count'], reverse=True)[:10]
    
    print("| 达人 | 视频类型 | 播放量 | 点赞 | 评论 | 收藏 | 赞评比 | 收藏占比 |")
    print("|---|---|---|---|---|---|---|---|")
    for v in sorted_by_play:
        print(f"| {v['kol_name']} | {v['video_type']} | {v['play_count']:,} | {v['digg']:,} | {v['comment']:,} | {v['collect']:,} | {v['lc_ratio']:.1f} | {v['collect_ratio']*100:.1f}% |")

    # 3.4 高价值内容分析 (Top 10 by Collect Ratio, filtered by > 10k views)
    print("\n### 4. 高价值内容分析 (Top 10 收藏占比, 播放>1万)")
    
    high_value_videos = [v for v in merged_data if v['play_count'] > 10000]
    sorted_by_collect = sorted(high_value_videos, key=lambda x: x['collect_ratio'], reverse=True)[:10]
    
    print("| 达人 | 视频类型 | 播放量 | 收藏数 | 点赞数 | 收藏占比 |")
    print("|---|---|---|---|---|---|")
    for v in sorted_by_collect:
        print(f"| {v['kol_name']} | {v['video_type']} | {v['play_count']:,} | {v['collect']:,} | {v['digg']:,} | {v['collect_ratio']*100:.1f}% |")

if __name__ == "__main__":
    analyze_and_generate_content()

