"""
Crunchbase公司数据分析脚本

分析gg_crunchbase_company表中的数据分布情况：
1. 按月份分布
2. 按行业分布
3. 按总部位置国家分布
4. 按融资类型分布
5. A轮公司单独分析
"""

import os
import sys
from collections import defaultdict, Counter
from typing import Dict, List, Any
import json

# 添加项目路径到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from supabase import create_client, Client

# Supabase配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def get_supabase_client() -> Client:
    """获取Supabase客户端"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("请设置SUPABASE_URL和SUPABASE_KEY环境变量")

    return create_client(SUPABASE_URL, SUPABASE_KEY)

def load_crunchbase_data() -> List[Dict[str, Any]]:
    """从数据库加载Crunchbase公司数据"""
    print("正在连接数据库...")
    supabase = get_supabase_client()

    print("正在查询数据...")
    response = supabase.table('gg_crunchbase_company').select('*').execute()

    return response.data

def extract_month_from_date(date_str: str) -> str:
    """从日期字符串中提取月份"""
    if not date_str:
        return "未知"

    try:
        # 格式如 "Feb 20, 2025"
        parts = date_str.split()
        if len(parts) >= 2:
            month = parts[0]
            # 标准化月份名称
            month_map = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            }
            return month_map.get(month, month)
    except:
        pass

    return "未知"

def extract_country_from_location(location_str: str) -> str:
    """从位置字符串中提取国家"""
    if not location_str:
        return "未知"

    try:
        # 格式如 "Paris, Ile-de-France, France"
        parts = location_str.split(',')
        if len(parts) >= 3:
            return parts[-1].strip()
        elif len(parts) == 2:
            # 可能是 "City, Country"
            return parts[-1].strip()
        elif len(parts) == 1:
            # 只有城市或国家
            return parts[0].strip()
    except:
        pass

    return "未知"

def flatten_industries(industries_json: List[str]) -> List[str]:
    """展开行业列表"""
    if not industries_json:
        return ["未知"]

    return industries_json if isinstance(industries_json, list) else ["未知"]

def analyze_monthly_distribution(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """按月份分析分布"""
    monthly_counts = defaultdict(int)

    for item in data:
        month = extract_month_from_date(item.get('last_funding_date', ''))
        monthly_counts[month] += 1

    # 排序月份
    sorted_months = sorted(monthly_counts.items(), key=lambda x: x[0])
    return dict(sorted_months)

def analyze_industry_distribution(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """按行业分析分布"""
    industry_counts = Counter()

    for item in data:
        industries = flatten_industries(item.get('industries', []))
        for industry in industries:
            industry_counts[industry] += 1

    # 返回前20个行业
    return dict(industry_counts.most_common(20))

def analyze_country_distribution(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """按国家分析分布"""
    country_counts = defaultdict(int)

    for item in data:
        country = extract_country_from_location(item.get('headquarters_location', ''))
        country_counts[country] += 1

    # 返回前20个国家
    sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_countries[:20])

def analyze_funding_type_distribution(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """按融资类型分析分布"""
    funding_counts = defaultdict(int)

    for item in data:
        funding_type = item.get('last_funding_type', '未知') or '未知'
        funding_counts[funding_type] += 1

    # 排序
    sorted_funding = sorted(funding_counts.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_funding)

def analyze_series_a_companies(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """单独分析A轮公司"""
    series_a_data = [item for item in data if item.get('last_funding_type') == 'Series A']

    return {
        'total_count': len(series_a_data),
        'monthly_distribution': analyze_monthly_distribution(series_a_data),
        'industry_distribution': analyze_industry_distribution(series_a_data),
        'country_distribution': analyze_country_distribution(series_a_data)
    }

def print_analysis_results(results: Dict[str, Any]):
    """打印分析结果"""
    print("\n" + "="*80)
    print("CRUNCHBASE 公司数据分析报告")
    print("="*80)

    print(f"\n总公司数量: {results['total_companies']}")

    print("\n📅 按月份分布:")
    for month, count in results['monthly_distribution'].items():
        print(f"  {month}: {count} 家")

    print("\n🏭 按行业分布 (Top 20):")
    for industry, count in results['industry_distribution'].items():
        print(f"  {industry}: {count} 家")

    print("\n🌍 按国家分布 (Top 20):")
    for country, count in results['country_distribution'].items():
        print(f"  {country}: {count} 家")

    print("\n💰 按融资类型分布:")
    for funding_type, count in results['funding_type_distribution'].items():
        print(f"  {funding_type}: {count} 家")

    print("\n" + "-"*80)
    print("🎯 A轮公司专项分析")
    print("-"*80)

    series_a = results['series_a_analysis']
    print(f"A轮公司总数: {series_a['total_count']} 家")

    print("\n📅 A轮公司按月份分布:")
    for month, count in series_a['monthly_distribution'].items():
        print(f"  {month}: {count} 家")

    print("\n🏭 A轮公司按行业分布 (Top 20):")
    for industry, count in series_a['industry_distribution'].items():
        print(f"  {industry}: {count} 家")

    print("\n🌍 A轮公司按国家分布 (Top 20):")
    for country, count in series_a['country_distribution'].items():
        print(f"  {country}: {count} 家")

def save_results_to_file(results: Dict[str, Any], filename: str = "crunchbase_analysis_results.json"):
    """保存结果到文件"""
    output_path = os.path.join(os.path.dirname(__file__), filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📁 分析结果已保存到: {output_path}")

def main():
    """主函数"""
    try:
        print("开始分析Crunchbase公司数据...")

        # 加载数据
        data = load_crunchbase_data()
        print(f"成功加载 {len(data)} 条公司数据")

        # 执行各项分析
        results = {
            'total_companies': len(data),
            'monthly_distribution': analyze_monthly_distribution(data),
            'industry_distribution': analyze_industry_distribution(data),
            'country_distribution': analyze_country_distribution(data),
            'funding_type_distribution': analyze_funding_type_distribution(data),
            'series_a_analysis': analyze_series_a_companies(data)
        }

        # 打印结果
        print_analysis_results(results)

        # 保存结果
        save_results_to_file(results)

        print("\n✅ 分析完成！")

    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
