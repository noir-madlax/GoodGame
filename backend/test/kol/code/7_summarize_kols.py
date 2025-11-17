#!/usr/bin/env python3
"""
脚本名称: 7_summarize_kols.py
功能描述: 汇总所有分析结果，生成护肤达人列表
输入: ../output/file/{aweme_id}/analysis.json
输出: ../output/7_kol_summary_{timestamp}.json 和 7_kol_list_{timestamp}.md
"""

import json
import time
from pathlib import Path
from typing import List, Dict
from collections import defaultdict


def load_all_analyses() -> List[dict]:
    """加载所有分析结果
    
    返回:
        所有分析结果的列表
    """
    output_dir = Path(__file__).resolve().parent.parent / "output" / "file"
    
    if not output_dir.exists():
        raise RuntimeError("媒体文件目录不存在")
    
    analyses = []
    
    for aweme_dir in output_dir.iterdir():
        if not aweme_dir.is_dir():
            continue
        
        analysis_file = aweme_dir / "analysis.json"
        if not analysis_file.exists():
            continue
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                analyses.append(data)
        except Exception as e:
            print(f"读取 {analysis_file} 失败: {e}")
            continue
    
    return analyses


def extract_kols_from_analyses(analyses: List[dict]) -> List[dict]:
    """从分析结果中提取所有达人信息
    
    参数:
        analyses: 分析结果列表
        
    返回:
        所有达人信息的列表
    """
    all_kols = []
    
    for analysis in analyses:
        aweme_id = analysis.get("aweme_id")
        desc = analysis.get("desc", "")
        analysis_data = analysis.get("analysis", {})
        
        kols_mentioned = analysis_data.get("kols_mentioned", [])
        
        for kol in kols_mentioned:
            # 添加来源信息
            kol_with_source = kol.copy()
            kol_with_source["source_aweme_id"] = aweme_id
            kol_with_source["source_desc"] = desc[:200]  # 截取前200个字符
            all_kols.append(kol_with_source)
    
    return all_kols


def merge_duplicate_kols(kols: List[dict]) -> List[dict]:
    """合并重复的达人（基于名称）
    
    参数:
        kols: 达人列表
        
    返回:
        合并后的达人列表
    """
    # 按名称分组
    kol_groups = defaultdict(list)
    
    for kol in kols:
        name = kol.get("name", "").strip()
        if name:
            kol_groups[name].append(kol)
    
    # 合并同名达人
    merged_kols = []
    
    for name, group in kol_groups.items():
        if len(group) == 1:
            merged_kols.append(group[0])
        else:
            # 合并多个记录
            merged = {
                "name": name,
                "mention_count": len(group),
                "platforms": list(set(kol.get("platform", "") for kol in group if kol.get("platform"))),
                "professional_backgrounds": list(set(kol.get("professional_background", "") for kol in group if kol.get("professional_background"))),
                "characteristics": list(set(char for kol in group for char in kol.get("characteristics", []))),
                "account_ids": list(set(kol.get("account_id", "") for kol in group if kol.get("account_id"))),
                "follower_counts": list(set(kol.get("follower_count", "") for kol in group if kol.get("follower_count"))),
                "ranking_positions": list(set(kol.get("ranking_position", "") for kol in group if kol.get("ranking_position"))),
                "mention_contexts": [kol.get("mention_context", "") for kol in group],
                "confidence_levels": [kol.get("confidence", "medium") for kol in group],
                "sources": [{"aweme_id": kol.get("source_aweme_id"), "desc": kol.get("source_desc")} for kol in group],
            }
            merged_kols.append(merged)
    
    # 按提及次数排序
    merged_kols.sort(key=lambda x: x.get("mention_count", 1), reverse=True)
    
    return merged_kols


def generate_markdown_report(kols: List[dict], output_path: Path) -> None:
    """生成Markdown格式的达人列表报告
    
    参数:
        kols: 达人列表
        output_path: 输出文件路径
    """
    lines = []
    
    lines.append("# 抖音护肤达人调研汇总")
    lines.append("")
    lines.append(f"生成时间: {time.strftime('%Y年%m月%d日 %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 统计信息
    lines.append("## 📊 统计信息")
    lines.append("")
    lines.append(f"- **识别到的达人总数**: {len(kols)} 位")
    
    high_confidence = sum(1 for kol in kols if "high" in kol.get("confidence_levels", []))
    medium_confidence = sum(1 for kol in kols if "medium" in kol.get("confidence_levels", []))
    
    lines.append(f"- **高置信度达人**: {high_confidence} 位")
    lines.append(f"- **中置信度达人**: {medium_confidence} 位")
    lines.append("")
    
    # 达人列表
    lines.append("## 👤 护肤达人详细列表")
    lines.append("")
    
    for idx, kol in enumerate(kols, 1):
        lines.append(f"### {idx}. {kol['name']}")
        lines.append("")
        
        # 基本信息
        if isinstance(kol.get("mention_count"), int) and kol.get("mention_count") > 1:
            lines.append(f"**提及次数**: {kol['mention_count']} 次")
            lines.append("")
        
        if kol.get("platforms"):
            platforms = [p for p in kol["platforms"] if p]
            if platforms:
                lines.append(f"**平台**: {', '.join(platforms)}")
                lines.append("")
        
        if kol.get("professional_backgrounds"):
            backgrounds = [b for b in kol["professional_backgrounds"] if b]
            if backgrounds:
                lines.append(f"**专业背景**: {', '.join(backgrounds)}")
                lines.append("")
        
        if kol.get("characteristics"):
            chars = [c for c in kol["characteristics"] if c]
            if chars:
                lines.append(f"**特点标签**: {', '.join(chars)}")
                lines.append("")
        
        if kol.get("account_ids"):
            ids = [i for i in kol["account_ids"] if i]
            if ids:
                lines.append(f"**账号ID**: {', '.join(ids)}")
                lines.append("")
        
        if kol.get("follower_counts"):
            counts = [c for c in kol["follower_counts"] if c]
            if counts:
                lines.append(f"**粉丝数**: {', '.join(counts)}")
                lines.append("")
        
        if kol.get("ranking_positions"):
            positions = [p for p in kol["ranking_positions"] if p]
            if positions:
                lines.append(f"**排名位置**: {', '.join(positions)}")
                lines.append("")
        
        # 提及方式
        if "mention_contexts" in kol:
            contexts = [c for c in kol["mention_contexts"] if c]
            if contexts:
                lines.append("**提及方式**:")
                for context in contexts[:3]:  # 最多显示3个
                    lines.append(f"- {context}")
                lines.append("")
        elif "mention_context" in kol:
            if kol["mention_context"]:
                lines.append(f"**提及方式**: {kol['mention_context']}")
                lines.append("")
        
        # 置信度
        if "confidence_levels" in kol:
            confidences = list(set(kol["confidence_levels"]))
            lines.append(f"**置信度**: {', '.join(confidences)}")
        elif "confidence" in kol:
            lines.append(f"**置信度**: {kol['confidence']}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main() -> None:
    print("=" * 80)
    print("护肤达人信息汇总脚本")
    print("=" * 80)
    
    # 加载所有分析结果
    print("\n[1/5] 加载分析结果...")
    analyses = load_all_analyses()
    print(f"✓ 加载了 {len(analyses)} 个分析结果")
    
    # 提取达人信息
    print("\n[2/5] 提取达人信息...")
    all_kols = extract_kols_from_analyses(analyses)
    print(f"✓ 提取到 {len(all_kols)} 条达人记录")
    
    # 合并重复达人
    print("\n[3/5] 合并重复达人...")
    merged_kols = merge_duplicate_kols(all_kols)
    print(f"✓ 合并后剩余 {len(merged_kols)} 位唯一达人")
    
    # 生成输出文件
    print("\n[4/5] 生成输出文件...")
    output_dir = Path(__file__).resolve().parent.parent / "output"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    
    # JSON格式
    json_file = output_dir / f"7_kol_summary_{stamp}.json"
    summary_data = {
        "generated_at": stamp,
        "total_kols": len(merged_kols),
        "total_mentions": len(all_kols),
        "kols": merged_kols
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ JSON文件已保存: {json_file}")
    
    # Markdown格式
    md_file = output_dir / f"7_kol_list_{stamp}.md"
    generate_markdown_report(merged_kols, md_file)
    print(f"✓ Markdown报告已保存: {md_file}")
    
    # 打印统计信息
    print("\n[5/5] 汇总完成")
    print("\n" + "=" * 80)
    print("统计信息")
    print("=" * 80)
    print(f"分析的帖子数: {len(analyses)}")
    print(f"原始达人记录: {len(all_kols)}")
    print(f"唯一达人数量: {len(merged_kols)}")
    
    # 显示TOP 10达人
    print("\n" + "=" * 80)
    print("TOP 10 护肤达人（按提及次数）")
    print("=" * 80)
    
    for idx, kol in enumerate(merged_kols[:10], 1):
        name = kol["name"]
        count = kol.get("mention_count", 1)
        background = kol.get("professional_backgrounds", [""])[0] if kol.get("professional_backgrounds") else ""
        
        print(f"{idx}. {name} (提及{count}次) {f'- {background}' if background else ''}")


if __name__ == "__main__":
    main()

