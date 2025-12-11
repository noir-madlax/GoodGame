#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段5: 数据分析

功能：
1. 读取阶段2和阶段4的数据
2. 执行6个维度分析:
   - 粉丝增长趋势
   - 发帖频率
   - 数据表现（阅读/点赞/评论）
   - 粉丝vs数据比例
   - 爆文情况
   - 互动趋势
3. 生成综合分析报告
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class KolAnalysisResult:
    """KOL分析结果"""
    kol_id: str
    kol_name: str
    
    # 基础数据
    fans_count: int = 0
    total_note_count: int = 0
    
    # 1. 粉丝增长趋势
    fans_count_current: int = 0
    fans_count_30d_ago: int = 0
    fans_growth_30d: int = 0
    fans_growth_rate_30d: float = 0.0
    fans_trend_status: str = ""  # rising/stable/declining
    positive_growth_days: int = 0
    negative_growth_days: int = 0
    
    # 2. 发帖频率
    post_count_30d: int = 0
    post_avg_per_week: float = 0.0
    active_days_7d: int = 0
    post_frequency_pass: bool = False  # 是否达标(>3篇/周)
    
    # 3. 数据表现
    read_median: int = 0
    read_avg: int = 0
    like_median: int = 0
    like_avg: int = 0
    collect_median: int = 0
    collect_avg: int = 0
    comment_median: int = 0
    comment_avg: int = 0
    interaction_median: int = 0
    interaction_avg: int = 0
    read_beyond_rate: float = 0.0
    interaction_beyond_rate: float = 0.0
    
    # 4. 粉丝vs数据比例
    read_fans_ratio_avg: float = 0.0
    read_fans_ratio_pass: bool = False  # >30%
    read_fans_ratio_pass_count: int = 0
    comment_gt_20_count: int = 0
    comment_gt_20_pass: bool = False
    comment_max: int = 0
    
    # 5. 爆文情况
    hot_note_threshold: int = 0
    hot_note_count: int = 0
    hot_note_pass: bool = False  # >1篇
    
    # 6. 互动趋势
    interaction_trend_status: str = ""
    daily_imp_avg: int = 0
    daily_read_avg: int = 0
    daily_engage_avg: int = 0
    
    # 综合评估
    overall_score: float = 0.0
    overall_rank: int = 0
    recommendation: str = ""
    notes: List[str] = field(default_factory=list)


class KolDataAnalyzer:
    """KOL数据分析器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent / "01_KOL数据获取"
        self.screening_dir = self.base_dir / "01_基础筛选数据"
        self.detail_dir = self.base_dir / "02_详细数据"
        self.output_dir = Path(__file__).parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载汇总数据
        self.all_data_file = self.detail_dir / "_all_kol_data.json"
        self.all_data = self._load_all_data()
        
        # 分析结果
        self.results: List[KolAnalysisResult] = []
    
    def _load_all_data(self) -> Dict[str, Any]:
        """加载汇总数据"""
        if not self.all_data_file.exists():
            raise FileNotFoundError(f"汇总数据文件不存在: {self.all_data_file}")
        
        with open(self.all_data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_api_data(self, kol_data: Dict, api_name: str, source: str = 'both') -> Optional[Dict]:
        """获取API数据"""
        # 先从screening_data找
        if source in ['both', 'screening']:
            screening = kol_data.get('screening_data', {}).get(api_name, {})
            result = screening.get('result', {})
            if result.get('code') == 0:
                return result.get('data', {})
        
        # 再从detail_data找
        if source in ['both', 'detail']:
            detail = kol_data.get('detail_data', {}).get(api_name, {})
            result = detail.get('result', {})
            if result.get('code') == 0:
                return result.get('data', {})
        
        return None
    
    def analyze_kol(self, kol_data: Dict) -> KolAnalysisResult:
        """分析单个KOL"""
        kol_id = kol_data['kol_id']
        kol_name = kol_data['kol_name']
        
        result = KolAnalysisResult(kol_id=kol_id, kol_name=kol_name)
        
        # 获取各API数据
        kol_info = self._get_api_data(kol_data, 'kol_info')
        note_rate = self._get_api_data(kol_data, 'kol_note_rate')
        fans_trend = self._get_api_data(kol_data, 'kol_fans_trend')
        fans_summary = self._get_api_data(kol_data, 'kol_fans_summary')
        note_list = self._get_api_data(kol_data, 'kol_note_list')
        core_data = self._get_api_data(kol_data, 'kol_core_data')
        data_summary_v1 = self._get_api_data(kol_data, 'kol_data_summary_v1')
        
        # 基础数据
        if kol_info:
            result.fans_count = kol_info.get('fansCount', 0) or 0
            result.total_note_count = kol_info.get('totalNoteCount', 0) or 0
            result.fans_count_current = result.fans_count
        
        # 1. 粉丝增长趋势分析
        if fans_trend:
            trend_list = fans_trend.get('list', []) or []
            if len(trend_list) >= 2:
                result.fans_count_30d_ago = trend_list[0].get('num', 0) or 0
                result.fans_count_current = trend_list[-1].get('num', 0) or result.fans_count
                result.fans_growth_30d = result.fans_count_current - result.fans_count_30d_ago
                
                if result.fans_count_30d_ago > 0:
                    result.fans_growth_rate_30d = round(
                        (result.fans_growth_30d / result.fans_count_30d_ago) * 100, 2
                    )
                
                # 计算正负增长天数
                positive = 0
                negative = 0
                for i in range(1, len(trend_list)):
                    diff = (trend_list[i].get('num', 0) or 0) - (trend_list[i-1].get('num', 0) or 0)
                    if diff > 0:
                        positive += 1
                    elif diff < 0:
                        negative += 1
                result.positive_growth_days = positive
                result.negative_growth_days = negative
                
                # 判断趋势状态
                if result.fans_growth_rate_30d > 5:
                    result.fans_trend_status = 'rising'
                elif result.fans_growth_rate_30d < -5:
                    result.fans_trend_status = 'declining'
                else:
                    result.fans_trend_status = 'stable'
        
        # 2. 发帖频率分析
        if note_rate:
            result.post_count_30d = note_rate.get('noteNumber', 0) or 0
            result.post_avg_per_week = round(result.post_count_30d / 4.3, 1)
            result.post_frequency_pass = result.post_avg_per_week >= 3
        
        if data_summary_v1:
            result.active_days_7d = data_summary_v1.get('activeDayInLast7', 0) or 0
        
        # 3. 数据表现分析
        if note_rate:
            result.read_median = note_rate.get('readMedian', 0) or 0
            result.interaction_median = note_rate.get('interactionMedian', 0) or 0
            result.like_median = note_rate.get('likeMedian', 0) or 0
            result.collect_median = note_rate.get('collectMedian', 0) or 0
            result.comment_median = note_rate.get('commentMedian', 0) or 0
            
            try:
                result.read_beyond_rate = float(note_rate.get('readMedianBeyondRate', 0) or 0)
            except (ValueError, TypeError):
                result.read_beyond_rate = 0.0
            try:
                result.interaction_beyond_rate = float(note_rate.get('interactionBeyondRate', 0) or 0)
            except (ValueError, TypeError):
                result.interaction_beyond_rate = 0.0
        
        # 从笔记列表计算平均值和评论>20的数量
        if note_list:
            notes = note_list.get('list', []) or []
            if notes:
                reads = [n.get('readNum', 0) or 0 for n in notes]
                likes = [n.get('likeNum', 0) or 0 for n in notes]
                collects = [n.get('collectNum', 0) or 0 for n in notes]
                
                result.read_avg = int(sum(reads) / len(reads)) if reads else 0
                result.like_avg = int(sum(likes) / len(likes)) if likes else 0
                result.collect_avg = int(sum(collects) / len(collects)) if collects else 0
                result.interaction_avg = result.like_avg + result.collect_avg
        
        # 4. 粉丝vs数据比例
        if note_list and result.fans_count > 0:
            notes = note_list.get('list', []) or []
            pass_count = 0
            comment_gt_20 = 0
            max_comment = 0
            ratios = []
            
            for note in notes:
                read = note.get('readNum', 0) or 0
                ratio = (read / result.fans_count) * 100 if result.fans_count > 0 else 0
                ratios.append(ratio)
                if ratio >= 30:
                    pass_count += 1
                
                # 评论数（从third_read_user_num估算，或直接使用）
                comment = note.get('commentNum', 0) or 0
                if comment > 20:
                    comment_gt_20 += 1
                if comment > max_comment:
                    max_comment = comment
            
            result.read_fans_ratio_avg = round(sum(ratios) / len(ratios), 1) if ratios else 0
            result.read_fans_ratio_pass = result.read_fans_ratio_avg >= 30
            result.read_fans_ratio_pass_count = pass_count
            result.comment_gt_20_count = comment_gt_20
            result.comment_gt_20_pass = comment_gt_20 >= 1
            result.comment_max = max_comment
        
        # 5. 爆文情况
        if result.interaction_median > 0:
            result.hot_note_threshold = result.interaction_median * 3
            
            if note_list:
                notes = note_list.get('list', []) or []
                hot_count = 0
                for note in notes:
                    interact = (note.get('likeNum', 0) or 0) + (note.get('collectNum', 0) or 0)
                    if interact >= result.hot_note_threshold:
                        hot_count += 1
                result.hot_note_count = hot_count
                result.hot_note_pass = hot_count >= 2
        
        # 6. 互动趋势
        if core_data:
            daily_data = core_data.get('dailyData', []) or []
            if daily_data:
                imps = [d.get('imp', 0) or 0 for d in daily_data]
                reads = [d.get('read', 0) or 0 for d in daily_data]
                engages = [d.get('engage', 0) or 0 for d in daily_data]
                
                result.daily_imp_avg = int(sum(imps) / len(imps)) if imps else 0
                result.daily_read_avg = int(sum(reads) / len(reads)) if reads else 0
                result.daily_engage_avg = int(sum(engages) / len(engages)) if engages else 0
                
                # 判断趋势（比较前后半段）
                if len(engages) >= 10:
                    first_half = sum(engages[:len(engages)//2])
                    second_half = sum(engages[len(engages)//2:])
                    if second_half > first_half * 1.1:
                        result.interaction_trend_status = 'rising'
                    elif second_half < first_half * 0.9:
                        result.interaction_trend_status = 'declining'
                    else:
                        result.interaction_trend_status = 'stable'
        
        # 综合评分
        score = 0
        
        # 粉丝增长 (20分)
        if result.fans_trend_status == 'rising':
            score += 20
        elif result.fans_trend_status == 'stable':
            score += 10
        
        # 发帖频率 (15分)
        if result.post_frequency_pass:
            score += 15
        elif result.post_avg_per_week >= 2:
            score += 10
        
        # 数据表现 (25分)
        if result.read_median >= 5000:
            score += 25
        elif result.read_median >= 1000:
            score += 20
        elif result.read_median >= 500:
            score += 15
        elif result.read_median >= 100:
            score += 10
        
        # 粉丝vs数据 (20分)
        if result.read_fans_ratio_pass:
            score += 15
        if result.comment_gt_20_pass:
            score += 5
        
        # 爆文 (10分)
        if result.hot_note_pass:
            score += 10
        elif result.hot_note_count >= 1:
            score += 5
        
        # 互动趋势 (10分)
        if result.interaction_trend_status == 'rising':
            score += 10
        elif result.interaction_trend_status == 'stable':
            score += 5
        
        result.overall_score = score
        
        # 推荐级别
        if score >= 80:
            result.recommendation = "强烈推荐"
        elif score >= 60:
            result.recommendation = "推荐"
        elif score >= 40:
            result.recommendation = "可考虑"
        else:
            result.recommendation = "不推荐"
        
        # 备注
        if result.post_count_30d == 0:
            result.notes.append("近30天无发帖")
        if result.post_count_30d < 3:
            result.notes.append("发帖频率过低")
        if result.fans_trend_status == 'declining':
            result.notes.append("粉丝持续下跌")
        if result.read_median < 100:
            result.notes.append("阅读数据较弱")
        
        return result
    
    def analyze_all(self):
        """分析所有KOL"""
        logger.info("=" * 60)
        logger.info("🔍 阶段5: 数据分析")
        logger.info("=" * 60)
        
        kols = self.all_data.get('kols', [])
        logger.info(f"待分析KOL数: {len(kols)}")
        
        for kol_data in kols:
            result = self.analyze_kol(kol_data)
            self.results.append(result)
            logger.info(f"  ✅ {result.kol_name}: 综合评分 {result.overall_score}")
        
        # 排名
        self.results.sort(key=lambda x: x.overall_score, reverse=True)
        for i, r in enumerate(self.results, 1):
            r.overall_rank = i
        
        self._save_results()
        self._generate_report()
    
    def _save_results(self):
        """保存分析结果"""
        results_data = {
            "generated_at": datetime.now().isoformat(),
            "total_kols": len(self.results),
            "results": [asdict(r) for r in self.results]
        }
        
        output_file = self.output_dir / "analysis_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📊 分析结果已保存: {output_file}")
    
    def _generate_report(self):
        """生成分析报告"""
        report = f"""# 能量棒KOL综合分析报告

> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> **分析KOL数**: {len(self.results)}

---

## 一、综合排名

| 排名 | KOL名称 | 综合评分 | 推荐级别 | 粉丝数 | 阅读中位数 | 发帖/周 | 备注 |
|------|---------|----------|----------|--------|------------|---------|------|
"""
        for r in self.results:
            notes_str = "; ".join(r.notes) if r.notes else "-"
            report += f"| {r.overall_rank} | {r.kol_name} | {r.overall_score} | {r.recommendation} | {r.fans_count:,} | {r.read_median:,} | {r.post_avg_per_week} | {notes_str} |\n"
        
        report += f"""

---

## 二、各维度详细分析

### 2.1 粉丝增长趋势

| KOL | 当前粉丝 | 30天前 | 增长数 | 增长率 | 趋势 |
|-----|----------|--------|--------|--------|------|
"""
        for r in self.results:
            trend_icon = "🟢" if r.fans_trend_status == 'rising' else ("🟡" if r.fans_trend_status == 'stable' else "🔴")
            report += f"| {r.kol_name} | {r.fans_count_current:,} | {r.fans_count_30d_ago:,} | {r.fans_growth_30d:+,} | {r.fans_growth_rate_30d:+.1f}% | {trend_icon} {r.fans_trend_status} |\n"
        
        report += f"""

### 2.2 发帖频率

| KOL | 30天发帖 | 平均/周 | 达标 | 7天活跃 |
|-----|----------|---------|------|---------|
"""
        for r in self.results:
            pass_icon = "✅" if r.post_frequency_pass else "❌"
            report += f"| {r.kol_name} | {r.post_count_30d} | {r.post_avg_per_week} | {pass_icon} | {r.active_days_7d}天 |\n"
        
        report += f"""

### 2.3 数据表现

| KOL | 阅读中位数 | 互动中位数 | 点赞中位数 | 收藏中位数 | 超越同行 |
|-----|------------|------------|------------|------------|----------|
"""
        for r in self.results:
            report += f"| {r.kol_name} | {r.read_median:,} | {r.interaction_median:,} | {r.like_median:,} | {r.collect_median:,} | {r.read_beyond_rate:.0f}% |\n"
        
        report += f"""

### 2.4 粉丝vs数据比例

| KOL | 阅读/粉丝比 | 达标 | 评论>20篇数 | 最高评论 |
|-----|-------------|------|-------------|----------|
"""
        for r in self.results:
            ratio_icon = "✅" if r.read_fans_ratio_pass else "❌"
            comment_icon = "✅" if r.comment_gt_20_pass else "❌"
            report += f"| {r.kol_name} | {r.read_fans_ratio_avg:.1f}% | {ratio_icon} | {r.comment_gt_20_count} {comment_icon} | {r.comment_max} |\n"
        
        report += f"""

### 2.5 爆文情况

| KOL | 爆文阈值 | 爆文数 | 达标 |
|-----|----------|--------|------|
"""
        for r in self.results:
            pass_icon = "✅" if r.hot_note_pass else "❌"
            report += f"| {r.kol_name} | {r.hot_note_threshold:,} | {r.hot_note_count} | {pass_icon} |\n"
        
        report += f"""

### 2.6 互动趋势

| KOL | 日均曝光 | 日均阅读 | 日均互动 | 趋势 |
|-----|----------|----------|----------|------|
"""
        for r in self.results:
            trend_icon = "🟢" if r.interaction_trend_status == 'rising' else ("🟡" if r.interaction_trend_status == 'stable' else ("🔴" if r.interaction_trend_status == 'declining' else "-"))
            report += f"| {r.kol_name} | {r.daily_imp_avg:,} | {r.daily_read_avg:,} | {r.daily_engage_avg:,} | {trend_icon} |\n"
        
        report += f"""

---

## 三、推荐结论

### 3.1 强烈推荐 ⭐⭐⭐

"""
        strong = [r for r in self.results if r.recommendation == "强烈推荐"]
        if strong:
            for r in strong:
                report += f"- **{r.kol_name}** (评分{r.overall_score}): 粉丝{r.fans_count:,}，阅读中位数{r.read_median:,}\n"
        else:
            report += "无\n"
        
        report += f"""

### 3.2 推荐 ⭐⭐

"""
        recommend = [r for r in self.results if r.recommendation == "推荐"]
        if recommend:
            for r in recommend:
                report += f"- **{r.kol_name}** (评分{r.overall_score}): 粉丝{r.fans_count:,}，阅读中位数{r.read_median:,}\n"
        else:
            report += "无\n"
        
        report += f"""

### 3.3 可考虑 ⭐

"""
        consider = [r for r in self.results if r.recommendation == "可考虑"]
        if consider:
            for r in consider:
                notes_str = f" ({'; '.join(r.notes)})" if r.notes else ""
                report += f"- **{r.kol_name}** (评分{r.overall_score}){notes_str}\n"
        else:
            report += "无\n"
        
        report += f"""

### 3.4 不推荐

"""
        not_recommend = [r for r in self.results if r.recommendation == "不推荐"]
        if not_recommend:
            for r in not_recommend:
                notes_str = f" ({'; '.join(r.notes)})" if r.notes else ""
                report += f"- **{r.kol_name}** (评分{r.overall_score}){notes_str}\n"
        else:
            report += "无\n"
        
        report += f"""

---

## 四、评分标准说明

| 维度 | 满分 | 评分标准 |
|------|------|----------|
| 粉丝增长 | 20分 | rising=20, stable=10 |
| 发帖频率 | 15分 | ≥3篇/周=15, ≥2篇/周=10 |
| 数据表现 | 25分 | 阅读中位数≥5000=25, ≥1000=20, ≥500=15, ≥100=10 |
| 粉丝vs数据 | 20分 | 阅读/粉丝≥30%=15, 评论>20条=5 |
| 爆文情况 | 10分 | ≥2篇=10, ≥1篇=5 |
| 互动趋势 | 10分 | rising=10, stable=5 |

---

*报告生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        report_file = self.output_dir / "综合分析报告.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📄 分析报告已保存: {report_file}")
        
        # 打印简要汇总
        logger.info("")
        logger.info("=" * 60)
        logger.info("📋 分析结果汇总")
        logger.info("=" * 60)
        logger.info(f"{'排名':<4} {'KOL名称':<15} {'评分':<6} {'推荐级别':<10}")
        logger.info("-" * 50)
        for r in self.results:
            logger.info(f"{r.overall_rank:<4} {r.kol_name:<15} {r.overall_score:<6} {r.recommendation:<10}")


def main():
    """主函数"""
    analyzer = KolDataAnalyzer()
    analyzer.analyze_all()


if __name__ == "__main__":
    main()
