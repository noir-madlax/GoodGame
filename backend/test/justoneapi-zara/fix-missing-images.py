"""
补充上传缺失的图片到 Supabase Storage

功能:
  1. 检查数据库中的图片记录
  2. 验证 Storage 中是否存在
  3. 如果不存在，从本地上传
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置区域 ====================
SOURCE_DIR = Path(__file__).parent / "output" / "search-item-list" / "20251202_144931"
IMAGES_DIR = SOURCE_DIR / "images"
BUCKET_NAME = "product-images"
MAX_WORKERS = 5


def load_supabase_client() -> Client:
    """加载 Supabase 客户端"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("未找到 SUPABASE_URL 或 SUPABASE_KEY")
    
    return create_client(url, key)


def check_image_exists_in_storage(supabase_url: str, storage_path: str) -> bool:
    """检查图片是否在 Storage 中存在"""
    url = f"{supabase_url}/storage/v1/object/public/{storage_path}"
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except:
        return False


def upload_image(supabase: Client, item_id: int, image_type: str, image_index: int = 0) -> bool:
    """上传单张图片"""
    # 确定本地文件路径
    if image_type == 'main':
        local_path = IMAGES_DIR / str(item_id) / "main.jpg"
        storage_path = f"product-images/{item_id}/main.jpg"
    else:
        local_path = IMAGES_DIR / str(item_id) / f"{image_index}.jpg"
        storage_path = f"product-images/{item_id}/{image_index}.jpg"
    
    if not local_path.exists():
        print(f"  ❌ 本地文件不存在: {local_path}")
        return False
    
    try:
        # 读取文件内容
        with open(local_path, "rb") as f:
            file_content = f.read()
        
        # 上传到 Storage
        result = supabase.storage.from_(BUCKET_NAME).upload(
            path=f"{item_id}/{'main' if image_type == 'main' else image_index}.jpg",
            file=file_content,
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )
        
        print(f"  ✅ 上传成功: {storage_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ 上传失败: {storage_path} - {e}")
        return False


def main():
    print("=" * 60)
    print("补充上传缺失的图片到 Supabase Storage")
    print("=" * 60)
    
    # 连接 Supabase
    supabase = load_supabase_client()
    supabase_url = os.getenv("SUPABASE_URL")
    print(f"✅ 已连接 Supabase")
    
    # 获取所有主图记录
    print("\n📋 获取数据库中的主图记录...")
    response = supabase.table("gg_taobao_product_images").select(
        "id, item_id, image_type, image_index, storage_path"
    ).eq("image_type", "main").execute()
    
    images = response.data
    print(f"  共 {len(images)} 条主图记录")
    
    # 检查哪些图片缺失
    missing_images = []
    print("\n🔍 检查 Storage 中的图片...")
    
    for img in images:
        storage_path = img.get("storage_path")
        if not storage_path:
            missing_images.append(img)
            continue
            
        exists = check_image_exists_in_storage(supabase_url, storage_path)
        if not exists:
            missing_images.append(img)
    
    print(f"  缺失 {len(missing_images)} 张图片")
    
    if not missing_images:
        print("\n✅ 所有图片都已存在，无需上传")
        return
    
    # 上传缺失的图片
    print(f"\n📤 开始上传 {len(missing_images)} 张缺失的图片...")
    
    success_count = 0
    fail_count = 0
    
    for img in missing_images:
        item_id = img["item_id"]
        print(f"\n处理 item_id: {item_id}")
        
        if upload_image(supabase, item_id, "main"):
            success_count += 1
        else:
            fail_count += 1
    
    # 统计结果
    print("\n" + "=" * 60)
    print("上传完成统计:")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ❌ 失败: {fail_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()

