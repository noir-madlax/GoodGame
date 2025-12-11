import requests
import os
import time
from typing import Optional, Dict, Any, List
from jobs.logger import get_logger

logger = get_logger(__name__)

# Constants
BASE_URL = "http://47.117.133.51:30015"
SEARCH_USER_ENDPOINT = "/api/xiaohongshu/search-user/v2"
MAX_SAFE_PAGES = 2

def search_user(keyword: str, max_pages: int = 2) -> Dict[str, Any]:
    """
    Search for users using UserSearch API with pagination.
    Iterates from page used internally (always starts at 1) up to limits.
    
    Args:
        keyword: Search keywords
        max_pages: Number of pages to fetch (default: 2, max capped at MAX_SAFE_PAGES)
    
    Returns:
        Dict containing aggregated results from all pages
    """
    token = os.getenv("JUSTONEAPI_API_KEY")
    if not token:
        logger.error("JUSTONEAPI_API_KEY environment variable not set.")
        return {
            "code": -1,
            "message": "Configuration Error: JUSTONEAPI_API_KEY missing",
            "data": []
        }

    all_results = []
    
    # Internal page handling
    start_page = 1
    # Cap max_pages for safety
    total_pages_to_fetch = min(max_pages, MAX_SAFE_PAGES)
    
    endpoint = f"{BASE_URL}{SEARCH_USER_ENDPOINT}"
    
    logger.info(f"Starting search for keyword: {keyword}, pages: {start_page} to {start_page + total_pages_to_fetch - 1}")

    for i in range(total_pages_to_fetch):
        current_page = start_page + i
        
        params = {
            "keyword": keyword,
            "page": current_page,
            "token": token
        }
        
        try:
            logger.info(f"Requesting page {current_page}...")
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Simple aggregation: extract 'data' and append to list
            # We assume 'data' is the relevant payload. 
            # If the API returns a list in 'data', we might want to extend our list.
            # If it returns a dict, we append the dict.
            # Without live API access, we preserve structure by appending 
            # the content of 'data' field.
            
            if data.get("code") == 0 or data.get("code") == "0" or data.get("success") is True:
                page_data = data.get("data")
                if page_data:
                    # If page_data is a list, extend (flatten).
                    # If it's a dict (e.g. meta + items), we might need to be smarter,
                    # but appending is safe for now to capture everything.
                    if isinstance(page_data, list):
                        all_results.extend(page_data)
                    else:
                        all_results.append(page_data)
            else:
                logger.error(f"API returned error on page {current_page}: {data.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Error fetching page {current_page}: {e}")
            
        # Avoid hitting rate limits aggressively
        if i < total_pages_to_fetch - 1:
            time.sleep(1)
            
    return {
        "code": 0,
        "message": "success",
        "data": all_results,
        "recordTime": time.strftime("%Y-%m-%d %H:%M:%S")
    }

if __name__ == "__main__":
    # Test block
    # We rely on env var now, so just call it.
    result = search_user(keyword="家居", max_pages=2)
    print("Search Result Summary:")
    print(f"Code: {result.get('code', 'N/A')}")
    print(f"Data count: {len(result.get('data', [])) if isinstance(result.get('data'), list) else 'N/A'}")
    print(result) # Uncomment to see full data
