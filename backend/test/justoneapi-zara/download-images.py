"""
淘宝商品图片下载脚本 (仅下载图片，不请求 API)
从已有的 JSON 数据中提取图片 URL 并下载

使用页面: 独立测试脚本
功能: 
  1. 读取已有的 page_*.json 文件
  2. 使用多线程并行下载商品主图和附图
  3. 跳过已下载的图片
  4. 建立商品与图片的关联索引

注意: 
  - 使用 HTTP 协议下载图片，避免 SSL 证书问题
  - 不会重新请求 API，只读取本地 JSON 文件
  - 已存在的图片会自动跳过
"""

import os
import json
import requests
import time
import urllib3
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 禁用 SSL 警告 (因为我们使用 HTTP)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 配置区域 ====================
# 源数据目录 (包含 pages 子目录的时间戳目录)
SOURCE_DIR = Path(__file__).parent / "output" / "search-item-list" / "20251202_144931"

# 图片 URL 前缀 (用于拼接 picUrlList 中的相对路径) - 使用 HTTP
IMAGE_URL_PREFIX = "http://g.search2.alicdn.com/img/bao/uploaded/i4/"

# 下载配置
DOWNLOAD_TIMEOUT = 30     # 下载超时时间（秒）
RETRY_COUNT = 3           # 重试次数
RETRY_DELAY = 1           # 重试间隔（秒）
MAX_WORKERS = 5           # 并行下载线程数

# 统计计数器 (线程安全)
stats_lock = Lock()
stats = {
    "downloaded": 0,    # 新下载的图片数
    "skipped": 0,       # 跳过的图片数 (已存在)
    "failed": 0         # 下载失败的图片数
}


def update_stats(key: str, count: int = 1):
    """线程安全地更新统计计数"""
    with stats_lock:
        stats[key] += count


def load_page_data(pages_dir: Path) -> list:
    """
    加载所有页面的 JSON 数据
    
    参数:
        pages_dir: pages 目录路径
    
    返回:
        list: [(page_num, data), ...] 按页码排序
    """
    pages_data = []
    
    # 查找所有 page_*.json 文件
    for json_file in sorted(pages_dir.glob("page_*.json")):
        try:
            # 提取页码
            page_num = int(json_file.stem.split("_")[1])
            
            # 读取 JSON 数据
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            pages_data.append((page_num, data))
            
        except Exception as e:
            print(f"   ❌ 加载失败: {json_file.name} - {e}")
    
    # 按页码排序
    pages_data.sort(key=lambda x: x[0])
    
    return pages_data


def extract_items_from_response(data: dict) -> list:
    """
    从 API 响应中提取商品列表
    """
    if data.get("code") != 0:
        return []
    
    api_data = data.get("data", {})
    if isinstance(api_data, dict):
        model = api_data.get("model", {})
        if isinstance(model, dict):
            return model.get("itemList", [])
    
    return []


def get_image_extension(url: str) -> str:
    """从 URL 中获取图片扩展名"""
    path = url.split("?")[0]
    ext = os.path.splitext(path)[1].lower()
    
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        ext = ".jpg"
    
    return ext


def convert_to_http_url(url: str) -> str:
    """将 HTTPS URL 转换为 HTTP URL"""
    if url.startswith("https://"):
        return url.replace("https://", "http://", 1)
    return url


def build_full_image_url(relative_path: str) -> str:
    """将相对路径拼接为完整的图片 URL (HTTP)"""
    return f"{IMAGE_URL_PREFIX}{relative_path}"


def download_single_image(url: str, save_path: Path) -> tuple:
    """
    下载单张图片 (带重试机制)
    
    参数:
        url: 图片 URL
        save_path: 保存路径
    
    返回:
        tuple: (success: bool, skipped: bool, local_path: str or None)
    """
    # 检查是否已存在
    if save_path.exists() and save_path.stat().st_size > 0:
        return (True, True, str(save_path.relative_to(save_path.parent.parent)))
    
    # 转换为 HTTP
    url = convert_to_http_url(url)
    
    # 添加请求头，模拟浏览器访问
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.taobao.com/",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    for attempt in range(RETRY_COUNT):
        try:
            response = requests.get(
                url, 
                headers=headers,
                timeout=DOWNLOAD_TIMEOUT, 
                stream=True,
                verify=False
            )
            response.raise_for_status()
            
            # 确保父目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return (True, False, str(save_path.relative_to(save_path.parent.parent)))
            
        except Exception as e:
            if attempt < RETRY_COUNT - 1:
                time.sleep(RETRY_DELAY)
            else:
                return (False, False, None)
    
    return (False, False, None)


def download_item_images_task(item: dict, images_dir: Path, page: int) -> dict:
    """
    下载单个商品的所有图片 (用于线程池)
    
    参数:
        item: 商品数据
        images_dir: 图片根目录
        page: 页码
    
    返回:
        dict: 商品索引条目
    """
    item_id = item.get("itemId")
    if not item_id:
        return None
    
    item_dir = images_dir / str(item_id)
    
    result = {
        "item_id": item_id,
        "main_image": None,
        "sub_images": [],
        "main_url": None,
        "sub_urls": [],
        "main_skipped": False,
        "sub_skipped": 0,
        "sub_downloaded": 0,
        "sub_failed": 0
    }
    
    # 下载主图 (picUrlFull)
    main_url = item.get("picUrlFull", "")
    if main_url:
        result["main_url"] = main_url
        ext = get_image_extension(main_url)
        main_path = item_dir / f"main{ext}"
        
        success, skipped, local_path = download_single_image(main_url, main_path)
        if success:
            result["main_image"] = local_path
            result["main_skipped"] = skipped
            if skipped:
                update_stats("skipped")
            else:
                update_stats("downloaded")
        else:
            update_stats("failed")
    
    # 下载附图 (picUrlList)
    pic_list = item.get("picUrlList", [])
    for idx, relative_url in enumerate(pic_list, start=1):
        full_url = build_full_image_url(relative_url)
        result["sub_urls"].append(full_url)
        
        ext = get_image_extension(relative_url)
        sub_path = item_dir / f"{idx}{ext}"
        
        success, skipped, local_path = download_single_image(full_url, sub_path)
        if success:
            result["sub_images"].append(local_path)
            if skipped:
                result["sub_skipped"] += 1
                update_stats("skipped")
            else:
                result["sub_downloaded"] += 1
                update_stats("downloaded")
        else:
            result["sub_failed"] += 1
            update_stats("failed")
    
    # 构建商品索引条目
    index_entry = {
        "item_id": item_id,
        "item_name": item.get("itemName"),
        "shop_id": item.get("shopId"),
        "shop_name": item.get("shopName"),
        "price_yuan": item.get("priceYuanDouble"),
        "discount_price_yuan": item.get("discntPriceYuan"),
        "order_count": item.get("orderPayUV"),
        "item_loc": item.get("itemLoc"),
        "page": page,
        "images": {
            "main": {
                "url": result["main_url"],
                "local_path": result["main_image"]
            },
            "sub": [
                {"url": url, "local_path": path}
                for url, path in zip(result["sub_urls"], result["sub_images"])
            ]
        }
    }
    
    return index_entry


def process_all_items_parallel(pages_data: list, images_dir: Path) -> list:
    """
    使用多线程并行处理所有商品
    
    参数:
        pages_data: 页面数据列表 [(page, data), ...]
        images_dir: 图片目录
    
    返回:
        list: 商品索引列表
    """
    # 收集所有商品任务
    all_tasks = []
    for page, data in pages_data:
        items = extract_items_from_response(data)
        for item in items:
            all_tasks.append((item, images_dir, page))
    
    total_items = len(all_tasks)
    print(f"\n📦 共 {total_items} 个商品待处理，使用 {MAX_WORKERS} 个线程并行下载...")
    
    all_items_index = []
    completed_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_item = {
            executor.submit(download_item_images_task, item, images_dir, page): (item, page)
            for item, images_dir, page in all_tasks
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_item):
            item, page = future_to_item[future]
            completed_count += 1
            
            try:
                index_entry = future.result()
                if index_entry:
                    all_items_index.append(index_entry)
                    
                    # 打印进度
                    item_id = index_entry["item_id"]
                    item_name = (index_entry.get("item_name") or "")[:25]
                    
                    with stats_lock:
                        current_stats = f"[下载:{stats['downloaded']} 跳过:{stats['skipped']} 失败:{stats['failed']}]"
                    
                    print(f"   [{completed_count}/{total_items}] 商品 {item_id}: {item_name}... {current_stats}")
                    
            except Exception as e:
                print(f"   ❌ 处理失败: {e}")
    
    # 按页码和商品ID排序
    all_items_index.sort(key=lambda x: (x["page"], x["item_id"]))
    
    return all_items_index


def save_items_index(root_dir: Path, items_index: list) -> None:
    """保存商品索引文件"""
    index_path = root_dir / "items_index.json"
    
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(items_index, f, ensure_ascii=False, indent=2)
    
    print(f"\n📋 商品索引已保存: {index_path}")
    print(f"   共 {len(items_index)} 个商品")


def save_summary(root_dir: Path, pages_data: list, items_index: list) -> None:
    """保存汇总信息"""
    total_main_images = sum(
        1 for item in items_index 
        if item.get("images", {}).get("main", {}).get("local_path")
    )
    total_sub_images = sum(
        len([s for s in item.get("images", {}).get("sub", []) if s.get("local_path")])
        for item in items_index
    )
    
    summary = {
        "download_time": datetime.now().isoformat(),
        "source_dir": str(SOURCE_DIR),
        "total_pages": len(pages_data),
        "total_items": len(items_index),
        "total_main_images": total_main_images,
        "total_sub_images": total_sub_images,
        "download_stats": {
            "downloaded": stats["downloaded"],
            "skipped": stats["skipped"],
            "failed": stats["failed"]
        },
        "pages": []
    }
    
    for page, data in pages_data:
        items = extract_items_from_response(data)
        page_info = {
            "page": page,
            "code": data.get("code"),
            "item_count": len(items)
        }
        summary["pages"].append(page_info)
    
    summary_path = root_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 汇总信息已保存: {summary_path}")
    print(f"   总页数: {len(pages_data)}")
    print(f"   总商品数: {len(items_index)}")
    print(f"   主图数量: {total_main_images}")
    print(f"   附图数量: {total_sub_images}")


def main():
    """主函数: 从已有 JSON 数据下载商品图片"""
    print("=" * 70)
    print("🖼️  淘宝商品图片下载脚本 (多线程并行下载)")
    print("=" * 70)
    
    pages_dir = SOURCE_DIR / "pages"
    images_dir = SOURCE_DIR / "images"
    
    if not pages_dir.exists():
        print(f"❌ 源目录不存在: {pages_dir}")
        return
    
    images_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 源数据目录: {SOURCE_DIR}")
    print(f"📂 图片输出目录: {images_dir}")
    print(f"🧵 并行线程数: {MAX_WORKERS}")
    
    # 1. 加载所有页面数据
    print(f"\n📖 正在加载 JSON 数据...")
    pages_data = load_page_data(pages_dir)
    print(f"   ✅ 共加载 {len(pages_data)} 个页面")
    
    # 2. 并行处理所有商品并下载图片
    all_items_index = process_all_items_parallel(pages_data, images_dir)
    
    # 3. 保存商品索引
    save_items_index(SOURCE_DIR, all_items_index)
    
    # 4. 保存汇总信息
    save_summary(SOURCE_DIR, pages_data, all_items_index)
    
    print("\n" + "=" * 70)
    print("✅ 图片下载完成！")
    print(f"   📥 新下载: {stats['downloaded']} 张")
    print(f"   ⏭️  跳过: {stats['skipped']} 张 (已存在)")
    print(f"   ❌ 失败: {stats['failed']} 张")
    print(f"📁 结果目录: {SOURCE_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
