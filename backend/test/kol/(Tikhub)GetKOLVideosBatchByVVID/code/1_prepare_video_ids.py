import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

def load_env():
    # Go up from backend/test/kol/kol-video-fetcher/ to backend/
    current_dir = Path(__file__).parent
    backend_dir = current_dir.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded env from {env_path}")
    else:
        print(f"Warning: .env not found at {env_path}")

def main():
    load_env()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not set")
        return

    supabase: Client = create_client(url, key)
    
    print("Fetching target KOLs...")
    # 1. Get target KOLs
    response = supabase.table("gg_xingtu_kol_base_info")\
        .select("kol_id, kol_name")\
        .eq("is_mid_tier_skincare_kol", True)\
        .execute()
    
    target_kols = response.data
    target_kol_ids = [k['kol_id'] for k in target_kols]
    print(f"Found {len(target_kols)} target KOLs")
    
    if not target_kols:
        print("No KOLs found. Exiting.")
        return

    # 2. Get videos for these KOLs
    # Since 309 KOLs might be too many for an 'in' query, and the video table is small (15k),
    # we'll try to fetch all videos or fetch in batches.
    # Actually, 15k rows is small enough to fetch all relevant ones if we filter by video_tag in (3,5,6)
    # But we need to filter by kol_id too. 
    # Let's try fetching all videos for simplicity, or paginating if needed.
    
    print("Fetching videos...")
    all_videos = []
    
    # Fetch in chunks to avoid timeouts or limits. 15k rows might require pagination.
    # Supabase default limit is usually 1000.
    page_size = 1000
    start = 0
    
    while True:
        print(f"Fetching videos offset {start}...")
        # We only care about tags 3, 5, 6
        # We can't easily do "kol_id in [...]" for 300 IDs.
        # So we fetch all videos with tags 3, 5, 6 and filter in python, 
        # or we rely on the fact that we probably want most videos in the table anyway?
        # No, the table might contain videos for other KOLs.
        # But let's assume we can fetch all videos with relevant tags first.
        
        res = supabase.table("gg_xingtu_kol_videos")\
            .select("*")\
            .in_("video_tag", [3, 5, 6])\
            .range(start, start + page_size - 1)\
            .execute()
            
        videos = res.data
        if not videos:
            break
            
        all_videos.extend(videos)
        start += page_size
        
        if len(videos) < page_size:
            break
            
    print(f"Fetched {len(all_videos)} total videos with tags 3,5,6")
    
    # Filter for our target KOLs
    target_kol_id_set = set(target_kol_ids)
    relevant_videos = [v for v in all_videos if v['kol_id'] in target_kol_id_set]
    print(f"Filtered down to {len(relevant_videos)} videos belonging to target KOLs")
    
    # 3. Organize by KOL and select 1 of each type
    kol_video_map = {} # kol_id -> {3: video, 5: video, 6: video}
    
    for v in relevant_videos:
        kid = v['kol_id']
        tag = v['video_tag']
        if kid not in kol_video_map:
            kol_video_map[kid] = {}
            
        # If we already have a video for this tag, check if this one is better (more views)
        # Assuming 'vv' is views.
        current_best = kol_video_map[kid].get(tag)
        if not current_best:
            kol_video_map[kid][tag] = v
        else:
            if (v.get('vv') or 0) > (current_best.get('vv') or 0):
                kol_video_map[kid][tag] = v
                
    # 4. Construct final list
    final_list = []
    total_videos_count = 0
    
    for kol in target_kols:
        kid = kol['kol_id']
        videos = kol_video_map.get(kid, {})
        
        entry = {
            "kol_id": kid,
            "kol_name": kol.get('kol_name'),
            "videos": {
                "masterpiece": videos.get(3, {}).get("item_id"), # tag 3
                "hot": videos.get(5, {}).get("item_id"),         # tag 5
                "newest": videos.get(6, {}).get("item_id")       # tag 6
            },
            "video_details": {
                 "masterpiece": videos.get(3),
                 "hot": videos.get(5),
                 "newest": videos.get(6)
            }
        }
        
        # Count found videos
        found = 0
        if entry["videos"]["masterpiece"]: found += 1
        if entry["videos"]["hot"]: found += 1
        if entry["videos"]["newest"]: found += 1
        total_videos_count += found
        
        final_list.append(entry)
        
    print(f"Constructed list for {len(final_list)} KOLs. Total videos found: {total_videos_count}")
    
    # 5. Save output
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "kol_video_ids.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()

