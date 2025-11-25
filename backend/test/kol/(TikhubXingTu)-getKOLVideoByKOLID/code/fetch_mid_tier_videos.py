import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# 配置
MAX_RETRIES = 3
TIMEOUT = 60
RATE_LIMIT_DELAY = 2  # seconds

class RateLimiter:
    def __init__(self, max_per_second=1):
        self.min_interval = 1.0 / max_per_second
        self.last_request_time = 0

    def wait_if_needed(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

def load_api_key():
    """从环境变量加载TikHub API Key"""
    # Assuming script is in backend/test/kol/getKOLVideoByKOLID/code/
    # .env is in backend/
    backend_dir = Path(__file__).resolve().parents[4] 
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        # print(f"✅ 从 {env_path} 加载环境变量")
        load_dotenv(env_path)
    else:
        print(f"⚠️ 未找到环境变量文件: {env_path}")
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    return api_key

def load_cookie():
    """从cookie文件加载Cookie"""
    # Cookie file path based on utils.py: backend/test/kol/cookie
    backend_dir = Path(__file__).resolve().parents[4]
    cookie_path = backend_dir / 'test' / 'kol' / 'cookie'
    
    if not cookie_path.exists():
        print(f"⚠️ Cookie文件不存在: {cookie_path}")
        return None
    
    try:
        with open(cookie_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # 尝试解析JSON
            try:
                cookie_list = json.loads(content)
                cookie_parts = []
                if isinstance(cookie_list, list):
                    for cookie_item in cookie_list:
                        if isinstance(cookie_item, dict) and 'name' in cookie_item and 'value' in cookie_item:
                            name = cookie_item['name']
                            value = cookie_item['value']
                            if name:
                                cookie_parts.append(f"{name}={value}")
                    return '; '.join(cookie_parts)
                elif isinstance(cookie_list, dict):
                     # Maybe it's a dict?
                     pass
            except json.JSONDecodeError:
                # Maybe it's already a string?
                return content

        return content
    except Exception as e:
        print(f"⚠️ Cookie加载失败: {e}")
        return None

def fetch_kol_videos(kol_id, api_key, cookie, rate_limiter):
    """获取KOL视频数据 (支持重试和多域名)"""
    domains = [
        "https://api.tikhub.io",
        "https://api.tikhub.dev"
    ]
    endpoint = "/api/v1/douyin/xingtu/kol_rec_videos_v1"
    
    params = {
        "kolId": kol_id,
        "count": 10,
        "cursor": 0
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Cookie": cookie if cookie else ""
    }
    
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        domain = domains[attempt % len(domains)]
        url = f"{domain}{endpoint}"
        
        rate_limiter.wait_if_needed()
        
        print(f"   🚀 [Attempt {attempt+1}/{MAX_RETRIES}] 请求URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code >= 500:
                print(f"   ⚠️ 服务器错误 {response.status_code}, 尝试重试...")
                last_error = f"HTTP {response.status_code}: {response.text}"
            else:
                print(f"   ❌ 请求失败: {response.status_code}")
                return {"code": response.status_code, "message": response.text}
                
        except Exception as e:
            print(f"   ⚠️ 请求异常: {e}, 尝试重试...")
            last_error = str(e)
            
        time.sleep(1)
        
    print(f"   ❌ 所有重试均失败. Last error: {last_error}")
    return {"error": last_error}

def main():
    # Target KOLs from the user request (from DB query)
    targets = [
        {"kol_id":"6852500018742427651","kol_name":"欧阳白浅专供高端美容院护肤工厂源头","fans_count":683223},
        {"kol_id":"6957967843048554533","kol_name":"一好护肤","fans_count":153328},
        {"kol_id":"6870161674108665870","kol_name":"影子爱护肤","fans_count":121314},
        {"kol_id":"7004243194900643871","kol_name":"李拜天（败家版）","fans_count":677011},
        {"kol_id":"7097417916731260958","kol_name":"诗诗爱护肤","fans_count":108506},
        {"kol_id":"7279399698954190885","kol_name":"安神-护肤","fans_count":161274},
        {"kol_id":"6744563381727920141","kol_name":"护肤 问莫嫡","fans_count":594038},
        {"kol_id":"7489955985092509706","kol_name":"植唯安护肤","fans_count":258332},
        {"kol_id":"7135664853816967181","kol_name":"蔡蔡教护肤","fans_count":352737}
    ]

    print("="*60)
    print(f"开始获取 {len(targets)} 个KOL的推荐视频数据")
    print("="*60)
    
    try:
        api_key = load_api_key()
        cookie = load_cookie()
    except Exception as e:
        print(f"❌ 环境加载失败: {e}")
        return

    script_dir = Path(__file__).resolve().parent
    output_dir = script_dir.parent / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rate_limiter = RateLimiter(max_per_second=0.5)
    summary_data = []
    
    for idx, kol in enumerate(targets, 1):
        kol_id = kol.get('kol_id')
        nickname = kol.get('kol_name', 'Unknown')
        
        print(f"\n[{idx}/{len(targets)}] 处理 KOL: {nickname} (ID: {kol_id})")
        
        data = fetch_kol_videos(kol_id, api_key, cookie, rate_limiter)
        
        result_record = {
            "kol_info": kol,
            "fetched_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "api_response": data
        }
        
        filename = f"kol_videos_{kol_id}.json"
        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result_record, f, ensure_ascii=False, indent=2)
            
        print(f"   💾 已保存到: {filepath.name}")
        
        # Extract summary info
        api_data = data.get('data', {})
        if not isinstance(api_data, dict):
             api_data = {}
             
        masterpiece_list = api_data.get('masterpiece_videos', [])
        newest_video = api_data.get('newest_video')
        hot_video = api_data.get('personal_hot_video')
        
        video_count = len(masterpiece_list)
        if newest_video: video_count += 1
        if hot_video: video_count += 1
        
        summary_data.append({
            "nickname": nickname,
            "kol_id": kol_id,
            "video_count": video_count,
            "details": {
                "masterpiece_count": len(masterpiece_list),
                "has_newest": bool(newest_video),
                "has_hot": bool(hot_video)
            },
            "status": "success" if data and data.get('code') == 200 else "failed"
        })
        
        time.sleep(RATE_LIMIT_DELAY)
        
    print("\n" + "="*60)
    print("📊 执行总结")
    print("="*60)
    for item in summary_data:
        print(f"- {item['nickname']}: {item['status']}, 获取视频数: {item['video_count']}")
        
    summary_file = output_dir / 'mid_tier_execution_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    print(f"\n📝 总结报告已保存: {summary_file}")

if __name__ == "__main__":
    main()

