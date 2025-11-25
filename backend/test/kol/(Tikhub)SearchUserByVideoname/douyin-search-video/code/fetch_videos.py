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
    # 当前: backend/test/kol/video/douyin-search-video/code/fetch_videos.py
    # .env: backend/.env
    # parents[0]=code, [1]=douyin-search-video, [2]=video, [3]=kol, [4]=test, [5]=backend
    backend_dir = Path(__file__).resolve().parents[5]
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
    url_list = [
        "https://api.tikhub.dev/api/v1/douyin/search/fetch_video_search_v4",
        "https://api.tikhub.io/api/v1/douyin/search/fetch_video_search_v4"
    ]
    
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
    print(f"   Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    for url in url_list:
        try:
            print(f"   尝试 URL: {url}")
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   ❌ URL {url} 请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   响应内容: {e.response.text}")
            # Continue to next URL
            continue
            
    return None

def get_latest_state(output_dir):
    """
    从输出目录中获取最新的页面状态
    返回: (next_page_index, next_offset, next_backtrace, next_search_id)
    """
    if not output_dir.exists():
        return 0, 0, "", ""

    files = list(output_dir.glob("video_search_page_*.json"))
    if not files:
        return 0, 0, "", ""
        
    # 提取页码并排序
    page_files = []
    for f in files:
        try:
            # 文件名格式: video_search_page_{page}_{timestamp}.json
            parts = f.stem.split('_')
            page_num = int(parts[3])
            page_files.append((page_num, f))
        except (IndexError, ValueError):
            continue
            
    if not page_files:
        return 0, 0, "", ""
        
    # 按页码排序，取最大
    page_files.sort(key=lambda x: x[0])
    last_page_num, last_file = page_files[-1]
    
    print(f"🔍 发现已有进度，最后页码: {last_page_num}，文件: {last_file.name}")
    
    try:
        with open(last_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        resp_data = data.get('data', {})
        config = resp_data.get('config', {})
        next_page_info = config.get('next_page', {})
        
        next_offset = next_page_info.get('cursor')
        next_search_id = next_page_info.get('search_id')
        next_backtrace = config.get('backtrace')
        
        # 如果缺少关键翻页信息，则无法继续
        if next_offset is None or not next_search_id:
            print("⚠️ 上一页数据缺少翻页参数 (cursor/search_id)，无法断点续传")
            return last_page_num + 1, 0, "", "" # 尝试但不一定成功
            
        return last_page_num + 1, next_offset, next_backtrace, next_search_id
        
    except Exception as e:
        print(f"❌ 读取上一页数据失败: {e}")
        return 0, 0, "", ""

def main():
    # 关键词配置
    keyword = "皮肤好 专家"
    
    print("\n" + "="*70)
    print(f"开始获取抖音视频搜索数据 - 关键词: {keyword}")
    print("="*70 + "\n")
    
    try:
        api_key = load_api_key()
    except Exception as e:
        print(f"❌ {e}")
        return

    # 设置输出目录
    script_dir = Path(__file__).parent
    # 替换空格为下划线，避免路径问题
    safe_keyword = keyword.replace(" ", "_")
    output_dir = script_dir.parent / 'output' / f'keyword_{safe_keyword}' / 'detail'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rate_limiter = RateLimiter(max_per_second=2) # 保守一点
    
    # 恢复状态
    start_page, current_offset, current_backtrace, current_search_id = get_latest_state(output_dir)
    
    if start_page > 0:
        print(f"📋 恢复进度: 从第 {start_page} 页开始 (Offset: {current_offset})")
    else:
        print(f"📋 新任务: 从第 0 页开始")
    
    # 初始参数
    current_page = start_page
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 目标: 获取所有页，直到没有数据
    # target_page_count = 3
    # end_page = start_page + target_page_count
    
    # 设置一个较大的上限以防死循环，但主要依赖 has_more
    max_pages_limit = 100 
    
    while current_page < max_pages_limit:
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
                # 遇到错误是否终止？如果是临时的网络错误可能需要重试，这里简单处理先终止
                # 可以根据错误码决定
            break
            
        # 保存数据
        filename = f"video_search_page_{current_page}_{timestamp}.json"
        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存: {filepath.name}")
        
        # 提取下一页参数
        resp_data = data.get('data', {})
        config = resp_data.get('config', {})
        next_page_info = config.get('next_page', {})
        
        # 检查是否有更多数据
        has_more = config.get('has_more', 0)
        print(f"   Has More: {has_more}")
        
        # 获取翻页参数
        next_offset = next_page_info.get('cursor')
        next_search_id = next_page_info.get('search_id')
        next_backtrace = config.get('backtrace')
        
        print(f"   Next Offset: {next_offset}")
        print(f"   Next Search ID: {next_search_id}")
        
        # 验证翻页是否有效
        if current_page > 0 and next_offset == current_offset:
             print("⚠️ 警告: Offset 没有变化，可能陷入循环")
             # 可以在这里增加重试或者退出逻辑
             # 暂时先观察，如果 API 设计就是这样可能会有问题
             
        # 更新参数
        if next_offset is not None:
            current_offset = next_offset
        else:
            print("⚠️ 未找到 offset/cursor 字段")
            
        if next_search_id:
            current_search_id = next_search_id
            
        if next_backtrace:
            current_backtrace = next_backtrace
            
        current_page += 1
        
        # 如果没有更多数据，停止翻页
        if has_more == 0:
             print("✅ has_more=0，已到达最后一页")
             break
             
        # 简单的反爬虫延迟
        time.sleep(1)

    if current_page >= max_pages_limit:
        print(f"⚠️ 达到最大页数限制 ({max_pages_limit})，停止获取")

    print(f"\n{'='*70}")
    print(f"✅ 任务完成")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()

