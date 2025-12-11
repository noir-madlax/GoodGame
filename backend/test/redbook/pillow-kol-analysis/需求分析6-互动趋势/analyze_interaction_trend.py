#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KOL 互动趋势分析脚本 - 需求6

需求说明：
- 数据趋势（粉丝/阅读/评论/互动）
- 使用 engage（互动=点赞+收藏+评论）作为趋势指标

数据来源：
- kol_core_data: 30天每日数据 (dailyData: imp, read, engage)

数据库字段：
- interaction_trend_status: 趋势状态 (rising/stable/declining)
- interaction_trend_detail: JSONB 趋势详情
- daily_imp_avg: 30天日均曝光
- daily_read_avg: 30天日均阅读
- daily_engage_avg: 30天日均互动
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
class InteractionTrendAnalysis:
    """互动趋势分析结果"""
    # 日均数据
    daily_imp_avg: float           # 30天日均曝光
    daily_read_avg: float          # 30天日均阅读
    daily_engage_avg: float        # 30天日均互动
    
    # 趋势状态
    interaction_trend_status: str  # rising/stable/declining
    
    # 趋势详情
    interaction_trend_detail: Dict[str, Any]


class InteractionTrendAnalyzer:
    """互动趋势分析器"""
    
    def __init__(self, data_dir: str = None):
        base_dir = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_dir / "output" / "api_data"
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
    
    def _calculate_trend(self, values: List[float]) -> Tuple[str, float]:
        """
        计算趋势状态
        
        使用简单线性回归斜率判断：
        - 斜率 > 5%均值：上升期
        - 斜率 < -5%均值：下降期
        - 其他：稳定期
        
        返回: (趋势状态, 斜率)
        """
        if not values or len(values) < 7:
            return 'stable', 0
        
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        # 计算斜率
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable', 0
        
        slope = numerator / denominator
        
        # 计算相对变化率
        if y_mean == 0:
            return 'stable', 0
        
        relative_change = slope * n / y_mean  # 30天总变化率
        
        # 判断趋势
        if relative_change > 0.15:  # 30天增长>15%
            return 'rising', round(slope, 2)
        elif relative_change < -0.15:  # 30天下降>15%
            return 'declining', round(slope, 2)
        else:
            return 'stable', round(slope, 2)
    
    def analyze_interaction_trend(self, kol_data: Dict[str, Any]) -> Optional[InteractionTrendAnalysis]:
        """
        分析互动趋势
        
        使用 kol_core_data.dailyData 中的 engage 数据
        """
        core_data_api = kol_data.get('apis', {}).get('kol_core_data', {})
        
        if core_data_api.get('code') != 0:
            logger.warning("kol_core_data 数据获取失败")
            return None
        
        data = core_data_api.get('data')
        if not data:
            logger.warning("kol_core_data data 为空")
            return None
        
        daily_data = data.get('dailyData', [])
        
        if not daily_data:
            logger.warning("dailyData 为空")
            return None
        
        # 提取数据
        imp_list = []
        read_list = []
        engage_list = []
        
        for day in daily_data:
            imp_list.append(day.get('imp', 0) or 0)
            read_list.append(day.get('read', 0) or 0)
            engage_list.append(day.get('engage', 0) or 0)
        
        # 计算日均值
        daily_imp_avg = round(statistics.mean(imp_list), 2) if imp_list else 0
        daily_read_avg = round(statistics.mean(read_list), 2) if read_list else 0
        daily_engage_avg = round(statistics.mean(engage_list), 2) if engage_list else 0
        
        # 计算互动趋势
        trend_status, slope = self._calculate_trend(engage_list)
        
        # 计算前后半月对比
        mid = len(engage_list) // 2
        first_half_avg = statistics.mean(engage_list[:mid]) if engage_list[:mid] else 0
        second_half_avg = statistics.mean(engage_list[mid:]) if engage_list[mid:] else 0
        
        change_rate = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        
        # 构建详情
        trend_detail = {
            'data_days': len(engage_list),
            'first_half_avg': round(first_half_avg, 2),
            'second_half_avg': round(second_half_avg, 2),
            'change_rate': round(change_rate, 2),
            'slope': slope,
            'daily_data': [
                {
                    'date': daily_data[i].get('dateKey', ''),
                    'imp': imp_list[i],
                    'read': read_list[i],
                    'engage': engage_list[i]
                }
                for i in range(min(30, len(daily_data)))  # 最多保存30天
            ]
        }
        
        return InteractionTrendAnalysis(
            daily_imp_avg=daily_imp_avg,
            daily_read_avg=daily_read_avg,
            daily_engage_avg=daily_engage_avg,
            interaction_trend_status=trend_status,
            interaction_trend_detail=trend_detail
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
    
    def analyze_batch(self, kol_ids: List[str]) -> List[Tuple[str, str, InteractionTrendAnalysis]]:
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
            analysis = self.analyze_interaction_trend(kol_data)
            
            if analysis:
                results.append((kol_id, kol_name, analysis))
            else:
                failed.append(kol_id)
        
        logger.info(f"分析完成: 成功 {len(results)}, 失败 {len(failed)}")
        return results
    
    def save_to_db(self, results: List[Tuple[str, str, InteractionTrendAnalysis]]) -> Tuple[int, int]:
        """保存分析结果到数据库"""
        success_count = 0
        fail_count = 0
        
        for kol_id, kol_name, analysis in results:
            try:
                data = {
                    'kol_id': kol_id,
                    'daily_imp_avg': analysis.daily_imp_avg,
                    'daily_read_avg': analysis.daily_read_avg,
                    'daily_engage_avg': analysis.daily_engage_avg,
                    'interaction_trend_status': analysis.interaction_trend_status,
                    'interaction_trend_detail': json.dumps(analysis.interaction_trend_detail, ensure_ascii=False),
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
    
    def generate_report(self, results: List[Tuple[str, str, InteractionTrendAnalysis]]) -> str:
        """生成分析报告"""
        if not results:
            return "没有分析结果"
        
        total = len(results)
        
        # 统计各趋势数量
        rising_count = sum(1 for _, _, a in results if a.interaction_trend_status == 'rising')
        stable_count = sum(1 for _, _, a in results if a.interaction_trend_status == 'stable')
        declining_count = sum(1 for _, _, a in results if a.interaction_trend_status == 'declining')
        
        avg_imp = statistics.mean([a.daily_imp_avg for _, _, a in results])
        avg_read = statistics.mean([a.daily_read_avg for _, _, a in results])
        avg_engage = statistics.mean([a.daily_engage_avg for _, _, a in results])
        
        # 按日均互动排序
        sorted_results = sorted(results, key=lambda x: x[2].daily_engage_avg, reverse=True)
        
        report = f"""# KOL 互动趋势分析报告

> **项目**: 枕头分析  
> **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> **KOL 数量**: {total}

---

## 一、整体概况

| 指标 | 数值 |
|------|------|
| 分析 KOL 总数 | {total} |
| 上升期 (rising) | {rising_count} ({rising_count/total*100:.1f}%) |
| 稳定期 (stable) | {stable_count} ({stable_count/total*100:.1f}%) |
| 下降期 (declining) | {declining_count} ({declining_count/total*100:.1f}%) |
| 平均日均曝光 | {avg_imp:,.0f} |
| 平均日均阅读 | {avg_read:,.0f} |
| 平均日均互动 | {avg_engage:,.0f} |

---

## 二、完整排名（按日均互动）

| 排名 | KOL名称 | 日均曝光 | 日均阅读 | 日均互动 | 趋势状态 |
|------|---------|----------|----------|----------|----------|
"""
        status_icons = {
            'rising': '📈 上升',
            'stable': '➡️ 稳定',
            'declining': '📉 下降'
        }
        
        for i, (kol_id, kol_name, a) in enumerate(sorted_results, 1):
            status_icon = status_icons.get(a.interaction_trend_status, '❓')
            report += f"| {i} | {kol_name} | {a.daily_imp_avg:,.0f} | {a.daily_read_avg:,.0f} | {a.daily_engage_avg:,.0f} | {status_icon} |\n"
        
        report += f"""

---

## 三、判断标准说明

- **趋势计算**: 基于30天日互动数据的线性回归斜率
- **上升期**: 30天互动增长 > 15%
- **下降期**: 30天互动下降 > 15%
- **稳定期**: 变化在±15%之内
- **日均互动**: engage（点赞+收藏+评论）的30天平均值

---

*报告生成时间: {datetime.now().isoformat()}*
"""
        return report


def main():
    """主函数"""
    analyzer = InteractionTrendAnalyzer()
    
    logger.info("正在获取所有 KOL 列表...")
    kol_ids = analyzer.get_all_kol_ids_from_files()
    logger.info(f"找到 {len(kol_ids)} 个 KOL")
    
    if not kol_ids:
        logger.error("没有找到 KOL 数据")
        return
    
    logger.info("开始分析互动趋势...")
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
    report_file = report_dir / f"interaction_trend_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"报告已保存: {report_file}")
    print(report)
    
    return results


if __name__ == "__main__":
    main()
