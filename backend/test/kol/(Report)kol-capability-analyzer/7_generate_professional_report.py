#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成达人视频数据专业分析报告

结合 kol_video_ids.json (类型映射) 和 final_video_details.json (详细数据)，
生成针对 3 类视频（热门、最新、爆款）的对比分析，以及 251 位达人的综合能力评估报告。
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import statistics
# import pandas as pd

def generate_professional_report():
    """生成专业分析报告"""
    
    base_dir = Path(__file__).parent.parent / "kol-video-fetcher" / "output"
    ids_file = Path(__file__).parent.parent / "kol-video-fetcher" / "output" / "kol_video_ids.json"
    details_file = base_dir / "final_video_details.json"
    
    if not ids_file.exists() or not details_file.exists():
        print("❌ 缺少必要的数据文件")
        return

    print("📊 开始生成专业达人视频数据报告...")
    print("=" * 60)

    # 1. 加载数据
    with open(ids_file, 'r', encoding='utf-8') as f:
        kol_structure = json.load(f)  # List of {kol_id, videos: {masterpiece: id, ...}}
        
    with open(details_file, 'r', encoding='utf-8') as f:
        video_details_list = json.load(f)
        
    # 建立视频ID到详情的映射
    video_map = {v['aweme_id']: v for v in video_details_list if v.get('aweme_id')}
    
    print(f"📚 加载 KOL 结构: {len(kol_structure)} 位")
    print(f"🎥 加载视频详情: {len(video_map)} 个")
    print()

    # 2. 整合数据 (按类型)
    type_stats = defaultdict(list)
    kol_stats = {} # kol_id -> {type: stats}
    
    valid_kols = []
    
    for kol in kol_structure:
        kol_id = kol['kol_id']
        kol_name = kol.get('kol_name', 'Unknown')
        
        # 收集该达人的视频数据
        kol_video_data = {}
        valid_videos_count = 0
        
        for v_type, vid in kol['videos'].items():
            if not vid: continue
            
            details = video_map.get(vid)
            if not details: continue
            
            stats = details.get('statistics', {})
            digg = stats.get('digg_count', 0)
            comment = stats.get('comment_count', 0)
            share = stats.get('share_count', 0)
            collect = stats.get('collect_count', 0)
            
            # 计算衍生指标
            safe_digg = max(digg, 1)
            safe_comment = max(comment, 1)
            
            metrics = {
                'digg': digg,
                'comment': comment,
                'share': share,
                'collect': collect,
                'interaction_rate': (comment + share + collect) / safe_digg,
                'like_comment_ratio': digg / safe_comment,
                'engagement_score': (digg + comment*2 + share*3 + collect*2) # 简单加权分
            }
            
            type_stats[v_type].append(metrics)
            kol_video_data[v_type] = metrics
            valid_videos_count += 1
            
        if valid_videos_count > 0:
            # 计算达人综合指标
            total_digg = sum(d['digg'] for d in kol_video_data.values())
            avg_digg = total_digg / valid_videos_count
            
            # 综合互动率
            avg_interaction_rate = sum(d['interaction_rate'] for d in kol_video_data.values()) / valid_videos_count
            
            # 综合赞评比
            avg_ratio = sum(d['like_comment_ratio'] for d in kol_video_data.values()) / valid_videos_count
            
            kol_stats[kol_id] = {
                'name': kol_name,
                'video_count': valid_videos_count,
                'avg_digg': avg_digg,
                'avg_interaction_rate': avg_interaction_rate,
                'avg_ratio': avg_ratio,
                'details': kol_video_data
            }
            valid_kols.append(kol_stats[kol_id])

    print(f"✅ 有效分析达人: {len(valid_kols)} 位")
    print()

    # 3. 输出报告：视频类型对比
    print("📑 第一部分：视频类型数据表现对比")
    print("-" * 60)
    print(f"{'类型':<12} | {'平均点赞':<10} | {'平均互动率':<10} | {'平均赞评比':<10} | {'样本数':<6}")
    print("-" * 60)
    
    type_mapping = {
        'masterpiece': '爆款视频 (Tag 3)',
        'hot': '热门视频 (Tag 5)',
        'newest': '最新视频 (Tag 6)'
    }
    
    for v_type in ['masterpiece', 'hot', 'newest']:
        stats_list = type_stats.get(v_type, [])
        if not stats_list: continue
        
        avg_digg = statistics.mean([s['digg'] for s in stats_list])
        avg_int_rate = statistics.mean([s['interaction_rate'] for s in stats_list])
        avg_ratio = statistics.mean([s['like_comment_ratio'] for s in stats_list])
        
        type_name = type_mapping.get(v_type, v_type)
        print(f"{type_name:<12} | {avg_digg:<10.1f} | {avg_int_rate:<10.4f} | {avg_ratio:<10.1f} | {len(stats_list):<6}")
    print()
    
    # 4. 输出报告：达人分布情况
    print("📑 第二部分：251位达人分布情况评估")
    print("-" * 60)
    
    # 按平均点赞分布 (量级)
    digg_levels = {
        '头部 (>1万赞)': len([k for k in valid_kols if k['avg_digg'] > 10000]),
        '腰部 (1千-1万)': len([k for k in valid_kols if 1000 <= k['avg_digg'] <= 10000]),
        '尾部 (1百-1千)': len([k for k in valid_kols if 100 <= k['avg_digg'] < 1000]),
        '起步 (<100赞)': len([k for k in valid_kols if k['avg_digg'] < 100])
    }
    
    print("1. 流量层级分布 (基于平均点赞):")
    for level, count in digg_levels.items():
        print(f"   - {level}: {count} 人 ({count/len(valid_kols)*100:.1f}%)")
    print()
    
    # 按互动质量分布 (互动率)
    int_levels = {
        'S级互动 (>10%)': len([k for k in valid_kols if k['avg_interaction_rate'] > 0.1]),
        'A级互动 (5%-10%)': len([k for k in valid_kols if 0.05 <= k['avg_interaction_rate'] <= 0.1]),
        'B级互动 (1%-5%)': len([k for k in valid_kols if 0.01 <= k['avg_interaction_rate'] < 0.05]),
        'C级互动 (<1%)': len([k for k in valid_kols if k['avg_interaction_rate'] < 0.01])
    }
    
    print("2. 互动质量分布 (基于互动率):")
    for level, count in int_levels.items():
        print(f"   - {level}: {count} 人 ({count/len(valid_kols)*100:.1f}%)")
    print()
    
    # 5. 综合评估矩阵
    print("📑 第三部分：优质达人潜力评估矩阵")
    print("-" * 60)
    
    # 筛选出 "双高" 达人 (点赞 > 1000 且 互动率 > 5%)
    high_potential = [
        k for k in valid_kols 
        if k['avg_digg'] > 1000 and k['avg_interaction_rate'] > 0.05
    ]
    
    print(f"💎 潜力带货达人 (点赞>1k & 互动>5%): 共 {len(high_potential)} 人")
    
    # 输出前5名
    high_potential.sort(key=lambda x: x['avg_interaction_rate'], reverse=True)
    
    print(f"\n{'达人名称':<20} | {'平均点赞':<8} | {'互动率':<8} | {'赞评比':<8}")
    print("-" * 60)
    for k in high_potential[:10]:
        name = k['name'][:18] + ".." if len(k['name']) > 18 else k['name']
        print(f"{name:<20} | {k['avg_digg']:<8.0f} | {k['avg_interaction_rate']:<8.4f} | {k['avg_ratio']:<8.1f}")
        
    print("-" * 60)
    print("\n💡 评估结论:")
    print("1. 爆款视频 (Masterpiece) 通常具有极高的互动率，是拉动达人整体数据的关键。")
    print("2. 热门视频 (Hot) 代表了达人近期的流量表现，更接近真实带货时的预期流量。")
    print("3. 最新视频 (Newest) 反映了达人的活跃度和当前账号状态。")
    print(f"4. 在这 {len(valid_kols)} 位达人中，约 {digg_levels['腰部 (1千-1万)']} 位处于腰部流量层级，配合 {int_levels['A级互动 (5%-10%)']} 位高互动达人，是性价比最高的带货人选。")

    # 保存报告
    report_data = {
        'type_comparison': {
            k: {
                'avg_digg': statistics.mean([s['digg'] for s in v]),
                'avg_interaction_rate': statistics.mean([s['interaction_rate'] for s in v]),
                'count': len(v)
            } for k, v in type_stats.items() if v
        },
        'distribution': {
            'digg_levels': digg_levels,
            'interaction_levels': int_levels
        },
        'high_potential_kols': high_potential
    }
    
    json_file = base_dir / "professional_kol_report.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n💾 完整数据报告已保存: {json_file}")

if __name__ == "__main__":
    generate_professional_report()

