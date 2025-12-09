#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KOL 数据分析脚本 - 枕头项目

功能：
1. 分析粉丝增长趋势（需求1）
2. 将结果保存到数据库
3. 生成增长排名报告
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class FansTrendAnalysis:
    """粉丝趋势分析结果"""
    fans_count_current: int
    fans_count_30d_ago: int
    fans_growth_30d: int
    fans_growth_rate_30d: float
    fans_trend_status: str  # rising/stable/declining
    fans_trend_detail: Dict[str, Any]


@dataclass 
class KolAnalysisResult:
    """KOL 分析结果"""
    kol_id: str
    kol_name: str
    project_name: str = "枕头分析"
    
    # 需求1: 粉丝增长趋势
    fans_count_current: Optional[int] = None
    fans_count_30d_ago: Optional[int] = None
    fans_growth_30d: Optional[int] = None
    fans_growth_rate_30d: Optional[float] = None
    fans_trend_status: Optional[str] = None
    fans_trend_detail: Optional[Dict] = None
    
    # 分析元数据
    analysis_date: Optional[str] = None


class KolMetricsAnalyzer:
    """KOL 数据分析器"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "output" / "api_data"
        self.results: List[KolAnalysisResult] = []
        self._init_supabase()
    
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
        
        # 检查是否有实际数据（非 skipped）
        apis = data.get('apis', {})
        has_real_data = False
        for api_name, api_data in apis.items():
            if isinstance(api_data, dict) and api_data.get('code') == 0:
                has_real_data = True
                break
        
        if not has_real_data:
            logger.warning(f"KOL {kol_id} 没有有效的 API 数据")
            return None
        
        return data
    
    def analyze_fans_trend(self, kol_data: Dict[str, Any]) -> Optional[FansTrendAnalysis]:
        """
        分析需求1：粉丝增长趋势
        
        评估维度：
        1. 30天粉丝增长数和增长率
        2. 增长趋势稳定性（是否持续增长，有无大波动）
        3. 与同行对比的表现
        """
        fans_trend = kol_data.get('apis', {}).get('kol_fans_trend', {})
        fans_summary = kol_data.get('apis', {}).get('kol_fans_summary', {})
        
        if fans_trend.get('code') != 0:
            return None
        
        trend_data = fans_trend.get('data', {})
        trend_list = trend_data.get('list', [])
        
        if not trend_list or len(trend_list) < 7:
            logger.warning(f"粉丝趋势数据不足")
            return None
        
        # 基础数据
        fans_current = trend_list[-1]['num'] if trend_list else 0
        fans_30d_ago = trend_list[0]['num'] if trend_list else 0
        fans_growth = fans_current - fans_30d_ago
        fans_growth_rate = (fans_growth / fans_30d_ago * 100) if fans_30d_ago > 0 else 0
        
        # 计算趋势稳定性
        daily_changes = []
        for i in range(1, len(trend_list)):
            change = trend_list[i]['num'] - trend_list[i-1]['num']
            daily_changes.append(change)
        
        # 统计分析
        positive_days = sum(1 for c in daily_changes if c > 0)
        negative_days = sum(1 for c in daily_changes if c < 0)
        zero_days = sum(1 for c in daily_changes if c == 0)
        avg_daily_change = statistics.mean(daily_changes) if daily_changes else 0
        
        # 计算波动性（标准差/平均值）
        if daily_changes and avg_daily_change != 0:
            volatility = statistics.stdev(daily_changes) / abs(avg_daily_change) if len(daily_changes) > 1 else 0
        else:
            volatility = 0
        
        # 判断趋势状态
        if fans_growth_rate > 5:
            trend_status = "rising"
        elif fans_growth_rate < -2:
            trend_status = "declining"
        else:
            trend_status = "stable"
        
        # 获取同行对比数据
        summary_data = fans_summary.get('data', {}) if fans_summary.get('code') == 0 else {}
        beyond_rate = summary_data.get('fansGrowthBeyondRate', '')
        
        return FansTrendAnalysis(
            fans_count_current=fans_current,
            fans_count_30d_ago=fans_30d_ago,
            fans_growth_30d=fans_growth,
            fans_growth_rate_30d=round(fans_growth_rate, 4),
            fans_trend_status=trend_status,
            fans_trend_detail={
                'positive_days': positive_days,
                'negative_days': negative_days,
                'zero_days': zero_days,
                'avg_daily_change': round(avg_daily_change, 2),
                'volatility': round(volatility, 4),
                'beyond_rate': beyond_rate,
                'daily_data': [
                    {'date': item['dateKey'], 'fans': item['num']}
                    for item in trend_list
                ]
            }
        )
    
    def analyze_single_kol(self, kol_id: str) -> Optional[KolAnalysisResult]:
        """分析单个 KOL"""
        kol_data = self.load_kol_data(kol_id)
        if not kol_data:
            return None
        
        kol_name = kol_data.get('kol_name', 'Unknown')
        
        # 分析粉丝趋势
        fans_trend = self.analyze_fans_trend(kol_data)
        
        if not fans_trend:
            logger.warning(f"KOL {kol_id} 粉丝趋势分析失败")
            return None
        
        result = KolAnalysisResult(
            kol_id=kol_id,
            kol_name=kol_name,
            project_name="枕头分析",
            fans_count_current=fans_trend.fans_count_current,
            fans_count_30d_ago=fans_trend.fans_count_30d_ago,
            fans_growth_30d=fans_trend.fans_growth_30d,
            fans_growth_rate_30d=fans_trend.fans_growth_rate_30d,
            fans_trend_status=fans_trend.fans_trend_status,
            fans_trend_detail=fans_trend.fans_trend_detail,
            analysis_date=datetime.now().isoformat()
        )
        
        return result
    
    def get_all_kol_ids_from_files(self) -> List[str]:
        """从文件系统获取所有有实际数据的 KOL ID 列表"""
        kol_ids = []
        
        for kol_dir in sorted(self.data_dir.iterdir()):
            if not kol_dir.is_dir() or not kol_dir.name.startswith('kol_'):
                continue
            
            data_file = kol_dir / "all_data.json"
            if not data_file.exists():
                continue
            
            # 检查是否有实际数据
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            apis = data.get('apis', {})
            has_real_data = any(
                isinstance(api_data, dict) and api_data.get('code') == 0
                for api_data in apis.values()
            )
            
            if has_real_data:
                kol_id = kol_dir.name.replace('kol_', '')
                kol_ids.append(kol_id)
        
        return kol_ids
    
    def analyze_batch(self, kol_ids: List[str]) -> List[KolAnalysisResult]:
        """批量分析 KOL"""
        results = []
        failed = []
        
        for i, kol_id in enumerate(kol_ids):
            logger.info(f"分析进度: {i+1}/{len(kol_ids)} - KOL: {kol_id}")
            
            result = self.analyze_single_kol(kol_id)
            if result:
                results.append(result)
            else:
                failed.append(kol_id)
        
        logger.info(f"分析完成: 成功 {len(results)}, 失败 {len(failed)}")
        if failed:
            logger.info(f"失败的 KOL: {failed[:10]}{'...' if len(failed) > 10 else ''}")
        
        self.results = results
        return results
    
    def save_to_db(self, results: List[KolAnalysisResult]) -> Tuple[int, int]:
        """保存分析结果到数据库"""
        success_count = 0
        fail_count = 0
        
        for result in results:
            try:
                # 转换为字典
                data = {
                    'kol_id': result.kol_id,
                    'kol_name': result.kol_name,
                    'project_name': result.project_name,
                    'fans_count_current': result.fans_count_current,
                    'fans_count_30d_ago': result.fans_count_30d_ago,
                    'fans_growth_30d': result.fans_growth_30d,
                    'fans_growth_rate_30d': result.fans_growth_rate_30d,
                    'fans_trend_status': result.fans_trend_status,
                    'fans_trend_detail': json.dumps(result.fans_trend_detail) if result.fans_trend_detail else None,
                    'analysis_date': result.analysis_date,
                    'updated_at': datetime.now().isoformat()
                }
                
                # 使用 upsert 操作
                self.supabase.table('gg_pgy_kol_analysis_result').upsert(
                    data,
                    on_conflict='kol_id,project_name'
                ).execute()
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"保存 KOL {result.kol_id} 失败: {e}")
                fail_count += 1
        
        return success_count, fail_count
    
    def generate_growth_ranking_report(self, results: List[KolAnalysisResult]) -> str:
        """生成增长排名报告（无评分）"""
        if not results:
            return "没有分析结果"
        
        # 统计数据
        total = len(results)
        rising = sum(1 for r in results if r.fans_trend_status == 'rising')
        stable = sum(1 for r in results if r.fans_trend_status == 'stable')
        declining = sum(1 for r in results if r.fans_trend_status == 'declining')
        
        avg_growth_rate = statistics.mean([r.fans_growth_rate_30d for r in results if r.fans_growth_rate_30d is not None])
        
        # 按增长率排序
        sorted_by_growth = sorted(results, key=lambda x: x.fans_growth_rate_30d or 0, reverse=True)
        
        report = f"""# KOL 粉丝增长排名报告

> **项目**: 枕头分析  
> **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
> **KOL 数量**: {total}

---

## 一、整体概况

| 指标 | 数值 |
|------|------|
| 分析 KOL 总数 | {total} |
| 上升期 (>5%) | {rising} ({rising/total*100:.1f}%) |
| 稳定期 (-2%~5%) | {stable} ({stable/total*100:.1f}%) |
| 下降期 (<-2%) | {declining} ({declining/total*100:.1f}%) |
| 平均增长率 | {avg_growth_rate:.2f}% |

---

## 二、完整增长率排名

| 排名 | KOL名称 | 当前粉丝 | 30天增长 | 增长率 | 趋势状态 |
|------|---------|----------|----------|--------|----------|
"""
        for i, r in enumerate(sorted_by_growth, 1):
            growth_sign = '+' if r.fans_growth_30d >= 0 else ''
            status_emoji = {'rising': '🟢', 'stable': '🟡', 'declining': '🔴'}.get(r.fans_trend_status, '')
            report += f"| {i} | {r.kol_name} | {r.fans_count_current:,} | {growth_sign}{r.fans_growth_30d:,} | {r.fans_growth_rate_30d:.2f}% | {status_emoji} {r.fans_trend_status} |\n"
        
        report += f"""

---

## 三、趋势状态说明

- 🟢 **rising (上升期)**: 30天增长率 > 5%
- 🟡 **stable (稳定期)**: 30天增长率在 -2% ~ 5% 之间
- 🔴 **declining (下降期)**: 30天增长率 < -2%

---

*报告生成时间: {datetime.now().isoformat()}*
"""
        return report


def main():
    """主函数 - 处理全量 KOL"""
    analyzer = KolMetricsAnalyzer()
    
    # 获取所有有实际数据的 KOL ID
    logger.info("正在获取所有有效的 KOL 列表...")
    kol_ids = analyzer.get_all_kol_ids_from_files()
    logger.info(f"找到 {len(kol_ids)} 个有效的 KOL")
    
    if not kol_ids:
        logger.error("没有找到有效的 KOL 数据")
        return
    
    # 批量分析
    logger.info("开始批量分析...")
    results = analyzer.analyze_batch(kol_ids)
    logger.info(f"分析完成，成功 {len(results)} 个")
    
    if not results:
        logger.error("没有成功的分析结果")
        return
    
    # 保存到数据库
    logger.info("保存结果到数据库...")
    success, fail = analyzer.save_to_db(results)
    logger.info(f"数据库保存完成: 成功 {success}, 失败 {fail}")
    
    # 生成增长排名报告
    logger.info("生成增长排名报告...")
    report = analyzer.generate_growth_ranking_report(results)
    
    # 保存报告
    report_dir = Path(__file__).parent / "output" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"fans_growth_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"报告已保存: {report_file}")
    print(report)
    
    return results


if __name__ == "__main__":
    main()
