# Tavily Extract API 测试 - 提取搜索结果中的详细信息
# To install: pip install tavily-python python-dotenv
import os
import json
import time
from tavily import TavilyClient
from dotenv import load_dotenv
from urllib.parse import urlparse

# 加载环境变量
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
load_dotenv(dotenv_path)

# ==========================================
# Tavily Extract API 参数配置
# 文档: https://docs.tavily.com/documentation/api-reference/endpoint/extract
# ==========================================

# API Key
API_KEY = os.getenv("TAVILY_API_KEY")

# 提取深度
# 'basic': 基础提取，1 credit / 5 URLs
# 'advanced': 高级提取 (包含表格、嵌入内容等)，2 credits / 5 URLs
EXTRACT_DEPTH = "advanced"

# 提取内容格式
# 'markdown': 返回 Markdown 格式
# 'text': 返回纯文本
FORMAT = "markdown"

# 是否包含提取的图片列表
INCLUDE_IMAGES = False

# 是否包含 Favicon
INCLUDE_FAVICON = False

# 超时时间 (秒)
# Default: 10s for basic, 30s for advanced
TIMEOUT = 30.0

# ==========================================

# 输出目录
OUTPUT_DIR = "../output/新星_护肤_抖音_网红达人_extract"
# 搜索结果文件路径 (作为输入)
INPUT_SEARCH_RESULT = "../output/response_formatted.json"

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

if not API_KEY:
    print("Error: TAVILY_API_KEY not found in environment variables.")
    exit(1)

# 创建客户端
client = TavilyClient(API_KEY)

def get_safe_filename(url):
    """根据URL生成安全的文件名"""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    # 提取路径的最后一部分或查询参数作为标识
    path_part = parsed.path.strip("/").replace("/", "_")
    if not path_part:
        path_part = "home"
    
    # 截断过长的文件名
    safe_name = f"{domain}_{path_part}"
    # 替换非法字符
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in safe_name)[:50]

def run_extraction():
    # 1. 读取搜索结果
    if not os.path.exists(INPUT_SEARCH_RESULT):
        print(f"Error: Input file {INPUT_SEARCH_RESULT} not found. Please run 'Tavily Search.py' first.")
        return

    print(f"Reading URLs from: {INPUT_SEARCH_RESULT}")
    with open(INPUT_SEARCH_RESULT, "r", encoding="utf-8") as f:
        search_data = json.load(f)
    
    results = search_data.get("results", [])
    if not results:
        print("No results found in search data.")
        return

    urls_to_extract = [res["url"] for res in results]
    
    print("开始提取网页内容...")
    print(f"Params: depth={EXTRACT_DEPTH}, format={FORMAT}")
    print(f"共需处理 {len(urls_to_extract)} 个URL")
    print("-" * 50)

    successful_extractions = 0
    failed_extractions = 0

    for i, url in enumerate(urls_to_extract, 1):
        print(f"正在处理第 {i}/{len(urls_to_extract)} 个URL: {url}")

        try:
            # 调用 extract API
            response = client.extract(
                urls=url,
                extract_depth=EXTRACT_DEPTH,
                format=FORMAT,
                include_images=INCLUDE_IMAGES,
                include_favicon=INCLUDE_FAVICON,
                timeout=TIMEOUT
            )

            # 生成文件名
            filename_base = get_safe_filename(url)
            
            # 保存原始返回数据
            raw_filename = os.path.join(OUTPUT_DIR, f"{filename_base}_raw.json")
            with open(raw_filename, "w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False)

            # 保存格式化的JSON数据
            formatted_filename = os.path.join(OUTPUT_DIR, f"{filename_base}_formatted.json")
            with open(formatted_filename, "w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False, indent=2)

            # 保存内容文本 (Markdown)
            if response.get('results') and len(response['results']) > 0:
                result = response['results'][0]
                if result.get('raw_content'):
                    text_filename = os.path.join(OUTPUT_DIR, f"{filename_base}_content.md")
                    with open(text_filename, "w", encoding="utf-8") as f:
                        f.write(f"# {search_data.get('results')[i-1].get('title', 'No Title')}\n\n") # Use title from search result as fallback/header
                        f.write(f"**URL:** {url}\n\n")
                        f.write("---\n\n")
                        f.write(result['raw_content'])

            successful_extractions += 1
            print(f"✓ 成功提取: {filename_base}")
            
            # 添加延迟
            if i < len(urls_to_extract):
                time.sleep(1)

        except Exception as e:
            failed_extractions += 1
            print(f"✗ 提取失败: {url}")
            print(f"  错误信息: {str(e)}")
            
            # 记录错误
            error_log = os.path.join(OUTPUT_DIR, "extraction_errors.log")
            with open(error_log, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {url} - {str(e)}\n")

    print("-" * 50)
    print("提取完成!")
    print(f"成功: {successful_extractions} 个")
    print(f"失败: {failed_extractions} 个")
    print(f"结果保存在: {OUTPUT_DIR}")

if __name__ == "__main__":
    run_extraction()
