"""
高优先级公司产品业务信息查询脚本 - Bocha API版本
功能：对指定的5家高优先级公司进行产品、业务、客户等方面的搜索
重点：产品介绍、客户痛点、应用场景、行业方向、客户名称等业务信息
API参数：freshness=oneYear, summary=true, count=20
"""

import os
import json
import re
import time
import requests
from typing import Optional, List, Dict
from dotenv import load_dotenv

# ==========================================
# 环境配置
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
# 路径: backend/test/bocha-api/code/ -> backend/
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
env_path = os.path.join(backend_dir, ".env")
load_dotenv(env_path)

BOCHA_API_KEY = os.getenv("BOCHA_API_KEY")
ENDPOINT_URL = "https://api.bochaai.com/v1/web-search"

if not BOCHA_API_KEY:
    raise ValueError("Missing BOCHA_API_KEY environment variable")

# 输出目录 - 使用新的子目录
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(current_dir), "output", "china-company-business")
os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

# ==========================================
# Bocha API 配置参数
# ==========================================
FRESHNESS = "oneYear"  # 一年内的数据
SUMMARY = True         # 显示文本摘要
COUNT = 20             # 返回20条结果

# ==========================================
# 高优先级公司列表 - 使用中文名称
# ==========================================
HIGH_PRIORITY_COMPANIES = [
    {
        "name_cn": "曼孚科技",
        "name_en": "Mindflow",
        "location": "杭州",
        "industry": "AI数据标注、大数据服务",
        "description": "AI数据标注和大数据全链路服务公司"
    },
    {
        "name_cn": "奇臻商城",
        "name_en": "Qizhen Mall",
        "location": "北京通州",
        "industry": "AI电商、机器学习",
        "description": "AI驱动的电子商务解决方案企业"
    },
    {
        "name_cn": "快牛智营",
        "name_en": "QuickCEP",
        "location": "北京",
        "industry": "跨境电商SaaS、营销自动化",
        "description": "跨境独立站SaaS营销平台"
    },
    {
        "name_cn": "新晨互动娱乐",
        "name_en": "Xinchen Interactive Entertainment",
        "location": "厦门",
        "industry": "数字媒体、电商、社交媒体",
        "description": "数字媒体和电商社交解决方案企业"
    },
    {
        "name_cn": "优阅达数据科技",
        "name_en": "Yiwen Data Technology",
        "location": "深圳",
        "industry": "AI数据平台、企业数据治理",
        "description": "企业级AI数据知识平台提供商"
    }
]

def create_business_query(company: Dict) -> str:
    """为公司创建业务导向的查询 - 聚焦产品和业务信息，全中文"""
    query = f"""{company['name_cn']} 公司产品介绍 客户案例 应用场景 服务行业 商业模式 {company['location']}"""
    return query

def search_company_business_bocha(company: Dict) -> Optional[Dict]:
    """使用Bocha API搜索公司业务信息"""
    try:
        # 创建文件夹 - 使用中文名称
        safe_name = re.sub(r'[^\w\-_\.]', '_', company['name_cn'])
        company_dir = os.path.join(OUTPUT_BASE_DIR, safe_name)
        os.makedirs(company_dir, exist_ok=True)

        # 构建查询
        query = create_business_query(company)
        print(f"正在通过Bocha搜索 {company['name_cn']}（{company['name_en']}）的业务信息...")

        # 准备请求头和载荷
        headers = {
            "Authorization": f"Bearer {BOCHA_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "query": query,
            "freshness": FRESHNESS,
            "summary": SUMMARY,
            "count": COUNT
        }

        print(f"  查询: {query}")
        print(f"  参数: freshness={FRESHNESS}, summary={SUMMARY}, count={COUNT}")

        # 发送请求
        response = requests.post(ENDPOINT_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # 保存原始响应
        raw_file = os.path.join(company_dir, "bocha_raw_response.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 提取结果数量
        result_count = 0
        if "data" in data and "webPages" in data["data"]:
            value = data["data"]["webPages"].get("value", [])
            result_count = len(value)
        elif "webPages" in data:
            value = data["webPages"].get("value", [])
            result_count = len(value)

        # 格式化并保存响应
        formatted_data = {
            "company_name_cn": company['name_cn'],
            "company_name_en": company['name_en'],
            "location": company['location'],
            "industry": company['industry'],
            "query": query,
            "search_params": {
                "freshness": FRESHNESS,
                "summary": SUMMARY,
                "count": COUNT
            },
            "result_count": result_count,
            "raw_response": data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        formatted_file = os.path.join(company_dir, "bocha_formatted_response.json")
        with open(formatted_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=2)

        print(f"✓ {company['name_cn']} Bocha搜索完成，收到 {result_count} 条结果")
        return formatted_data

    except requests.exceptions.RequestException as e:
        print(f"✗ {company['name_cn']} Bocha搜索失败: {str(e)}")
        return None
    except Exception as e:
        print(f"✗ {company['name_cn']} Bocha搜索异常: {str(e)}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("开始对高优先级公司进行业务信息搜索（Bocha）...")
    print(f"共需处理 {len(HIGH_PRIORITY_COMPANIES)} 家公司")
    print(f"API参数: freshness={FRESHNESS}, summary={SUMMARY}, count={COUNT}")
    print("=" * 60)

    results = []
    for company in HIGH_PRIORITY_COMPANIES:
        result = search_company_business_bocha(company)
        if result:
            results.append(result)

        # 添加延迟避免API限制
        time.sleep(1)

    print(f"\nBocha搜索完成！成功处理 {len(results)}/{len(HIGH_PRIORITY_COMPANIES)} 家公司")

    # 生成汇总报告
    summary_file = os.path.join(OUTPUT_BASE_DIR, "bocha_search_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_companies": len(HIGH_PRIORITY_COMPANIES),
            "successful_searches": len(results),
            "companies": [{"cn": r['company_name_cn'], "en": r['company_name_en'], "results": r['result_count']} for r in results],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "search_type": "business_focused",
            "api": "bocha",
            "params": {
                "freshness": FRESHNESS,
                "summary": SUMMARY,
                "count": COUNT
            }
        }, f, ensure_ascii=False, indent=2)

    print(f"汇总报告已保存到: {summary_file}")
    return results

if __name__ == "__main__":
    main()

