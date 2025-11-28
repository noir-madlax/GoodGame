# To install: pip install tavily-python python-dotenv
import os
import json
from tavily import TavilyClient
from dotenv import load_dotenv

# 加载环境变量
# 假设 .env 文件在 backend 目录下
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
load_dotenv(dotenv_path)

# ==========================================
# Tavily Search API 参数配置
# 文档: https://docs.tavily.com/documentation/api-reference/endpoint/search
# ==========================================

# API Key
# 从环境变量 TAVILY_API_KEY 获取
API_KEY = os.getenv("TAVILY_API_KEY")

# 搜索查询词
# The search query to execute with Tavily.
QUERY = "抖音上新星的护肤保养的网红达人"

# 搜索深度
# 'basic': 快速，1 credit
# 'advanced': 高质量内容，2 credits
SEARCH_DEPTH = "advanced"

# 搜索主题
# 'general': 通用搜索，来源广泛
# 'news': 实时新闻更新，适用于政治、体育、大事件
# 'finance': 金融相关
TOPIC = "news"

# 结果数量限制
# Default: 5, Max: 20
MAX_RESULTS = 10

# 时间范围
# 用于过滤结果的发布时间或更新时间
# 'day', 'week', 'month', 'year' (or 'd', 'w', 'm', 'y')
TIME_RANGE = "month"

# 是否包含 LLM 生成的答案
# True/False or 'basic'/'advanced'
INCLUDE_ANSWER = True

# 是否包含原始 HTML 内容
# True/False or 'markdown'/'text'
# include_raw_content: True
INCLUDE_RAW_CONTENT = False

# 是否包含图片
INCLUDE_IMAGES = False

# 国家/地区增强 (仅适用于 topic='general')
# e.g., 'cn' for China
# 由于选择了 topic='news'，此参数可能无效或被忽略，但在此列出作为参考
COUNTRY = "cn" 

# ==========================================

if not API_KEY:
    print("Error: TAVILY_API_KEY not found in environment variables.")
    print(f"Checked .env path: {dotenv_path}")
    exit(1)

# 创建客户端
client = TavilyClient(API_KEY)

print(f"Executing search for: '{QUERY}'")
print(f"Params: topic={TOPIC}, depth={SEARCH_DEPTH}, max={MAX_RESULTS}, time={TIME_RANGE}")

try:
    # 执行搜索
    response = client.search(
        query=QUERY,
        search_depth=SEARCH_DEPTH,
        max_results=MAX_RESULTS,
        include_answer=INCLUDE_ANSWER,
        include_raw_content=INCLUDE_RAW_CONTENT,
        include_images=INCLUDE_IMAGES,
        topic=TOPIC,
        time_range=TIME_RANGE,
        # country=COUNTRY # Note: Country is officially for 'general' topic only
    )

    # 确保输出目录存在
    output_dir = "../output"
    os.makedirs(output_dir, exist_ok=True)

    # 保存原始返回数据
    raw_path = os.path.join(output_dir, "response_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False)

    # 保存格式化的 JSON 数据（用于人类阅读）
    formatted_path = os.path.join(output_dir, "response_formatted.json")
    with open(formatted_path, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=2)

    print(f"Search completed successfully.")
    print(f"Raw data saved to: {raw_path}")
    print(f"Formatted data saved to: {formatted_path}")

    # 打印简要结果
    if 'results' in response:
        print(f"\nFound {len(response['results'])} results:")
        for res in response['results'][:3]:
            print(f"- {res.get('title', 'No Title')} ({res.get('url')})")

except Exception as e:
    print(f"Error during search: {str(e)}")
