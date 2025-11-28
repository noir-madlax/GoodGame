import os
import time
import json
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from pathlib import Path
from typing import List, Dict, Any

# -----------------------------------------------------------------------------
# 配置与环境加载
# -----------------------------------------------------------------------------

def load_env():
    """加载环境变量，从当前目录向上寻找 backend/.env"""
    current_dir = Path(__file__).parent
    # 假设结构: backend/test/kol/(Tikhub)GetVideoComments/code/fetch_comments.py
    # 需要向上 4 级找到 backend/.env
    backend_dir = current_dir.parent.parent.parent.parent
    env_path = backend_dir / '.env'

    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量: {env_path}")
    else:
        print(f"⚠️ 未找到环境变量文件: {env_path}")

# -----------------------------------------------------------------------------
# Supabase 操作
# -----------------------------------------------------------------------------

def get_supabase_client() -> Client:
    """初始化并返回 Supabase 客户端"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("❌ 缺少 SUPABASE_URL 或 SUPABASE_KEY")
    return create_client(url, key)

def get_target_kol_ids(supabase: Client) -> List[str]:
    """
    获取所有腰部护肤达人的 KOL ID
    条件: is_mid_tier_skincare_kol = True
    """
    print("🔍 正在查询腰部护肤达人列表...")
    # 注意：Supabase 默认限制 1000 条，如果腰部达人超过这个数需要分页，但目前看描述应该不多
    response = supabase.table("gg_xingtu_kol_base_info")\
        .select("kol_id")\
        .eq("is_mid_tier_skincare_kol", True)\
        .execute()
    
    kol_ids = [item['kol_id'] for item in response.data if item.get('kol_id')]
    print(f"✅ 找到 {len(kol_ids)} 位腰部护肤达人")
    return kol_ids

def get_videos_for_kols(supabase: Client, kol_ids: List[str]) -> List[Dict]:
    """
    获取指定 KOL 列表发布的视频信息
    从 gg_xingtu_kol_videos_details 表中查询
    """
    print(f"🔍 正在查询这 {len(kol_ids)} 位达人的视频...")
    
    # 由于 kol_ids 可能较多，分批查询以避免 URL 过长
    all_videos = []
    batch_size = 50 # 每次查 50 个 KOL 的视频
    
    for i in range(0, len(kol_ids), batch_size):
        batch_ids = kol_ids[i:i+batch_size]
        try:
            # 查询 kol_id 在 batch_ids 中的视频
            # 只需 aweme_id 和 kol_id，也许还需要 title 做文件名方便识别
            response = supabase.table("gg_xingtu_kol_videos_details")\
                .select("aweme_id, kol_id, video_desc")\
                .in_("kol_id", batch_ids)\
                .execute()
            
            videos = response.data
            all_videos.extend(videos)
            print(f"   ...已获取 {len(videos)} 个视频 (批次 {i//batch_size + 1})")
        except Exception as e:
            print(f"❌ 查询视频批次失败: {e}")
            
    print(f"✅ 总计找到 {len(all_videos)} 个相关视频")
    return all_videos

# -----------------------------------------------------------------------------
# TikHub API 操作
# -----------------------------------------------------------------------------

def fetch_video_comments(aweme_id: str, output_dir: Path, api_key: str):
    """
    调用 TikHub API 获取单个视频的评论数据并保存
    
    API: /api/v1/douyin/app/v3/fetch_video_comments
    Docs: https://api.tikhub.io/#/Douyin-App-V3-API/fetch_video_comments_api_v1_douyin_app_v3_fetch_video_comments_get
    """
    base_url = "https://api.tikhub.io/api/v1/douyin/app/v3/fetch_video_comments"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    all_comments = []
    cursor = 0
    has_more = 1
    page_count = 0
    max_pages = 5  # 限制每个视频抓取的页数，避免评论过多导致耗时过长（可根据需求调整）
    
    print(f"📥 开始抓取视频 {aweme_id} 的评论...")
    
    while has_more == 1 and page_count < max_pages:
        params = {
            "aweme_id": aweme_id,
            "cursor": cursor,
            "count": 20 # 保持默认
        }
        
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ API 请求失败: {response.status_code} - {response.text}")
                break
                
            data = response.json()
            
            # 检查 API 返回的业务状态
            # TikHub 通常直接返回数据，或在 data 字段中
            # 根据文档，直接返回评论数据结构
            
            # 尝试解析 comments
            # 注意：实际返回结构可能包含在 'data' 字段里，也可能是直接的一级字段
            # 这里根据一般 TikHub 抖音接口习惯，通常是 data['comments']
            # 如果直接是代理响应，可能与抖音原生结构一致
            
            # 保存原始响应以便调试
            # debug_file = output_dir / f"{aweme_id}_page_{page_count}_debug.json"
            # with open(debug_file, "w", encoding="utf-8") as f:
            #    json.dump(data, f, ensure_ascii=False)
            
            # 提取评论列表
            comments_list = data.get("comments", [])
            if not comments_list and "data" in data:
                 # 有时候包裹在 data 层级下
                 comments_list = data["data"].get("comments", [])
            
            if not comments_list:
                print(f"   ⚠️ 第 {page_count+1} 页无评论数据或结构不匹配")
                # 即使没有评论也可能有 cursor 更新，或者就是没评论了
                if data.get("status_code") == 0: # 成功但无数据
                     pass
                else:
                     print(f"   API 消息: {data.get('status_msg')}")
            
            if comments_list:
                all_comments.extend(comments_list)
                print(f"   ✅ 第 {page_count+1} 页获取 {len(comments_list)} 条评论")
            
            # 更新游标
            cursor = data.get("cursor", 0)
            has_more = data.get("has_more", 0)
            page_count += 1
            
            # 礼貌性延时，避免 QPS 过高
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            break
            
    # 保存结果
    if all_comments:
        output_file = output_dir / f"comments_{aweme_id}.json"
        result = {
            "aweme_id": aweme_id,
            "total_fetched": len(all_comments),
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "comments": all_comments
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 已保存 {len(all_comments)} 条评论到 {output_file.name}")
    else:
        print(f"⚠️ 视频 {aweme_id} 未抓取到任何评论")

# -----------------------------------------------------------------------------
# 主流程
# -----------------------------------------------------------------------------

def main():
    load_env()
    
    # 1. 检查 TikHub Key
    tikhub_key = os.getenv("tikhub_API_KEY")
    if not tikhub_key:
        print("❌ 错误: 未找到 tikhub_API_KEY 环境变量")
        return

    # 2. 连接数据库
    try:
        supabase = get_supabase_client()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    # 3. 获取目标视频
    target_kol_ids = get_target_kol_ids(supabase)
    if not target_kol_ids:
        print("⚠️ 未找到目标 KOL，结束任务")
        return
        
    videos = get_videos_for_kols(supabase, target_kol_ids)
    if not videos:
        print("⚠️ 未找到相关视频，结束任务")
        return
        
    # 4. 准备输出目录
    current_dir = Path(__file__).parent
    output_dir = current_dir.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🚀 开始抓取评论，目标视频数: {len(videos)}")
    print(f"📂 结果将保存至: {output_dir}")
    
    # 5. 遍历视频抓取评论
    # 限制抓取数量用于测试，避免一次跑太久
    # 这里如果需要跑全部，可以去掉切片 [:5]
    # 为了演示和测试，我们先跑前 5 个视频
    test_limit = 5
    print(f"ℹ️ 测试模式：仅处理前 {test_limit} 个视频 (如需全部请修改代码)")
    
    for i, video in enumerate(videos[:test_limit]):
        aweme_id = video.get("aweme_id")
        if not aweme_id:
            continue
            
        print(f"\n[{i+1}/{min(len(videos), test_limit)}] 处理视频: {aweme_id}")
        fetch_video_comments(aweme_id, output_dir, tikhub_key)
        
        # 视频间延时
        time.sleep(2)

    print("\n✅ 所有任务已完成")

if __name__ == "__main__":
    main()

