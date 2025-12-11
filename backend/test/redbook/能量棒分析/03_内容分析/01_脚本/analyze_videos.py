#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段6-3: AI视频分析

功能：
1. 使用Gemini 2.5 Flash分析视频
2. 支持双API Key并行（GEMINI_API_KEY2 + GEMINI_API_KEY3）
3. 4并发处理
4. 断点续传，跳过已分析的视频
5. 保存原始返回和进度

目标KOL (4人, 18个视频)
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import threading

# 加载环境变量
BACKEND_DIR = Path("/Users/rigel/project/hdl-tikhub-goodgame/backend")
load_dotenv(BACKEND_DIR / '.env')

# 项目路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "02_视频数据"
RESULT_DIR = PROJECT_DIR / "03_分析结果"
PROMPT_DIR = PROJECT_DIR / "prompts"

# 确保目录存在
RESULT_DIR.mkdir(parents=True, exist_ok=True)

# API Keys
API_KEYS = []
key2 = os.getenv('GEMINI_API_KEY2', '')
key3 = os.getenv('GEMINI_API_KEY3', '')
if key2:
    API_KEYS.append(key2)
if key3:
    API_KEYS.append(key3)
if not API_KEYS:
    # 备用key
    key1 = os.getenv('GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY_ANALYZE', '')
    if key1:
        API_KEYS.append(key1)

print(f"📌 可用API Key数量: {len(API_KEYS)}")

# 配置
CONFIG = {
    "max_workers": 4,  # 4并发
    "max_retries": 3,
    "model_name": "gemini-2.5-flash",
    "temperature": 0.3,
    "max_output_tokens": 8192,
    "request_timeout": 300,
}


def log(msg: str):
    """实时打印日志"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {msg}", flush=True)


def load_system_prompt() -> str:
    """加载系统prompt"""
    prompt_file = PROMPT_DIR / "video_analysis_prompt.txt"
    if prompt_file.exists():
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    raise FileNotFoundError(f"Prompt文件不存在: {prompt_file}")


def load_video_list() -> List[Dict]:
    """加载视频列表"""
    video_list_file = DATA_DIR / "video_list.json"
    with open(video_list_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('videos', [])


def get_analyzed_videos() -> set:
    """获取已分析的视频ID"""
    analyzed = set()
    for kol_dir in RESULT_DIR.glob("kol_*"):
        for f in kol_dir.glob("*_analysis.json"):
            note_id = f.stem.replace('_analysis', '')
            analyzed.add(note_id)
    return analyzed


def save_analysis_result(video_meta: Dict, result: Dict, raw_response: str):
    """保存分析结果"""
    kol_id = video_meta.get('kol_id')
    note_id = video_meta.get('note_id')
    
    result_dir = RESULT_DIR / f"kol_{kol_id}"
    result_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存解析后的结果
    result_file = result_dir / f"{note_id}_analysis.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'video_metadata': video_meta,
            'analysis_result': result,
            'analyzed_at': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)
    
    # 保存原始返回
    raw_file = result_dir / f"{note_id}_raw_response.txt"
    with open(raw_file, 'w', encoding='utf-8') as f:
        f.write(raw_response)


def create_analysis_prompt(video_meta: Dict) -> str:
    """创建分析提示"""
    content = video_meta.get('content', '无正文')
    if len(content) > 1000:
        content = content[:1000] + "..."
    
    return f"""
## 视频背景信息

- **博主名称**: {video_meta.get('kol_name', '未知')}
- **视频标题**: {video_meta.get('title', '无标题')}
- **视频正文**: 
{content}
- **点赞数**: {video_meta.get('like_num', 0)}
- **收藏数**: {video_meta.get('collect_num', 0)}

请观看上传的视频，结合以上背景信息，进行专业分析。
"""


def analyze_video_with_key(video_path: str, video_meta: Dict, api_key: str, 
                           video_index: int, total: int) -> Tuple[Optional[Dict], str]:
    """使用指定API Key分析视频"""
    import google.generativeai as genai
    
    genai.configure(api_key=api_key)
    
    note_id = video_meta.get('note_id', 'unknown')
    kol_name = video_meta.get('kol_name', 'Unknown')
    title = (video_meta.get('title') or '无标题')[:25]
    
    # 获取key的后4位用于日志
    key_suffix = api_key[-4:] if len(api_key) > 4 else '????'
    
    for attempt in range(CONFIG['max_retries']):
        try:
            system_prompt = load_system_prompt()
            
            if attempt == 0:
                log(f"  [{video_index}/{total}] 📤 上传: {kol_name} - {title}... (key:...{key_suffix})")
            else:
                log(f"  [{video_index}/{total}] 🔄 重试({attempt+1}): {title}...")
                time.sleep(30 * attempt)
            
            # 上传视频
            video_file = genai.upload_file(video_path, mime_type="video/mp4")
            
            log(f"  [{video_index}/{total}] ⏳ 处理中...")
            while video_file.state.name == "PROCESSING":
                time.sleep(3)
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name != "ACTIVE":
                log(f"  [{video_index}/{total}] ❌ 处理失败: {video_file.state.name}")
                continue
            
            # 创建模型
            model = genai.GenerativeModel(
                model_name=CONFIG['model_name'],
                generation_config={
                    "temperature": CONFIG['temperature'],
                    "max_output_tokens": CONFIG['max_output_tokens']
                }
            )
            
            user_prompt = create_analysis_prompt(video_meta)
            
            log(f"  [{video_index}/{total}] 🔍 分析中...")
            response = model.generate_content(
                [video_file, system_prompt, user_prompt],
                request_options={"timeout": CONFIG['request_timeout']}
            )
            
            raw_response = response.text
            
            # 提取JSON
            result_text = raw_response
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
            log(f"  [{video_index}/{total}] ✅ 完成: {kol_name} - {title} | 评分: {score}")
            
            return result, raw_response
            
        except json.JSONDecodeError as e:
            log(f"  [{video_index}/{total}] ❌ JSON错误: {title}")
            return None, f"JSON解析错误: {e}"
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower():
                log(f"  [{video_index}/{total}] ⚠️ 配额限制(key:...{key_suffix})，等待重试...")
                if attempt < CONFIG['max_retries'] - 1:
                    time.sleep(60 * (attempt + 1))
                    continue
            log(f"  [{video_index}/{total}] ❌ 异常: {title} - {err_str[:80]}")
            if attempt == CONFIG['max_retries'] - 1:
                return None, f"异常: {err_str}"
    
    return None, "达到最大重试次数"


class ApiKeyPool:
    """API Key轮询池"""
    
    def __init__(self, keys: List[str]):
        self.keys = keys
        self.index = 0
        self.lock = threading.Lock()
    
    def get_key(self) -> str:
        """获取下一个可用的key"""
        with self.lock:
            key = self.keys[self.index % len(self.keys)]
            self.index += 1
            return key


def analyze_single_task(args: Tuple) -> Tuple[str, Optional[Dict], str]:
    """单个视频分析任务"""
    video_meta, video_index, total, key_pool = args
    
    note_id = video_meta['note_id']
    file_path = video_meta.get('file_path')
    
    if not file_path or not Path(file_path).exists():
        log(f"  [{video_index}/{total}] ❌ 文件不存在: {note_id}")
        return note_id, None, "文件不存在"
    
    # 从池中获取API Key
    api_key = key_pool.get_key()
    
    result, raw_response = analyze_video_with_key(
        file_path, video_meta, api_key, video_index, total
    )
    
    if result:
        save_analysis_result(video_meta, result, raw_response)
    
    return note_id, result, raw_response


def analyze_all_videos():
    """分析所有视频"""
    log("=" * 60)
    log("🚀 阶段6-3: AI视频分析")
    log("=" * 60)
    
    # 加载视频列表
    videos = load_video_list()
    videos = [v for v in videos if v.get('downloaded') and v.get('file_path')]
    
    # 获取已分析的
    analyzed = get_analyzed_videos()
    
    # 筛选待分析的
    to_analyze = [v for v in videos if v['note_id'] not in analyzed]
    skipped = len(videos) - len(to_analyze)
    
    log(f"总视频数: {len(videos)}")
    log(f"已分析: {skipped}")
    log(f"待分析: {len(to_analyze)}")
    log(f"API Keys: {len(API_KEYS)}")
    log(f"并发数: {CONFIG['max_workers']}")
    log("")
    
    if not to_analyze:
        log("✅ 所有视频已分析完成")
        return
    
    if not API_KEYS:
        log("❌ 没有可用的API Key，请配置GEMINI_API_KEY2或GEMINI_API_KEY3")
        return
    
    # 创建Key池
    key_pool = ApiKeyPool(API_KEYS)
    
    # 准备任务
    tasks = [(v, i+1, len(to_analyze), key_pool) for i, v in enumerate(to_analyze)]
    
    # 并行执行
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
        futures = {executor.submit(analyze_single_task, task): task[0]['note_id'] for task in tasks}
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                log(f"任务异常: {e}")
    
    # 统计
    elapsed = time.time() - start_time
    success = sum(1 for r in results if r[1] is not None)
    
    log("")
    log("=" * 60)
    log(f"📋 分析完成汇总")
    log("=" * 60)
    log(f"总耗时: {elapsed/60:.1f} 分钟")
    log(f"成功: {success}/{len(to_analyze)}")
    log(f"失败: {len(to_analyze) - success}")
    
    # 生成汇总报告
    generate_summary_reports()


def generate_kol_summary(kol_id: str, kol_name: str) -> Optional[str]:
    """生成单个KOL的汇总报告"""
    kol_result_dir = RESULT_DIR / f"kol_{kol_id}"
    if not kol_result_dir.exists():
        return None
    
    analysis_files = list(kol_result_dir.glob("*_analysis.json"))
    if not analysis_files:
        return None
    
    video_analyses = []
    for f in analysis_files:
        with open(f, 'r', encoding='utf-8') as file:
            video_analyses.append(json.load(file))
    
    # 收集数据
    scores_d1, scores_d2, scores_d3 = [], [], []
    all_evidence = []
    
    for va in video_analyses:
        meta = va.get('video_metadata', {})
        result = va.get('analysis_result', {})
        
        d1 = result.get('dimension_1_style', {})
        d2 = result.get('dimension_2_editing', {})
        d3 = result.get('dimension_3_speaking', {})
        
        if d1.get('score'): scores_d1.append(d1['score'])
        if d2.get('score'): scores_d2.append(d2['score'])
        if d3.get('score'): scores_d3.append(d3['score'])
        
        video_info = {
            'title': meta.get('title', ''),
            'video_summary': result.get('video_summary', ''),
            'd1_score': d1.get('score', 0),
            'd2_score': d2.get('score', 0),
            'd3_score': d3.get('score', 0),
            'd1_reasoning': d1.get('score_reasoning', '无'),
            'd2_reasoning': d2.get('score_reasoning', '无'),
            'd3_reasoning': d3.get('score_reasoning', '无'),
            'overall': result.get('overall_assessment', {})
        }
        all_evidence.append(video_info)
    
    # 计算平均分
    avg_d1 = sum(scores_d1) / len(scores_d1) if scores_d1 else 0
    avg_d2 = sum(scores_d2) / len(scores_d2) if scores_d2 else 0
    avg_d3 = sum(scores_d3) / len(scores_d3) if scores_d3 else 0
    avg_overall = (avg_d1 + avg_d2 + avg_d3) / 3
    
    def get_rating(score):
        if score >= 4.5: return "优秀 ⭐⭐⭐"
        elif score >= 4: return "良好 ⭐⭐"
        elif score >= 3: return "一般 ⭐"
        else: return "较弱"
    
    # 生成报告
    report = f"""# {kol_name} 内容能力综合评估报告

> **评估目的**：判断该博主是否适合进行**能量棒/健康食品品牌**的推广合作

---

## 一、博主基本信息

| 项目 | 信息 |
|------|------|
| 博主名称 | {kol_name} |
| 分析视频数 | {len(video_analyses)} 个 |
| 评估时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

---

## 二、三维度综合评分

| 评估维度 | 平均得分 | 评级 | 说明 |
|----------|----------|------|------|
| 维度1：形象与生活方式 | {avg_d1:.1f} 分 | {get_rating(avg_d1)} | 与健康/运动的关联度 |
| 维度2：剪辑能力 | {avg_d2:.1f} 分 | {get_rating(avg_d2)} | 视频制作专业度 |
| 维度3：口播能力 | {avg_d3:.1f} 分 | {get_rating(avg_d3)} | 产品卖点传达能力 |
| **综合评分** | **{avg_overall:.1f} 分** | **{get_rating(avg_overall)}** | - |

---

## 三、各视频分析摘要

"""
    
    for i, ev in enumerate(all_evidence, 1):
        report += f"""### 视频{i}: {ev['title']}

**内容概要**: {ev['video_summary']}

**评分详情**:

| 维度 | 得分 | 评分理由 |
|------|------|----------|
| 形象生活方式 | {ev['d1_score']}分 | {ev['d1_reasoning'][:100]}... |
| 剪辑能力 | {ev['d2_score']}分 | {ev['d2_reasoning'][:100]}... |
| 口播能力 | {ev['d3_score']}分 | {ev['d3_reasoning'][:100]}... |

---

"""
    
    # 优劣势
    all_strengths, all_weaknesses = [], []
    for ev in all_evidence:
        overall = ev.get('overall', {})
        all_strengths.extend(overall.get('strengths', []))
        all_weaknesses.extend(overall.get('weaknesses', []))
    
    report += """## 四、综合评估

### 4.1 主要优势

"""
    for s in list(set(all_strengths))[:5]:
        report += f"- {s}\n"
    
    report += "\n### 4.2 不足之处\n\n"
    for w in list(set(all_weaknesses))[:5]:
        report += f"- {w}\n"
    
    # 最终结论
    if avg_overall >= 4:
        recommendation, fit = "⭐⭐⭐ 强烈推荐", "非常适合"
    elif avg_overall >= 3.5:
        recommendation, fit = "⭐⭐ 推荐", "适合"
    elif avg_overall >= 3:
        recommendation, fit = "⭐ 谨慎", "一般"
    else:
        recommendation, fit = "暂不推荐", "不太适合"
    
    report += f"""
---

## 五、最终结论

| 项目 | 结论 |
|------|------|
| **推荐等级** | {recommendation} |
| **能量棒推广适合度** | {fit} |
| **形象生活方式** | {avg_d1:.1f}分 |
| **剪辑能力** | {avg_d2:.1f}分 |
| **口播能力** | {avg_d3:.1f}分 |
| **综合评分** | {avg_overall:.1f}分 |

---

*报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 模型: Gemini 2.5 Flash | 视频数: {len(video_analyses)}*
"""
    
    # 保存报告
    report_file = kol_result_dir / f"{kol_name}_综合评估报告.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存JSON汇总
    summary_json = {
        'kol_id': kol_id,
        'kol_name': kol_name,
        'video_count': len(video_analyses),
        'scores': {
            'd1_avg': round(avg_d1, 1),
            'd2_avg': round(avg_d2, 1),
            'd3_avg': round(avg_d3, 1),
            'overall': round(avg_overall, 1)
        },
        'recommendation': recommendation,
        'energy_bar_fit': fit,
        'generated_at': datetime.now().isoformat()
    }
    
    json_file = kol_result_dir / f"{kol_name}_综合评估.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary_json, f, ensure_ascii=False, indent=2)
    
    log(f"  📄 {kol_name}: 报告已生成")
    return report


def generate_summary_reports():
    """生成所有KOL的汇总报告"""
    log("")
    log("📊 生成汇总报告...")
    
    # 加载视频列表获取KOL信息
    videos = load_video_list()
    kol_map = {}
    for v in videos:
        kol_id = v['kol_id']
        if kol_id not in kol_map:
            kol_map[kol_id] = v['kol_name']
    
    # 为每个KOL生成报告
    all_summaries = []
    for kol_id, kol_name in kol_map.items():
        report = generate_kol_summary(kol_id, kol_name)
        if report:
            # 读取JSON汇总
            json_file = RESULT_DIR / f"kol_{kol_id}" / f"{kol_name}_综合评估.json"
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    all_summaries.append(json.load(f))
    
    # 生成横向比较报告
    if all_summaries:
        generate_comparison_report(all_summaries)


def generate_comparison_report(summaries: List[Dict]):
    """生成KOL横向比较报告"""
    # 按综合评分排序
    summaries.sort(key=lambda x: x['scores']['overall'], reverse=True)
    
    report = f"""# 能量棒KOL横向比较报告

> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> **KOL数量**: {len(summaries)}

---

## 一、综合排名

| 排名 | KOL名称 | 综合评分 | 形象生活 | 剪辑能力 | 口播能力 | 推荐等级 | 能量棒适合度 |
|------|---------|----------|----------|----------|----------|----------|--------------|
"""
    
    for i, s in enumerate(summaries, 1):
        report += f"| {i} | {s['kol_name']} | {s['scores']['overall']:.1f} | {s['scores']['d1_avg']:.1f} | {s['scores']['d2_avg']:.1f} | {s['scores']['d3_avg']:.1f} | {s['recommendation']} | {s['energy_bar_fit']} |\n"
    
    report += """
---

## 二、各维度对比

### 2.1 形象与生活方式（与健康/运动关联度）

"""
    for s in summaries:
        report += f"- **{s['kol_name']}**: {s['scores']['d1_avg']:.1f}分\n"
    
    report += """
### 2.2 剪辑能力

"""
    for s in summaries:
        report += f"- **{s['kol_name']}**: {s['scores']['d2_avg']:.1f}分\n"
    
    report += """
### 2.3 口播能力

"""
    for s in summaries:
        report += f"- **{s['kol_name']}**: {s['scores']['d3_avg']:.1f}分\n"
    
    report += f"""
---

## 三、推荐结论

### 强烈推荐 ⭐⭐⭐

"""
    strong = [s for s in summaries if '强烈推荐' in s['recommendation']]
    if strong:
        for s in strong:
            report += f"- **{s['kol_name']}** (综合{s['scores']['overall']:.1f}分)\n"
    else:
        report += "无\n"
    
    report += """
### 推荐 ⭐⭐

"""
    recommend = [s for s in summaries if s['recommendation'] == '⭐⭐ 推荐']
    if recommend:
        for s in recommend:
            report += f"- **{s['kol_name']}** (综合{s['scores']['overall']:.1f}分)\n"
    else:
        report += "无\n"
    
    report += """
### 谨慎 / 不推荐

"""
    others = [s for s in summaries if '谨慎' in s['recommendation'] or '不推荐' in s['recommendation']]
    if others:
        for s in others:
            report += f"- **{s['kol_name']}** ({s['recommendation']})\n"
    else:
        report += "无\n"
    
    report += f"""
---

*报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # 保存报告
    report_file = RESULT_DIR / "KOL横向比较报告.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存JSON
    json_file = RESULT_DIR / "KOL横向比较数据.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'summaries': summaries
        }, f, ensure_ascii=False, indent=2)
    
    log(f"  📄 横向比较报告已生成: {report_file}")


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='AI视频分析')
    parser.add_argument('--report-only', action='store_true', help='仅生成报告，不分析')
    args = parser.parse_args()
    
    if args.report_only:
        generate_summary_reports()
    else:
        analyze_all_videos()


if __name__ == "__main__":
    main()
