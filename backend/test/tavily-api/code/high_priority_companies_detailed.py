"""
高优先级公司产品详细介绍查询脚本
功能：对指定的5家高优先级公司进行更详细的产品介绍搜索
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

# 输出目录
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(current_dir), "output", "china-company")

# ==========================================
# 高优先级公司列表 - 广告/市场营销方向中国公司
# ==========================================
HIGH_PRIORITY_COMPANIES = [
    {
        "name": "Kuaizi Technology",
        "location": "广州",
        "industry": "Artificial Intelligence (AI), Content Creators, Marketing Automation",
        "description": "全球领先、中国首个AI创意平台，专注于营销自动化和AI内容创作"
    },
    {
        "name": "LightSail Technology",
        "location": "深圳",
        "industry": "Artificial Intelligence (AI), Information Technology, Internet",
        "description": "专业互联网营销服务提供商，专注于互联网营销和品牌运营"
    },
    {
        "name": "Xinchen Interactive Entertainment",
        "location": "厦门",
        "industry": "Digital Media, E-Commerce, Social Media",
        "description": "综合媒体服务提供商，专注于孵化个人商业IP和社交媒体运营"
    }
]

def create_detailed_query(company: Dict) -> str:
    """为公司创建详细的产品介绍查询"""
    query = f"""请详细介绍{company['name']}这家中国{company['location']}的公司产品和服务。

主要业务领域：{company['industry']}
公司定位：{company['description']}

我需要以下详细信息：
1. 核心产品线和技术平台的具体介绍
2. 每个产品的详细功能和技术特点
3. 产品的技术架构和实现方式
4. 支持的数据类型和处理能力
5. 集成方式（API、SDK、云端部署等）
6. 产品的性能指标和优势
7. 典型应用场景和使用案例
8. 服务的具体客户类型和行业
9. 官网链接和技术文档链接
10. 最新版本的功能更新和技术突破

请提供尽可能详细和准确的产品技术信息。"""
    return query

def search_company_details(company: Dict) -> Optional[Dict]:
    """使用Tavily API搜索公司详细信息"""
    try:
        # 创建文件夹
        safe_name = re.sub(r'[^\w\-_\.]', '_', company['name'])
        company_dir = os.path.join(OUTPUT_BASE_DIR, f"{safe_name}_detailed")
        os.makedirs(company_dir, exist_ok=True)

        # 构建查询
        query = create_detailed_query(company)
        print(f"正在搜索 {company['name']} 的详细信息...")

        # 执行搜索
        response = tavily_client.search(
            query=query,
            include_answer="advanced",
            search_depth="advanced",
            max_results=15
        )

        # 保存原始响应
        raw_file = os.path.join(company_dir, "response_raw.json")
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)

        # 格式化并保存响应
        formatted_data = {
            "company_name": company['name'],
            "location": company['location'],
            "industry": company['industry'],
            "query": query,
            "answer": response.get('answer', ''),
            "images": response.get('images', []),
            "results": response.get('results', []),
            "response_time": response.get('response_time', 0),
            "request_id": response.get('request_id', '')
        }

        formatted_file = os.path.join(company_dir, "response_formatted.json")
        with open(formatted_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=2)

        print(f"✓ {company['name']} 搜索完成")
        return formatted_data

    except Exception as e:
        print(f"✗ {company['name']} 搜索失败: {str(e)}")
        return None

def main():
    """主函数"""
    print("开始对高优先级公司进行详细产品介绍搜索...")
    print(f"共需处理 {len(HIGH_PRIORITY_COMPANIES)} 家公司")

    results = []
    for company in HIGH_PRIORITY_COMPANIES:
        result = search_company_details(company)
        if result:
            results.append(result)

        # 添加延迟避免API限制
        time.sleep(2)

    print(f"\n搜索完成！成功处理 {len(results)}/{len(HIGH_PRIORITY_COMPANIES)} 家公司")

    # 生成汇总报告
    summary_file = os.path.join(OUTPUT_BASE_DIR, "high_priority_companies_detailed_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_companies": len(HIGH_PRIORITY_COMPANIES),
            "successful_searches": len(results),
            "companies": [r['company_name'] for r in results],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, ensure_ascii=False, indent=2)

    print(f"汇总报告已保存到: {summary_file}")

if __name__ == "__main__":
    main()
