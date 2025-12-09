#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KOL 数据表现分析脚本 - 需求3

需求说明：
- 阅读、点赞、评论的平均值 & 中位数（过去一个月）

数据来源：
- kol_note_rate: 中位数 (readMedian, likeMedian, collectMedian, commentMedian, interactionMedian)
- kol_note_rate: 超越同行比例 (readMedianBeyondRate, interactionBeyondRate)
- kol_note_list: 阅读/点赞/收藏数据 (readNum, likeNum, collectNum)
- note_comments: 评论数据 (comments_count)

数据库字段：
- read_avg, read_median: 阅读平均/中位
- like_avg, like_median: 点赞平均/中位
- collect_avg, collect_median: 收藏平均/中位
- comment_avg, comment_median: 评论平均/中位
- interaction_avg, interaction_median: 互动平均/中位
- read_beyond_rate, interaction_beyond_rate: 超越同行比例
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import statistics
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DataPerformanceAnalysis:
    """数据表现分析结果"""
    # 阅读数据
    read_avg: float              # 阅读平均值
    read_median: int             # 阅读中位数
    read_beyond_rate: float      # 阅读超越同行比例
    
    # 点赞数据
    like_avg: float              # 点赞平均值
    like_median: int             # 点赞中位数
    
    # 收藏数据
    collect_avg: float           # 收藏平均值
    collect_median: int          # 收藏中位数
    
    # 评论数据
    comment_avg: float           # 评论平均值
    comment_median: int          # 评论中位数
    
    # 互动数据 (点赞+收藏+评论)
    interaction_avg: float       # 互动平均值
    interaction_median: int      # 互动中位数
    interaction_beyond_rate: float  # 互动超越同行比例


class DataPerformanceAnalyzer:
    """数据表现分析器"""
    
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
        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
            try:
                return datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
            except:
                continue
        return None
    
    def analyze_data_performance(self, kol_data: Dict[str, Any], comments_data: Optional[Dict[str, Any]]) -> Optional[DataPerformanceAnalysis]:
        """
        分析数据表现
        
        数据来源：
        1. 中位数：kol_note_rate API
        2. 阅读/点赞/收藏平均值：kol_note_list API (30天内笔记)
        3. 评论数据：note_comments 文件 (30天内笔记)
        4. 超越同行比例：kol_note_rate API
        """
        note_rate_api = kol_data.get('apis', {}).get('kol_note_rate', {})
        note_list_api = kol_data.get('apis', {}).get('kol_note_list', {})
        
        # 获取中位数和超越同行比例 (从 kol_note_rate)
        if note_rate_api.get('code') != 0:
            logger.warning("kol_note_rate 数据获取失败")
            return None
        
        rate_data = note_rate_api.get('data', {})
        
        # 中位数
        read_median = rate_data.get('readMedian', 0) or 0
        like_median = rate_data.get('likeMedian', 0) or 0
        collect_median = rate_data.get('collectMedian', 0) or 0
        comment_median = rate_data.get('commentMedian', 0) or 0
        interaction_median = rate_data.get('interactionMedian', 0) or 0
        
        # 超越同行比例
        read_beyond_rate = float(rate_data.get('readMedianBeyondRate', 0) or 0)
        interaction_beyond_rate = float(rate_data.get('interactionBeyondRate', 0) or 0)
        
        # 计算平均值 (从 kol_note_list, 30天内笔记)
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)
        
        read_nums = []
        like_nums = []
        collect_nums = []
        
        if note_list_api.get('code') == 0:
            note_list = note_list_api.get('data', {}).get('list', [])
            
            for note in note_list:
                note_date = self._parse_date(note.get('date', ''))
                if note_date and note_date >= thirty_days_ago:
                    read_nums.append(note.get('readNum', 0) or 0)
                    like_nums.append(note.get('likeNum', 0) or 0)
                    collect_nums.append(note.get('collectNum', 0) or 0)
        
        # 计算阅读/点赞/收藏平均值
        read_avg = round(statistics.mean(read_nums), 2) if read_nums else 0
        like_avg = round(statistics.mean(like_nums), 2) if like_nums else 0
        collect_avg = round(statistics.mean(collect_nums), 2) if collect_nums else 0
        
        # 计算评论平均值 (从评论数据文件, 30天内笔记)
        comment_nums = []
        if comments_data:
            notes = comments_data.get('notes', [])
            for note in notes:
                note_date_str = note.get('create_date', '')
                note_date = self._parse_date(note_date_str)
                if note_date and note_date >= thirty_days_ago:
                    comment_nums.append(note.get('comments_count', 0) or 0)
        
        comment_avg = round(statistics.mean(comment_nums), 2) if comment_nums else 0
        
        # 计算互动平均值 (点赞+收藏+评论)
        # 如果有评论数据，使用评论数据文件计算
        if comments_data and comments_data.get('notes'):
            interaction_nums = []
            notes = comments_data.get('notes', [])
            for note in notes:
                note_date_str = note.get('create_date', '')
                note_date = self._parse_date(note_date_str)
                if note_date and note_date >= thirty_days_ago:
                    likes = note.get('likes', 0) or 0
                    collected = note.get('collected_count', 0) or 0
                    comments = note.get('comments_count', 0) or 0
                    interaction_nums.append(likes + collected + comments)
            interaction_avg = round(statistics.mean(interaction_nums), 2) if interaction_nums else 0
        else:
            # 备选：使用 kol_note_list 的数据 (没有评论)
            interaction_avg = round(like_avg + collect_avg + comment_avg, 2)
        
        return DataPerformanceAnalysis(
            read_avg=read_avg,
            read_median=read_median,
            read_beyond_rate=read_beyond_rate,
            like_avg=like_avg,
            like_median=like_median,
            collect_avg=collect_avg,
            collect_median=collect_median,
            comment_avg=comment_avg,
            comment_median=comment_median,
            interaction_avg=interaction_avg,
            interaction_median=interaction_median,
            interaction_beyond_rate=interaction_beyond_rate
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
    
    def analyze_batch(self, kol_ids: List[str]) -> List[Tuple[str, str, DataPerformanceAnalysis]]:
        """批量分析 KOL 数据表现"""
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
            
            analysis = self.analyze_data_performance(kol_data, comments_data)
            
            if analysis:
                results.append((kol_id, kol_name, analysis))
            else:
                failed.append(kol_id)
        
        logger.info(f"分析完成: 成功 {len(results)}, 失败 {len(failed)}")
        return results
    
    def save_to_db(self, results: List[Tuple[str, str, DataPerformanceAnalysis]]) -> Tuple[int, int]:
        """保存分析结果到数据库"""
        success_count = 0
        fail_count = 0
        
        for kol_id, kol_name, analysis in results:
            try:
                data = {
                    'kol_id': kol_id,
                    'read_avg': analysis.read_avg,
                    'read_median': analysis.read_median,
                    'read_beyond_rate': analysis.read_beyond_rate,
                    'like_avg': analysis.like_avg,
                    'like_median': analysis.like_median,
                    'collect_avg': analysis.collect_avg,
                    'collect_median': analysis.collect_median,
                    'comment_avg': analysis.comment_avg,
                    'comment_median': analysis.comment_median,
                    'interaction_avg': analysis.interaction_avg,
                    'interaction_median': analysis.interaction_median,
                    'interaction_beyond_rate': analysis.interaction_beyond_rate,
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
    
    def generate_report(self, results: List[Tuple[str, str, DataPerformanceAnalysis]]) -> str:
        """生成数据表现分析报告"""
        if not results:
            return "没有分析结果"
        
        total = len(results)
        
        # 统计数据
        avg_read_avg = statistics.mean([a.read_avg for _, _, a in results])
        avg_read_median = statistics.mean([a.read_median for _, _, a in results])
        avg_like_avg = statistics.mean([a.like_avg for _, _, a in results])
        avg_comment_avg = statistics.mean([a.comment_avg for _, _, a in results])
        avg_interaction_avg = statistics.mean([a.interaction_avg for _, _, a in results])
        avg_read_beyond = statistics.mean([a.read_beyond_rate for _, _, a in results])
        avg_interaction_beyond = statistics.mean([a.interaction_beyond_rate for _, _, a in results])
        
        # 按互动平均值排序
        sorted_results = sorted(results, key=lambda x: x[2].interaction_avg, reverse=True)
        
        report = f"""# KOL 数据表现分析报告

> **项目**: 枕头分析  
> **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> **KOL 数量**: {total}

---

## 一、整体概况

| 指标 | 平均值 |
|------|--------|
| 阅读平均值 (均值) | {avg_read_avg:,.0f} |
| 阅读中位数 (均值) | {avg_read_median:,.0f} |
| 点赞平均值 (均值) | {avg_like_avg:,.0f} |
| 评论平均值 (均值) | {avg_comment_avg:,.1f} |
| 互动平均值 (均值) | {avg_interaction_avg:,.0f} |
| 阅读超越同行 (均值) | {avg_read_beyond:.1f}% |
| 互动超越同行 (均值) | {avg_interaction_beyond:.1f}% |

---

## 二、完整数据表现排名（按互动平均值）

| 排名 | KOL名称 | 阅读均值 | 阅读中位 | 点赞均值 | 评论均值 | 互动均值 | 阅读超越 | 互动超越 |
|------|---------|----------|----------|----------|----------|----------|----------|----------|
"""
        for i, (kol_id, kol_name, a) in enumerate(sorted_results, 1):
            report += f"| {i} | {kol_name} | {a.read_avg:,.0f} | {a.read_median:,} | {a.like_avg:,.0f} | {a.comment_avg:.1f} | {a.interaction_avg:,.0f} | {a.read_beyond_rate:.1f}% | {a.interaction_beyond_rate:.1f}% |\n"
        
        report += f"""

---

## 三、数据说明

- **阅读均值/中位**: 30天内笔记的阅读数统计
- **点赞均值**: 30天内笔记的点赞数平均值
- **评论均值**: 30天内笔记的评论数平均值（来自原生接口）
- **互动均值**: 点赞+收藏+评论的平均值
- **超越同行**: API 提供的超越同行比例

---

*报告生成时间: {datetime.now().isoformat()}*
"""
        return report


def main():
    """主函数"""
    analyzer = DataPerformanceAnalyzer()
    
    logger.info("正在获取所有 KOL 列表...")
    kol_ids = analyzer.get_all_kol_ids_from_files()
    logger.info(f"找到 {len(kol_ids)} 个 KOL")
    
    if not kol_ids:
        logger.error("没有找到 KOL 数据")
        return
    
    logger.info("开始分析数据表现...")
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
    report_file = report_dir / f"data_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"报告已保存: {report_file}")
    print(report)
    
    return results


if __name__ == "__main__":
    main()
