#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用Gemini 2.5 Flash分析视频内容

分析维度：
1. 博主形象与家居风格
2. 剪辑能力
3. 口播能力

模型配置：
- 模型: gemini-2.5-flash (Google Gemini API直连)
- 温度: 0.3
- max_output_tokens: 8192
- 并行处理: 5个视频同时分析
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai

# 加载环境变量
BACKEND_DIR = Path("/Users/rigel/project/hdl-tikhub-goodgame/backend")
load_dotenv(BACKEND_DIR / '.env')

# 项目路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "02_视频数据"
RESULT_DIR = PROJECT_DIR / "03_分析结果"
PROMPT_DIR = PROJECT_DIR / "prompts"

# 配置Gemini - 优先使用GEMINI_API_KEY2
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY2', '') or os.getenv('GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY_ANALYZE', '')
genai.configure(api_key=GEMINI_API_KEY)


def log(msg: str):
    """实时打印日志"""
    print(msg, flush=True)


def get_supabase_client():
    """获取Supabase客户端"""
    from supabase import create_client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    return create_client(url, key)


def enrich_video_metadata(note_id: str, basic_meta: Dict) -> Dict:
    """从数据库获取完整的视频元数据"""
    client = get_supabase_client()
    
    note_resp = client.table('gg_pgy_kol_notes').select(
        'note_id, kol_id, title, raw_data'
    ).eq('note_id', note_id).single().execute()
    
    if note_resp.data:
        raw_data = note_resp.data.get('raw_data') or {}
        basic_meta['content'] = raw_data.get('content', '')
    
    kol_id = basic_meta.get('kol_id')
    if kol_id:
        kol_resp = client.table('gg_pgy_kol_analysis_result').select(
            'kol_name, fans_count_current'
        ).eq('kol_id', kol_id).single().execute()
        
        if kol_resp.data:
            basic_meta['kol_name'] = kol_resp.data.get('kol_name') or basic_meta.get('kol_name', '')
            basic_meta['fans_count'] = kol_resp.data.get('fans_count_current', 0)
    
    return basic_meta


def load_system_prompt() -> str:
    """从文件加载系统prompt"""
    prompt_file = PROMPT_DIR / "video_analysis_prompt.txt"
    if prompt_file.exists():
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    raise FileNotFoundError(f"Prompt文件不存在: {prompt_file}")


def create_analysis_prompt(video_metadata: Dict) -> str:
    """创建分析提示词"""
    content = video_metadata.get('content', '无正文')
    if len(content) > 1000:
        content = content[:1000] + "..."
    
    return f"""
## 视频背景信息

- **博主名称**: {video_metadata.get('kol_name', '未知')}
- **视频标题**: {video_metadata.get('title', '无标题')}
- **视频正文**: 
{content}

请观看上传的视频，结合以上背景信息，进行专业分析。
"""


def analyze_video(video_path: str, video_metadata: Dict, video_index: int = 0, total: int = 1, max_retries: int = 3) -> Optional[Dict]:
    """分析单个视频（带实时日志和重试）"""
    note_id = video_metadata.get('note_id', 'unknown')
    title = (video_metadata.get('title') or '无标题')[:25]
    
    if not GEMINI_API_KEY:
        log(f"  [{video_index}/{total}] ❌ 未配置 GEMINI_API_KEY")
        return None
    
    for attempt in range(max_retries):
        try:
            system_prompt = load_system_prompt()
            
            if attempt == 0:
                log(f"  [{video_index}/{total}] 📤 上传: {title}...")
            else:
                log(f"  [{video_index}/{total}] 🔄 重试({attempt+1}/{max_retries}): {title}...")
                time.sleep(30 * attempt)  # 指数退避
            
            video_file = genai.upload_file(video_path, mime_type="video/mp4")
            
            log(f"  [{video_index}/{total}] ⏳ 处理中...")
            while video_file.state.name == "PROCESSING":
                time.sleep(3)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name != "ACTIVE":
                log(f"  [{video_index}/{total}] ❌ 处理失败: {video_file.state.name}")
                continue
            
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config={"temperature": 0.3, "max_output_tokens": 8192}
            )
            
            user_prompt = create_analysis_prompt(video_metadata)
            
            log(f"  [{video_index}/{total}] 🔍 分析中...")
            response = model.generate_content(
                [video_file, system_prompt, user_prompt],
                request_options={"timeout": 300}
            )
            
            result_text = response.text
            
            # 提取JSON
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            
            # 修复不完整JSON
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                if result_text.count('{') > result_text.count('}'):
                    missing = result_text.count('{') - result_text.count('}')
                    result_text = result_text.rstrip(',\n ') + '\n' + '}' * missing
                    result = json.loads(result_text)
                else:
                    raise
            
            # 清理上传文件
            try:
                genai.delete_file(video_file.name)
            except:
                pass
            
            score = result.get('overall_assessment', {}).get('overall_score', 'N/A')
            log(f"  [{video_index}/{total}] ✅ 完成: {title} | 评分: {score}")
            
            return result
            
        except json.JSONDecodeError as e:
            log(f"  [{video_index}/{total}] ❌ JSON错误: {title}")
            return None
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower():
                log(f"  [{video_index}/{total}] ⚠️ 配额限制，等待重试...")
                if attempt < max_retries - 1:
                    time.sleep(60 * (attempt + 1))  # 1分钟, 2分钟...
                    continue
            log(f"  [{video_index}/{total}] ❌ 异常: {title} - {err_str[:50]}")
            if attempt == max_retries - 1:
                return None
    
    return None


def save_result(result: Dict, video_metadata: Dict):
    """保存分析结果"""
    kol_id = video_metadata.get('kol_id')
    note_id = video_metadata.get('note_id')
    
    result_dir = RESULT_DIR / f"kol_{kol_id}"
    result_dir.mkdir(parents=True, exist_ok=True)
    
    result_file = result_dir / f"{note_id}_analysis.json"
    
    full_result = {
        'video_metadata': video_metadata,
        'analysis_result': result,
        'analyzed_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(full_result, f, ensure_ascii=False, indent=2)


def analyze_single_video_task(args):
    """单个视频分析任务（用于并行）"""
    video_meta, video_index, total = args
    note_id = video_meta['note_id']
    
    # 从数据库获取content
    video_meta = enrich_video_metadata(note_id, video_meta.copy())
    
    video_path = video_meta.get('file_path')
    if not video_path or not Path(video_path).exists():
        log(f"  [{video_index}/{total}] ❌ 文件不存在: {note_id}")
        return None
    
    result = analyze_video(video_path, video_meta, video_index, total)
    
    if result:
        save_result(result, video_meta)
    
    return (note_id, result)


def analyze_kol_videos(kol_id: str, skip_analyzed: bool = True, max_workers: int = 5):
    """并行分析指定KOL的所有视频"""
    video_list_file = DATA_DIR / "video_list.json"
    with open(video_list_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    videos = [v for v in data['videos'] if v.get('kol_id') == kol_id and v.get('downloaded')]
    
    if not videos:
        log(f"❌ 找不到KOL {kol_id} 的视频")
        return
    
    kol_name = videos[0].get('kol_name', 'Unknown')
    
    # 检查已分析
    analyzed = set()
    kol_result_dir = RESULT_DIR / f"kol_{kol_id}"
    if kol_result_dir.exists():
        analyzed = {f.stem.replace('_analysis', '') for f in kol_result_dir.glob('*_analysis.json')}
    
    # 筛选待分析
    if skip_analyzed:
        to_analyze = [v for v in videos if v['note_id'] not in analyzed]
        skipped = len(videos) - len(to_analyze)
    else:
        to_analyze = videos
        skipped = 0
    
    log(f"\n{'='*60}")
    log(f"KOL: {kol_name}")
    log(f"总视频: {len(videos)} | 待分析: {len(to_analyze)} | 跳过: {skipped}")
    log(f"并行数: {min(max_workers, len(to_analyze))}")
    log(f"{'='*60}")
    
    if not to_analyze:
        log("✅ 所有视频已分析完成")
        return
    
    # 准备任务
    tasks = [(v, i+1, len(to_analyze)) for i, v in enumerate(to_analyze)]
    
    # 并行执行
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_single_video_task, task): task for task in tasks}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    
    success = sum(1 for r in results if r[1] is not None)
    log(f"\n✅ {kol_name} 分析完成: {success}/{len(to_analyze)} 成功")


def generate_kol_summary(kol_id: str, kol_name: str) -> Optional[str]:
    """生成KOL汇总报告"""
    
    kol_result_dir = RESULT_DIR / f"kol_{kol_id}"
    if not kol_result_dir.exists():
        log(f"❌ 找不到KOL {kol_name} 的分析结果")
        return None
    
    analysis_files = list(kol_result_dir.glob("*_analysis.json"))
    if not analysis_files:
        log(f"❌ KOL {kol_name} 没有分析结果")
        return None
    
    video_analyses = []
    for f in analysis_files:
        with open(f, 'r', encoding='utf-8') as file:
            video_analyses.append(json.load(file))
    
    log(f"📊 汇总 {kol_name} 的 {len(video_analyses)} 个视频...")
    
    # 收集数据
    scores_d1, scores_d2, scores_d3 = [], [], []
    all_evidence = []
    home_styles, soft_decorations, pillow_observations = [], [], []
    
    for va in video_analyses:
        meta = va.get('video_metadata', {})
        result = va.get('analysis_result', {})
        
        d1 = result.get('dimension_1_style', {})
        d2 = result.get('dimension_2_editing', {})
        d3 = result.get('dimension_3_speaking', {})
        
        if d1.get('score'): scores_d1.append(d1['score'])
        if d2.get('score'): scores_d2.append(d2['score'])
        if d3.get('score'): scores_d3.append(d3['score'])
        
        if d1.get('home_style_type'): home_styles.append(d1['home_style_type'])
        if d1.get('soft_decoration_details'): soft_decorations.append(d1['soft_decoration_details'])
        if d1.get('pillow_or_cushion_observed'): pillow_observations.append(d1['pillow_or_cushion_observed'])
        
        video_info = {
            'title': meta.get('title', ''),
            'is_ad': meta.get('is_advertise', False),
            'video_summary': result.get('video_summary', ''),
            'd1_score': d1.get('score', 0),
            'd2_score': d2.get('score', 0),
            'd3_score': d3.get('score', 0),
            # 完整保留评分理由，不截断
            'd1_reasoning': d1.get('score_reasoning', '无'),
            'd2_reasoning': d2.get('score_reasoning', '无'),
            'd3_reasoning': d3.get('score_reasoning', '无'),
            'd3_key_quotes': d3.get('key_quotes', []),
            'overall': result.get('overall_assessment', {})
        }
        all_evidence.append(video_info)
    
    # 计算平均分
    avg_d1 = sum(scores_d1) / len(scores_d1) if scores_d1 else 0
    avg_d2 = sum(scores_d2) / len(scores_d2) if scores_d2 else 0
    avg_d3 = sum(scores_d3) / len(scores_d3) if scores_d3 else 0
    avg_overall = (avg_d1 + avg_d2 + avg_d3) / 3
    
    fans_count = video_analyses[0].get('video_metadata', {}).get('fans_count', 0)
    
    def get_rating(score):
        if score >= 4.5: return "优秀 ⭐⭐⭐"
        elif score >= 4: return "良好 ⭐⭐"
        elif score >= 3: return "一般 ⭐"
        else: return "较弱"
    
    # 生成报告
    report = f"""# {kol_name} 内容能力综合评估报告

> **评估目的**：判断该博主是否适合进行**抱枕品牌**的推广合作

---

## 一、博主基本信息

| 项目 | 信息 |
|------|------|
| 博主名称 | {kol_name} |
| 粉丝数量 | {fans_count or 0:,} |
| 分析视频数 | {len(video_analyses)} 个 |
| 评估时间 | {time.strftime('%Y-%m-%d %H:%M:%S')} |

---

## 二、三维度综合评分

| 评估维度 | 平均得分 | 评级 | 说明 |
|----------|----------|------|------|
| 维度1：形象与家居风格 | {avg_d1:.1f} 分 | {get_rating(avg_d1)} | 对抱枕推广最重要的维度 |
| 维度2：剪辑能力 | {avg_d2:.1f} 分 | {get_rating(avg_d2)} | 视频制作专业度 |
| 维度3：口播能力 | {avg_d3:.1f} 分 | {get_rating(avg_d3)} | 产品卖点传达能力 |
| **综合评分** | **{avg_overall:.1f} 分** | **{get_rating(avg_overall)}** | - |

---

## 三、各视频分析摘要

"""
    
    for i, ev in enumerate(all_evidence, 1):
        ad_tag = " [广告]" if ev['is_ad'] else ""
        report += f"""### 视频{i}: {ev['title']}{ad_tag}

**内容概要**: {ev['video_summary']}

**评分详情**:

| 维度 | 得分 | 评分理由 |
|------|------|----------|
| 形象风格 | {ev['d1_score']}分 | {ev['d1_reasoning']} |
| 剪辑能力 | {ev['d2_score']}分 | {ev['d2_reasoning']} |
| 口播能力 | {ev['d3_score']}分 | {ev['d3_reasoning']} |

---

"""
    
    # 家居风格分析
    report += """## 四、抱枕推广适合度分析

### 4.1 家居风格与软装元素

"""
    if home_styles:
        report += f"**家居风格**: {', '.join(set(home_styles))}\n\n"
    
    if soft_decorations:
        report += "**软装元素**:\n"
        for i, dec in enumerate(soft_decorations, 1):
            report += f"- 视频{i}: {dec}\n"
        report += "\n"
    
    has_pillow = any(p and '无' not in p and '没有' not in p for p in pillow_observations if p)
    if has_pillow:
        report += "**抱枕出现**: ✅ 有\n"
    else:
        report += "**抱枕出现**: ❌ 未明显出现\n"
    
    # 口播分析
    report += f"""
### 4.2 口播能力

"""
    if avg_d3 > 1.5:
        report += f"博主具有口播能力（{avg_d3:.1f}分），能够传达产品卖点。\n"
    else:
        report += "博主视频主要依靠画面传达，口播较少。如需口播介绍，需额外沟通。\n"
    
    # 契合度
    report += "\n### 4.3 品牌契合度\n\n"
    if avg_d1 >= 4:
        report += "✅ **高度契合**: 家居风格温馨有品味，适合抱枕推广。\n"
    elif avg_d1 >= 3:
        report += "⚠️ **基本契合**: 家居环境尚可，可考虑合作。\n"
    else:
        report += "❌ **契合度低**: 可能不太适合家居软装推广。\n"
    
    # 优劣势
    all_strengths, all_weaknesses = [], []
    for ev in all_evidence:
        overall = ev.get('overall', {})
        all_strengths.extend(overall.get('strengths', []))
        all_weaknesses.extend(overall.get('weaknesses', []))
    
    report += "\n---\n\n## 五、综合评估\n\n### 5.1 主要优势\n\n"
    for s in list(set(all_strengths))[:5]:
        report += f"- {s}\n"
    
    report += "\n### 5.2 不足之处\n\n"
    for w in list(set(all_weaknesses))[:5]:
        report += f"- {w}\n"
    
    # 最终结论
    if avg_overall >= 4:
        recommendation, pillow_fit = "⭐⭐⭐ 强烈推荐", "非常适合"
    elif avg_overall >= 3.5:
        recommendation, pillow_fit = "⭐⭐ 推荐", "适合"
    elif avg_overall >= 3:
        recommendation, pillow_fit = "⭐ 谨慎", "一般"
    else:
        recommendation, pillow_fit = "暂不推荐", "不太适合"
    
    report += f"""
---

## 六、最终结论

| 项目 | 结论 |
|------|------|
| **推荐等级** | {recommendation} |
| **抱枕推广适合度** | {pillow_fit} |
| **形象风格** | {avg_d1:.1f}分 |
| **剪辑能力** | {avg_d2:.1f}分 |
| **口播能力** | {avg_d3:.1f}分 |
| **综合评分** | {avg_overall:.1f}分 |

---

*报告生成: {time.strftime('%Y-%m-%d %H:%M:%S')} | 模型: Gemini 2.5 Flash | 视频数: {len(video_analyses)}*
"""
    
    # 保存
    report_file = kol_result_dir / f"{kol_name}_综合评估报告.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    summary_json = {
        'kol_id': kol_id,
        'kol_name': kol_name,
        'fans_count': fans_count,
        'video_count': len(video_analyses),
        'scores': {
            'd1_avg': round(avg_d1, 1),
            'd2_avg': round(avg_d2, 1),
            'd3_avg': round(avg_d3, 1),
            'overall': round(avg_overall, 1)
        },
        'recommendation': recommendation,
        'pillow_fit': pillow_fit,
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    json_file = kol_result_dir / f"{kol_name}_综合评估.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary_json, f, ensure_ascii=False, indent=2)
    
    log(f"✅ 报告: {report_file.name}")
    return report


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='Gemini视频分析')
    parser.add_argument('--kol-id', type=str, help='分析指定KOL的所有视频')
    parser.add_argument('--kol-ids', type=str, help='批量分析多个KOL（逗号分隔）')
    parser.add_argument('--summary', type=str, help='生成指定KOL的汇总报告')
    parser.add_argument('--workers', type=int, default=5, help='并行数（默认5）')
    args = parser.parse_args()
    
    if args.kol_id:
        analyze_kol_videos(args.kol_id, max_workers=args.workers)
        # 分析完自动生成报告
        video_list_file = DATA_DIR / "video_list.json"
        with open(video_list_file, 'r') as f:
            data = json.load(f)
        for v in data['videos']:
            if v.get('kol_id') == args.kol_id:
                generate_kol_summary(args.kol_id, v.get('kol_name', 'Unknown'))
                break
    
    elif args.kol_ids:
        kol_ids = [k.strip() for k in args.kol_ids.split(',')]
        for kol_id in kol_ids:
            analyze_kol_videos(kol_id, max_workers=args.workers)
            # 生成报告
            video_list_file = DATA_DIR / "video_list.json"
            with open(video_list_file, 'r') as f:
                data = json.load(f)
            for v in data['videos']:
                if v.get('kol_id') == kol_id:
                    generate_kol_summary(kol_id, v.get('kol_name', 'Unknown'))
                    break
            log("\n" + "="*60 + "\n")
    
    elif args.summary:
        video_list_file = DATA_DIR / "video_list.json"
        with open(video_list_file, 'r') as f:
            data = json.load(f)
        for v in data['videos']:
            if v.get('kol_id') == args.summary:
                generate_kol_summary(args.summary, v.get('kol_name', 'Unknown'))
                break
    
    else:
        print("用法:")
        print("  --kol-id <ID>      分析指定KOL的所有视频")
        print("  --kol-ids <IDs>    批量分析多个KOL（逗号分隔）")
        print("  --summary <ID>     生成指定KOL的汇总报告")
        print("  --workers <N>      并行数（默认5）")


if __name__ == "__main__":
    main()
