"""
上传商品图片到 Supabase Storage
并更新 gg_taobao_product_images 表的 storage_path 字段

使用页面: 独立测试脚本
功能:
  1. 读取本地图片文件
  2. 上传到 Supabase Storage (bucket: product-images)
  3. 更新数据库中的 storage_path 字段
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes

# ==================== 配置区域 ====================
# 源数据目录
SOURCE_DIR = Path(__file__).parent / "output" / "search-item-list" / "20251202_144931"
IMAGES_DIR = SOURCE_DIR / "images"

# Storage bucket 名称
BUCKET_NAME = "product-images"

# 并发上传线程数
MAX_WORKERS = 5


def load_supabase_client() -> Client:
    """加载 Supabase 客户端"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError(f"未找到 SUPABASE_URL 或 SUPABASE_KEY")
    
    print(f"✅ 成功连接 Supabase")
    return create_client(url, key)


def ensure_bucket_exists(supabase: Client) -> None:
    """确保 Storage bucket 存在"""
    try:
        # 尝试获取 bucket 信息
        buckets = supabase.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        
        if BUCKET_NAME not in bucket_names:
            # 创建 bucket (公开访问)
            supabase.storage.create_bucket(
                BUCKET_NAME,
                options={"public": True}
            )
            print(f"📦 已创建 Storage bucket: {BUCKET_NAME}")
        else:
            print(f"📦 Storage bucket 已存在: {BUCKET_NAME}")
            
    except Exception as e:
        print(f"⚠️ 检查 bucket 时出错: {e}")


def get_images_to_upload(supabase: Client) -> list:
    """
    获取需要上传的图片列表
    只获取 storage_path 为空或不以 'product-images/' 开头的记录
    """
    # 查询所有图片记录
    result = supabase.table("gg_taobao_product_images").select(
        "id, item_id, image_type, image_index, storage_path"
    ).execute()
    
    images_to_upload = []
    for row in result.data:
        # 检查本地文件是否存在
        item_id = row["item_id"]
        image_type = row["image_type"]
        image_index = row["image_index"]
        
        if image_type == "main":
            local_path = IMAGES_DIR / str(item_id) / "main.jpg"
        else:
            local_path = IMAGES_DIR / str(item_id) / f"{image_index}.jpg"
        
        # 只上传本地存在且未上传过的图片
        storage_path = row.get("storage_path") or ""
        if local_path.exists() and not storage_path.startswith("product-images/"):
            images_to_upload.append({
                "id": row["id"],
                "item_id": item_id,
                "image_type": image_type,
                "image_index": image_index,
                "local_path": local_path
            })
    
    return images_to_upload


def upload_single_image(supabase: Client, image_info: dict) -> dict:
    """
    上传单张图片到 Storage
    
    返回:
        dict: {"id": ..., "success": bool, "storage_path": str or None}
    """
    item_id = image_info["item_id"]
    image_type = image_info["image_type"]
    image_index = image_info["image_index"]
    local_path = image_info["local_path"]
    
    # 构建 Storage 路径
    if image_type == "main":
        storage_path = f"{item_id}/main.jpg"
    else:
        storage_path = f"{item_id}/{image_index}.jpg"
    
    try:
        # 读取文件
        with open(local_path, "rb") as f:
            file_data = f.read()
        
        # 上传到 Storage
        result = supabase.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )
        
        # 返回完整路径
        full_path = f"{BUCKET_NAME}/{storage_path}"
        return {
            "id": image_info["id"],
            "success": True,
            "storage_path": full_path
        }
        
    except Exception as e:
        error_msg = str(e)
        # 如果是重复上传错误，也算成功
        if "Duplicate" in error_msg or "already exists" in error_msg:
            full_path = f"{BUCKET_NAME}/{storage_path}"
            return {
                "id": image_info["id"],
                "success": True,
                "storage_path": full_path
            }
        return {
            "id": image_info["id"],
            "success": False,
            "storage_path": None,
            "error": error_msg
        }


def update_storage_paths(supabase: Client, results: list) -> None:
    """批量更新数据库中的 storage_path"""
    success_results = [r for r in results if r["success"]]
    
    if not success_results:
        print("   没有需要更新的记录")
        return
    
    # 分批更新
    batch_size = 50
    updated_count = 0
    
    for i in range(0, len(success_results), batch_size):
        batch = success_results[i:i + batch_size]
        
        for result in batch:
            try:
                supabase.table("gg_taobao_product_images").update({
                    "storage_path": result["storage_path"]
                }).eq("id", result["id"]).execute()
                updated_count += 1
            except Exception as e:
                print(f"   ⚠️ 更新失败 ID={result['id']}: {e}")
        
        print(f"   📝 已更新 {updated_count}/{len(success_results)} 条记录")


def main():
    """主函数"""
    print("=" * 70)
    print("📤 上传商品图片到 Supabase Storage")
    print("=" * 70)
    
    # 1. 加载 Supabase 客户端
    supabase = load_supabase_client()
    
    # 2. 确保 bucket 存在
    ensure_bucket_exists(supabase)
    
    # 3. 获取需要上传的图片列表
    print(f"\n📋 正在获取待上传图片列表...")
    images_to_upload = get_images_to_upload(supabase)
    print(f"   共 {len(images_to_upload)} 张图片待上传")
    
    if not images_to_upload:
        print("\n✅ 所有图片已上传完成！")
        return
    
    # 4. 并行上传图片
    print(f"\n🚀 开始上传 (使用 {MAX_WORKERS} 个线程)...")
    
    results = []
    success_count = 0
    fail_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(upload_single_image, supabase, img): img
            for img in images_to_upload
        }
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            
            if result["success"]:
                success_count += 1
            else:
                fail_count += 1
                print(f"   ❌ 上传失败: {result.get('error', 'Unknown error')}")
            
            if i % 50 == 0 or i == len(images_to_upload):
                print(f"   📷 进度: {i}/{len(images_to_upload)} (成功: {success_count}, 失败: {fail_count})")
    
    # 5. 更新数据库
    print(f"\n📝 正在更新数据库...")
    update_storage_paths(supabase, results)
    
    print("\n" + "=" * 70)
    print("✅ 上传完成！")
    print(f"   成功: {success_count} 张")
    print(f"   失败: {fail_count} 张")
    print("=" * 70)


if __name__ == "__main__":
    main()

