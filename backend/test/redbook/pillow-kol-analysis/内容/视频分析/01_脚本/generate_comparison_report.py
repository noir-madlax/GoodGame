#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成所有KOL的横向比较报告
"""

import json
import time
from pathlib import Path

RESULT_DIR = Path(__file__).parent.parent / "03_分析结果"


def load_all_summaries():
    """加载所有KOL的汇总数据"""
    kol_summaries = []
    
    for d in sorted(RESULT_DIR.iterdir()):
        if not d.is_dir() or not d.name.startswith('kol_'):
            continue
        
        kol_id = d.name.replace('kol_', '')
        
        # 找汇总JSON
        for f in d.glob('*_综合评估.json'):
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                data['kol_id'] = kol_id
                
                # 计算overall（兼容旧格式）
                scores = data.get('scores', {})
                if not scores.get('overall') or scores.get('overall') == 0:
                    # 尝试从分析文件重新计算
                    analysis_files = list(d.glob('*_analysis.json'))
                    if analysis_files:
                        d1_scores, d2_scores, d3_scores = [], [], []
                        for af in analysis_files:
                            with open(af, 'r', encoding='utf-8') as afile:
                                adata = json.load(afile)
                                result = adata.get('analysis_result', {})
                                d1 = result.get('dimension_1_style', {}).get('score')
                                d2 = result.get('dimension_2_editing', {}).get('score')
                                d3 = result.get('dimension_3_speaking', {}).get('score')
                                if d1: d1_scores.append(d1)
                                if d2: d2_scores.append(d2)
                                if d3: d3_scores.append(d3)
                        
                        if d1_scores:
                            scores['d1_avg'] = round(sum(d1_scores) / len(d1_scores), 1)
                            scores['d2_avg'] = round(sum(d2_scores) / len(d2_scores), 1) if d2_scores else 0
                            scores['d3_avg'] = round(sum(d3_scores) / len(d3_scores), 1) if d3_scores else 0
                            scores['overall'] = round((scores['d1_avg'] + scores['d2_avg'] + scores['d3_avg']) / 3, 1)
                            data['scores'] = scores
                
                kol_summaries.append(data)
                break
    
    # 按综合评分排序
    return sorted(kol_summaries, key=lambda x: -(x['scores'].get('overall') or 0))


def generate_comparison_report():
    """生成横向比较报告"""
    summaries = load_all_summaries()
    
    if not summaries:
        print("❌ 没有找到任何KOL分析数据")
        return
    
    print(f"📊 生成 {len(summaries)} 个KOL的横向比较报告...")
    
    # 分级
    tier1 = [s for s in summaries if (s['scores'].get('overall') or 0) >= 4.5]  # 强烈推荐
    tier2 = [s for s in summaries if 4.0 <= (s['scores'].get('overall') or 0) < 4.5]  # 推荐
    tier3 = [s for s in summaries if 3.5 <= (s['scores'].get('overall') or 0) < 4.0]  # 可考虑
    tier4 = [s for s in summaries if (s['scores'].get('overall') or 0) < 3.5]  # 暂不推荐
    
    report = f"""# KOL横向比较与选择建议报告

> **项目**: 抱枕品牌推广KOL筛选
> **生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
> **分析KOL数**: {len(summaries)} 位

---

## 一、总览排名

| 排名 | KOL | 综合评分 | 形象风格 | 剪辑能力 | 口播能力 | 粉丝数 | 推荐等级 |
|------|-----|---------|---------|---------|---------|--------|---------|
"""
    
    for i, s in enumerate(summaries, 1):
        scores = s['scores']
        overall = scores.get('overall') or 0
        fans = s.get('fans_count', 0)
        fans_str = f"{fans:,}" if fans else "N/A"
        
        # 推荐等级emoji
        if overall >= 4.5:
            level = "⭐⭐⭐ 强烈推荐"
        elif overall >= 4.0:
            level = "⭐⭐ 推荐"
        elif overall >= 3.5:
            level = "⭐ 可考虑"
        else:
            level = "暂不推荐"
        
        report += f"| {i} | {s['kol_name']} | **{overall}** | {scores.get('d1_avg', 0)} | {scores.get('d2_avg', 0)} | {scores.get('d3_avg', 0)} | {fans_str} | {level} |\n"
    
    report += """
---

## 二、分级推荐

"""
    
    # Tier 1
    report += f"""### 🥇 第一梯队：强烈推荐（{len(tier1)}位）

> 综合评分 ≥ 4.5分，各维度表现均衡优秀

"""
    if tier1:
        for s in tier1:
            scores = s['scores']
            report += f"""**{s['kol_name']}** - {scores.get('overall', 0)}分
- 形象风格: {scores.get('d1_avg', 0)}分 | 剪辑能力: {scores.get('d2_avg', 0)}分 | 口播能力: {scores.get('d3_avg', 0)}分
- 粉丝: {s.get('fans_count', 0):,}
- 适合度: {s.get('pillow_fit', 'N/A')}

"""
    else:
        report += "*暂无*\n\n"
    
    # Tier 2
    report += f"""### 🥈 第二梯队：推荐（{len(tier2)}位）

> 综合评分 4.0-4.4分，整体表现良好

"""
    if tier2:
        for s in tier2:
            scores = s['scores']
            report += f"""**{s['kol_name']}** - {scores.get('overall', 0)}分
- 形象风格: {scores.get('d1_avg', 0)}分 | 剪辑能力: {scores.get('d2_avg', 0)}分 | 口播能力: {scores.get('d3_avg', 0)}分
- 粉丝: {s.get('fans_count', 0):,}

"""
    else:
        report += "*暂无*\n\n"
    
    # Tier 3
    report += f"""### 🥉 第三梯队：可考虑（{len(tier3)}位）

> 综合评分 3.5-3.9分，有特定优势但也有明显短板

"""
    if tier3:
        for s in tier3:
            scores = s['scores']
            # 找优势和短板
            dims = {'形象风格': scores.get('d1_avg', 0), '剪辑能力': scores.get('d2_avg', 0), '口播能力': scores.get('d3_avg', 0)}
            best = max(dims, key=dims.get)
            worst = min(dims, key=dims.get)
            report += f"- **{s['kol_name']}**: {scores.get('overall', 0)}分 | 优势: {best}({dims[best]}分) | 短板: {worst}({dims[worst]}分)\n"
        report += "\n"
    else:
        report += "*暂无*\n\n"
    
    # Tier 4
    report += f"""### ⚠️ 暂不推荐（{len(tier4)}位）

> 综合评分 < 3.5分，与抱枕推广需求匹配度较低

"""
    if tier4:
        for s in tier4:
            scores = s['scores']
            report += f"- {s['kol_name']}: {scores.get('overall', 0)}分\n"
        report += "\n"
    else:
        report += "*暂无*\n\n"
    
    # 维度分析
    report += """---

## 三、维度专项分析

### 3.1 形象风格TOP5（对抱枕推广最重要）

"""
    d1_sorted = sorted(summaries, key=lambda x: -(x['scores'].get('d1_avg') or 0))[:5]
    for i, s in enumerate(d1_sorted, 1):
        report += f"{i}. **{s['kol_name']}**: {s['scores'].get('d1_avg', 0)}分\n"
    
    report += """
### 3.2 口播能力TOP5（产品卖点传达）

"""
    d3_sorted = sorted(summaries, key=lambda x: -(x['scores'].get('d3_avg') or 0))[:5]
    for i, s in enumerate(d3_sorted, 1):
        report += f"{i}. **{s['kol_name']}**: {s['scores'].get('d3_avg', 0)}分\n"
    
    report += """
### 3.3 剪辑能力TOP5（视频制作水平）

"""
    d2_sorted = sorted(summaries, key=lambda x: -(x['scores'].get('d2_avg') or 0))[:5]
    for i, s in enumerate(d2_sorted, 1):
        report += f"{i}. **{s['kol_name']}**: {s['scores'].get('d2_avg', 0)}分\n"
    
    # 最终建议
    report += """
---

## 四、选择建议

### 4.1 首选推荐

基于综合评分、形象风格契合度和口播能力，**最适合抱枕品牌推广**的KOL：

"""
    # 筛选：综合>=4.0 且 D1>=4.0 且 D3>=4.0
    best_fit = [s for s in summaries if 
                (s['scores'].get('overall') or 0) >= 4.0 and 
                (s['scores'].get('d1_avg') or 0) >= 4.0 and 
                (s['scores'].get('d3_avg') or 0) >= 4.0]
    
    if best_fit:
        for i, s in enumerate(best_fit, 1):
            scores = s['scores']
            report += f"""**{i}. {s['kol_name']}** ⭐
   - 综合: {scores.get('overall', 0)}分 | 形象: {scores.get('d1_avg', 0)}分 | 口播: {scores.get('d3_avg', 0)}分
   - 粉丝: {s.get('fans_count', 0):,}
   - 理由: 家居风格与软装产品契合，口播能力强，能有效传达产品卖点

"""
    else:
        # 退而求其次
        backup = [s for s in summaries if (s['scores'].get('overall') or 0) >= 4.0][:3]
        for i, s in enumerate(backup, 1):
            scores = s['scores']
            report += f"**{i}. {s['kol_name']}**: {scores.get('overall', 0)}分\n"
    
    report += """### 4.2 备选方案

如果首选KOL档期或报价不合适，以下KOL也值得考虑：

"""
    # 综合>=3.5 且不在best_fit中
    best_fit_names = {s['kol_name'] for s in best_fit}
    backup = [s for s in summaries if 
              (s['scores'].get('overall') or 0) >= 3.5 and 
              s['kol_name'] not in best_fit_names][:5]
    
    for s in backup:
        scores = s['scores']
        report += f"- **{s['kol_name']}**: {scores.get('overall', 0)}分\n"
    
    report += f"""
---

## 五、数据说明

- **分析方法**: 使用 Gemini 2.5 Flash 对每位KOL的多个视频进行多维度分析
- **评分维度**:
  - 维度1（形象风格）: 博主形象、家居风格、软装元素、与抱枕品牌的契合度
  - 维度2（剪辑能力）: 视频制作水平、镜头运用、节奏把控
  - 维度3（口播能力）: 语言表达、卖点传达、说服力
- **数据时间**: {time.strftime('%Y-%m-%d')}
- **总分析视频数**: {sum(s.get('video_count', 0) for s in summaries)} 个

---

*报告自动生成，仅供参考。实际合作请综合考虑KOL报价、档期、过往合作案例等因素。*
"""
    
    # 保存报告
    report_file = RESULT_DIR / "KOL横向比较报告.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 报告已生成: {report_file}")
    
    # 同时生成JSON
    json_data = {
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_kols': len(summaries),
        'tier1_count': len(tier1),
        'tier2_count': len(tier2),
        'tier3_count': len(tier3),
        'tier4_count': len(tier4),
        'rankings': [
            {
                'rank': i,
                'kol_name': s['kol_name'],
                'kol_id': s.get('kol_id', ''),
                'overall': s['scores'].get('overall', 0),
                'd1': s['scores'].get('d1_avg', 0),
                'd2': s['scores'].get('d2_avg', 0),
                'd3': s['scores'].get('d3_avg', 0),
                'fans_count': s.get('fans_count', 0),
                'video_count': s.get('video_count', 0),
                'recommendation': s.get('recommendation', ''),
                'pillow_fit': s.get('pillow_fit', '')
            }
            for i, s in enumerate(summaries, 1)
        ]
    }
    
    json_file = RESULT_DIR / "KOL横向比较数据.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 数据已生成: {json_file}")
    
    return report


if __name__ == "__main__":
    generate_comparison_report()
