"""
高优先级公司产品业务信息查询脚本
功能：对指定的5家高优先级公司进行产品、业务、客户等方面的搜索
重点：产品介绍、客户痛点、应用场景、行业方向、客户名称等业务信息
"""

import os
import json
import re
import time
from typing import Optional, List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client
from tavily import TavilyClient

# ==========================================
# 环境配置
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
# 路径: backend/test/tavily-api/code/ -> backend/
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
env_path = os.path.join(backend_dir, ".env")
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, TAVILY_API_KEY]):
    print(f"Debug: SUPABASE_URL={bool(SUPABASE_URL)}")
    print(f"Debug: SUPABASE_KEY={bool(SUPABASE_KEY)}")
    print(f"Debug: TAVILY_API_KEY={bool(TAVILY_API_KEY)}")
    raise ValueError("Missing environment variables")

# 创建客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
tavily_client = TavilyClient(TAVILY_API_KEY)

# 输出目录 - 使用新的子目录避免覆盖之前的输出
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(current_dir), "output", "china-company-business")
os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

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
    """为公司创建业务导向的查询 - 聚焦产品和业务信息"""
    query = f"""请详细介绍{company['name_cn']}（{company['name_en']}）这家中国{company['location']}的公司。

主要业务领域：{company['industry']}

我需要以下业务和产品方面的信息：
1. 公司的核心产品有哪些？每个产品解决什么问题？
2. 公司的目标客户是谁？服务哪些行业？
3. 客户使用产品前遇到的痛点和问题是什么？
4. 产品的典型应用场景有哪些？
5. 已经服务的客户名称和案例有哪些？
6. 公司的商业模式是什么？如何收费？
7. 与竞争对手相比有什么优势？
8. 公司的官网链接是什么？

请提供真实的业务信息和客户案例。"""
    return query

def search_company_business(company: Dict) -> Optional[Dict]:
    """使用Tavily API搜索公司业务信息"""
    try:
        # 创建文件夹 - 使用中文名称
        safe_name = re.sub(r'[^\w\-_\.]', '_', company['name_cn'])
        company_dir = os.path.join(OUTPUT_BASE_DIR, safe_name)
        os.makedirs(company_dir, exist_ok=True)

        # 构建查询
        query = create_business_query(company)
        print(f"正在搜索 {company['name_cn']}（{company['name_en']}）的业务信息...")

        # 执行搜索
        response = tavily_client.search(
            query=query,
            include_answer="advanced",
            search_depth="advanced",
            max_results=15
        )

        # 保存原始响应
        raw_file = os.path.join(company_dir, "tavily_raw_response.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)

        # 格式化并保存响应
        formatted_data = {
            "company_name_cn": company['name_cn'],
            "company_name_en": company['name_en'],
            "location": company['location'],
            "industry": company['industry'],
            "query": query,
            "answer": response.get('answer', ''),
            "images": response.get('images', []),
            "results": response.get('results', []),
            "response_time": response.get('response_time', 0),
            "request_id": response.get('request_id', '')
        }

        formatted_file = os.path.join(company_dir, "tavily_formatted_response.json")
        with open(formatted_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=2)

        print(f"✓ {company['name_cn']} Tavily搜索完成")
        return formatted_data

    except Exception as e:
        print(f"✗ {company['name_cn']} Tavily搜索失败: {str(e)}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("开始对高优先级公司进行业务信息搜索（Tavily）...")
    print(f"共需处理 {len(HIGH_PRIORITY_COMPANIES)} 家公司")
    print("=" * 60)

    results = []
    for company in HIGH_PRIORITY_COMPANIES:
        result = search_company_business(company)
        if result:
            results.append(result)

        # 添加延迟避免API限制
        time.sleep(2)

    print(f"\nTavily搜索完成！成功处理 {len(results)}/{len(HIGH_PRIORITY_COMPANIES)} 家公司")

    # 生成汇总报告
    summary_file = os.path.join(OUTPUT_BASE_DIR, "tavily_search_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_companies": len(HIGH_PRIORITY_COMPANIES),
            "successful_searches": len(results),
            "companies": [{"cn": r['company_name_cn'], "en": r['company_name_en']} for r in results],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "search_type": "business_focused"
        }, f, ensure_ascii=False, indent=2)

    print(f"汇总报告已保存到: {summary_file}")
    return results

if __name__ == "__main__":
    main()

