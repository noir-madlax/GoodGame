#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KOL 粉丝vs数据比例分析脚本 - 需求4

需求说明：
- 单篇阅读数据 > 粉丝数据的 30%
- 单篇评论数据 > 20 条
- 前提条件：非投流（非广告笔记）

数据来源：
- kol_info: 粉丝数 (fansCount)
- kol_note_list: 阅读数/广告标记 (readNum, isAdvertise)
- note_comments: 评论数 (comments_count)

数据库字段：
- read_fans_ratio_avg: 阅读/粉丝比例平均值
- read_fans_ratio_pass: 是否达标（有笔记超过30%）
- read_fans_ratio_pass_count: 达标笔记数（阅读>粉丝30%）
- comment_gt_20_count: 评论>20条的笔记数
- comment_gt_20_pass: 是否达标（有笔记评论>20）
- comment_max: 单篇评论最高数
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
import statistics
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class FansRatioAnalysis:
    """粉丝vs数据比例分析结果"""
    fans_count: int                   # 粉丝数
    note_count_30d: int               # 30天内非广告笔记数
    
    # 阅读vs粉丝
    read_fans_ratio_avg: float        # 阅读/粉丝比例平均值
    read_fans_ratio_pass: bool        # 是否有笔记达标（>30%）
    read_fans_ratio_pass_count: int   # 达标笔记数
    
    # 评论>20条
    comment_gt_20_count: int          # 评论>20条的笔记数
    comment_gt_20_pass: bool          # 是否有笔记达标
    comment_max: int                  # 单篇评论最高数


class FansRatioAnalyzer:
    """粉丝vs数据比例分析器"""
    
    def __init__(self, data_dir: str = None, comments_dir: str = None):
        base_dir = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_dir / "output" / "api_data"
        self.comments_dir = Path(comments_dir) if comments_dir else base_dir / "output" / "note_comments"
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
            return None
        
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_kol_comments(self, kol_id: str) -> Optional[Dict[str, Any]]:
        """加载 KOL 的评论数据"""
        comments_file = self.comments_dir / f"kol_{kol_id}_notes.json"
        
        if not comments_file.exists():
            return None
        
        with open(comments_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        try:
            return datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
        except:
            return None
    
    def analyze_fans_ratio(self, kol_data: Dict[str, Any], comments_data: Optional[Dict[str, Any]]) -> Optional[FansRatioAnalysis]:
        """
        分析粉丝vs数据比例
        
        评估维度：
        1. 阅读/粉丝比例 > 30%
        2. 单篇评论 > 20 条
        3. 只统计非广告笔记（非投流）
        """
        kol_info_api = kol_data.get('apis', {}).get('kol_info', {})
        note_list_api = kol_data.get('apis', {}).get('kol_note_list', {})
        
        # 获取粉丝数
        if kol_info_api.get('code') != 0:
            logger.warning("kol_info 数据获取失败")
            return None
        
        fans_count = kol_info_api.get('data', {}).get('fansCount', 0) or 0
        
        if fans_count == 0:
            logger.warning("粉丝数为0，跳过")
            return None
        
        # 计算阈值：30% 粉丝数
        read_threshold = fans_count * 0.3
        
        # 处理笔记列表 (30天内非广告笔记)
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)
        
        notes_30d_non_ad = []
        if note_list_api.get('code') == 0:
            note_list = note_list_api.get('data', {}).get('list', [])
            
            for note in note_list:
                note_date = self._parse_date(note.get('date', ''))
                is_advertise = note.get('isAdvertise', False)
                
                # 只统计30天内的非广告笔记
                if note_date and note_date >= thirty_days_ago and not is_advertise:
                    notes_30d_non_ad.append({
                        'note_id': note.get('noteId', ''),
                        'read_num': note.get('readNum', 0) or 0,
                        'date': note.get('date', '')
                    })
        
        note_count_30d = len(notes_30d_non_ad)
        
        # 计算阅读/粉丝比例
        read_ratios = []
        read_pass_count = 0
        
        for note in notes_30d_non_ad:
            read_num = note['read_num']
            ratio = read_num / fans_count if fans_count > 0 else 0
            read_ratios.append(ratio)
            
            if read_num > read_threshold:
                read_pass_count += 1
        
        read_fans_ratio_avg = round(statistics.mean(read_ratios) * 100, 2) if read_ratios else 0
        read_fans_ratio_pass = read_pass_count > 0
        
        # 统计评论>20条的笔记 (从评论数据文件)
        comment_gt_20_count = 0
        comment_max = 0
        
        if comments_data:
            notes = comments_data.get('notes', [])
            
            for note in notes:
                note_date_str = note.get('create_date', '')
                note_date = self._parse_date(note_date_str)
                
                # 只统计30天内的笔记
                if note_date and note_date >= thirty_days_ago:
                    comments_count = note.get('comments_count', 0) or 0
                    
                    if comments_count > comment_max:
                        comment_max = comments_count
                    
                    if comments_count > 20:
                        comment_gt_20_count += 1
        
        comment_gt_20_pass = comment_gt_20_count > 0
        
        return FansRatioAnalysis(
            fans_count=fans_count,
            note_count_30d=note_count_30d,
            read_fans_ratio_avg=read_fans_ratio_avg,
            read_fans_ratio_pass=read_fans_ratio_pass,
            read_fans_ratio_pass_count=read_pass_count,
            comment_gt_20_count=comment_gt_20_count,
            comment_gt_20_pass=comment_gt_20_pass,
            comment_max=comment_max
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
    
    def analyze_batch(self, kol_ids: List[str]) -> List[Tuple[str, str, FansRatioAnalysis]]:
        """批量分析 KOL"""
        results = []
        failed = []
        
        for i, kol_id in enumerate(kol_ids):
            logger.info(f"分析进度: {i+1}/{len(kol_ids)} - KOL: {kol_id}")
            
            kol_data = self.load_kol_data(kol_id)
            if not kol_data:
                failed.append(kol_id)
                continue
            
            kol_name = kol_data.get('kol_name', 'Unknown')
            comments_data = self.load_kol_comments(kol_id)
            
            analysis = self.analyze_fans_ratio(kol_data, comments_data)
            
            if analysis:
                results.append((kol_id, kol_name, analysis))
            else:
                failed.append(kol_id)
        
        logger.info(f"分析完成: 成功 {len(results)}, 失败 {len(failed)}")
        return results
    
    def save_to_db(self, results: List[Tuple[str, str, FansRatioAnalysis]]) -> Tuple[int, int]:
        """保存分析结果到数据库"""
        success_count = 0
        fail_count = 0
        
        for kol_id, kol_name, analysis in results:
            try:
                data = {
                    'kol_id': kol_id,
                    'read_fans_ratio_avg': analysis.read_fans_ratio_avg,
                    'read_fans_ratio_pass': analysis.read_fans_ratio_pass,
                    'read_fans_ratio_pass_count': analysis.read_fans_ratio_pass_count,
                    'comment_gt_20_count': analysis.comment_gt_20_count,
                    'comment_gt_20_pass': analysis.comment_gt_20_pass,
                    'comment_max': analysis.comment_max,
                    'updated_at': datetime.now().isoformat()
                }
                
                self.supabase.table('gg_pgy_kol_analysis_result').upsert(
                    data,
                    on_conflict='kol_id,project_name'
                ).execute()
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"保存 KOL {kol_id} 失败: {e}")
                fail_count += 1
        
        return success_count, fail_count
    
    def generate_report(self, results: List[Tuple[str, str, FansRatioAnalysis]]) -> str:
        """生成分析报告"""
        if not results:
            return "没有分析结果"
        
        total = len(results)
        
        # 统计数据
        read_pass_count = sum(1 for _, _, a in results if a.read_fans_ratio_pass)
        comment_pass_count = sum(1 for _, _, a in results if a.comment_gt_20_pass)
        both_pass_count = sum(1 for _, _, a in results if a.read_fans_ratio_pass and a.comment_gt_20_pass)
        
        avg_ratio = statistics.mean([a.read_fans_ratio_avg for _, _, a in results])
        avg_comment_gt_20 = statistics.mean([a.comment_gt_20_count for _, _, a in results])
        max_comment = max([a.comment_max for _, _, a in results])
        
        # 按阅读/粉丝比例排序
        sorted_results = sorted(results, key=lambda x: x[2].read_fans_ratio_avg, reverse=True)
        
        report = f"""# KOL 粉丝vs数据比例分析报告

> **项目**: 枕头分析  
> **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> **KOL 数量**: {total}

---

## 一、整体概况

| 指标 | 数值 |
|------|------|
| 分析 KOL 总数 | {total} |
| 阅读>粉丝30%达标 | {read_pass_count} ({read_pass_count/total*100:.1f}%) |
| 评论>20条达标 | {comment_pass_count} ({comment_pass_count/total*100:.1f}%) |
| 双项达标 | {both_pass_count} ({both_pass_count/total*100:.1f}%) |
| 阅读/粉丝比例均值 | {avg_ratio:.1f}% |
| 评论>20条笔记均值 | {avg_comment_gt_20:.1f} 篇 |
| 最高单篇评论数 | {max_comment} 条 |

---

## 二、完整排名（按阅读/粉丝比例）

| 排名 | KOL名称 | 粉丝数 | 阅读/粉丝% | 达标笔记 | 评论>20 | 最高评论 | 阅读✓ | 评论✓ |
|------|---------|--------|------------|----------|---------|----------|-------|-------|
"""
        for i, (kol_id, kol_name, a) in enumerate(sorted_results, 1):
            read_icon = "✅" if a.read_fans_ratio_pass else "❌"
            comment_icon = "✅" if a.comment_gt_20_pass else "❌"
            report += f"| {i} | {kol_name} | {a.fans_count:,} | {a.read_fans_ratio_avg:.1f}% | {a.read_fans_ratio_pass_count} 篇 | {a.comment_gt_20_count} 篇 | {a.comment_max} 条 | {read_icon} | {comment_icon} |\n"
        
        report += f"""

---

## 三、判断标准说明

- **阅读达标**: 单篇阅读数 > 粉丝数的30%（非广告笔记）
- **评论达标**: 单篇评论数 > 20 条
- **阅读/粉丝%**: 所有非广告笔记的阅读/粉丝比例平均值
- **达标笔记**: 满足阅读>粉丝30%条件的笔记数量

---

*报告生成时间: {datetime.now().isoformat()}*
"""
        return report


def main():
    """主函数"""
    analyzer = FansRatioAnalyzer()
    
    logger.info("正在获取所有 KOL 列表...")
    kol_ids = analyzer.get_all_kol_ids_from_files()
    logger.info(f"找到 {len(kol_ids)} 个 KOL")
    
    if not kol_ids:
        logger.error("没有找到 KOL 数据")
        return
    
    logger.info("开始分析粉丝vs数据比例...")
    results = analyzer.analyze_batch(kol_ids)
    logger.info(f"分析完成，成功 {len(results)} 个")
    
    if not results:
        logger.error("没有成功的分析结果")
        return
    
    logger.info("保存结果到数据库...")
    success, fail = analyzer.save_to_db(results)
    logger.info(f"数据库保存完成: 成功 {success}, 失败 {fail}")
    
    logger.info("生成分析报告...")
    report = analyzer.generate_report(results)
    
    report_dir = Path(__file__).parent / "output"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"fans_ratio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"报告已保存: {report_file}")
    print(report)
    
    return results


if __name__ == "__main__":
    main()
