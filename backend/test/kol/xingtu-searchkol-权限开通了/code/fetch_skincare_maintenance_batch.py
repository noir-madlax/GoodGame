#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量获取"护肤保养"关键词数据（支持速率限制和重试）

功能：
1. 检查已有的页面数据，避免重复获取
2. 批量获取指定范围的页面
3. 失败自动重试（最多3次）
4. 速率限制（每秒最多5个请求）
5. 实时显示进度

作者: AI Agent
创建时间: 2025-11-18
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import threading
from queue import Queue


class RateLimiter:
    """速率限制器：每秒最多N个请求"""
    def __init__(self, max_per_second=5):
        self.max_per_second = max_per_second  # 每秒最多请求数
        self.min_interval = 1.0 / max_per_second  # 最小间隔时间
        self.last_request_time = 0  # 上次请求时间
        self.lock = threading.Lock()  # 线程锁
    
    def wait_if_needed(self):
        """如果需要，等待到可以发起下一个请求"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()


def load_api_key():
    """从环境变量加载 TikHub API Key"""
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 从 {env_path} 加载环境变量")
    else:
        print(f"⚠️ 未找到 .env 文件: {env_path}")
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    
    return api_key


def search_kol_with_retry(keyword, page, api_key, rate_limiter, max_retries=3):
    """
    调用 TikHub API 搜索星图 KOL（带重试机制）
    
    Args:
        keyword: 搜索关键词
        page: 页码
        api_key: API密钥
        rate_limiter: 速率限制器
        max_retries: 最大重试次数
    
    Returns:
        API响应数据，失败返回None
    """
    # 使用大陆可访问域名，避免防火墙拦截
    url = "https://api.tikhub.dev/api/v1/douyin/xingtu/search_kol_v1"
    
    params = {
        "keyword": keyword,
        "page": str(page),
        "count": "20",
        "sort_type": "1",
        "platformSource": "_1"
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    for attempt in range(max_retries):
        try:
            # 等待速率限制
            rate_limiter.wait_if_needed()
            
            # 发起请求
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查响应是否成功
            if data.get('code') == 200:
                return data
            else:
                print(f"   ⚠️ API返回错误: {data.get('message', 'Unknown error')}")
                if attempt < max_retries - 1:
                    print(f"   ⏳ 1秒后重试 (尝试 {attempt + 2}/{max_retries})...")
                    time.sleep(1)
                    continue
                else:
                    return None
        
        except requests.exceptions.RequestException as e:
            print(f"   ❌ 请求异常: {e}")
            if attempt < max_retries - 1:
                print(f"   ⏳ 1秒后重试 (尝试 {attempt + 2}/{max_retries})...")
                time.sleep(1)
                continue
            else:
                return None
    
    return None


def get_existing_pages(detail_dir):
    """获取已存在的页码列表"""
    existing_pages = []
    for file in Path(detail_dir).glob('raw_page_*.json'):
        try:
            page_num = int(file.stem.split('_')[2])
            existing_pages.append(page_num)
        except:
            pass
    return sorted(existing_pages)


def fetch_page_range(keyword, start_page, end_page, output_dir, api_key):
    """
    获取指定范围的页面数据
    
    Args:
        keyword: 搜索关键词
        start_page: 起始页码
        end_page: 结束页码（包含）
        output_dir: 输出目录
        api_key: API密钥
    
    Returns:
        成功页数, 失败页数, 跳过页数
    """
    detail_dir = output_dir / 'detail'
    detail_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查已有页面
    existing_pages = get_existing_pages(detail_dir)
    
    print(f"\n{'='*70}")
    print(f"📋 批量获取任务")
    print(f"{'='*70}")
    print(f"关键词: '{keyword}'")
    print(f"目标范围: 第 {start_page} - {end_page} 页")
    print(f"已有页面: {len(existing_pages)} 页")
    print(f"{'='*70}\n")
    
    # 创建速率限制器（每秒最多5个请求）
    rate_limiter = RateLimiter(max_per_second=5)
    
    success_count = 0
    failure_count = 0
    skip_count = 0
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    total_pages = end_page - start_page + 1
    
    for page in range(start_page, end_page + 1):
        current = page - start_page + 1
        progress = f"[{current}/{total_pages}]"
        
        # 检查是否已存在
        if page in existing_pages:
            print(f"⏭️  {progress} 第 {page} 页已存在，跳过")
            skip_count += 1
            continue
        
        print(f"📄 {progress} 正在获取第 {page} 页...", end='', flush=True)
        
        # 调用API（带重试）
        data = search_kol_with_retry(keyword, page, api_key, rate_limiter, max_retries=3)
        
        if data and data.get('code') == 200:
            # 保存数据
            filename = f"raw_page_{page}_{timestamp}.json"
            filepath = detail_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            authors = data.get('data', {}).get('authors', [])
            has_more = data.get('data', {}).get('pagination', {}).get('has_more', False)
            
            print(f" ✅ 成功 (达人数: {len(authors)}, has_more: {has_more})")
            success_count += 1
            
            # 如果没有更多数据，提前结束
            if not has_more:
                print(f"\n⚠️ 第 {page} 页显示 has_more=false，可能已到达数据末尾")
                break
        else:
            print(f" ❌ 失败（已重试3次）")
            failure_count += 1
    
    print(f"\n{'='*70}")
    print(f"📊 批量获取完成")
    print(f"{'='*70}")
    print(f"✅ 成功: {success_count} 页")
    print(f"❌ 失败: {failure_count} 页")
    print(f"⏭️  跳过: {skip_count} 页（已存在）")
    print(f"{'='*70}\n")
    
    return success_count, failure_count, skip_count


def verify_no_duplicates(detail_dir):
    """验证是否有重复的达人数据"""
    print("\n🔍 验证数据完整性...")
    
    all_author_ids = set()
    duplicate_ids = set()
    page_author_count = {}
    
    files = sorted(Path(detail_dir).glob('raw_page_*.json'))
    
    for file in files:
        try:
            page_num = int(file.stem.split('_')[2])
            
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                authors = data.get('data', {}).get('authors', [])
                
                page_ids = []
                for author in authors:
                    author_id = author.get('attribute_datas', {}).get('id')
                    if author_id:
                        page_ids.append(author_id)
                        if author_id in all_author_ids:
                            duplicate_ids.add(author_id)
                        all_author_ids.add(author_id)
                
                page_author_count[page_num] = len(page_ids)
        except Exception as e:
            print(f"⚠️ 读取文件失败 {file}: {e}")
    
    print(f"\n📊 数据统计:")
    print(f"   总页数: {len(files)}")
    print(f"   总达人数（原始）: {sum(page_author_count.values())}")
    print(f"   总达人数（去重）: {len(all_author_ids)}")
    print(f"   重复达人数: {len(duplicate_ids)}")
    
    if duplicate_ids:
        print(f"\n⚠️ 发现 {len(duplicate_ids)} 个重复达人ID")
        print(f"   重复ID示例: {list(duplicate_ids)[:5]}")
    else:
        print(f"\n✅ 无重复数据，数据质量良好")
    
    # 显示页面范围
    if page_author_count:
        min_page = min(page_author_count.keys())
        max_page = max(page_author_count.keys())
        print(f"\n📄 页面范围: 第 {min_page} - {max_page} 页")
    
    return len(all_author_ids), len(duplicate_ids)


def main():
    """主函数"""
    print("\n" + "="*70)
    print("批量获取'护肤保养'关键词数据")
    print("="*70 + "\n")
    
    try:
        # 1. 加载 API Key
        api_key = load_api_key()
        
        # 2. 设置目录
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / 'output' / 'keyword_护肤保养'
        
        # 3. 获取用户输入（或使用默认值）
        # 这里设置获取 79-150 页（剩余所有数据）
        start_page = 79
        end_page = 150
        
        print(f"📋 任务配置:")
        print(f"   关键词: 护肤保养")
        print(f"   起始页: {start_page}")
        print(f"   结束页: {end_page}")
        print(f"   总页数: {end_page - start_page + 1}")
        print(f"   速率限制: 每秒最多5个请求")
        print(f"   失败重试: 最多3次，间隔1秒\n")
        
        # 4. 执行批量获取
        success, failure, skip = fetch_page_range(
            keyword='护肤保养',
            start_page=start_page,
            end_page=end_page,
            output_dir=output_dir,
            api_key=api_key
        )
        
        # 5. 验证数据完整性
        detail_dir = output_dir / 'detail'
        total_unique, duplicates = verify_no_duplicates(detail_dir)
        
        print(f"\n{'='*70}")
        print(f"✅ 所有任务完成！")
        print(f"{'='*70}\n")
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 用户中断任务")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

