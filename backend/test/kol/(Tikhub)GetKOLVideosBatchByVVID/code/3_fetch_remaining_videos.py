import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

def load_env():
    current_dir = Path(__file__).parent
    backend_dir = current_dir.parent.parent.parent
    env_path = backend_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)

def main():
    load_env()
    api_key = os.getenv("tikhub_API_KEY")
    if not api_key:
        print("Error: tikhub_API_KEY not set in .env")
        return

    current_dir = Path(__file__).parent
    output_dir = current_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    input_file = output_dir / "kol_video_ids.json"
    final_details_file = output_dir / "final_video_details.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run step 1 first.")
        return

    # 1. Load all video IDs from kol_video_ids.json
    print("Loading source video IDs...")
    with open(input_file, "r", encoding="utf-8") as f:
        kol_data = json.load(f)

    all_video_ids = []
    for kol in kol_data:
        videos = kol.get("videos", {})
        for v_type, vid in videos.items():
            if vid:
                all_video_ids.append(vid)
    
    # Deduplicate source IDs
    source_unique_ids = []
    seen_source = set()
    for vid in all_video_ids:
        if vid not in seen_source:
            seen_source.add(vid)
            source_unique_ids.append(vid)
            
    print(f"Total unique source video IDs: {len(source_unique_ids)}")

    # 2. Load already processed IDs from final_video_details.json
    processed_ids = set()
    existing_details = []
    
    if final_details_file.exists():
        print("Loading existing details...")
        try:
            with open(final_details_file, "r", encoding="utf-8") as f:
                existing_details = json.load(f)
                for item in existing_details:
                    aid = item.get("aweme_id")
                    if aid:
                        processed_ids.add(aid)
        except Exception as e:
            print(f"Warning: Could not read existing details: {e}")
            
    print(f"Already processed {len(processed_ids)} videos.")

    # 3. Identify remaining IDs
    remaining_ids = [vid for vid in source_unique_ids if vid not in processed_ids]
    print(f"Remaining videos to fetch: {len(remaining_ids)}")
    
    if not remaining_ids:
        print("No new videos to fetch. Done.")
        return

    # 4. Batch and Fetch
    batch_size = 50
    batches = [remaining_ids[i:i + batch_size] for i in range(0, len(remaining_ids), batch_size)]

    url = "https://api.tikhub.io/api/v1/douyin/app/v3/fetch_multi_video_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    new_results = []

    # Determine start batch number based on existing files to avoid overwriting?
    # Or just start from next batch number?
    # Let's find the highest batch number in output_dir
    existing_batches = [f.name for f in output_dir.glob("batch_*_response.json")]
    max_batch = 0
    for fname in existing_batches:
        try:
            # batch_X_response.json
            num = int(fname.split('_')[1])
            if num > max_batch:
                max_batch = num
        except:
            pass
    
    start_batch_num = max_batch + 1
    print(f"Starting from batch number {start_batch_num}")

    for i, batch in enumerate(batches):
        batch_num = start_batch_num + i
        print(f"Processing batch {batch_num} ({i+1}/{len(batches)}) with {len(batch)} IDs...")
        
        # API expects a list of strings as body
        payload = batch
        
        # Save request
        req_file = output_dir / f"batch_{batch_num}_request.json"
        with open(req_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            
        try:
            response = requests.post(url, headers=headers, json=payload)
            print(f"Batch {batch_num} status code: {response.status_code}")
            
            if response.status_code != 200:
                 print(f"Error response: {response.text[:200]}")
            
            try:
                resp_data = response.json()
            except:
                resp_data = {"error": "Invalid JSON", "raw": response.text}
            
            # Save raw response
            resp_file = output_dir / f"batch_{batch_num}_response.json"
            with open(resp_file, "w", encoding="utf-8") as f:
                json.dump(resp_data, f, ensure_ascii=False, indent=2)
                
            if response.status_code == 200 and resp_data.get("code") == 200:
                 data_obj = resp_data.get("data", {})
                 aweme_details = data_obj.get("aweme_details", [])
                 
                 if aweme_details:
                    for vid in aweme_details:
                        stats = vid.get("statistics", {})
                        aid = stats.get("aweme_id") or vid.get("aweme_id")
                        if not aid: continue
                        
                        # Extract play addr
                        video_info = vid.get("video", {})
                        play_addr = video_info.get("play_addr", {}) or video_info.get("play_addr_h264", {})
                        url_list = play_addr.get("url_list", [])
                        video_url = url_list[0] if url_list else None
                        
                        # Extract cover
                        cover_info = video_info.get("cover", {}) or video_info.get("origin_cover", {})
                        cover_url_list = cover_info.get("url_list", [])
                        cover_url = cover_url_list[0] if cover_url_list else None
                        
                        # Extract author
                        author_info = vid.get("author", {})
                        
                        parsed = {
                            "aweme_id": aid,
                            "desc": vid.get("desc"),
                            "statistics": stats,
                            "author": {
                                "uid": author_info.get("uid"),
                                "nickname": author_info.get("nickname"),
                                "unique_id": author_info.get("unique_id")
                            },
                            "video_url": video_url,
                            "cover_url": cover_url,
                            "raw_video_data": vid 
                        }
                        new_results.append(parsed)
            else:
                print(f"Error in batch {batch_num}: {resp_data.get('msg')}")
                
        except Exception as e:
            print(f"Exception in batch {batch_num}: {e}")
            
        time.sleep(1.5) # Rate limit niceness

    # 5. Append new results to existing details and save
    total_details = existing_details + new_results
    
    # Optional: Deduplicate again by ID just in case
    final_map = {}
    for item in total_details:
        aid = item.get("aweme_id")
        if aid:
            final_map[aid] = item
            
    final_list = list(final_map.values())
    
    with open(final_details_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    print(f"Added {len(new_results)} new videos.")
    print(f"Total videos in final file: {len(final_list)}")
    print("Done.")

if __name__ == "__main__":
    main()

