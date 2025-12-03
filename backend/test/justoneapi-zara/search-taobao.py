"""
淘宝/天猫商品搜索脚本 (含图片下载)
使用 Just One API 的 /api/taobao/search-item-list/v1 接口
搜索关键词: zara
筛选条件: 仅天猫商品 (tmall=true), 按销量排序 (sort=_sale)

使用页面: 独立测试脚本
功能: 
  1. 批量请求淘宝天猫商品搜索接口
  2. 下载商品主图和附图
  3. 建立商品与图片的关联索引

目录结构:
  output/search-item-list/{timestamp}/
  ├── pages/                    # 原始 JSON 数据
  │   ├── page_1.json
  │   └── ...
  ├── images/                   # 图片目录
  │   └── {itemId}/            # 按商品 ID 分目录
  │       ├── main.jpg         # 主图 (picUrlFull)
  │       ├── 1.jpg            # 附图1 (picUrlList[0])
  │       └── ...
  ├── items_index.json          # 商品索引（itemId -> 商品信息 + 图片路径映射）
  └── summary.json              # 汇总信息
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# ==================== 配置区域 ====================
# API 基础 URL
BASE_URL = "http://47.117.133.51:30015"

# 搜索接口路径
SEARCH_ENDPOINT = "/api/taobao/search-item-list/v1"

# 搜索参数配置
KEYWORD = "zara"  # 搜索关键词
SORT = "_sale"    # 排序方式: _sale=按销量排序
TMALL = True      # 是否仅搜索天猫商品

# 图片 URL 前缀 (用于拼接 picUrlList 中的相对路径)
IMAGE_URL_PREFIX = "https://g.search2.alicdn.com/img/bao/uploaded/i4/"

# 下载配置
MAX_DOWNLOAD_WORKERS = 5  # 并发下载线程数
DOWNLOAD_TIMEOUT = 30     # 下载超时时间（秒）
REQUEST_DELAY = 0.5       # 请求间隔（秒），避免频率限制


def load_api_key() -> str:
    """
    从 .env 文件加载 API Key
    
    返回:
        str: JUSTONEAPI_API_KEY 的值
    
    异常:
        ValueError: 如果未找到 API Key
    """
    # 加载 backend/.env 文件
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    api_key = os.getenv("JUSTONEAPI_API_KEY")
    if not api_key:
        raise ValueError(
            f"未找到 JUSTONEAPI_API_KEY 环境变量，请检查 {env_path} 文件"
        )
    
    print(f"✅ 成功加载 API Key: {api_key[:8]}...")
    return api_key


def create_output_dirs(timestamp: str = None) -> dict:
    """
    创建输出目录结构
    
    参数:
        timestamp: 时间戳字符串，如果为 None 则自动生成
    
    返回:
        dict: 包含各目录路径的字典
            - root: 根目录
            - pages: JSON 数据目录
            - images: 图片目录
    """
    # 生成时间戳目录名
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 创建目录路径
    root_dir = Path(__file__).parent / "output" / "search-item-list" / timestamp
    pages_dir = root_dir / "pages"
    images_dir = root_dir / "images"
    
    # 创建目录
    pages_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    
    dirs = {
        "root": root_dir,
        "pages": pages_dir,
        "images": images_dir,
        "timestamp": timestamp
    }
    
    print(f"📁 输出目录: {root_dir}")
    return dirs


def search_taobao(
    token: str,
    keyword: str,
    page: int,
    sort: str = "_sale",
    tmall: bool = True
) -> dict:
    """
    调用淘宝/天猫商品搜索接口
    
    参数:
        token: API Token (JUSTONEAPI_API_KEY)
        keyword: 搜索关键词
        page: 页码 (从 1 开始)
        sort: 排序方式 (_sale=销量, _bid=价格降序, bid=价格升序, _coefp=综合)
        tmall: 是否仅搜索天猫商品
    
    返回:
        dict: API 响应的 JSON 数据
    """
    # 构建请求参数
    params = {
        "token": token,
        "keyword": keyword,
        "sort": sort,
        "tmall": str(tmall).lower(),
        "page": page
    }
    
    # 构建完整 URL
    url = f"{BASE_URL}{SEARCH_ENDPOINT}"
    
    print(f"\n🔍 正在请求第 {page} 页...")
    print(f"   参数: keyword={keyword}, sort={sort}, tmall={tmall}, page={page}")
    
    # 发送 GET 请求
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    
    # 解析 JSON 响应
    data = response.json()
    
    # 打印响应状态
    code = data.get("code", "unknown")
    message = data.get("message", "")
    print(f"   响应状态: code={code}, message={message}")
    
    return data


def save_page_response(pages_dir: Path, page: int, data: dict) -> None:
    """
    保存 API 响应到 JSON 文件
    
    参数:
        pages_dir: pages 目录路径
        page: 页码
        data: API 响应数据
    """
    filename = f"page_{page}.json"
    filepath = pages_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"   💾 已保存: {filepath.name}")


def extract_items_from_response(data: dict) -> list:
    """
    从 API 响应中提取商品列表
    
    参数:
        data: API 响应数据
    
    返回:
        list: 商品列表
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
    """
    从 URL 中获取图片扩展名
    
    参数:
        url: 图片 URL
    
    返回:
        str: 扩展名 (如 .jpg, .png)
    """
    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[1].lower()
    
    # 默认使用 .jpg
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        ext = ".jpg"
    
    return ext


def build_full_image_url(relative_path: str) -> str:
    """
    将相对路径拼接为完整的图片 URL
    
    参数:
        relative_path: 相对路径 (如 "i1/2228361831/xxx.jpg")
    
    返回:
        str: 完整的图片 URL
    """
    return f"{IMAGE_URL_PREFIX}{relative_path}"


def download_image(url: str, save_path: Path) -> bool:
    """
    下载单张图片
    
    参数:
        url: 图片 URL
        save_path: 保存路径
    
    返回:
        bool: 是否下载成功
    """
    try:
        response = requests.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True)
        response.raise_for_status()
        
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        print(f"      ⚠️ 下载失败: {url} - {e}")
        return False


def download_item_images(
    item: dict,
    images_dir: Path
) -> dict:
    """
    下载单个商品的所有图片
    
    参数:
        item: 商品数据
        images_dir: 图片根目录
    
    返回:
        dict: 图片下载结果
            - item_id: 商品 ID
            - main_image: 主图本地路径 (相对于 images_dir)
            - sub_images: 附图本地路径列表
            - main_url: 主图原始 URL
            - sub_urls: 附图原始 URL 列表
    """
    item_id = item.get("itemId")
    if not item_id:
        return None
    
    # 创建商品图片目录
    item_dir = images_dir / str(item_id)
    item_dir.mkdir(parents=True, exist_ok=True)
    
    result = {
        "item_id": item_id,
        "main_image": None,
        "sub_images": [],
        "main_url": None,
        "sub_urls": []
    }
    
    # 下载主图 (picUrlFull)
    main_url = item.get("picUrlFull", "")
    if main_url:
        result["main_url"] = main_url
        ext = get_image_extension(main_url)
        main_path = item_dir / f"main{ext}"
        
        if download_image(main_url, main_path):
            # 存储相对路径 (相对于 images_dir)
            result["main_image"] = f"{item_id}/main{ext}"
    
    # 下载附图 (picUrlList)
    pic_list = item.get("picUrlList", [])
    for idx, relative_url in enumerate(pic_list, start=1):
        full_url = build_full_image_url(relative_url)
        result["sub_urls"].append(full_url)
        
        ext = get_image_extension(relative_url)
        sub_path = item_dir / f"{idx}{ext}"
        
        if download_image(full_url, sub_path):
            result["sub_images"].append(f"{item_id}/{idx}{ext}")
    
    return result


def process_items_and_download_images(
    items: list,
    images_dir: Path,
    page: int
) -> list:
    """
    处理商品列表并下载图片
    
    参数:
        items: 商品列表
        images_dir: 图片目录
        page: 当前页码 (用于日志)
    
    返回:
        list: 商品索引列表 (包含商品信息和图片路径)
    """
    items_index = []
    
    print(f"\n📷 正在下载第 {page} 页的商品图片 (共 {len(items)} 个商品)...")
    
    for idx, item in enumerate(items, start=1):
        item_id = item.get("itemId")
        item_name = item.get("itemName", "")[:30]  # 截取前30个字符
        print(f"   [{idx}/{len(items)}] 商品 {item_id}: {item_name}...")
        
        # 下载图片
        image_result = download_item_images(item, images_dir)
        
        if image_result:
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
                # 图片信息
                "images": {
                    "main": {
                        "url": image_result["main_url"],
                        "local_path": image_result["main_image"]
                    },
                    "sub": [
                        {"url": url, "local_path": path}
                        for url, path in zip(
                            image_result["sub_urls"],
                            image_result["sub_images"]
                        )
                    ]
                }
            }
            items_index.append(index_entry)
            
            # 统计下载成功数
            main_ok = 1 if image_result["main_image"] else 0
            sub_ok = len(image_result["sub_images"])
            sub_total = len(image_result["sub_urls"])
            print(f"      ✅ 主图: {main_ok}/1, 附图: {sub_ok}/{sub_total}")
        
        # 添加短暂延迟，避免请求过快
        time.sleep(0.1)
    
    return items_index


def save_items_index(root_dir: Path, items_index: list) -> None:
    """
    保存商品索引文件
    
    参数:
        root_dir: 根目录
        items_index: 商品索引列表
    """
    index_path = root_dir / "items_index.json"
    
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(items_index, f, ensure_ascii=False, indent=2)
    
    print(f"\n📋 商品索引已保存: {index_path}")
    print(f"   共 {len(items_index)} 个商品")


def save_summary(root_dir: Path, pages_results: list, items_index: list) -> None:
    """
    保存汇总信息
    
    参数:
        root_dir: 根目录
        pages_results: 页面请求结果列表 [(page, data), ...]
        items_index: 商品索引列表
    """
    # 统计图片数量
    total_main_images = sum(
        1 for item in items_index 
        if item.get("images", {}).get("main", {}).get("local_path")
    )
    total_sub_images = sum(
        len(item.get("images", {}).get("sub", []))
        for item in items_index
    )
    
    summary = {
        "search_time": datetime.now().isoformat(),
        "keyword": KEYWORD,
        "sort": SORT,
        "tmall": TMALL,
        "total_pages": len(pages_results),
        "total_items": len(items_index),
        "total_main_images": total_main_images,
        "total_sub_images": total_sub_images,
        "pages": []
    }
    
    for page, data in pages_results:
        items = extract_items_from_response(data)
        page_info = {
            "page": page,
            "code": data.get("code"),
            "message": data.get("message", ""),
            "item_count": len(items)
        }
        summary["pages"].append(page_info)
    
    summary_path = root_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 汇总信息已保存: {summary_path}")
    print(f"   总页数: {len(pages_results)}")
    print(f"   总商品数: {len(items_index)}")
    print(f"   主图数量: {total_main_images}")
    print(f"   附图数量: {total_sub_images}")


def fetch_and_download(
    api_key: str,
    pages: list,
    dirs: dict
) -> tuple:
    """
    获取商品数据并下载图片
    
    参数:
        api_key: API Key
        pages: 页码列表
        dirs: 目录路径字典
    
    返回:
        tuple: (pages_results, items_index)
    """
    pages_results = []
    all_items_index = []
    
    for page in pages:
        try:
            # 请求数据
            data = search_taobao(
                token=api_key,
                keyword=KEYWORD,
                page=page,
                sort=SORT,
                tmall=TMALL
            )
            
            # 保存 JSON 响应
            save_page_response(dirs["pages"], page, data)
            pages_results.append((page, data))
            
            # 提取商品列表
            items = extract_items_from_response(data)
            
            # 下载图片并建立索引
            if items:
                page_index = process_items_and_download_images(
                    items, dirs["images"], page
                )
                all_items_index.extend(page_index)
            
            # 请求间隔
            time.sleep(REQUEST_DELAY)
            
        except requests.RequestException as e:
            print(f"   ❌ 请求失败: {e}")
            error_data = {"error": str(e), "page": page}
            save_page_response(dirs["pages"], page, error_data)
            pages_results.append((page, error_data))
    
    return pages_results, all_items_index


def main():
    """
    主函数: 执行淘宝商品搜索并下载图片
    """
    print("=" * 70)
    print("🛒 淘宝/天猫商品搜索脚本 (含图片下载)")
    print("=" * 70)
    
    # 配置要获取的页码 (1-30 页)
    pages = list(range(1, 31))  # 第 1-30 页
    
    print(f"\n📋 任务配置:")
    print(f"   关键词: {KEYWORD}")
    print(f"   仅天猫: {TMALL}")
    print(f"   排序: {SORT}")
    print(f"   页码范围: {pages[0]}-{pages[-1]} (共 {len(pages)} 页)")
    
    # 1. 加载 API Key
    api_key = load_api_key()
    
    # 2. 创建输出目录
    dirs = create_output_dirs()
    
    # 3. 获取数据并下载图片
    pages_results, items_index = fetch_and_download(api_key, pages, dirs)
    
    # 4. 保存商品索引
    save_items_index(dirs["root"], items_index)
    
    # 5. 保存汇总信息
    save_summary(dirs["root"], pages_results, items_index)
    
    print("\n" + "=" * 70)
    print("✅ 任务完成！")
    print(f"📁 结果目录: {dirs['root']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
