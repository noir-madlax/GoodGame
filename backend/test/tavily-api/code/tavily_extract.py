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
TIMEOUT = 60.0

# ==========================================

# 输出目录配置（基于查询词，与search脚本保持一致）
# 这里需要从BochaAI结果中读取查询词，或者手动指定
QUERY = "新星护肤保养的网红达人在抖音平台上的"  # BochaAI查询词
SAFE_QUERY_DIR = "".join(c if c.isalnum() or c in " " else "_" for c in QUERY).strip().replace(" ", "_")[:50]

OUTPUT_BASE_DIR = f"/Users/rigel/project/hdl-tikhub-goodgame/backend/test/tavily-api/output/{SAFE_QUERY_DIR}"
EXTRACT_OUTPUT_DIR = f"{OUTPUT_BASE_DIR}/extract"

print(f"输出基础目录: {OUTPUT_BASE_DIR}")
print(f"提取输出目录: {EXTRACT_OUTPUT_DIR}")

# 确保基础输出目录存在
os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

# BochaAI 结果文件路径 (作为输入)
INPUT_BOCHA_RESULT = "/Users/rigel/project/hdl-tikhub-goodgame/backend/test/bocha-api/output/新星护肤保养的网红达人在抖音平台上的/result.json"

# 确保输出目录存在
os.makedirs(EXTRACT_OUTPUT_DIR, exist_ok=True)

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
    # 1. 读取BochaAI搜索结果
    if not os.path.exists(INPUT_BOCHA_RESULT):
        print(f"Error: Input file {INPUT_BOCHA_RESULT} not found.")
        return

    print(f"Reading URLs from: {INPUT_BOCHA_RESULT}")
    with open(INPUT_BOCHA_RESULT, "r", encoding="utf-8") as f:
        bocha_data = json.load(f)

    # 提取webPages.value中的结果
    web_pages = bocha_data.get("data", {}).get("webPages", {}).get("value", [])
    if not web_pages:
        print("No web pages found in BochaAI data.")
        return

    urls_to_extract = [page["url"] for page in web_pages if page.get("url")]
    
    print("开始提取网页内容...")
    print(f"Params: depth={EXTRACT_DEPTH}, format={FORMAT}")
    print(f"共需处理 {len(urls_to_extract)} 个URL")
    print(f"结果将保存到: {EXTRACT_OUTPUT_DIR}")
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
            raw_filename = os.path.join(EXTRACT_OUTPUT_DIR, f"{filename_base}_raw.json")
            with open(raw_filename, "w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False)

            # 保存格式化的JSON数据
            formatted_filename = os.path.join(EXTRACT_OUTPUT_DIR, f"{filename_base}_formatted.json")
            with open(formatted_filename, "w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False, indent=2)

            # 保存内容文本 (Markdown)
            if response.get('results') and len(response['results']) > 0:
                result = response['results'][0]
                if result.get('raw_content'):
                    # 从BochaAI数据中获取标题
                    title = web_pages[i-1].get('name', 'No Title') if i-1 < len(web_pages) else 'No Title'
                    text_filename = os.path.join(EXTRACT_OUTPUT_DIR, f"{filename_base}_content.md")
                    with open(text_filename, "w", encoding="utf-8") as f:
                        f.write(f"# {title}\n\n")
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
            error_log = os.path.join(EXTRACT_OUTPUT_DIR, "extraction_errors.log")
            with open(error_log, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {url} - {str(e)}\n")

    print("-" * 50)
    print("提取完成!")
    print(f"成功: {successful_extractions} 个")
    print(f"失败: {failed_extractions} 个")
    print(f"结果保存在: {EXTRACT_OUTPUT_DIR}")

if __name__ == "__main__":
    run_extraction()
