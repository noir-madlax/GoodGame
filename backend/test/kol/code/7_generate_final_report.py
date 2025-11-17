#!/usr/bin/env python3
"""
脚本名称: 7_generate_final_report.py
功能描述: 汇总所有Gemini分析结果，生成最终的护肤达人列表和详细统计报告。
输入: ../output/file/{aweme_id}/analysis.json (所有Gemini分析结果文件)
输出: ../output/final_kol_report_{timestamp}.md (最终Markdown报告)
      ../output/final_kol_data_{timestamp}.json (JSON格式数据)
"""

import json
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List


def find_all_analysis_results() -> List[Path]:
    """查找所有analysis.json文件"""
    output_dir = Path(__file__).resolve().parent.parent / "output" / "file"
    return sorted(list(output_dir.glob("*/analysis.json")))


def load_search_keyword() -> str:
    """加载搜索关键词"""
    input_file = Path(__file__).resolve().parent.parent / "input"
    if input_file.exists():
        content = input_file.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if line.startswith("搜索关键词="):
                return line.split("=", 1)[1].strip()
    return "未知"


def main() -> None:
    print("=" * 80)
    print("护肤达人最终汇总报告生成脚本")
    print("=" * 80)

    print("\n[1/4] 加载搜索关键词...")
    search_keyword = load_search_keyword()
    print(f"✓ 搜索关键词: {search_keyword}")

    print("\n[2/4] 查找所有分析结果文件...")
    analysis_files = find_all_analysis_results()
    if not analysis_files:
        print("✗ 未找到任何分析结果文件。请确保已运行 6_analyze_content_with_media.py。")
        return

    print(f"✓ 找到 {len(analysis_files)} 个分析结果文件")

    # 数据结构
    kol_mentions = defaultdict(lambda: {
        "count": 0,
        "posts": [],  # 包含该达人的帖子列表
        "platforms": set(),
        "professional_backgrounds": set(),
        "characteristics": set(),
        "contexts": []
    })
    
    total_posts_analyzed = 0
    relevant_posts = 0
    posts_with_kols = 0
    posts_by_type = {"视频": 0, "图文": 0, "其他": 0}
    failed_analyses = []

    print("\n[3/4] 汇总分析结果...")
    for file_path in analysis_files:
        total_posts_analyzed += 1
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            
            aweme_id = analysis_data.get("aweme_id")
            content_type = analysis_data.get("content_type", "其他")
            desc = analysis_data.get("desc", "")
            media_analyzed = analysis_data.get("media_analyzed", False)
            media_count = analysis_data.get("media_count", 0)
            
            # 统计帖子类型
            if content_type in posts_by_type:
                posts_by_type[content_type] += 1
            else:
                posts_by_type["其他"] += 1
            
            # 检查是否有错误
            analysis = analysis_data.get("analysis", {})
            if "error" in analysis:
                failed_analyses.append({
                    "aweme_id": aweme_id,
                    "content_type": content_type,
                    "error": analysis["error"],
                    "desc": desc[:100]
                })
                continue
            
            # 检查内容相关性
            content_analysis = analysis.get("content_analysis", {})
            is_relevant = content_analysis.get("is_relevant", False)
            
            if is_relevant:
                relevant_posts += 1
            
            # 提取KOL信息
            kols = analysis.get("kols_mentioned", [])
            if kols:
                posts_with_kols += 1
                
                for kol in kols:
                    kol_name = kol.get("name", "").strip()
                    if not kol_name:
                        continue
                    
                    # 更新KOL提及次数和详情
                    kol_mentions[kol_name]["count"] += 1
                    kol_mentions[kol_name]["posts"].append({
                        "aweme_id": aweme_id,
                        "content_type": content_type,
                        "desc": desc[:100],
                        "context": kol.get("mention_context", ""),
                        "confidence": kol.get("confidence", "medium")
                    })
                    
                    # 汇总其他信息
                    platform = kol.get("platform", "")
                    if platform:
                        kol_mentions[kol_name]["platforms"].add(platform)
                    
                    bg = kol.get("professional_background", "")
                    if bg:
                        kol_mentions[kol_name]["professional_backgrounds"].add(bg)
                    
                    characteristics = kol.get("characteristics", [])
                    if characteristics:
                        for char in characteristics:
                            kol_mentions[kol_name]["characteristics"].add(char)
                    
                    mention_context = kol.get("mention_context", "")
                    if mention_context:
                        kol_mentions[kol_name]["contexts"].append(mention_context)
        
        except json.JSONDecodeError:
            print(f"  警告: 文件 {file_path.name} 不是有效的JSON，跳过。")
            failed_analyses.append({
                "aweme_id": file_path.parent.name,
                "error": "JSON解析失败"
            })
        except Exception as e:
            print(f"  警告: 读取或处理文件 {file_path.name} 时发生错误: {e}")
            failed_analyses.append({
                "aweme_id": file_path.parent.name,
                "error": str(e)
            })

    # 转换集合为列表（用于JSON序列化）
    for kol_name in kol_mentions:
        kol_mentions[kol_name]["platforms"] = list(kol_mentions[kol_name]["platforms"])
        kol_mentions[kol_name]["professional_backgrounds"] = list(kol_mentions[kol_name]["professional_backgrounds"])
        kol_mentions[kol_name]["characteristics"] = list(kol_mentions[kol_name]["characteristics"])

    # 按提及次数排序
    sorted_kols = sorted(kol_mentions.items(), key=lambda x: x[1]["count"], reverse=True)

    print("\n[4/4] 生成最终报告...")
    output_dir = Path(__file__).resolve().parent.parent / "output"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    
    # 生成Markdown报告
    report_file = output_dir / f"final_kol_report_{stamp}.md"
    with report_file.open("w", encoding="utf-8") as f:
        f.write(f"# 抖音护肤达人调研最终报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**搜索关键词**: \"{search_keyword}\"\n\n")
        f.write("---\n\n")
        
        # 1. 总体概览
        f.write(f"## 1. 总体分析概览\n\n")
        f.write(f"| 指标 | 数值 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 分析帖子总数 | {total_posts_analyzed} |\n")
        f.write(f"| 相关护肤/美妆内容帖子数 | {relevant_posts} ({relevant_posts/total_posts_analyzed*100:.1f}%) |\n")
        f.write(f"| 发现达人的帖子数 | {posts_with_kols} ({posts_with_kols/total_posts_analyzed*100:.1f}%) |\n")
        f.write(f"| 发现的独立达人数量 | {len(sorted_kols)} |\n")
        f.write(f"| 分析失败的帖子数 | {len(failed_analyses)} |\n")
        f.write(f"\n")
        
        f.write(f"### 1.1 帖子类型分布\n\n")
        f.write(f"| 内容类型 | 数量 | 占比 |\n")
        f.write(f"|----------|------|------|\n")
        for content_type, count in posts_by_type.items():
            if count > 0:
                f.write(f"| {content_type} | {count} | {count/total_posts_analyzed*100:.1f}% |\n")
        f.write(f"\n")
        
        # 2. 提及次数最多的护肤达人列表
        f.write(f"## 2. 提及次数最多的护肤达人排名\n\n")
        if sorted_kols:
            f.write(f"| 排名 | 达人名称 | 提及次数 | 平台 | 专业背景 | 主要特点 |\n")
            f.write(f"|------|----------|----------|------|----------|----------|\n")
            for i, (kol_name, info) in enumerate(sorted_kols[:20], 1):
                platforms = ", ".join(info["platforms"]) if info["platforms"] else "-"
                backgrounds = ", ".join(info["professional_backgrounds"]) if info["professional_backgrounds"] else "-"
                characteristics = ", ".join(list(info["characteristics"])[:3]) if info["characteristics"] else "-"
                if len(info["characteristics"]) > 3:
                    characteristics += "..."
                f.write(f"| {i} | **{kol_name}** | {info['count']} | {platforms} | {backgrounds} | {characteristics} |\n")
        else:
            f.write("未在内容中发现明确提及的护肤达人。\n")
        f.write(f"\n")
        
        # 3. 达人详细信息
        f.write(f"## 3. 达人详细信息\n\n")
        if sorted_kols:
            for i, (kol_name, info) in enumerate(sorted_kols[:20], 1):
                f.write(f"### 3.{i} {kol_name}\n\n")
                f.write(f"**提及次数**: {info['count']}\n\n")
                
                if info["platforms"]:
                    f.write(f"**平台**: {', '.join(info['platforms'])}\n\n")
                
                if info["professional_backgrounds"]:
                    f.write(f"**专业背景**: {', '.join(info['professional_backgrounds'])}\n\n")
                
                if info["characteristics"]:
                    f.write(f"**主要特点**:\n")
                    for char in list(info["characteristics"])[:10]:
                        f.write(f"- {char}\n")
                    if len(info["characteristics"]) > 10:
                        f.write(f"- ...（还有{len(info['characteristics']) - 10}个特点）\n")
                    f.write(f"\n")
                
                f.write(f"**提及上下文**:\n")
                # 去重并限制显示数量
                unique_contexts = list(set(info["contexts"]))[:3]
                for context in unique_contexts:
                    f.write(f"- {context}\n")
                if len(info["contexts"]) > 3:
                    f.write(f"- ...（还有{len(info['contexts']) - 3}条提及）\n")
                f.write(f"\n")
                
                f.write(f"**相关帖子**:\n")
                for post in info["posts"][:3]:
                    f.write(f"- [{post['content_type']}] `{post['aweme_id']}`: {post['desc']}...\n")
                if len(info["posts"]) > 3:
                    f.write(f"- ...（还有{len(info['posts']) - 3}个帖子）\n")
                f.write(f"\n")
        
        # 4. 分析失败的帖子
        if failed_analyses:
            f.write(f"## 4. 分析失败的帖子\n\n")
            f.write(f"以下 {len(failed_analyses)} 个帖子分析失败：\n\n")
            f.write(f"| 帖子ID | 内容类型 | 错误原因 | 描述片段 |\n")
            f.write(f"|--------|----------|----------|----------|\n")
            for fail_info in failed_analyses[:10]:
                aweme_id = fail_info.get("aweme_id", "未知")
                content_type = fail_info.get("content_type", "未知")
                error = fail_info.get("error", "未知错误")[:50]
                desc = fail_info.get("desc", "")[:50] if fail_info.get("desc") else "-"
                f.write(f"| `{aweme_id}` | {content_type} | {error} | {desc} |\n")
            if len(failed_analyses) > 10:
                f.write(f"\n*（还有{len(failed_analyses) - 10}个失败帖子未显示）*\n")
            f.write(f"\n")
        
        # 5. 附录
        f.write(f"## 5. 附录\n\n")
        f.write(f"### 5.1 分析方法说明\n\n")
        f.write(f"本报告通过以下步骤生成：\n\n")
        f.write(f"1. 使用TikHub API搜索抖音平台相关内容\n")
        f.write(f"2. 下载搜索结果中的视频和图文内容\n")
        f.write(f"3. 使用Gemini 2.5 Flash多模态AI模型分析内容\n")
        f.write(f"4. 提取和汇总所有提及的护肤/美妆达人信息\n")
        f.write(f"5. 生成详细的统计报告和达人排名\n\n")
        
        f.write(f"### 5.2 数据说明\n\n")
        f.write(f"- **提及次数**: 指该达人在不同帖子中被提及的总次数\n")
        f.write(f"- **平台**: 达人活跃的社交媒体平台（抖音、小红书等）\n")
        f.write(f"- **专业背景**: 达人的教育或职业背景（如有提及）\n")
        f.write(f"- **主要特点**: 达人的内容特色或专业领域\n\n")
        
        f.write(f"---\n\n")
        f.write(f"*报告生成时间: {datetime.now().isoformat()}*\n")
        f.write(f"*数据来源: TikHub API + Gemini AI 分析*\n")
    
    print(f"✓ Markdown报告已保存: {report_file}")
    
    # 生成JSON数据文件
    json_data = {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(),
            "search_keyword": search_keyword,
            "total_posts_analyzed": total_posts_analyzed,
            "relevant_posts": relevant_posts,
            "posts_with_kols": posts_with_kols,
            "total_unique_kols": len(sorted_kols),
            "failed_analyses_count": len(failed_analyses),
            "posts_by_type": posts_by_type
        },
        "kols_ranking": [
            {
                "rank": i,
                "name": kol_name,
                "mention_count": info["count"],
                "platforms": info["platforms"],
                "professional_backgrounds": info["professional_backgrounds"],
                "characteristics": info["characteristics"],
                "posts": info["posts"]
            }
            for i, (kol_name, info) in enumerate(sorted_kols, 1)
        ],
        "failed_analyses": failed_analyses
    }
    
    json_file = output_dir / f"final_kol_data_{stamp}.json"
    with json_file.open("w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ JSON数据已保存: {json_file}")
    
    print("\n" + "=" * 80)
    print("汇总统计")
    print("=" * 80)
    print(f"总帖子数: {total_posts_analyzed}")
    print(f"相关内容帖子: {relevant_posts} ({relevant_posts/total_posts_analyzed*100:.1f}%)")
    print(f"发现达人的帖子: {posts_with_kols} ({posts_with_kols/total_posts_analyzed*100:.1f}%)")
    print(f"发现独立达人数: {len(sorted_kols)}")
    print(f"分析失败帖子数: {len(failed_analyses)}")
    
    if sorted_kols:
        print("\n提及次数最多的达人（前10位）:")
        for i, (kol_name, info) in enumerate(sorted_kols[:10], 1):
            print(f"  {i}. {kol_name} (提及{info['count']}次)")
    
    print("=" * 80)
    print("\n完成！最终报告和数据已生成。")


if __name__ == "__main__":
    main()

