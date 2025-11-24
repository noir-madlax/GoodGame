#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
搜索抖音视频 - 关键词 "护肤保养"
接口: /api/v1/douyin/search/fetch_video_search_v4

功能：
1. 搜索指定关键词的视频
2. 获取前3页数据
3. 自动处理翻页参数 (offset, page, backtrace, search_id)
4. 保存原始JSON数据

作者: AI Agent
创建时间: 2025-11-24
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import threading

class RateLimiter:
    """速率限制器：每秒最多N个请求"""
    def __init__(self, max_per_second=5):
        self.max_per_second = max_per_second
        self.min_interval = 1.0 / max_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()

def load_api_key():
    """从环境变量加载 TikHub API Key"""
    # 根据脚本位置向上查找 .env
    # 当前: backend/test/video/douyin-search-video/code/fetch_videos.py
    # .env: backend/.env
    backend_dir = Path(__file__).resolve().parents[4]
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 从 {env_path} 加载环境变量")
    else:
        # 尝试从当前工作目录查找
        cwd_env = Path.cwd() / '.env'
        if cwd_env.exists():
             load_dotenv(cwd_env)
             print(f"✅ 从 {cwd_env} 加载环境变量")
        else:
             print(f"⚠️ 未找到 .env 文件")
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    
    return api_key

def fetch_video_search_page(keyword, page, offset, backtrace, search_id, api_key, rate_limiter):
    """
    获取单页视频搜索结果
    """
    # 使用大陆可访问域名
    # url = "https://api.tikhub.dev/api/v1/douyin/search/fetch_video_search_v4"
    url = "https://api.tikhub.io/api/v1/douyin/search/fetch_video_search_v4"
    
    payload = {
        "keyword": keyword,
        "offset": offset,
        "page": page,
        "backtrace": backtrace,
        "search_id": search_id
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    rate_limiter.wait_if_needed()
    
    print(f"➡️ 请求第 {page} 页 (offset={offset}, backtrace={backtrace[:10]}..., search_id={search_id[:10]}...)")
    print(f"   URL: {url}")
    print(f"   Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   响应内容: {e.response.text}")
        return None

def main():
    print("\n" + "="*70)
    print("开始获取抖音视频搜索数据 - 关键词: 护肤保养")
    print("="*70 + "\n")
    
    try:
        api_key = load_api_key()
    except Exception as e:
        print(f"❌ {e}")
        return

    # 设置输出目录
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / 'output' / 'keyword_护肤保养' / 'detail'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rate_limiter = RateLimiter(max_per_second=2) # 保守一点
    
    # 初始参数
    keyword = "护肤保养"
    current_page = 0
    current_offset = 0
    current_backtrace = ""
    current_search_id = ""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 获取前3页
    max_pages = 3
    
    for i in range(max_pages):
        print(f"\n📄 正在获取第 {current_page} 页...")
        
        data = fetch_video_search_page(
            keyword, 
            current_page, 
            current_offset, 
            current_backtrace, 
            current_search_id, 
            api_key, 
            rate_limiter
        )
        
        if not data or data.get('code') != 200:
            print(f"❌ 获取失败或返回错误码: {data.get('code') if data else 'No Data'}")
            if data:
                print(f"   消息: {data.get('message')}")
            break
            
        # 保存数据
        filename = f"video_search_page_{current_page}_{timestamp}.json"
        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存: {filepath.name}")
        
        # 提取下一页参数
        # 注意：需要根据实际返回结构调整字段获取方式
        # 根据经验，这些字段可能在 data 对象下
        resp_data = data.get('data', {})
        
        # 尝试获取翻页参数
        # 优先从 data 中获取，如果没有则看 root (视API具体实现而定)
        next_offset = resp_data.get('offset')
        # 注意：有时候 offset 在 API 中是 'cursor' 或者其他名字，但文档说是 offset
        # 按照文档：翻页时从上一次响应中获取 offset、backtrace 和 search_id
        
        # 如果 data 中没有，尝试在 root 找 (虽然不太可能，但为了健壮性)
        if next_offset is None:
            next_offset = data.get('offset')
            
        next_backtrace = resp_data.get('backtrace') or data.get('backtrace') or ""
        next_search_id = resp_data.get('search_id') or data.get('search_id') or ""
        
        items = resp_data.get('data', []) # 视频列表通常在 data.data 或 data.aweme_list
        # 根据文档截图，返回包含 config 和 data。 data 是业务数据。
        # 通常 items 可能是 data.data 或者 data 列表本身
        # 这里的 resp_data = data['data']
        # 让我们打印一下 keys 方便调试
        # print(f"   Response Keys: {resp_data.keys()}")
        
        # 更新参数
        if next_offset is not None:
            current_offset = next_offset
        else:
            print("⚠️ 未找到 offset 字段，尝试手动增加 offset (不建议)")
            # 如果没找到，可能到底了或者结构不对
            # 暂时不做手动增加，以免死循环
            pass
            
        current_backtrace = next_backtrace
        current_search_id = next_search_id
        current_page += 1
        
        # 简单检查是否有更多数据
        if not resp_data:
             print("⚠️ data 为空，停止翻页")
             break

    print(f"\n{'='*70}")
    print(f"✅ 任务完成")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()

