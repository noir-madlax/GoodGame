"""
商品图片向量化脚本
使用 CLIP 模型生成图片向量，支持图片相似度搜索

使用页面: 独立测试脚本
功能:
  1. 从本地读取商品图片
  2. 使用 CLIP 模型生成向量
  3. 存储到 gg_taobao_image_embeddings 表

模型信息:
  - 模型: openai/clip-vit-base-patch32
  - 向量维度: 512
  - 本地运行，无需 API 费用

依赖安装:
  pip install transformers torch pillow
"""

import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from supabase import create_client, Client
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

# ==================== 配置区域 ====================
# 源数据目录
SOURCE_DIR = Path(__file__).parent / "output" / "search-item-list" / "20251202_144931"
IMAGES_DIR = SOURCE_DIR / "images"

# CLIP 模型配置
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
EMBEDDING_DIMENSIONS = 512  # clip-vit-base-patch32 的向量维度

# 并发配置
MAX_WORKERS = 4  # 图片处理线程数
BATCH_SIZE = 20  # 数据库批量写入大小


class CLIPEmbedder:
    """CLIP 图片向量生成器"""
    
    def __init__(self, model_name: str = CLIP_MODEL_NAME):
        """
        初始化 CLIP 模型
        
        参数:
            model_name: CLIP 模型名称
        """
        print(f"📦 正在加载 CLIP 模型: {model_name}")
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"   使用设备: {self.device}")
        
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()  # 设置为评估模式
        print(f"✅ CLIP 模型加载完成")
    
    def get_image_embedding(self, image_path: str) -> list:
        """
        生成单张图片的向量
        
        参数:
            image_path: 图片路径
        
        返回:
            list: 512 维向量
        """
        try:
            # 加载图片
            image = Image.open(image_path).convert("RGB")
            
            # 处理图片
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 生成向量
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            # 归一化
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # 转换为列表
            embedding = image_features.cpu().numpy()[0].tolist()
            
            return embedding
            
        except Exception as e:
            print(f"   ⚠️ 图片处理失败 {image_path}: {e}")
            return None


def load_supabase_client() -> Client:
    """加载 Supabase 客户端"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("未找到 SUPABASE_URL 或 SUPABASE_KEY")
    
    print(f"✅ 成功连接 Supabase")
    return create_client(url, key)


def get_images_without_embeddings(supabase: Client, include_sub: bool = True) -> list:
    """
    获取还没有生成向量的图片
    
    参数:
        supabase: Supabase 客户端
        include_sub: 是否包含副图 (默认 True，处理所有图片)
    """
    # 获取所有图片 (主图 + 副图)
    # 注意: Supabase 默认只返回 1000 条，需要分页获取全部
    all_images = []
    offset = 0
    limit = 1000
    
    while True:
        query = supabase.table("gg_taobao_product_images").select(
            "id, product_id, item_id, image_type, image_index, storage_path"
        ).range(offset, offset + limit - 1)
        
        if not include_sub:
            query = query.eq("image_type", "main")
        
        result = query.execute()
        all_images.extend(result.data)
        
        if len(result.data) < limit:
            break
        offset += limit
    
    # 获取已有向量的图片 ID (同样需要分页)
    all_embeddings = []
    offset = 0
    
    while True:
        result = supabase.table("gg_taobao_image_embeddings").select(
            "image_id"
        ).range(offset, offset + limit - 1).execute()
        all_embeddings.extend(result.data)
        
        if len(result.data) < limit:
            break
        offset += limit
    
    existing_ids = {row["image_id"] for row in all_embeddings}
    
    # 过滤出未生成向量的图片
    images = []
    for img in all_images:
        if img["id"] not in existing_ids:
            # 构建本地路径
            item_id = img["item_id"]
            image_type = img["image_type"]
            image_index = img["image_index"]
            
            # 根据图片类型构建文件名
            if image_type == "main":
                filename = "main.jpg"
            else:
                filename = f"{image_index}.jpg"
            
            local_path = IMAGES_DIR / str(item_id) / filename
            
            if local_path.exists():
                img["local_path"] = str(local_path)
                images.append(img)
    
    return images


def process_single_image(embedder: CLIPEmbedder, image_info: dict) -> dict:
    """
    处理单张图片，生成向量
    
    参数:
        embedder: CLIP 向量生成器
        image_info: 图片信息
    
    返回:
        dict: 包含向量的结果
    """
    local_path = image_info["local_path"]
    
    embedding = embedder.get_image_embedding(local_path)
    
    if embedding:
        return {
            "image_id": image_info["id"],
            "product_id": image_info["product_id"],
            "item_id": image_info["item_id"],
            "embedding_model": CLIP_MODEL_NAME,
            "embedding": embedding,
            "success": True
        }
    else:
        return {
            "image_id": image_info["id"],
            "success": False
        }


def save_embeddings_batch(supabase: Client, embeddings: list) -> int:
    """批量保存向量到数据库"""
    if not embeddings:
        return 0
    
    # 过滤成功的结果
    valid_embeddings = [
        {
            "image_id": e["image_id"],
            "product_id": e["product_id"],
            "item_id": e["item_id"],
            "embedding_model": e["embedding_model"],
            "embedding": e["embedding"]
        }
        for e in embeddings if e["success"]
    ]
    
    if not valid_embeddings:
        return 0
    
    try:
        supabase.table("gg_taobao_image_embeddings").upsert(
            valid_embeddings,
            on_conflict="image_id"
        ).execute()
        return len(valid_embeddings)
    except Exception as e:
        print(f"   ⚠️ 批量保存失败: {e}")
        return 0


def main():
    """主函数"""
    print("=" * 70)
    print("🖼️  商品图片向量化 (CLIP)")
    print("=" * 70)
    
    # 1. 加载 Supabase 客户端
    supabase = load_supabase_client()
    
    # 2. 加载 CLIP 模型
    embedder = CLIPEmbedder()
    
    # 3. 获取待处理图片 (包含主图和副图)
    print(f"\n📋 正在获取待处理图片...")
    images = get_images_without_embeddings(supabase, include_sub=True)
    print(f"   共 {len(images)} 张图片待处理 (主图 + 副图)")
    
    if not images:
        print("\n✅ 所有图片已完成向量化！")
        return
    
    # 4. 处理图片 (使用线程池)
    print(f"\n🚀 开始生成向量...")
    
    total_processed = 0
    total_success = 0
    batch_results = []
    
    start_time = time.time()
    
    # 由于 CLIP 模型在 GPU/MPS 上运行，使用较少的线程避免内存问题
    for i, image_info in enumerate(images, 1):
        result = process_single_image(embedder, image_info)
        batch_results.append(result)
        
        if result["success"]:
            total_success += 1
        
        # 批量保存
        if len(batch_results) >= BATCH_SIZE:
            saved = save_embeddings_batch(supabase, batch_results)
            batch_results = []
            
            elapsed = time.time() - start_time
            speed = i / elapsed if elapsed > 0 else 0
            print(f"   ✅ 进度: {i}/{len(images)} (成功: {total_success}, 速度: {speed:.1f} 张/秒)")
        
        total_processed += 1
    
    # 保存剩余的
    if batch_results:
        save_embeddings_batch(supabase, batch_results)
    
    # 5. 统计
    elapsed = time.time() - start_time
    
    print(f"\n📊 处理完成:")
    print(f"   处理图片数: {total_processed}")
    print(f"   成功数: {total_success}")
    print(f"   耗时: {elapsed:.1f} 秒")
    print(f"   平均速度: {total_processed / elapsed:.1f} 张/秒")
    
    # 验证
    result = supabase.table("gg_taobao_image_embeddings").select(
        "id", count="exact"
    ).execute()
    
    print(f"   数据库向量数: {result.count}")
    
    print("\n" + "=" * 70)
    print("✅ 图片向量化完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()

