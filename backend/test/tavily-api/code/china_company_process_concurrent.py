"""
中国公司信息批量查询脚本 (并发版本)
功能：从数据库获取 is_china_focus_company=true 的公司，通过 Tavily API 查询详细信息，
     提取公司介绍(answer)和官网URL，并回写数据库。
并发策略：使用 ThreadPoolExecutor 实现3个并发线程，通过预先分配任务列表避免重复查询。
"""

import os
import json
import re
import time
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
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
# 并发配置
# ==========================================
MAX_WORKERS = 3  # 并发线程数
RATE_LIMIT_DELAY = 1  # 每个请求后的延迟（秒）

# ==========================================
# 工具函数 (保持原有逻辑不变)
# ==========================================

def clean_location(loc_str: str) -> str:
    """从完整地址中提取城市名"""
    if not loc_str:
        return "China"
    parts = loc_str.split(',')
    if parts:
        return parts[0].strip()
    return loc_str


def extract_url(text: str) -> Optional[str]:
    """从文本中提取第一个URL"""
    if not text:
        return None
    url_pattern = r'https?://[a-zA-Z0-9.-]+(?:/[a-zA-Z0-9.\-_\?=&%]*)?'
    match = re.search(url_pattern, text)
    if match:
        return match.group(0).rstrip('.,;)')
    return None


def update_company_in_db(company_id: int, summary: str, url: str) -> bool:
    """更新数据库中的公司信息"""
    data = {
        "tavily_summary": summary,
        "official_website_url": url
    }
    try:
        supabase.table("gg_crunchbase_company").update(data).eq("id", company_id).execute()
        return True
    except Exception as e:
        print(f"[ERROR] DB update failed for ID {company_id}: {e}")
        return False


def process_single_company(company: Dict) -> Dict:
    """
    处理单个公司的查询逻辑
    参数: company - 包含 id, organization_name, industries, headquarters_location 的字典
    返回: 处理结果字典，包含 id, name, success, answer, url
    """
    company_id = company['id']
    name = company['organization_name']
    city = clean_location(company['headquarters_location'])
    industries = ", ".join(company['industries'] if company['industries'] else [])
    
    result = {
        "id": company_id,
        "name": name,
        "success": False,
        "answer": None,
        "url": None,
        "error": None
    }
    
    # 构建查询 (保持原有格式)
    query = f"介绍一下{name}这家中国{city}的公司产品。\n他主要做{industries}方面的业务方面。\n我需要他进一步的产品介绍，功能介绍，官网链接，服务的客户\n"
    
    try:
        # 调用 Tavily API
        search_result = tavily_client.search(
            query=query,
            include_answer="advanced",
            search_depth="advanced",
            max_results=10
        )
        
        # 保存到本地文件
        safe_name = "".join(c if c.isalnum() or c in " " else "_" for c in name).strip().replace(" ", "_")
        company_output_dir = os.path.join(OUTPUT_BASE_DIR, safe_name)
        os.makedirs(company_output_dir, exist_ok=True)
        
        with open(os.path.join(company_output_dir, "response_raw.json"), "w", encoding="utf-8") as f:
            json.dump(search_result, f, ensure_ascii=False)
        
        with open(os.path.join(company_output_dir, "response_formatted.json"), "w", encoding="utf-8") as f:
            json.dump(search_result, f, ensure_ascii=False, indent=2)
        
        # 提取 answer 和 URL
        answer = search_result.get('answer', '')
        url = extract_url(answer)
        
        # 如果 answer 中没有 URL，尝试从 results 中获取
        if not url and search_result.get('results'):
            for res in search_result['results']:
                if res.get('url'):
                    url = res.get('url')
                    break
        
        # 更新数据库
        db_success = update_company_in_db(company_id, answer, url)
        
        result["success"] = db_success
        result["answer"] = answer[:100] + "..." if answer and len(answer) > 100 else answer
        result["url"] = url
        
    except Exception as e:
        result["error"] = str(e)
        print(f"[ERROR] Processing {name} (ID: {company_id}): {e}")
    
    # 请求后延迟，避免触发 API 限流
    time.sleep(RATE_LIMIT_DELAY)
    
    return result


def fetch_pending_companies() -> List[Dict]:
    """
    一次性获取所有待处理的公司列表
    条件: is_china_focus_company = true AND tavily_summary IS NULL
    """
    try:
        response = supabase.table("gg_crunchbase_company")\
            .select("id, organization_name, industries, headquarters_location")\
            .eq("is_china_focus_company", True)\
            .is_("tavily_summary", "null")\
            .execute()
        return response.data
    except Exception as e:
        print(f"[ERROR] Failed to fetch companies: {e}")
        return []


def run_concurrent_processing():
    """
    主函数：并发处理所有待处理的公司
    策略：
    1. 一次性从数据库获取所有待处理公司（避免并发时重复查询）
    2. 使用 ThreadPoolExecutor 并发处理
    3. 实时打印进度
    """
    print("=" * 60)
    print("中国公司信息批量查询 (并发版本)")
    print(f"并发数: {MAX_WORKERS}")
    print("=" * 60)
    
    # Step 1: 获取所有待处理公司
    companies = fetch_pending_companies()
    total = len(companies)
    
    if total == 0:
        print("\n[INFO] 没有待处理的公司，任务完成！")
        return
    
    print(f"\n[INFO] 找到 {total} 家待处理公司")
    print("-" * 60)
    
    # Step 2: 并发处理
    completed = 0
    success_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_company = {
            executor.submit(process_single_company, company): company
            for company in companies
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_company):
            completed += 1
            result = future.result()
            
            if result["success"]:
                success_count += 1
                status = "✓"
            else:
                failed_count += 1
                status = "✗"
            
            # 打印进度
            print(f"[{completed}/{total}] {status} {result['name']} (ID: {result['id']})")
            if result["url"]:
                print(f"         URL: {result['url']}")
            if result["error"]:
                print(f"         Error: {result['error']}")
    
    # Step 3: 打印汇总
    print("\n" + "=" * 60)
    print("处理完成！")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print(f"  总计: {total}")
    print("=" * 60)


if __name__ == "__main__":
    run_concurrent_processing()

