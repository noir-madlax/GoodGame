import os
import json
from supabase import create_client, Client

# 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INPUT_FILE = os.path.join(OUTPUT_DIR, "all_kols_skincare_stats.json")
NON_SKINCARE_FILE = os.path.join(OUTPUT_DIR, "non_skincare_kols_with_titles.json")
MID_TIER_FILE = os.path.join(OUTPUT_DIR, "mid_tier_skincare_kols.json")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("❌ 错误: 缺少必要的环境变量")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def main():
    print("📖 读取数据...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        all_kols = json.load(f)
    
    print(f"✅ 共加载 {len(all_kols)} 位 KOL 数据")
    
    # 1. 筛选护肤视频数为 0 的 KOL
    non_skincare_kols = [k for k in all_kols if k["skincare_videos_count"] == 0]
    print(f"🔍 发现 {len(non_skincare_kols)} 位非护肤 KOL，正在获取其视频标题示例...")
    
    # 批量获取标题 (为了效率，分批查询)
    # 我们只取前 5 个标题
    non_skincare_ids = [k["kol_id"] for k in non_skincare_kols]
    
    # 由于 Supabase 'in' 查询有限制，分批处理
    batch_size = 100
    titles_map = {} # kol_id -> [title1, title2...]
    
    for i in range(0, len(non_skincare_ids), batch_size):
        batch_ids = non_skincare_ids[i:i+batch_size]
        try:
            # 我们不需要取所有视频，每个KOL取几个就行。
            # 但 Supabase 很难用单次查询实现 "Group Limit"。
            # 策略：查这些 KOL 的所有视频，然后内存里取前5个。
            # 如果视频太多，可能比较慢。但总视频数也就几千条。
            response = supabase.table("gg_xingtu_kol_videos")\
                .select("kol_id, item_title")\
                .in_("kol_id", batch_ids)\
                .neq("item_title", "")\
                .not_.is_("item_title", "null")\
                .execute()
            
            for v in response.data:
                kid = v["kol_id"]
                title = v["item_title"]
                if kid not in titles_map:
                    titles_map[kid] = []
                if len(titles_map[kid]) < 5: # 每个只存5个
                    titles_map[kid].append(title)
        except Exception as e:
            print(f"⚠️ 查询视频标题失败: {e}")

    # 更新数据结构
    for k in non_skincare_kols:
        k["sample_titles_non_skincare"] = titles_map.get(k["kol_id"], [])
        
    # 保存非护肤 KOL
    with open(NON_SKINCARE_FILE, "w", encoding="utf-8") as f:
        json.dump(non_skincare_kols, f, ensure_ascii=False, indent=2)
    print(f"💾 已保存非护肤 KOL: {NON_SKINCARE_FILE}")
    
    # 2. 筛选 10w-100w 粉丝的护肤达人
    mid_tier_kols = [
        k for k in all_kols 
        if k["skincare_videos_count"] > 0 
        and 100000 <= k["fans_count"] <= 1000000
    ]
    print(f"🔍 发现 {len(mid_tier_kols)} 位腰部护肤达人 (10w-100w 粉丝)")
    
    # 保存腰部达人
    with open(MID_TIER_FILE, "w", encoding="utf-8") as f:
        json.dump(mid_tier_kols, f, ensure_ascii=False, indent=2)
    print(f"💾 已保存腰部护肤达人: {MID_TIER_FILE}")

if __name__ == "__main__":
    main()

