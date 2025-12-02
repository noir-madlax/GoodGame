# To install: pip install tavily-python
from tavily import TavilyClient
client = TavilyClient(os.getenv("TAVILY_API_KEY"))
response = client.search(
    query="介绍一下QuickCEP这家中国北京的公司产品。\n他主要做电商，零售，SaaS方面的业务方面。\n我需要他进一步的产品介绍，功能介绍，官网链接，服务的客户\n",
    include_answer="advanced",
    search_depth="advanced",
    max_results=10
)
print(response)