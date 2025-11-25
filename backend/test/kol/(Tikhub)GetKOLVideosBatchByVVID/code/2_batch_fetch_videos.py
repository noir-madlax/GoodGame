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
    input_file = current_dir / "output" / "kol_video_ids.json"
    output_dir = current_dir / "output"
    output_dir.mkdir(exist_ok=True)

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run step 1 first.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        kol_data = json.load(f)

    # Collect all video IDs
    all_video_ids = []
    for kol in kol_data:
        videos = kol.get("videos", {})
        for v_type, vid in videos.items():
            if vid:
                all_video_ids.append(vid)

    # Deduplicate while preserving order
    unique_ids = []
    seen = set()
    for vid in all_video_ids:
        if vid not in seen:
            seen.add(vid)
            unique_ids.append(vid)

    print(f"Total unique video IDs found: {len(unique_ids)}")
    
    # Take first 100
    target_ids = unique_ids[:100]
    print(f"Targeting first {len(target_ids)} videos")

    # Batch into chunks of 50
    batch_size = 50
    batches = [target_ids[i:i + batch_size] for i in range(0, len(target_ids), batch_size)]

    url = "https://api.tikhub.io/api/v1/douyin/app/v3/fetch_multi_video_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    all_results = []

    for i, batch in enumerate(batches):
        batch_num = i + 1
        print(f"Processing batch {batch_num}/{len(batches)} with {len(batch)} IDs...")
        
        # Try sending list directly as body, based on 422 error "Input should be a valid list"
        # payload = {"aweme_ids": batch} 
        payload = batch
        
        # Save request
        req_file = output_dir / f"batch_{batch_num}_request.json"
        with open(req_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            
        try:
            response = requests.post(url, headers=headers, json=payload)
            print(f"Batch {batch_num} status code: {response.status_code}")
            
            resp_data = response.json()
            
            # Save raw response
            resp_file = output_dir / f"batch_{batch_num}_response.json"
            with open(resp_file, "w", encoding="utf-8") as f:
                json.dump(resp_data, f, ensure_ascii=False, indent=2)
                
            if response.status_code == 200 and resp_data.get("code") == 200:
                 # Extract video data
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
                            "raw_video_data": vid # Optional: keep raw data if needed
                        }
                        all_results.append(parsed)
            else:
                print(f"Error in batch {batch_num}: {resp_data.get('msg')}")
                
        except Exception as e:
            print(f"Exception in batch {batch_num}: {e}")
            
        time.sleep(1) # Rate limit niceness

    # Save final parsed results
    final_file = output_dir / "final_video_details.json"
    with open(final_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(all_results)} video details to {final_file}")
    print("Done.")

if __name__ == "__main__":
    main()

