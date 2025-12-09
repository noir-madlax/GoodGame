#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单个 KOL 综合分析报告生成脚本

功能：
1. 从数据库读取分析结果
2. 生成 Markdown 格式的报告
3. 支持批量生成所有 KOL 报告
4. 生成增长排名报告
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class KolReportGenerator:
    """KOL 报告生成器"""
    
    def __init__(self, project_name: str = "枕头分析"):
        self.project_name = project_name
        self._init_supabase()
        self.output_dir = Path(__file__).parent / "output" / "kol_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_supabase(self):
        """初始化 Supabase 连接"""
        backend_dir = Path(__file__).parent.parent.parent.parent
        env_path = backend_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
        
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            raise ValueError("请在 .env 文件中配置 SUPABASE_URL 和 SUPABASE_KEY")
        
        self.supabase = create_client(url, key)
    
    def get_kol_data(self, kol_id: str) -> Optional[Dict[str, Any]]:
        """获取单个 KOL 的分析数据"""
        response = self.supabase.table('gg_pgy_kol_analysis_result').select('*').eq(
            'kol_id', kol_id
        ).eq('project_name', self.project_name).execute()
        
        if response.data:
            return response.data[0]
        return None
    
    def get_all_kols(self) -> List[Dict[str, Any]]:
        """获取所有 KOL 的分析数据"""
        response = self.supabase.table('gg_pgy_kol_analysis_result').select('*').eq(
            'project_name', self.project_name
        ).execute()
        
        return response.data or []
    
    def get_growth_rank(self, kol_id: str) -> tuple:
        """获取增长率排名"""
        response = self.supabase.table('gg_pgy_kol_analysis_result').select(
            'kol_id, fans_growth_rate_30d'
        ).eq('project_name', self.project_name).order(
            'fans_growth_rate_30d', desc=True
        ).execute()
        
        total = len(response.data)
        for i, row in enumerate(response.data, 1):
            if row['kol_id'] == kol_id:
                return i, total
        return None, total
    
    def _format_number(self, num: Any) -> str:
        """格式化数字"""
        if num is None:
            return "-"
        if isinstance(num, (int, float)):
            if abs(num) >= 1000:
                return f"{num:,.0f}"
            return str(num)
        return str(num)
    
    def _format_percent(self, num: Any) -> str:
        """格式化百分比"""
        if num is None:
            return "-"
        return f"{float(num):.2f}%"
    
    def _format_trend_status(self, status: str) -> str:
        """格式化趋势状态"""
        status_map = {
            'rising': '🟢 上升期',
            'stable': '🟡 稳定期',
            'declining': '🔴 下降期'
        }
        return status_map.get(status, status or '-')
    
    def _format_bool(self, val: bool) -> str:
        """格式化布尔值"""
        if val is None:
            return "-"
        return "✅ 达标" if val else "❌ 不达标"
    
    def generate_report(self, kol_data: Dict[str, Any]) -> str:
        """生成单个 KOL 的报告"""
        kol_id = kol_data.get('kol_id', 'Unknown')
        kol_name = kol_data.get('kol_name', 'Unknown')
        
        # 获取排名
        rank, total = self.get_growth_rank(kol_id)
        rank_str = f"{rank} / {total}" if rank else "-"
        
        # 解析 detail 数据
        fans_detail = {}
        if kol_data.get('fans_trend_detail'):
            try:
                fans_detail = json.loads(kol_data['fans_trend_detail']) if isinstance(
                    kol_data['fans_trend_detail'], str
                ) else kol_data['fans_trend_detail']
            except:
                pass
        
        post_detail = {}
        if kol_data.get('post_frequency_detail'):
            try:
                post_detail = json.loads(kol_data['post_frequency_detail']) if isinstance(
                    kol_data['post_frequency_detail'], str
                ) else kol_data['post_frequency_detail']
            except:
                pass
        
        hot_detail = {}
        if kol_data.get('hot_note_detail'):
            try:
                hot_detail = json.loads(kol_data['hot_note_detail']) if isinstance(
                    kol_data['hot_note_detail'], str
                ) else kol_data['hot_note_detail']
            except:
                pass
        
        report = f"""# KOL 综合分析报告

> **项目**: {self.project_name}  
> **KOL**: {kol_name}  
> **KOL ID**: {kol_id}  
> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 一、粉丝增长趋势

### 1.1 核心数据

| 指标 | 数值 |
|------|------|
| 当前粉丝数 | {self._format_number(kol_data.get('fans_count_current'))} |
| 30天前粉丝数 | {self._format_number(kol_data.get('fans_count_30d_ago'))} |
| 30天增长数 | +{self._format_number(kol_data.get('fans_growth_30d'))} |
| 30天增长率 | {self._format_percent(kol_data.get('fans_growth_rate_30d'))} |
| 趋势状态 | {self._format_trend_status(kol_data.get('fans_trend_status'))} |
| **增长排名** | **{rank_str}** |

### 1.2 增长稳定性

| 指标 | 数值 |
|------|------|
| 正增长天数 | {fans_detail.get('positive_days', '-')} 天 |
| 负增长天数 | {fans_detail.get('negative_days', '-')} 天 |
| 日均增长 | +{fans_detail.get('avg_daily_change', '-')} 粉丝 |
| 超越同行 | {fans_detail.get('beyond_rate', '-')}% |

---

## 二、发帖频率

### 2.1 核心数据

| 指标 | 数值 | 达标 |
|------|------|------|
| 30天发帖数 | {kol_data.get('post_count_30d', '-')} 篇 | - |
| 平均每周发帖 | {kol_data.get('post_avg_per_week', '-')} 篇 | {self._format_bool(kol_data.get('post_frequency_pass'))} |
| **近7天活跃天数** | **{kol_data.get('active_days_7d', '-')} 天** | - |

---

## 三、数据表现（阅读/点赞/评论）

### 3.1 中位数与平均值

| 指标 | 中位数 | 平均值 |
|------|--------|--------|
| 阅读数 | {self._format_number(kol_data.get('read_median'))} | {self._format_number(kol_data.get('read_avg'))} |
| 点赞数 | {self._format_number(kol_data.get('like_median'))} | {self._format_number(kol_data.get('like_avg'))} |
| 收藏数 | {self._format_number(kol_data.get('collect_median'))} | {self._format_number(kol_data.get('collect_avg'))} |
| 评论数 | {self._format_number(kol_data.get('comment_median'))} | {self._format_number(kol_data.get('comment_avg'))} |
| 互动数 | {self._format_number(kol_data.get('interaction_median'))} | {self._format_number(kol_data.get('interaction_avg'))} |

### 3.2 数据表现评估

| 评估项 | 结果 |
|--------|------|
| **阅读中位数超越同行** | **{self._format_percent(kol_data.get('read_beyond_rate'))}** |
| **互动中位数超越同行** | **{self._format_percent(kol_data.get('interaction_beyond_rate'))}** |

---

## 四、粉丝 vs 数据比例

### 4.1 阅读/粉丝比例

| 指标 | 数值 | 达标 |
|------|------|------|
| 阅读/粉丝平均比例 | {self._format_percent(kol_data.get('read_fans_ratio_avg'))} | {self._format_bool(kol_data.get('read_fans_ratio_pass'))} |
| 达标笔记数 | {kol_data.get('read_fans_ratio_pass_count', '-')} / **{kol_data.get('note_count_30d', '-')}** 篇 | - |

### 4.2 评论数判断

| 指标 | 数值 | 达标 |
|------|------|------|
| 评论>20条的笔记 | {kol_data.get('comment_gt_20_count', '-')} 篇 | {self._format_bool(kol_data.get('comment_gt_20_pass'))} |
| **评论最高笔记** | **{kol_data.get('comment_max', '-')} 条** | - |

---

## 五、爆文情况

### 5.1 爆文统计

| 指标 | 数值 | 达标 |
|------|------|------|
| 爆文阈值 | {self._format_number(kol_data.get('hot_note_threshold'))} (互动中位数×3) | - |
| 爆文数量 | {kol_data.get('hot_note_count', '-')} 篇 | {self._format_bool(kol_data.get('hot_note_pass'))} |

---

## 六、互动趋势

### 6.1 核心数据

| 指标 | 数值 |
|------|------|
| 互动趋势状态 | {self._format_trend_status(kol_data.get('interaction_trend_status'))} |
| **30天日均曝光** | **{self._format_number(kol_data.get('daily_imp_avg'))}** |
| **30天日均阅读** | **{self._format_number(kol_data.get('daily_read_avg'))}** |
| **30天日均互动** | **{self._format_number(kol_data.get('daily_engage_avg'))}** |

---

## 七、综合判断

### 7.1 各维度达标情况

| 维度 | 状态 | 备注 |
|------|------|------|
| 粉丝增长趋势 | {self._format_trend_status(kol_data.get('fans_trend_status'))} | 增长率 {self._format_percent(kol_data.get('fans_growth_rate_30d'))} |
| 发帖频率 (>3篇/周) | {self._format_bool(kol_data.get('post_frequency_pass'))} | {kol_data.get('post_avg_per_week', '-')} 篇/周 |
| 阅读/粉丝比例 (>30%) | {self._format_bool(kol_data.get('read_fans_ratio_pass'))} | {self._format_percent(kol_data.get('read_fans_ratio_avg'))} |
| 评论>20条 | {self._format_bool(kol_data.get('comment_gt_20_pass'))} | {kol_data.get('comment_gt_20_count', '-')} 篇 |
| 爆文数量 (>1篇) | {self._format_bool(kol_data.get('hot_note_pass'))} | {kol_data.get('hot_note_count', '-')} 篇 |
| 互动趋势 | {self._format_trend_status(kol_data.get('interaction_trend_status'))} | - |

### 7.2 分析备注

{kol_data.get('analysis_notes', '暂无备注')}

---

*数据来源: gg_pgy_kol_analysis_result*  
*分析时间: {kol_data.get('analysis_date', '-')}*
"""
        return report
    
    def save_report(self, kol_id: str, report: str) -> str:
        """保存报告到文件"""
        filename = f"kol_report_{kol_id[:8]}.md"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return str(filepath)
    
    def generate_single(self, kol_id: str) -> Optional[str]:
        """生成单个 KOL 报告"""
        kol_data = self.get_kol_data(kol_id)
        if not kol_data:
            logger.warning(f"未找到 KOL {kol_id} 的分析数据")
            return None
        
        report = self.generate_report(kol_data)
        filepath = self.save_report(kol_id, report)
        logger.info(f"报告已生成: {filepath}")
        return filepath
    
    def generate_all(self) -> List[str]:
        """生成所有 KOL 报告"""
        kols = self.get_all_kols()
        filepaths = []
        
        for kol_data in kols:
            report = self.generate_report(kol_data)
            filepath = self.save_report(kol_data['kol_id'], report)
            filepaths.append(filepath)
        
        logger.info(f"共生成 {len(filepaths)} 份报告")
        return filepaths
    
    def generate_growth_ranking(self) -> str:
        """生成增长率排名报告"""
        kols = self.get_all_kols()
        
        # 按增长率排序
        kols_sorted = sorted(
            kols, 
            key=lambda x: float(x.get('fans_growth_rate_30d') or 0), 
            reverse=True
        )
        
        report = f"""# KOL 粉丝增长率排名

> **项目**: {self.project_name}  
> **KOL 数量**: {len(kols)}  
> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 增长率排名

| 排名 | KOL名称 | 当前粉丝 | 30天增长 | 增长率 | 趋势状态 |
|------|---------|----------|----------|--------|----------|
"""
        for i, kol in enumerate(kols_sorted, 1):
            growth = kol.get('fans_growth_30d', 0) or 0
            growth_sign = '+' if growth >= 0 else ''
            report += f"| {i} | {kol.get('kol_name', '-')} | {self._format_number(kol.get('fans_count_current'))} | {growth_sign}{self._format_number(growth)} | {self._format_percent(kol.get('fans_growth_rate_30d'))} | {self._format_trend_status(kol.get('fans_trend_status'))} |\n"
        
        report += f"""

---

*生成时间: {datetime.now().isoformat()}*
"""
        
        # 保存排名报告
        filepath = self.output_dir / "growth_ranking.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"排名报告已生成: {filepath}")
        return report


def main():
    """主函数"""
    generator = KolReportGenerator()
    
    # 生成增长率排名
    print("=" * 60)
    print("生成增长率排名报告")
    print("=" * 60)
    ranking = generator.generate_growth_ranking()
    print(ranking)


if __name__ == "__main__":
    main()
