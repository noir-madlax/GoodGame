import os
import json
import time
from tavily import TavilyClient
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
load_dotenv(dotenv_path)

# API Configuration
API_KEY = os.getenv("TAVILY_API_KEY")
if not API_KEY:
    print("Error: TAVILY_API_KEY not found.")
    exit(1)

client = TavilyClient(API_KEY)

# Output configuration
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "china-company")

# Data for the pilot run (from DB query)
companies = [
    {
        "id": 724,
        "organization_name": "Hubbot",
        "industries": ["Artificial Intelligence (AI)"],
        "headquarters_location": "Xiamen, Fujian, China"
    },
    {
        "id": 2608,
        "organization_name": "OpenPie",
        "industries": ["Analytics", "Cloud Computing", "Cloud Data Services", "Software"],
        "headquarters_location": "Hangzhou, Zhejiang, China"
    },
    {
        "id": 2840,
        "organization_name": "Yiou Software",
        "industries": ["Software"],
        "headquarters_location": "Beijing, Beijing, China"
    }
]

def clean_location(loc_str):
    # Extract city from "City, Province, Country"
    parts = loc_str.split(',')
    if parts:
        return parts[0].strip()
    return loc_str

def run_search():
    for company in companies:
        name = company['organization_name']
        city = clean_location(company['headquarters_location'])
        industries = ", ".join(company['industries'])
        
        print(f"\nProcessing {name} (ID: {company['id']})...")
        
        # Construct query
        # "介绍一下QuickCEP这家中国北京的公司产品。\n他主要做电商，零售，SaaS方面的业务方面。\n我需要他进一步的产品介绍，功能介绍，官网链接，服务的客户\n"
        query = f"介绍一下{name}这家中国{city}的公司产品。\n他主要做{industries}方面的业务方面。\n我需要他进一步的产品介绍，功能介绍，官网链接，服务的客户\n"
        
        print(f"Query: {query.strip()}")
        
        try:
            # Execute search
            response = client.search(
                query=query,
                include_answer="advanced",
                search_depth="advanced",
                max_results=10
            )
            
            # Create output directory
            safe_name = "".join(c if c.isalnum() or c in " " else "_" for c in name).strip().replace(" ", "_")
            company_output_dir = os.path.join(OUTPUT_BASE_DIR, safe_name)
            os.makedirs(company_output_dir, exist_ok=True)
            
            # Save raw response
            raw_path = os.path.join(company_output_dir, "response_raw.json")
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False)
                
            # Save formatted response
            formatted_path = os.path.join(company_output_dir, "response_formatted.json")
            with open(formatted_path, "w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False, indent=2)
                
            print(f"Saved results to {company_output_dir}")
            
            # Print answer for verification
            answer = response.get('answer', 'No answer provided')
            print("-" * 40)
            print("Tavily Answer:")
            print(answer)
            print("-" * 40)
            
        except Exception as e:
            print(f"Error processing {name}: {e}")
        
        # Be nice to the API
        time.sleep(1)

if __name__ == "__main__":
    run_search()

