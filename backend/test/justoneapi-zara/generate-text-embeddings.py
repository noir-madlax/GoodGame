"""
商品文本向量化脚本
使用 OpenAI text-embedding-3-small 模型生成商品名称的向量

使用页面: 独立测试脚本
功能:
  1. 获取所有商品名称
  2. 调用 OpenAI Embedding API 生成向量
  3. 存储到 gg_taobao_product_embeddings 表

注意:
  - 需要配置 OPENAI_API_KEY 环境变量
  - 如果没有 OPENAI_API_KEY，可以使用 OPENROUTER_API_KEY (通过 OpenRouter 调用 OpenAI)
  - text-embedding-3-small 生成 1536 维向量
  - 价格: $0.02 / 1M tokens
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

# ==================== 配置区域 ====================
# Embedding 模型
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# 批处理大小 (OpenAI 支持批量请求)
BATCH_SIZE = 50

# 请求间隔 (秒)
REQUEST_DELAY = 0.5


def load_clients() -> tuple:
    """加载 Supabase 和 OpenAI 客户端"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    # Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("未找到 SUPABASE_URL 或 SUPABASE_KEY")
    
    supabase = create_client(supabase_url, supabase_key)
    print(f"✅ 成功连接 Supabase")
    
    # OpenAI - 优先使用 OPENAI_API_KEY，否则使用 OPENROUTER_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    if openai_key:
        # 直接使用 OpenAI
        openai_client = OpenAI(api_key=openai_key)
        print(f"✅ 使用 OpenAI API")
    elif openrouter_key:
        # 通过 OpenRouter 调用 OpenAI
        openai_client = OpenAI(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1"
        )
        print(f"✅ 使用 OpenRouter API (调用 OpenAI)")
    else:
        raise ValueError("未找到 OPENAI_API_KEY 或 OPENROUTER_API_KEY，请在 .env 文件中配置")
    
    return supabase, openai_client


def get_products_without_embeddings(supabase: Client) -> list:
    """获取还没有生成向量的商品"""
    # 获取所有商品
    products_result = supabase.table("gg_taobao_products").select(
        "id, item_id, item_name"
    ).execute()
    
    # 获取已有向量的商品 ID
    embeddings_result = supabase.table("gg_taobao_product_embeddings").select(
        "product_id"
    ).eq("embedding_type", "text").execute()
    
    existing_ids = {row["product_id"] for row in embeddings_result.data}
    
    # 过滤出未生成向量的商品
    products = [
        p for p in products_result.data 
        if p["id"] not in existing_ids and p["item_name"]
    ]
    
    return products


def generate_embeddings_batch(openai_client: OpenAI, texts: list) -> list:
    """
    批量生成文本向量
    
    参数:
        openai_client: OpenAI 客户端
        texts: 文本列表
    
    返回:
        list: 向量列表 (与输入顺序对应)
    """
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    
    # 按 index 排序确保顺序正确
    embeddings = [None] * len(texts)
    for item in response.data:
        embeddings[item.index] = item.embedding
    
    return embeddings


def save_embeddings(supabase: Client, embeddings_data: list) -> None:
    """保存向量到数据库"""
    if not embeddings_data:
        return
    
    # 批量插入
    supabase.table("gg_taobao_product_embeddings").upsert(
        embeddings_data,
        on_conflict="product_id,embedding_type"
    ).execute()


def main():
    """主函数"""
    print("=" * 70)
    print("🔢 商品文本向量化 (OpenAI text-embedding-3-small)")
    print("=" * 70)
    
    # 1. 加载客户端
    supabase, openai_client = load_clients()
    
    # 2. 获取待处理商品
    print(f"\n📋 正在获取待处理商品...")
    products = get_products_without_embeddings(supabase)
    print(f"   共 {len(products)} 个商品待处理")
    
    if not products:
        print("\n✅ 所有商品已完成向量化！")
        return
    
    # 3. 分批处理
    print(f"\n🚀 开始生成向量 (批大小: {BATCH_SIZE})...")
    
    total_processed = 0
    total_tokens = 0
    
    for i in range(0, len(products), BATCH_SIZE):
        batch = products[i:i + BATCH_SIZE]
        
        # 提取文本
        texts = [p["item_name"] for p in batch]
        
        try:
            # 生成向量
            embeddings = generate_embeddings_batch(openai_client, texts)
            
            # 构建数据
            embeddings_data = []
            for j, product in enumerate(batch):
                if embeddings[j]:
                    embeddings_data.append({
                        "product_id": product["id"],
                        "item_id": product["item_id"],
                        "embedding_type": "text",
                        "embedding_model": EMBEDDING_MODEL,
                        "embedding": embeddings[j],
                        "source_text": product["item_name"]
                    })
            
            # 保存到数据库
            save_embeddings(supabase, embeddings_data)
            
            total_processed += len(batch)
            print(f"   ✅ 已处理 {total_processed}/{len(products)} 个商品")
            
            # 请求间隔
            time.sleep(REQUEST_DELAY)
            
        except Exception as e:
            print(f"   ❌ 批次处理失败: {e}")
            time.sleep(2)  # 出错后等待更长时间
    
    # 4. 统计
    print(f"\n📊 处理完成:")
    print(f"   处理商品数: {total_processed}")
    
    # 验证
    result = supabase.table("gg_taobao_product_embeddings").select(
        "id", count="exact"
    ).eq("embedding_type", "text").execute()
    
    print(f"   数据库向量数: {result.count}")
    
    print("\n" + "=" * 70)
    print("✅ 向量化完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()

