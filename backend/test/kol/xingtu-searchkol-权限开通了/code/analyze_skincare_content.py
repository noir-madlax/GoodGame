import os
import json
import time
import asyncio
import aiohttp
from typing import List, Dict
from supabase import create_client, Client
from math import ceil

# 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# 优先使用环境变量中的模型，否则默认为 gpt-4o-mini
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENROUTER_API_KEY]):
    print("❌ 错误: 缺少必要的环境变量 (SUPABASE_URL, SUPABASE_KEY, OPENROUTER_API_KEY)")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def analyze_titles_batch(session: aiohttp.ClientSession, titles_batch: List[Dict]) -> Dict[str, bool]:
    """
    调用 LLM 分析一批标题
    titles_batch: [{"id": 1, "title": "xxx"}, ...]
    返回: {"id1": true, "id2": false, ...}
    """
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
            
            # 清理 Markdown 代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            return json.loads(content.strip())
    except Exception as e:
        print(f"⚠️ Exception: {e}")
        return {}

async def main():
    print("🚀 开始获取视频数据...")
    
    # 1. 从数据库获取视频标题
    try:
        # 分页获取所有数据
        videos = []
        batch_size = 1000
        offset = 0
        
        while True:
            response = supabase.table("gg_xingtu_kol_videos")\
                .select("id, kol_id, item_title")\
                .neq("item_title", "")\
                .not_.is_("item_title", "null")\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            batch_data = response.data
            if not batch_data:
                break
                
            videos.extend(batch_data)
            offset += batch_size
            print(f"  已加载 {len(videos)} 条数据...")
            
    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")
        return

    print(f"✅ 总共获取到 {len(videos)} 条非空标题视频")
    
    # 2. 分批处理
    BATCH_SIZE = 50  # 每批 50 条
    batches = [videos[i:i + BATCH_SIZE] for i in range(0, len(videos), BATCH_SIZE)]
    
    results = {}
    start_time = time.time()
    
    print(f"📦 分为 {len(batches)} 个批次进行 LLM 分析...")
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        # 为了避免速率限制，我们限制并发数
        CONCURRENCY_LIMIT = 10
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        async def limited_batch_process(batch, batch_idx):
            async with semaphore:
                # 准备 batch 数据
                processed_batch = [{"id": str(v["id"]), "title": v["item_title"]} for v in batch]
                
                print(f"  🔄 处理批次 {batch_idx+1}/{len(batches)}...")
                batch_result = await analyze_titles_batch(session, processed_batch)
                
                if batch_result:
                    results.update(batch_result)
                else:
                    print(f"  ⚠️ 批次 {batch_idx+1} 失败或无结果")

        for i, batch in enumerate(batches):
            tasks.append(limited_batch_process(batch, i))
        
        await asyncio.gather(*tasks)

    duration = time.time() - start_time
    print(f"✅ 分析完成！耗时: {duration:.2f}秒")
    print(f"📊 成功分析: {len(results)}/{len(videos)} 条")
    
    # 3. 整合结果并分析
    skincare_videos = []
    kol_stats = {}  # {kol_id: {"total": 0, "skincare": 0, "titles": []}}

    for video in videos:
        vid = str(video["id"])
        kol_id = video["kol_id"]
        
        if kol_id not in kol_stats:
            kol_stats[kol_id] = {"total": 0, "skincare": 0, "titles": []}
        
        kol_stats[kol_id]["total"] += 1
        
        # 检查 LLM 结果
        is_skincare = results.get(vid, False)
        # 兼容可能的字符串返回值
        if isinstance(is_skincare, str):
            is_skincare = is_skincare.lower() == 'true'
            
        if is_skincare:
            skincare_videos.append(video)
            kol_stats[kol_id]["skincare"] += 1
            # 只保存前3个护肤标题作为示例
            if len(kol_stats[kol_id]["titles"]) < 3:
                kol_stats[kol_id]["titles"].append(video["item_title"])

    # 4. 统计护肤达人
    skincare_kols = []
    for kol_id, stats in kol_stats.items():
        if stats["skincare"] > 0:
            stats["ratio"] = round(stats["skincare"] / stats["total"] * 100, 2)
            stats["kol_id"] = kol_id
            skincare_kols.append(stats)
    
    # 按护肤视频数量排序
    skincare_kols.sort(key=lambda x: x["skincare"], reverse=True)

    # 5. 输出报告
    report = {
        "total_videos_analyzed": len(videos),
        "skincare_videos_found": len(skincare_videos),
        "skincare_video_ratio": f"{len(skincare_videos)/len(videos)*100:.2f}%",
        "total_kols": len(kol_stats),
        "skincare_kols_count": len(skincare_kols),
        "top_skincare_kols": skincare_kols[:20]  # 前20名
    }
    
    # 保存到文件
    output_file = "skincare_analysis_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"💾 报告已保存至 {output_file}")
    
    # 打印预览
    print("\n🏆 护肤视频最多的达人 TOP 10:")
    print(f"{'KOL ID':<25} {'护肤视频数':<10} {'总视频数':<10} {'占比':<10} {'示例标题'}")
    print("-" * 100)
    for kol in skincare_kols[:10]:
        titles_preview = kol['titles'][0][:20] + "..." if kol['titles'] else ""
        print(f"{kol['kol_id']:<25} {kol['skincare']:<10} {kol['total']:<10} {kol['ratio']}%    {titles_preview}")

if __name__ == "__main__":
    asyncio.run(main())

