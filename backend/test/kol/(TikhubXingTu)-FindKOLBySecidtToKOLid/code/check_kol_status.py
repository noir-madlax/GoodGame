#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从视频搜索结果中提取粉丝数在10w-100w的用户，并检查其星图KOL状态
接口: /api/v1/douyin/xingtu/get_xingtu_kolid_by_sec_user_id

流程:
1. 遍历指定目录下的视频搜索结果JSON文件
2. 提取用户信息(sec_uid, follower_count等)
3. 过滤粉丝数在 100,000 - 1,000,000 之间的用户
4. 调用TikHub API查询kol_id
5. 保存结果到 detail 目录

作者: AI Agent
创建时间: 2025-11-24
"""

import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
import threading

class RateLimiter:
    """速率限制器"""
    def __init__(self, max_per_second=2):
        self.max_per_second = max_per_second
        self.min_interval = 1.0 / max_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_interval:
                time.sleep(self.min_interval - time_since_last)
            self.last_request_time = time.time()

def load_api_key():
    """加载环境变量"""
    # 向上查找 .env
    # current: backend/test/kol/secidtToKOL/code/check_kol_status.py
    backend_dir = Path(__file__).resolve().parents[4]
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 从 {env_path} 加载环境变量")
    else:
        # 尝试cwd
        cwd_env = Path.cwd() / '.env'
        if cwd_env.exists():
            load_dotenv(cwd_env)
            print(f"✅ 从 {cwd_env} 加载环境变量")
            
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError("环境变量 tikhub_API_KEY 未设置")
    return api_key

def get_source_users(source_dirs):
    """从源目录提取符合条件的用户"""
    users = {} # sec_uid -> user_info
    
    print(f"🔍 开始扫描源文件...")
    
    for directory in source_dirs:
        path = Path(directory)
        if not path.exists():
            print(f"⚠️ 目录不存在: {path}")
            continue
            
        files = list(path.glob("video_search_page_*.json"))
        print(f"📂 扫描目录: {path.name} ({len(files)} 个文件)")
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 解析数据结构
                api_data = data.get('data', [])
                items = []
                if isinstance(api_data, list):
                    items = api_data
                elif isinstance(api_data, dict):
                    items = api_data.get('data') or api_data.get('aweme_list') or []
                
                for item in items:
                    author = None
                    if 'author' in item:
                        author = item['author']
                    elif 'aweme_info' in item and 'author' in item['aweme_info']:
                        author = item['aweme_info']['author']
                    
                    if author:
                        sec_uid = author.get('sec_uid')
                        uid = author.get('uid')
                        nickname = author.get('nickname')
                        follower_count = author.get('follower_count')
                        
                        # 必须有 sec_uid 且粉丝数符合要求
                        if sec_uid and follower_count is not None:
                            try:
                                fc = int(follower_count)
                                if 100000 <= fc <= 1000000:
                                    # 去重，保留最新的信息
                                    users[sec_uid] = {
                                        "uid": str(uid),
                                        "sec_uid": sec_uid,
                                        "nickname": nickname,
                                        "follower_count": fc,
                                        "source_file": file_path.name
                                    }
                            except (ValueError, TypeError):
                                pass
                                
            except Exception as e:
                print(f"❌ 读取文件 {file_path.name} 失败: {e}")
                
    print(f"✅ 共提取到 {len(users)} 个符合条件的用户 (10w-100w粉丝)")
    return list(users.values())

def check_kol_status(user, api_key, output_dir, rate_limiter):
    """检查单个用户的KOL状态"""
    sec_uid = user['sec_uid']
    uid = user['uid']
    nickname = user['nickname']
    
    # 检查是否已处理
    output_file = output_dir / f"kol_check_{uid}.json"
    if output_file.exists():
        # print(f"⏭️ 用户 {nickname} 已检查，跳过")
        return None # 返回None表示跳过
        
    url = "https://api.tikhub.io/api/v1/douyin/xingtu/get_xingtu_kolid_by_sec_user_id"
    params = {"sec_user_id": sec_uid}
    headers = {"Authorization": f"Bearer {api_key}"}
    
    rate_limiter.wait_if_needed()
    
    print(f"📡 检查用户: {nickname} (粉丝: {user['follower_count']})")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        # 保存结果
        result_data = {
            "user_info": user,
            "api_response": {},
            "is_kol": False,
            "kol_id": None,
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status_code": response.status_code
        }
        
        if response.status_code == 200:
            data = response.json()
            result_data["api_response"] = data
            
            # 解析 kol_id
            # 根据文档和返回结构: {"data": {"id": "...", ...}, "code": 200}
            # 如果没有 id 或者 id 为空/0，则不是 KOL
            kol_data = data.get('data', {})
            kol_id = kol_data.get('id')
            
            if kol_id and str(kol_id) != "0":
                print(f"   ✅ 是星图KOL! ID: {kol_id}")
                result_data["is_kol"] = True
                result_data["kol_id"] = str(kol_id)
            else:
                print(f"   ⚠️ 非星图KOL")
        else:
            print(f"   ❌ API请求失败: {response.status_code}")
            result_data["error"] = response.text
            
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
            
        return result_data
        
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        return None

def main():
    print("="*70)
    print("开始检查用户星图KOL状态 (粉丝 10w-100w)")
    print("="*70)
    
    try:
        api_key = load_api_key()
    except Exception as e:
        print(f"❌ {e}")
        return

    # 目录配置
    # 当前脚本在 backend/test/kol/secidtToKOL/code/
    # 项目根目录在 backend 上两级
    project_root = Path(__file__).resolve().parents[5] 
    
    # 源数据目录
    # 修正路径: searchVideoToFindKOL 而不是 video
    source_dirs = [
        project_root / "backend/test/kol/searchVideoToFindKOL/douyin-search-video/output/keyword_护肤保养/detail",
        project_root / "backend/test/kol/searchVideoToFindKOL/douyin-search-video/output/keyword_皮肤好_专家/detail"
    ]
    
    # 输出目录
    output_dir = Path(__file__).parent.parent / "detail"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary_dir = Path(__file__).parent.parent / "output"
    summary_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 获取用户
    users = get_source_users(source_dirs)
    
    if not users:
        print("未找到符合条件的用户")
        return
        
    # 2. 遍历检查
    rate_limiter = RateLimiter(max_per_second=3) # 稍微快一点，接口文档说 0.001$/次，注意余额
    
    checked_count = 0
    kol_count = 0
    
    for user in users:
        result = check_kol_status(user, api_key, output_dir, rate_limiter)
        if result:
            checked_count += 1
            if result['is_kol']:
                kol_count += 1
                
    # 3. 生成汇总
    print(f"\n{'='*70}")
    print(f"🎉 任务完成")
    print(f"新检查: {checked_count} 人")
    print(f"发现KOL: {kol_count} 人")
    
    # 扫描 detail 目录生成完整报告
    all_results = []
    for f in output_dir.glob("kol_check_*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                all_results.append(json.load(file))
        except:
            pass
            
    xingtu_kols = [r for r in all_results if r.get('is_kol')]
    
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_checked_files": len(all_results),
        "xingtu_kol_count": len(xingtu_kols),
        "xingtu_kol_list": [
            {
                "uid": r['user_info']['uid'],
                "nickname": r['user_info']['nickname'],
                "kol_id": r['kol_id'],
                "follower_count": r['user_info']['follower_count']
            }
            for r in xingtu_kols
        ]
    }
    
    report_file = summary_dir / "xingtu_kol_summary.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    print(f"📝 汇总报告已保存: {report_file}")

if __name__ == "__main__":
    main()

