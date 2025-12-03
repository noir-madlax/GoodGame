"""
使用增强文本重新生成商品向量

使用页面: 独立脚本
功能:
  1. 从 gg_taobao_product_apu 获取增强文本 (enhanced_text)
  2. 使用 OpenAI text-embedding-3-small 生成向量
  3. 更新 gg_taobao_product_embeddings 表

模型说明:
  - 模型: text-embedding-3-small (与搜索 API 一致)
  - 维度: 1536
  - 搜索时用户输入也使用同一模型向量化，确保语义空间一致

运行方式:
  python regenerate_embeddings_enhanced.py
  
  # 测试模式（只处理前 10 个）
  python regenerate_embeddings_enhanced.py --limit 10
  
  # 强制重新生成（覆盖已有向量）
  python regenerate_embeddings_enhanced.py --force
"""

import os
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

# ==================== 配置区域 ====================
# Embedding 模型 (与搜索 API 一致)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# 批处理大小
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
        openai_client = OpenAI(api_key=openai_key)
        print(f"✅ 使用 OpenAI API")
    elif openrouter_key:
        openai_client = OpenAI(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1"
        )
        print(f"✅ 使用 OpenRouter API (调用 OpenAI)")
    else:
        raise ValueError("未找到 OPENAI_API_KEY 或 OPENROUTER_API_KEY")
    
    return supabase, openai_client


def get_products_with_enhanced_text(supabase: Client, limit: int = None, force: bool = False) -> list:
    """
    获取有增强文本的商品
    
    参数:
        supabase: Supabase 客户端
        limit: 限制数量
        force: 是否强制重新生成（不跳过已有向量的）
    """
    # 获取所有有增强文本的商品
    query = supabase.table("gg_taobao_product_apu").select(
        "product_id, enhanced_text"
    ).not_.is_("enhanced_text", "null")
    
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    products = result.data
    
    if not force:
        # 获取已有向量的商品 ID
        embeddings_result = supabase.table("gg_taobao_product_embeddings").select(
            "product_id"
        ).eq("embedding_type", "text_enhanced").execute()
        
        existing_ids = {row["product_id"] for row in embeddings_result.data}
        
        # 过滤出未生成向量的商品
        products = [p for p in products if p["product_id"] not in existing_ids]
    
    return products


def generate_embeddings_batch(openai_client: OpenAI, texts: list) -> list:
    """批量生成文本向量"""
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
    
    # 批量 upsert
    supabase.table("gg_taobao_product_embeddings").upsert(
        embeddings_data,
        on_conflict="product_id,embedding_type"
    ).execute()


def update_original_embeddings(supabase: Client, embeddings_data: list) -> None:
    """
    同时更新原始的 text 类型向量
    这样搜索时使用原有的 text 类型查询也能受益
    """
    if not embeddings_data:
        return
    
    # 转换为 text 类型
    text_embeddings = []
    for item in embeddings_data:
        text_item = item.copy()
        text_item["embedding_type"] = "text"
        text_embeddings.append(text_item)
    
    supabase.table("gg_taobao_product_embeddings").upsert(
        text_embeddings,
        on_conflict="product_id,embedding_type"
    ).execute()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="使用增强文本重新生成商品向量")
    parser.add_argument("--limit", "-l", type=int, help="限制处理数量")
    parser.add_argument("--force", "-f", action="store_true", help="强制重新生成")
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔢 使用增强文本重新生成商品向量")
    print(f"   模型: {EMBEDDING_MODEL}")
    print(f"   维度: {EMBEDDING_DIMENSIONS}")
    print("=" * 70)
    
    # 1. 加载客户端
    supabase, openai_client = load_clients()
    
    # 2. 获取待处理商品
    print(f"\n📋 正在获取待处理商品...")
    products = get_products_with_enhanced_text(supabase, args.limit, args.force)
    print(f"   共 {len(products)} 个商品待处理")
    
    if not products:
        print("\n✅ 所有商品已完成增强向量化！")
        return
    
    # 3. 分批处理
    print(f"\n🚀 开始生成向量 (批大小: {BATCH_SIZE})...")
    
    total_processed = 0
    
    for i in range(0, len(products), BATCH_SIZE):
        batch = products[i:i + BATCH_SIZE]
        
        # 提取增强文本
        texts = [p["enhanced_text"] for p in batch]
        product_ids = [p["product_id"] for p in batch]
        
        try:
            # 生成向量
            embeddings = generate_embeddings_batch(openai_client, texts)
            
            # 构建数据 (text_enhanced 类型)
            embeddings_data = []
            for j, product_id in enumerate(product_ids):
                if embeddings[j]:
                    embeddings_data.append({
                        "product_id": product_id,
                        "embedding_type": "text_enhanced",
                        "embedding_model": EMBEDDING_MODEL,
                        "embedding": embeddings[j],
                        "source_text": texts[j]
                    })
            
            # 保存 text_enhanced 类型
            save_embeddings(supabase, embeddings_data)
            
            # 同时更新 text 类型（覆盖原始向量）
            update_original_embeddings(supabase, embeddings_data)
            
            total_processed += len(batch)
            print(f"   ✅ 已处理 {total_processed}/{len(products)} 个商品")
            
            # 请求间隔
            time.sleep(REQUEST_DELAY)
            
        except Exception as e:
            print(f"   ❌ 批次处理失败: {e}")
            time.sleep(2)
    
    # 4. 统计
    print(f"\n📊 处理完成:")
    print(f"   处理商品数: {total_processed}")
    
    # 验证
    result = supabase.table("gg_taobao_product_embeddings").select(
        "id", count="exact"
    ).eq("embedding_type", "text_enhanced").execute()
    
    print(f"   增强向量数: {result.count}")
    
    result2 = supabase.table("gg_taobao_product_embeddings").select(
        "id", count="exact"
    ).eq("embedding_type", "text").execute()
    
    print(f"   文本向量数 (已更新): {result2.count}")
    
    print("\n" + "=" * 70)
    print("✅ 增强向量化完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()

