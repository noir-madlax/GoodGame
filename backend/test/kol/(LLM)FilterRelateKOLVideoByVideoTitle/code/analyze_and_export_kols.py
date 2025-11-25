import os
import json
import time
import asyncio
import aiohttp
import csv
from typing import List, Dict, Set
from supabase import create_client, Client

# 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CACHE_FILE = os.path.join(OUTPUT_DIR, "video_analysis_cache.jsonl")
FULL_KOL_LIST_JSON = os.path.join(OUTPUT_DIR, "all_kols_skincare_stats.json")
FULL_KOL_LIST_CSV = os.path.join(OUTPUT_DIR, "all_kols_skincare_stats.csv")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENROUTER_API_KEY]):
    print("❌ 错误: 缺少必要的环境变量")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_cache() -> Dict[str, bool]:
    """加载本地缓存的分析结果"""
    cache = {}
    if os.path.exists(CACHE_FILE):
        print(f"📖 读取本地缓存: {CACHE_FILE}")
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    cache.update(data)
                except json.JSONDecodeError:
                    continue
        print(f"✅ 已加载 {len(cache)} 条缓存记录")
    return cache

def append_to_cache(results: Dict[str, bool]):
    """将新结果追加到本地缓存"""
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        for vid, is_related in results.items():
            json.dump({vid: is_related}, f, ensure_ascii=False)
            f.write("\n")

async def analyze_titles_batch(session: aiohttp.ClientSession, titles_batch: List[Dict]) -> Dict[str, bool]:
    """调用 LLM 分析一批标题"""
    prompt = """
你是一个专业的社交媒体内容分析师，专注于美妆和护肤领域。
请分析以下抖音视频标题，判断其内容是否主要与"护肤"（Skincare）、"美容"（Beauty）、"身体保养"（Body Care）或"美妆产品"（Cosmetics）相关。

判断标准：
1. ✅ 相关 (true): 包含皮肤问题（痘痘/黑头/美白/抗老）、护肤步骤、护肤品测评、化妆教程、美容仪器、医美体验等。
2. ❌ 不相关 (false): 游戏、美食、搞笑剧情、萌宠、数码、汽车、单纯的舞蹈/变装（无美妆教学）、一般的日常生活记录（未提及护肤品）。

请以 JSON 格式返回结果，Key 为视频 ID，Value 为 布尔值 (true/false)。

待分析标题列表：
"""
    for item in titles_batch:
        prompt += f'- ID: "{item["id"]}", 标题: "{item["title"]}"\n'
    
    prompt += "\n结果 JSON:"

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful JSON outputting assistant."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://goodgame.ai",
        "X-Title": "GoodGame Content Analysis"
    }

    try:
        async with session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                print(f"⚠️ API Error: {resp.status} - {error_text[:100]}")
                return {}
            
            result = await resp.json()
            content = result['choices'][0]['message']['content']
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            return json.loads(content.strip())
    except Exception as e:
        print(f"⚠️ Exception: {e}")
        return {}

async def main():
    # 1. 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 2. 加载缓存
    cached_results = load_cache()
    
    print("🚀 开始获取数据库视频数据...")
    try:
        videos = []
        batch_size = 1000
        offset = 0
        while True:
            print(f"  正在获取数据: offset={offset}, limit={batch_size}...")
            response = supabase.table("gg_xingtu_kol_videos")\
                .select("id, kol_id, item_title, item_publish_time")\
                .neq("item_title", "")\
                .not_.is_("item_title", "null")\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            batch_data = response.data
            if not batch_data:
                print("  ⚠️ 未获取到更多数据，停止加载。")
                break
            
            videos.extend(batch_data)
            current_count = len(batch_data)
            print(f"  已加载 {current_count} 条数据 (总计: {len(videos)})")
            
            if current_count < batch_size:
                print("  ⚠️ 数据量小于 batch_size，视为最后一页。")
                break
                
            offset += batch_size
    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")
        return

    print(f"✅ 总共获取到 {len(videos)} 条非空标题视频")
    
    # 3. 过滤出需要分析的视频（未缓存的）
    videos_to_analyze = [v for v in videos if str(v["id"]) not in cached_results]
    print(f"📊 需分析新视频: {len(videos_to_analyze)} 条 (已缓存 {len(cached_results)} 条)")
    
    # 4. 执行 LLM 分析
    if videos_to_analyze:
        BATCH_SIZE = 50
        batches = [videos_to_analyze[i:i + BATCH_SIZE] for i in range(0, len(videos_to_analyze), BATCH_SIZE)]
        
        print(f"📦 分为 {len(batches)} 个批次进行处理...")
        
        async with aiohttp.ClientSession() as session:
            sem = asyncio.Semaphore(10) # 并发控制

            async def process_batch(batch, idx):
                async with sem:
                    # 准备数据
                    input_data = [{"id": str(v["id"]), "title": v["item_title"]} for v in batch]
                    
                    # 调用 API
                    print(f"  🔄 处理批次 {idx+1}/{len(batches)}...")
                    batch_result = await analyze_titles_batch(session, input_data)
                    
                    if batch_result:
                        # 立即保存到缓存
                        append_to_cache(batch_result)
                        cached_results.update(batch_result)
                    else:
                        print(f"  ⚠️ 批次 {idx+1} 失败")

            tasks = [process_batch(b, i) for i, b in enumerate(batches)]
            await asyncio.gather(*tasks)
    else:
        print("✨ 所有视频均已分析，直接使用缓存数据。")

    # 5. 统计 KOL 数据
    print("📈 正在统计 KOL 数据...")
    kol_stats = {} # kol_id -> stats
    
    # 先初始化所有涉及的 KOL
    for video in videos:
        kol_id = video["kol_id"]
        if kol_id not in kol_stats:
            kol_stats[kol_id] = {
                "kol_id": kol_id,
                "total_videos": 0,
                "skincare_videos": 0,
                "recent_titles": [],
                "last_publish_time": 0
            }
        
        stats = kol_stats[kol_id]
        stats["total_videos"] += 1
        
        # 检查是否护肤相关
        vid_str = str(video["id"])
        is_skincare = cached_results.get(vid_str, False)
        # 处理可能的字符串 "true"/"false"
        if isinstance(is_skincare, str):
            is_skincare = is_skincare.lower() == 'true'
            
        if is_skincare:
            stats["skincare_videos"] += 1
            if len(stats["recent_titles"]) < 5:
                stats["recent_titles"].append(video["item_title"])
        
        # 更新最新发布时间
        pub_time = video.get("item_publish_time")
        # 简单处理时间戳或字符串
        # 这里略过复杂转换，仅作参考

    # 6. 获取 KOL 基础信息（粉丝数、报价等）
    # 为了全量，我们需要把所有 kol_ids 拿去查询 base_info 和 price
    all_kol_ids = list(kol_stats.keys())
    kol_details_map = {}
    
    print("📥 获取 KOL 基础信息...")
    # 分批查询 Supabase (避免 URL 过长)
    CHUNK_SIZE = 100
    for i in range(0, len(all_kol_ids), CHUNK_SIZE):
        chunk_ids = all_kol_ids[i:i+CHUNK_SIZE]
        try:
            # 查询 base_info
            resp_base = supabase.table("gg_xingtu_kol_base_info")\
                .select("kol_id, kol_name, fans_count, ecom_enabled")\
                .in_("kol_id", chunk_ids)\
                .execute()
            
            # 查询 price
            resp_price = supabase.table("gg_xingtu_kol_price")\
                .select("kol_id, video_21_60s_price")\
                .in_("kol_id", chunk_ids)\
                .execute()
            
            # 合并信息
            for item in resp_base.data:
                k_id = item["kol_id"]
                if k_id not in kol_details_map:
                    kol_details_map[k_id] = {}
                kol_details_map[k_id].update(item)
                
            for item in resp_price.data:
                k_id = item["kol_id"]
                if k_id not in kol_details_map:
                    kol_details_map[k_id] = {}
                kol_details_map[k_id]["video_21_60s_price"] = item.get("video_21_60s_price", 0)
                
        except Exception as e:
            print(f"⚠️ 获取KOL信息失败 (Chunk {i}): {e}")

    # 7. 整合最终列表
    final_list = []
    for kol_id, stats in kol_stats.items():
        details = kol_details_map.get(kol_id, {})
        
        ratio = 0
        if stats["total_videos"] > 0:
            ratio = round(stats["skincare_videos"] / stats["total_videos"] * 100, 2)
            
        entry = {
            "kol_id": kol_id,
            "kol_name": details.get("kol_name", "Unknown"),
            "fans_count": details.get("fans_count", 0),
            "is_ecom_enabled": details.get("ecom_enabled", False),
            "price_20_60s": details.get("video_21_60s_price", 0),
            "total_videos_analyzed": stats["total_videos"],
            "skincare_videos_count": stats["skincare_videos"],
            "skincare_ratio": f"{ratio}%",
            "skincare_ratio_num": ratio,
            "sample_titles": stats["recent_titles"]
        }
        final_list.append(entry)

    # 8. 排序和保存
    # 按护肤视频数量倒序，然后粉丝数倒序
    final_list.sort(key=lambda x: (x["skincare_videos_count"], x["fans_count"]), reverse=True)
    
    # 保存 JSON
    with open(FULL_KOL_LIST_JSON, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
    print(f"💾 全量 JSON 已保存: {FULL_KOL_LIST_JSON}")
    
    # 保存 CSV
    with open(FULL_KOL_LIST_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        header = ["KOL ID", "昵称", "粉丝数", "护肤相关度", "护肤视频数", "总视频数", "20-60s报价", "是否电商", "示例标题"]
        writer.writerow(header)
        for item in final_list:
            writer.writerow([
                item["kol_id"],
                item["kol_name"],
                item["fans_count"],
                item["skincare_ratio"],
                item["skincare_videos_count"],
                item["total_videos_analyzed"],
                item["price_20_60s"],
                "是" if item["is_ecom_enabled"] else "否",
                " | ".join(item["sample_titles"][:3])
            ])
    print(f"💾 全量 CSV 已保存: {FULL_KOL_LIST_CSV}")
    
    # 9. 输出摘要
    skincare_kols = [k for k in final_list if k["skincare_videos_count"] > 0]
    print("\n📊 统计摘要:")
    print(f"- 覆盖达人总数: {len(final_list)}")
    print(f"- 发布过护肤内容的达人: {len(skincare_kols)}")
    print(f"- 100% 垂直护肤达人: {len([k for k in skincare_kols if k['skincare_ratio_num'] == 100])}")

if __name__ == "__main__":
    asyncio.run(main())

