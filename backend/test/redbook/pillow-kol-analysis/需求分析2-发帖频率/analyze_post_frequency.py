#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KOL 发帖频率分析脚本 - 需求2&7

需求说明：
- 需求2：了解博主的内容更新频率
- 需求7：每周 > 3 篇以上

数据来源：
- kol_note_list: 笔记列表（包含发布日期）
- kol_data_summary_v1: 近期笔记数、近7天活跃天数

数据库字段：
- post_count_30d: 30天发帖数
- post_avg_per_week: 平均每周发帖数
- post_frequency_pass: 是否达标（>3篇/周）
- post_frequency_detail: JSONB 每周发帖详情
- active_days_7d: 近7天活跃天数
- note_count_30d: 30天内笔记总数
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from collections import defaultdict
import statistics
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PostFrequencyAnalysis:
    """发帖频率分析结果"""
    post_count_30d: int                    # 30天发帖数
    post_avg_per_week: float               # 平均每周发帖数
    post_frequency_pass: bool              # 是否达标（>3篇/周）
    active_days_7d: int                    # 近7天活跃天数
    note_count_30d: int                    # 30天内笔记总数（用于分母展示）
    post_frequency_detail: Dict[str, Any]  # 每周发帖详情


class PostFrequencyAnalyzer:
    """发帖频率分析器"""
    
    def __init__(self, data_dir: str = None):
        # 数据目录在上级目录
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "output" / "api_data"
        self.results = []
        self._init_supabase()
    
    def _init_supabase(self):
        """初始化 Supabase 连接"""
        backend_dir = Path(__file__).parent.parent.parent.parent.parent
        env_path = backend_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
        
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            raise ValueError("请在 .env 文件中配置 SUPABASE_URL 和 SUPABASE_KEY")
        
        self.supabase = create_client(url, key)
        logger.info("Supabase 连接成功")
    
    def load_kol_data(self, kol_id: str) -> Optional[Dict[str, Any]]:
        """加载单个 KOL 的 API 数据"""
        kol_dir = self.data_dir / f"kol_{kol_id}"
        data_file = kol_dir / "all_data.json"
        
        if not data_file.exists():
            logger.warning(f"未找到 KOL 数据文件: {kol_id}")
            return None
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return None
    
    def _get_week_key(self, date: datetime, base_date: datetime) -> str:
        """获取周标识（相对于基准日期的第几周）"""
        days_diff = (base_date - date).days
        week_num = days_diff // 7 + 1
        week_start = date - timedelta(days=date.weekday())
        week_end = week_start + timedelta(days=6)
        return f"第{week_num}周 ({week_start.strftime('%m/%d')}-{week_end.strftime('%m/%d')})"
    
    def analyze_post_frequency(self, kol_data: Dict[str, Any]) -> Optional[PostFrequencyAnalysis]:
        """
        分析发帖频率
        
        评估维度：
        1. 30天发帖数
        2. 平均每周发帖数
        3. 是否满足每周>3篇的要求
        4. 近7天活跃天数
        5. 每周发帖详情
        """
        note_list_api = kol_data.get('apis', {}).get('kol_note_list', {})
        data_summary_v1 = kol_data.get('apis', {}).get('kol_data_summary_v1', {})
        
        # 获取近7天活跃天数
        active_days_7d = 0
        if data_summary_v1.get('code') == 0:
            summary_data = data_summary_v1.get('data', {})
            active_days_7d = summary_data.get('activeDayInLast7', 0) or 0
        
        # 检查笔记列表数据
        if note_list_api.get('code') != 0:
            logger.warning("笔记列表数据获取失败")
            return None
        
        note_list = note_list_api.get('data', {}).get('list', [])
        
        if not note_list:
            logger.warning("笔记列表为空")
            return PostFrequencyAnalysis(
                post_count_30d=0,
                post_avg_per_week=0,
                post_frequency_pass=False,
                active_days_7d=active_days_7d,
                note_count_30d=0,
                post_frequency_detail={
                    'weekly_counts': [],
                    'all_weeks_pass': False,
                    'pass_weeks': 0,
                    'total_weeks': 0
                }
            )
        
        # 计算30天前的日期
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)
        
        # 筛选30天内的笔记
        notes_30d = []
        for note in note_list:
            note_date = self._parse_date(note.get('date', ''))
            if note_date and note_date >= thirty_days_ago:
                notes_30d.append({
                    'date': note_date,
                    'title': note.get('title', ''),
                    'is_video': note.get('isVideo', False),
                    'is_advertise': note.get('isAdvertise', False)
                })
        
        post_count_30d = len(notes_30d)
        note_count_30d = post_count_30d  # 30天内笔记总数
        
        # 计算平均每周发帖数（30天约等于4.3周）
        weeks_in_period = 30 / 7
        post_avg_per_week = round(post_count_30d / weeks_in_period, 2) if post_count_30d > 0 else 0
        
        # 按周分组统计
        weekly_counts = defaultdict(int)
        for note in notes_30d:
            # 计算该笔记属于哪一周
            days_ago = (today - note['date']).days
            week_num = days_ago // 7 + 1
            if week_num <= 4:  # 只统计最近4周
                weekly_counts[week_num] += 1
        
        # 生成每周详情
        weekly_detail = []
        for week_num in range(1, 5):  # 4周
            week_start = today - timedelta(days=week_num * 7)
            week_end = today - timedelta(days=(week_num - 1) * 7)
            count = weekly_counts.get(week_num, 0)
            weekly_detail.append({
                'week': f"第{week_num}周",
                'date_range': f"{week_start.strftime('%m/%d')}-{week_end.strftime('%m/%d')}",
                'count': count,
                'pass': count >= 3
            })
        
        # 计算达标周数
        pass_weeks = sum(1 for w in weekly_detail if w['pass'])
        total_weeks = len(weekly_detail)
        
        # 判断是否达标（平均每周>3篇）
        post_frequency_pass = post_avg_per_week >= 3
        
        return PostFrequencyAnalysis(
            post_count_30d=post_count_30d,
            post_avg_per_week=post_avg_per_week,
            post_frequency_pass=post_frequency_pass,
            active_days_7d=active_days_7d,
            note_count_30d=note_count_30d,
            post_frequency_detail={
                'weekly_counts': weekly_detail,
                'all_weeks_pass': pass_weeks == total_weeks,
                'pass_weeks': pass_weeks,
                'total_weeks': total_weeks
            }
        )
    
    def get_all_kol_ids_from_files(self) -> List[str]:
        """从文件系统获取所有有实际数据的 KOL ID 列表"""
        kol_ids = []
        
        for kol_dir in sorted(self.data_dir.iterdir()):
            if not kol_dir.is_dir() or not kol_dir.name.startswith('kol_'):
                continue
            
            data_file = kol_dir / "all_data.json"
            if not data_file.exists():
                continue
            
            kol_id = kol_dir.name.replace('kol_', '')
            kol_ids.append(kol_id)
        
        return kol_ids
    
    def analyze_batch(self, kol_ids: List[str]) -> List[Tuple[str, str, PostFrequencyAnalysis]]:
        """批量分析 KOL 发帖频率"""
        results = []
        failed = []
        
        for i, kol_id in enumerate(kol_ids):
            logger.info(f"分析进度: {i+1}/{len(kol_ids)} - KOL: {kol_id}")
            
            kol_data = self.load_kol_data(kol_id)
            if not kol_data:
                failed.append(kol_id)
                continue
            
            kol_name = kol_data.get('kol_name', 'Unknown')
            analysis = self.analyze_post_frequency(kol_data)
            
            if analysis:
                results.append((kol_id, kol_name, analysis))
            else:
                failed.append(kol_id)
        
        logger.info(f"分析完成: 成功 {len(results)}, 失败 {len(failed)}")
        return results
    
    def save_to_db(self, results: List[Tuple[str, str, PostFrequencyAnalysis]]) -> Tuple[int, int]:
        """保存分析结果到数据库"""
        success_count = 0
        fail_count = 0
        
        for kol_id, kol_name, analysis in results:
            try:
                data = {
                    'kol_id': kol_id,
                    'post_count_30d': analysis.post_count_30d,
                    'post_avg_per_week': analysis.post_avg_per_week,
                    'post_frequency_pass': analysis.post_frequency_pass,
                    'active_days_7d': analysis.active_days_7d,
                    'note_count_30d': analysis.note_count_30d,
                    'post_frequency_detail': json.dumps(analysis.post_frequency_detail, ensure_ascii=False),
                    'updated_at': datetime.now().isoformat()
                }
                
                # 使用 upsert 更新已有记录
                self.supabase.table('gg_pgy_kol_analysis_result').upsert(
                    data,
                    on_conflict='kol_id,project_name'
                ).execute()
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"保存 KOL {kol_id} 失败: {e}")
                fail_count += 1
        
        return success_count, fail_count
    
    def generate_report(self, results: List[Tuple[str, str, PostFrequencyAnalysis]]) -> str:
        """生成发帖频率分析报告"""
        if not results:
            return "没有分析结果"
        
        # 统计数据
        total = len(results)
        pass_count = sum(1 for _, _, a in results if a.post_frequency_pass)
        fail_count = total - pass_count
        
        avg_post_count = statistics.mean([a.post_count_30d for _, _, a in results])
        avg_weekly_post = statistics.mean([a.post_avg_per_week for _, _, a in results])
        avg_active_days = statistics.mean([a.active_days_7d for _, _, a in results])
        
        # 按平均每周发帖数排序
        sorted_results = sorted(results, key=lambda x: x[2].post_avg_per_week, reverse=True)
        
        report = f"""# KOL 发帖频率分析报告

> **项目**: 枕头分析  
> **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> **KOL 数量**: {total}

---

## 一、整体概况

| 指标 | 数值 |
|------|------|
| 分析 KOL 总数 | {total} |
| 达标 (≥3篇/周) | {pass_count} ({pass_count/total*100:.1f}%) |
| 不达标 (<3篇/周) | {fail_count} ({fail_count/total*100:.1f}%) |
| 平均30天发帖数 | {avg_post_count:.1f} 篇 |
| 平均每周发帖数 | {avg_weekly_post:.2f} 篇 |
| 平均近7天活跃天数 | {avg_active_days:.1f} 天 |

---

## 二、完整发帖频率排名

| 排名 | KOL名称 | 30天发帖 | 每周均发 | 近7天活跃 | 达标 |
|------|---------|----------|----------|-----------|------|
"""
        for i, (kol_id, kol_name, analysis) in enumerate(sorted_results, 1):
            pass_icon = "✅" if analysis.post_frequency_pass else "❌"
            report += f"| {i} | {kol_name} | {analysis.post_count_30d} 篇 | {analysis.post_avg_per_week:.1f} 篇 | {analysis.active_days_7d} 天 | {pass_icon} |\n"
        
        report += f"""

---

## 三、判断标准说明

- **达标标准**: 平均每周发帖 ≥ 3 篇
- **30天发帖数**: 统计过去30天内发布的笔记总数
- **每周均发**: 30天发帖数 / 4.3 (约30/7周)
- **近7天活跃天数**: API 直接提供的 `activeDayInLast7` 字段

---

*报告生成时间: {datetime.now().isoformat()}*
"""
        return report


def main():
    """主函数"""
    analyzer = PostFrequencyAnalyzer()
    
    # 获取所有 KOL ID
    logger.info("正在获取所有 KOL 列表...")
    kol_ids = analyzer.get_all_kol_ids_from_files()
    logger.info(f"找到 {len(kol_ids)} 个 KOL")
    
    if not kol_ids:
        logger.error("没有找到 KOL 数据")
        return
    
    # 批量分析
    logger.info("开始分析发帖频率...")
    results = analyzer.analyze_batch(kol_ids)
    logger.info(f"分析完成，成功 {len(results)} 个")
    
    if not results:
        logger.error("没有成功的分析结果")
        return
    
    # 保存到数据库
    logger.info("保存结果到数据库...")
    success, fail = analyzer.save_to_db(results)
    logger.info(f"数据库保存完成: 成功 {success}, 失败 {fail}")
    
    # 生成报告
    logger.info("生成分析报告...")
    report = analyzer.generate_report(results)
    
    # 保存报告
    report_dir = Path(__file__).parent / "output"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"post_frequency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"报告已保存: {report_file}")
    print(report)
    
    return results


if __name__ == "__main__":
    main()
