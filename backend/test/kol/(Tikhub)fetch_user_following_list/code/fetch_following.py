import os
import time
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict, Any

# -----------------------------------------------------------------------------
# 配置与环境加载
# -----------------------------------------------------------------------------

def load_env():
    """加载环境变量，从当前目录向上寻找 backend/.env"""
    current_dir = Path(__file__).parent
    # backend/test/kol/(Tikhub)fetch_user_following_list/code/fetch_following.py
    # 需要向上 4 级找到 backend/.env
    backend_dir = current_dir.parent.parent.parent.parent
    env_path = backend_dir / '.env'

    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量: {env_path}")
    else:
        print(f"⚠️ 未找到环境变量文件: {env_path}")

# -----------------------------------------------------------------------------
# 数据读取
# -----------------------------------------------------------------------------

def load_comments_users(json_path: Path) -> List[Dict]:
    """
    从评论 JSON 文件中提取用户信息
    """
    if not json_path.exists():
        print(f"❌ 文件不存在: {json_path}")
        return []
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    comments = data.get("comments", [])
    users = []
    seen_uids = set()
    
    for comment in comments:
        user = comment.get("user", {})
        uid = user.get("uid")
        sec_uid = user.get("sec_uid")
        
        if uid and sec_uid and uid not in seen_uids:
            users.append({
                "uid": uid,
                "sec_uid": sec_uid,
                "nickname": user.get("nickname", "Unknown")
            })
            seen_uids.add(uid)
            
    print(f"✅ 从 {len(comments)} 条评论中提取出 {len(users)} 个唯一用户")
    return users

# -----------------------------------------------------------------------------
# TikHub API 操作
# -----------------------------------------------------------------------------

def fetch_user_following(user: Dict, output_dir: Path, api_key: str):
    """
    获取用户的关注列表
    
    API: /api/v1/douyin/web/fetch_user_following_list
    Docs: https://api.tikhub.io/#/Douyin-Web-API/fetch_user_following_list_api_v1_douyin_web_fetch_user_following_list_get
    """
    # 注意：这里使用的是 Web API 还是 App API 需要确认。
    # 用户给的链接是 Douyin-Web-API/fetch_user_following_list
    base_url = "https://api.tikhub.io/api/v1/douyin/web/fetch_user_following_list"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    sec_user_id = user['sec_uid']
    nickname = user['nickname']
    uid = user['uid']
    
    print(f"📥 开始获取用户 [{nickname}] (sec_uid: {sec_user_id[:10]}...) 的关注列表")
    
    all_following = []
    max_time = 0 # 游标，第一页为0
    has_more = True
    page_count = 0
    max_pages = 3 # 限制页数防止过多
    
    while has_more and page_count < max_pages:
        params = {
            "sec_user_id": sec_user_id,
            "count": 20,
            "max_time": max_time
        }
        
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ API 请求失败: {response.status_code} - {response.text}")
                break
                
            data = response.json()
            
            # 解析数据
            # Web API 的返回结构通常在 data 字段中，或者是直接返回
            # 假设标准结构: { "followings": [...], "has_more": ..., "max_time": ... }
            # 或者 { "data": { "followings": ... } }
            
            followings = data.get("followings", [])
            if not followings and "data" in data:
                followings = data["data"].get("followings", [])
            
            if not followings:
                print(f"   ⚠️ 第 {page_count+1} 页无关注数据")
                if page_count == 0:
                     print(f"   API 响应: {json.dumps(data, ensure_ascii=False)[:200]}")
            else:
                all_following.extend(followings)
                print(f"   ✅ 第 {page_count+1} 页获取 {len(followings)} 个关注")
            
            # 更新游标
            max_time = data.get("max_time", 0)
            has_more = data.get("has_more", False)
            page_count += 1
            
            if not has_more:
                break
                
            time.sleep(1.5) # 礼貌延时
            
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            break
            
    # 保存结果
    output_file = output_dir / f"following_{uid}_{nickname}.json"
    result = {
        "user_info": user,
        "total_fetched": len(all_following),
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "following_list": all_following
    }
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 已保存 {len(all_following)} 个关注者到 {output_file.name}")
    except Exception as e:
        print(f"❌ 保存文件失败: {e}")
        # 尝试去除文件名中的特殊字符再次保存
        safe_nickname = "".join([c for c in nickname if c.isalnum() or c in (' ', '-', '_')])
        output_file = output_dir / f"following_{uid}_{safe_nickname}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 (重试) 已保存到 {output_file.name}")

# -----------------------------------------------------------------------------
# 主流程
# -----------------------------------------------------------------------------

def main():
    load_env()
    
    # 1. 检查 Key
    tikhub_key = os.getenv("tikhub_API_KEY")
    if not tikhub_key:
        print("❌ 错误: 未找到 tikhub_API_KEY 环境变量")
        return
        
    # 2. 定义输入文件路径
    # 使用用户指定的文件
    current_dir = Path(__file__).parent
    # 相对路径: ../../(Tikhub)GetVideoComments/output/
    input_file = current_dir.parent.parent / "(Tikhub)GetVideoComments/output/comments_7526514112366431545.json"
    
    output_dir = current_dir.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 读取评论文件: {input_file}")
    print(f"📂 输出目录: {output_dir}")
    
    # 3. 提取用户
    users = load_comments_users(input_file)
    if not users:
        print("⚠️ 未找到用户，结束")
        return
        
    # 4. 抓取关注列表
    print(f"\n🚀 开始抓取 {len(users)} 个用户的关注列表")
    
    for i, user in enumerate(users):
        print(f"\n[{i+1}/{len(users)}] 处理用户: {user['nickname']}")
        fetch_user_following(user, output_dir, tikhub_key)
        time.sleep(2)
        
    print("\n✅ 所有任务已完成")

if __name__ == "__main__":
    main()

