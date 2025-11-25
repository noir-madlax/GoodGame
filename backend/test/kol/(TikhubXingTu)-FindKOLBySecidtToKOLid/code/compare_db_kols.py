#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对比视频搜索发现的星图KOL与数据库中已有的星图KOL
"""

import json
import os
from pathlib import Path

def extract_video_kol_ids():
    """从 xingtu_kol_summary.json 中提取所有 kol_id"""
    summary_file = Path(__file__).parent.parent / 'output' / 'xingtu_kol_summary.json'

    with open(summary_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    kol_ids = set()
    for kol in data.get('xingtu_kol_list', []):
        kol_id = kol.get('kol_id')
        if kol_id:
            kol_ids.add(kol_id)

    return kol_ids

def main():
    # 提取视频搜索发现的KOL ID
    video_kol_ids = extract_video_kol_ids()
    print(f"📊 视频搜索发现的星图KOL数量: {len(video_kol_ids)}")

    # 查询数据库中的所有KOL ID
    print("🔍 查询数据库中的星图KOL...")

    # 查询 gg_xingtu_kol_base_info 表中的所有 kol_id
    db_query = "SELECT kol_id FROM gg_xingtu_kol_base_info"

    # 调用 MCP 查询数据库
    db_result = mcp_HDL_DB_execute_sql(project_id="kctuxiejpwykosghunib", query=db_query)

    db_kol_ids = set()
    if db_result and 'rows' in db_result:
        for row in db_result['rows']:
            db_kol_ids.add(str(row[0]))  # kol_id 是第一列，确保转换为字符串

    print(f"📊 数据库中已有的星图KOL数量: {len(db_kol_ids)}")

    # 进行对比分析
    overlap_ids = video_kol_ids.intersection(db_kol_ids)
    new_kols = video_kol_ids - db_kol_ids
    existing_kols = db_kol_ids - video_kol_ids

    print("\n📈 对比结果:")
    print(f"✅ 重合的KOL数量: {len(overlap_ids)}")
    print(f"🆕 视频搜索发现的新KOL: {len(new_kols)}")
    print(f"📚 数据库中已有但未在视频搜索中出现的KOL: {len(existing_kols)}")

    if len(video_kol_ids) > 0:
        overlap_rate = len(overlap_ids) / len(video_kol_ids) * 100
        print(f"📊 重合率: {overlap_rate:.1f}%")
    # 生成详细报告
    report = {
        "video_search_kol_count": len(video_kol_ids),
        "db_kol_count": len(db_kol_ids),
        "overlap_count": len(overlap_ids),
        "new_kol_count": len(new_kols),
        "existing_kol_count": len(existing_kols),
        "overlap_rate_percent": round(len(overlap_ids) / len(video_kol_ids) * 100, 2) if video_kol_ids else 0,
        "new_kol_ids": list(new_kols)[:10],  # 只显示前10个
        "overlap_kol_ids": list(overlap_ids)[:10],  # 只显示前10个
        "generated_at": "2025-11-24"
    }

    # 保存报告
    output_dir = Path(__file__).parent.parent / 'output'
    output_dir.mkdir(exist_ok=True)

    report_file = output_dir / 'kol_comparison_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n💾 对比报告已保存: {report_file}")

    # 打印前几个新发现的KOL
    if new_kols:
        print("\n🆕 新发现的KOL (前5个):")
        for kol_id in list(new_kols)[:5]:
            print(f"  - {kol_id}")

if __name__ == "__main__":
    main()
