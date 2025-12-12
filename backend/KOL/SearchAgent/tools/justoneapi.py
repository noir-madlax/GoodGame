import requests
import os
import time
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from jobs.logger import get_logger

logger = get_logger(__name__)

# Constants
BASE_URL = "http://47.117.133.51:30015"
SEARCH_USER_ENDPOINT = "/api/xiaohongshu/search-user/v2"
MAX_SAFE_PAGES = 2

@dataclass
class QueryResult:
    """Standardized result wrapper for individual items"""
    data: Dict[str, Any]
    source: str = "justoneapi"

@dataclass
class ApiResult:
    """Standardized API response wrapper"""
    tool_name: str
    parameters: Dict[str, Any]
    results: List[QueryResult] = field(default_factory=list)
    results_count: int = 0
    error_message: Optional[str] = None


def search_user(keyword: Union[str, List[str]], max_pages: int = 2) -> ApiResult:
    """
    Search for users using UserSearch API with pagination.
    Iterates from page used internally (always starts at 1) up to limits.
    
    Args:
        keyword: Search keywords (can be a single string or a list of strings)
        max_pages: Number of pages to fetch (default: 2, max capped at MAX_SAFE_PAGES)
    
    Returns:
        ApiResult containing aggregated results from all pages
    """
    token = os.getenv("JUSTONEAPI_API_KEY")
    parameters = {"keyword": keyword, "max_pages": max_pages}
    
    if not token:
        logger.error("JUSTONEAPI_API_KEY environment variable not set.")
        return ApiResult(
            tool_name="search_user",
            parameters=parameters,
            error_message="Configuration Error: JUSTONEAPI_API_KEY missing"
        )

    all_results = []
    
    # Internal page handling
    start_page = 1
    # Cap max_pages for safety
    total_pages_to_fetch = min(max_pages, MAX_SAFE_PAGES)
    
    endpoint = f"{BASE_URL}{SEARCH_USER_ENDPOINT}"
    
    # Normalize keyword to list
    keywords = [keyword] if isinstance(keyword, str) else keyword
    
    for kw in keywords:
        logger.info(f"Starting search for keyword: {kw}, pages: {start_page} to {start_page + total_pages_to_fetch - 1}")

        for i in range(total_pages_to_fetch):
            current_page = start_page + i
            
            params = {
                "keyword": kw,
                "page": current_page,
                "token": token
            }
            
            try:
                logger.info(f"Requesting page {current_page} for keyword '{kw}'...")
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
                    logger.error(f"API returned error on page {current_page} for keyword '{kw}': {data.get('message', 'Unknown error')}")
    
            except Exception as e:
                logger.error(f"Error fetching page {current_page} for keyword '{kw}': {e}")
                
            # Avoid hitting rate limits aggressively
            if i < total_pages_to_fetch - 1:
                time.sleep(1)
        
        # Small delay between keywords to be nice
        time.sleep(1)
    
    # Wrap results in QueryResult objects
    query_results = [QueryResult(data=item) for item in all_results]
    
    return ApiResult(
        tool_name="search_user",
        parameters=parameters,
        results=query_results,
        results_count=len(query_results)
    )

def execute_search_tool(tool_name: str, **kwargs) -> ApiResult:
    """
    Dispatcher for search tools.
    
    Args:
        tool_name: Name of the tool to execute
        **kwargs: Arguments for the tool
        
    Returns:
        ApiResult object
    """
    if tool_name == "search_user":
        # Extract arguments specifically for search_user if needed, 
        # or just pass kwargs if they match.
        # search_user expects 'keyword' and optional 'max_pages'
        return search_user(**kwargs)
    
    return ApiResult(
        tool_name=tool_name,
        parameters=kwargs,
        error_message=f"Tool '{tool_name}' not found"
    )

if __name__ == "__main__":
    # Test block
    # We rely on env var now, so just call it.
    # Testing with a list of keywords
    result = execute_search_tool("search_user", keyword=["家居", "科技"], max_pages=1)
    print("Search Result Summary:")
    print(f"Tool: {result.tool_name}")
    print(f"Error: {result.error_message}")
    print(f"Data count: {result.results_count}")
    if result.results_count > 0:
        print(f"First item sample: {result.results[0].data.get('nickname', 'No nickname')}")
    # print(result) # Uncomment to see full data
