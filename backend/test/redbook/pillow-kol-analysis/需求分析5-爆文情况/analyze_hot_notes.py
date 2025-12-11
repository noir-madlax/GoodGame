#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KOL 爆文情况分析脚本 - 需求5

需求说明：
- 数据波动性（月内不止一篇爆文）
- 爆文定义：互动数据超过中位数的 3 倍

数据来源：
- kol_note_rate: 互动中位数 (interactionMedian)
- kol_note_list / note_comments: 每篇笔记互动数据

数据库字段：
- hot_note_count: 爆文数量
- hot_note_pass: 是否达标（≥2篇爆文）
- hot_note_threshold: 爆文阈值（中位数×3）
- hot_note_detail: JSONB 爆文详情
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
class HotNoteAnalysis:
    """爆文情况分析结果"""
    interaction_median: int          # 互动中位数
    hot_note_threshold: int          # 爆文阈值（中位数×3）
    hot_note_count: int              # 爆文数量
    hot_note_pass: bool              # 是否达标（≥2篇）
    note_count_30d: int              # 30天内笔记数
    hot_note_detail: Dict[str, Any]  # 爆文详情


class HotNoteAnalyzer:
    """爆文情况分析器"""
    
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
    
    def analyze_hot_notes(self, kol_data: Dict[str, Any], comments_data: Optional[Dict[str, Any]]) -> Optional[HotNoteAnalysis]:
        """
        分析爆文情况
        
        爆文定义：互动数据 > 中位数 × 3
        达标标准：月内有 ≥2 篇爆文
        """
        note_rate_api = kol_data.get('apis', {}).get('kol_note_rate', {})
        
        # 获取互动中位数
        if note_rate_api.get('code') != 0:
            logger.warning("kol_note_rate 数据获取失败")
            return None
        
        rate_data = note_rate_api.get('data', {})
        interaction_median = rate_data.get('interactionMedian', 0) or 0
        
        if interaction_median == 0:
            logger.warning("互动中位数为0，跳过")
            return None
        
        # 计算爆文阈值
        hot_note_threshold = interaction_median * 3
        
        # 统计30天内笔记
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)
        
        hot_notes = []
        note_count_30d = 0
        
        # 优先使用评论数据（更完整的互动数据）
        if comments_data and comments_data.get('notes'):
            notes = comments_data.get('notes', [])
            
            for note in notes:
                note_date_str = note.get('create_date', '')
                note_date = self._parse_date(note_date_str)
                
                if note_date and note_date >= thirty_days_ago:
                    note_count_30d += 1
                    
                    # 计算互动数 = 点赞 + 收藏 + 评论
                    likes = note.get('likes', 0) or 0
                    collected = note.get('collected_count', 0) or 0
                    comments = note.get('comments_count', 0) or 0
                    interaction = likes + collected + comments
                    
                    if interaction > hot_note_threshold:
                        hot_notes.append({
                            'note_id': note.get('id', ''),
                            'title': note.get('title', '')[:30],
                            'interaction': interaction,
                            'likes': likes,
                            'collected': collected,
                            'comments': comments,
                            'date': note_date_str
                        })
        else:
            # 备选：使用 kol_note_list（没有评论数）
            note_list_api = kol_data.get('apis', {}).get('kol_note_list', {})
            
            if note_list_api.get('code') == 0:
                note_list = note_list_api.get('data', {}).get('list', [])
                
                for note in note_list:
                    note_date = self._parse_date(note.get('date', ''))
                    
                    if note_date and note_date >= thirty_days_ago:
                        note_count_30d += 1
                        
                        # 互动数 = 点赞 + 收藏（没有评论数）
                        likes = note.get('likeNum', 0) or 0
                        collected = note.get('collectNum', 0) or 0
                        interaction = likes + collected
                        
                        if interaction > hot_note_threshold:
                            hot_notes.append({
                                'note_id': note.get('noteId', ''),
                                'title': note.get('title', '')[:30],
                                'interaction': interaction,
                                'likes': likes,
                                'collected': collected,
                                'comments': 0,
                                'date': note.get('date', '')
                            })
        
        hot_note_count = len(hot_notes)
        hot_note_pass = hot_note_count >= 2  # 达标：≥2篇爆文
        
        # 按互动数排序
        hot_notes.sort(key=lambda x: x['interaction'], reverse=True)
        
        return HotNoteAnalysis(
            interaction_median=interaction_median,
            hot_note_threshold=int(hot_note_threshold),
            hot_note_count=hot_note_count,
            hot_note_pass=hot_note_pass,
            note_count_30d=note_count_30d,
            hot_note_detail={
                'threshold': int(hot_note_threshold),
                'hot_notes': hot_notes[:10]  # 只保留前10篇
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
    
    def analyze_batch(self, kol_ids: List[str]) -> List[Tuple[str, str, HotNoteAnalysis]]:
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
            
            analysis = self.analyze_hot_notes(kol_data, comments_data)
            
            if analysis:
                results.append((kol_id, kol_name, analysis))
            else:
                failed.append(kol_id)
        
        logger.info(f"分析完成: 成功 {len(results)}, 失败 {len(failed)}")
        return results
    
    def save_to_db(self, results: List[Tuple[str, str, HotNoteAnalysis]]) -> Tuple[int, int]:
        """保存分析结果到数据库"""
        success_count = 0
        fail_count = 0
        
        for kol_id, kol_name, analysis in results:
            try:
                data = {
                    'kol_id': kol_id,
                    'hot_note_count': analysis.hot_note_count,
                    'hot_note_pass': analysis.hot_note_pass,
                    'hot_note_threshold': analysis.hot_note_threshold,
                    'hot_note_detail': json.dumps(analysis.hot_note_detail, ensure_ascii=False),
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
    
    def generate_report(self, results: List[Tuple[str, str, HotNoteAnalysis]]) -> str:
        """生成分析报告"""
        if not results:
            return "没有分析结果"
        
        total = len(results)
        
        # 统计数据
        pass_count = sum(1 for _, _, a in results if a.hot_note_pass)
        total_hot_notes = sum(a.hot_note_count for _, _, a in results)
        avg_hot_notes = total_hot_notes / total if total > 0 else 0
        max_hot_notes = max(a.hot_note_count for _, _, a in results)
        
        # 按爆文数量排序
        sorted_results = sorted(results, key=lambda x: x[2].hot_note_count, reverse=True)
        
        report = f"""# KOL 爆文情况分析报告

> **项目**: 枕头分析  
> **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> **KOL 数量**: {total}

---

## 一、整体概况

| 指标 | 数值 |
|------|------|
| 分析 KOL 总数 | {total} |
| 达标 (≥2篇爆文) | {pass_count} ({pass_count/total*100:.1f}%) |
| 不达标 (<2篇爆文) | {total - pass_count} ({(total-pass_count)/total*100:.1f}%) |
| 爆文总数 | {total_hot_notes} 篇 |
| 平均爆文数 | {avg_hot_notes:.1f} 篇 |
| 最多爆文数 | {max_hot_notes} 篇 |

---

## 二、完整排名（按爆文数量）

| 排名 | KOL名称 | 互动中位 | 爆文阈值 | 爆文数 | 30天笔记 | 达标 |
|------|---------|----------|----------|--------|----------|------|
"""
        for i, (kol_id, kol_name, a) in enumerate(sorted_results, 1):
            pass_icon = "✅" if a.hot_note_pass else "❌"
            report += f"| {i} | {kol_name} | {a.interaction_median:,} | {a.hot_note_threshold:,} | {a.hot_note_count} 篇 | {a.note_count_30d} 篇 | {pass_icon} |\n"
        
        report += f"""

---

## 三、判断标准说明

- **爆文定义**: 互动数据（点赞+收藏+评论）> 互动中位数 × 3
- **达标标准**: 月内有 ≥2 篇爆文
- **爆文阈值**: 每个KOL的互动中位数 × 3
- **互动数据**: 优先使用原生接口数据（含评论），备选PGY接口（无评论）

---

*报告生成时间: {datetime.now().isoformat()}*
"""
        return report


def main():
    """主函数"""
    analyzer = HotNoteAnalyzer()
    
    logger.info("正在获取所有 KOL 列表...")
    kol_ids = analyzer.get_all_kol_ids_from_files()
    logger.info(f"找到 {len(kol_ids)} 个 KOL")
    
    if not kol_ids:
        logger.error("没有找到 KOL 数据")
        return
    
    logger.info("开始分析爆文情况...")
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
    report_file = report_dir / f"hot_notes_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"报告已保存: {report_file}")
    print(report)
    
    return results


if __name__ == "__main__":
    main()
