import os
import json
import re
import time
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from tavily import TavilyClient

# Setup paths and env
current_dir = os.path.dirname(os.path.abspath(__file__))
# Adjust path to reach backend root where .env is located
# file is in backend/test/tavily-api/code/
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
env_path = os.path.join(backend_dir, ".env")
load_dotenv(env_path)

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, TAVILY_API_KEY]):
    print(f"Debug: SUPABASE_URL={bool(SUPABASE_URL)}")
    print(f"Debug: SUPABASE_KEY={bool(SUPABASE_KEY)}")
    print(f"Debug: TAVILY_API_KEY={bool(TAVILY_API_KEY)}")
    raise ValueError("Missing environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
tavily_client = TavilyClient(TAVILY_API_KEY)

OUTPUT_BASE_DIR = os.path.join(os.path.dirname(current_dir), "output", "china-company")

def clean_location(loc_str):
    if not loc_str:
        return "China"
    parts = loc_str.split(',')
    if parts:
        return parts[0].strip()
    return loc_str

def extract_url(text: str) -> Optional[str]:
    if not text:
        return None
    # Regex to find URLs
    # Look for https:// or http:// followed by non-whitespace chars
    # Stop at common punctuation that ends a sentence if not part of URL
    url_pattern = r'https?://[a-zA-Z0-9.-]+(?:/[a-zA-Z0-9.\-_\?=&%]*)?'
    match = re.search(url_pattern, text)
    if match:
        return match.group(0).rstrip('.,;)')
    return None

def update_company_in_db(company_id: int, summary: str, url: str):
    data = {
        "tavily_summary": summary,
        "official_website_url": url
    }
    try:
        response = supabase.table("gg_crunchbase_company").update(data).eq("id", company_id).execute()
        # print(f"Updated DB for ID {company_id}")
    except Exception as e:
        print(f"Error updating DB for ID {company_id}: {e}")

def process_existing_files():
    print("Processing existing files...")
    # Mapping of ID to Folder Name based on previous run
    # Hubbot (724), OpenPie (2608), Yiou Software (2840)
    existing_mapping = {
        724: "Hubbot",
        2608: "OpenPie",
        2840: "Yiou_Software"
    }
    
    for company_id, folder_name in existing_mapping.items():
        file_path = os.path.join(OUTPUT_BASE_DIR, folder_name, "response_formatted.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    answer = data.get('answer', '')
                    url = extract_url(answer)
                    
                    print(f"Updating ID {company_id} ({folder_name})")
                    print(f"  Summary len: {len(answer)}")
                    print(f"  URL: {url}")
                    
                    update_company_in_db(company_id, answer, url)
            except Exception as e:
                print(f"Error reading file for {folder_name}: {e}")
        else:
            print(f"File not found for {folder_name} at {file_path}")

def process_new_batch(limit=10):
    print(f"\nFetching next {limit} companies...")
    
    # Query companies that need processing
    # is_china_focus_company = true AND tavily_summary IS NULL
    try:
        response = supabase.table("gg_crunchbase_company")\
            .select("id, organization_name, industries, headquarters_location")\
            .eq("is_china_focus_company", True)\
            .is_("tavily_summary", "null")\
            .limit(limit)\
            .execute()
            
        companies = response.data
        print(f"Found {len(companies)} companies to process.")
    except Exception as e:
        print(f"Error querying Supabase: {e}")
        return
    
    for company in companies:
        company_id = company['id']
        name = company['organization_name']
        city = clean_location(company['headquarters_location'])
        industries = ", ".join(company['industries'] if company['industries'] else [])
        
        print(f"\nProcessing {name} (ID: {company_id})...")
        
        query = f"介绍一下{name}这家中国{city}的公司产品。\n他主要做{industries}方面的业务方面。\n我需要他进一步的产品介绍，功能介绍，官网链接，服务的客户\n"
        
        try:
            # Search
            search_result = tavily_client.search(
                query=query,
                include_answer="advanced",
                search_depth="advanced",
                max_results=10
            )
            
            # Save to disk
            safe_name = "".join(c if c.isalnum() or c in " " else "_" for c in name).strip().replace(" ", "_")
            company_output_dir = os.path.join(OUTPUT_BASE_DIR, safe_name)
            os.makedirs(company_output_dir, exist_ok=True)
            
            with open(os.path.join(company_output_dir, "response_raw.json"), "w", encoding="utf-8") as f:
                json.dump(search_result, f, ensure_ascii=False)
            
            with open(os.path.join(company_output_dir, "response_formatted.json"), "w", encoding="utf-8") as f:
                json.dump(search_result, f, ensure_ascii=False, indent=2)
                
            # Extract and Update
            answer = search_result.get('answer', '')
            url = extract_url(answer)
            
            # If URL not in answer, try results
            if not url and search_result.get('results'):
                # Find first result with a URL
                for res in search_result['results']:
                    if res.get('url'):
                        url = res.get('url')
                        break
            
            print(f"  Answer: {answer[:50]}..." if answer else "  Answer: None")
            print(f"  URL: {url}")
            
            update_company_in_db(company_id, answer, url)
            
        except Exception as e:
            print(f"Error processing {name}: {e}")
            
        time.sleep(1) # Rate limit nice-ness

if __name__ == "__main__":
    process_existing_files()
    process_new_batch(10)

