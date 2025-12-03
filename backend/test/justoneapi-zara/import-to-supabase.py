"""
淘宝商品数据导入 Supabase 脚本
将爬取的商品数据和图片信息导入到 Supabase 数据库

使用页面: 独立测试脚本
功能:
  1. 读取 items_index.json 商品索引文件
  2. 将商品基础信息导入 gg_taobao_products 表
  3. 将图片信息导入 gg_taobao_product_images 表
  4. 上传图片到 Supabase Storage (可选)

注意:
  - 需要配置 SUPABASE_URL 和 SUPABASE_KEY 环境变量
  - 图片上传是可选的，可以只存储 URL
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# ==================== 配置区域 ====================
# 源数据目录
SOURCE_DIR = Path(__file__).parent / "output" / "search-item-list" / "20251202_144931"

# 搜索关键词 (用于标记数据来源)
SEARCH_KEYWORD = "zara"

# 是否上传图片到 Storage (暂时关闭，先只存储 URL)
UPLOAD_IMAGES = False


def load_supabase_client() -> Client:
    """
    加载 Supabase 客户端
    
    返回:
        Client: Supabase 客户端实例
    """
    # 加载 backend/.env 文件
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError(
            f"未找到 SUPABASE_URL 或 SUPABASE_KEY 环境变量，请检查 {env_path} 文件"
        )
    
    print(f"✅ 成功连接 Supabase: {url[:30]}...")
    return create_client(url, key)


def load_items_index(source_dir: Path) -> list:
    """
    加载商品索引文件
    
    参数:
        source_dir: 数据目录
    
    返回:
        list: 商品列表
    """
    index_path = source_dir / "items_index.json"
    
    if not index_path.exists():
        raise FileNotFoundError(f"商品索引文件不存在: {index_path}")
    
    with open(index_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    print(f"📖 已加载 {len(items)} 个商品")
    return items


def import_products(supabase: Client, items: list) -> dict:
    """
    导入商品数据到 gg_taobao_products 表
    
    参数:
        supabase: Supabase 客户端
        items: 商品列表
    
    返回:
        dict: item_id -> product_id 的映射
    """
    print(f"\n📦 正在导入商品数据...")
    
    # 去重：使用 item_id 作为 key，保留最后一个
    unique_items = {}
    for item in items:
        unique_items[item["item_id"]] = item
    
    print(f"   原始商品数: {len(items)}, 去重后: {len(unique_items)}")
    
    # 构建商品数据
    products_data = []
    for item in unique_items.values():
        # 提取主图和附图 URL
        main_image = item.get("images", {}).get("main", {})
        sub_images = item.get("images", {}).get("sub", [])
        
        product = {
            "item_id": item["item_id"],
            "item_name": item.get("item_name"),
            "shop_id": item.get("shop_id"),
            "shop_name": item.get("shop_name"),
            "price_yuan": item.get("price_yuan"),
            "discount_price_yuan": item.get("discount_price_yuan"),
            "order_count": item.get("order_count"),
            "item_loc": item.get("item_loc"),
            "main_image_url": main_image.get("url"),
            "sub_image_urls": [img.get("url") for img in sub_images if img.get("url")],
            "search_keyword": SEARCH_KEYWORD,
            "raw_data": item  # 保存完整原始数据
        }
        products_data.append(product)
    
    # 批量插入 (使用 upsert 避免重复)
    result = supabase.table("gg_taobao_products").upsert(
        products_data,
        on_conflict="item_id"  # 如果 item_id 已存在则更新
    ).execute()
    
    print(f"   ✅ 成功导入 {len(result.data)} 个商品")
    
    # 获取 item_id -> id 的映射
    item_id_map = {}
    for row in result.data:
        item_id_map[row["item_id"]] = row["id"]
    
    return item_id_map


def import_product_images(supabase: Client, items: list, item_id_map: dict) -> None:
    """
    导入商品图片数据到 gg_taobao_product_images 表
    
    参数:
        supabase: Supabase 客户端
        items: 商品列表
        item_id_map: item_id -> product_id 的映射
    """
    print(f"\n🖼️  正在导入图片数据...")
    
    # 构建图片数据
    images_data = []
    for item in items:
        item_id = item["item_id"]
        product_id = item_id_map.get(item_id)
        
        if not product_id:
            print(f"   ⚠️ 未找到商品 {item_id} 的 product_id，跳过图片导入")
            continue
        
        # 主图
        main_image = item.get("images", {}).get("main", {})
        if main_image.get("url"):
            images_data.append({
                "product_id": product_id,
                "item_id": item_id,
                "image_type": "main",
                "image_index": 0,
                "image_url": main_image.get("url"),
                "storage_path": main_image.get("local_path")  # 本地路径作为参考
            })
        
        # 附图
        sub_images = item.get("images", {}).get("sub", [])
        for idx, sub_image in enumerate(sub_images, start=1):
            if sub_image.get("url"):
                images_data.append({
                    "product_id": product_id,
                    "item_id": item_id,
                    "image_type": "sub",
                    "image_index": idx,
                    "image_url": sub_image.get("url"),
                    "storage_path": sub_image.get("local_path")
                })
    
    # 分批插入 (每批 100 条)
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(images_data), batch_size):
        batch = images_data[i:i + batch_size]
        
        try:
            result = supabase.table("gg_taobao_product_images").insert(batch).execute()
            total_inserted += len(result.data)
            print(f"   📷 已插入 {total_inserted}/{len(images_data)} 条图片记录")
        except Exception as e:
            print(f"   ❌ 批次插入失败: {e}")
    
    print(f"   ✅ 成功导入 {total_inserted} 条图片记录")


def print_summary(supabase: Client) -> None:
    """
    打印导入结果汇总
    """
    print(f"\n📊 导入结果汇总:")
    
    # 查询商品数量
    products_count = supabase.table("gg_taobao_products").select(
        "id", count="exact"
    ).eq("search_keyword", SEARCH_KEYWORD).execute()
    
    # 查询图片数量
    images_count = supabase.table("gg_taobao_product_images").select(
        "id", count="exact"
    ).execute()
    
    print(f"   商品数量: {products_count.count}")
    print(f"   图片数量: {images_count.count}")


def main():
    """
    主函数: 导入商品数据到 Supabase
    """
    print("=" * 70)
    print("📤 淘宝商品数据导入 Supabase")
    print("=" * 70)
    
    # 1. 加载 Supabase 客户端
    supabase = load_supabase_client()
    
    # 2. 加载商品索引
    items = load_items_index(SOURCE_DIR)
    
    # 3. 导入商品数据
    item_id_map = import_products(supabase, items)
    
    # 4. 导入图片数据
    import_product_images(supabase, items, item_id_map)
    
    # 5. 打印汇总
    print_summary(supabase)
    
    print("\n" + "=" * 70)
    print("✅ 数据导入完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()

