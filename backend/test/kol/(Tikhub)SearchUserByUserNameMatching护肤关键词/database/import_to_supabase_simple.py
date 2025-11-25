#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用简单的HTTP请求导入数据到Supabase
"""

import json
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

def load_env():
    """加载环境变量"""
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    return os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')

def main():
    print("=" * 60)
    print("导入用户数据到Supabase")
    print("=" * 60)
    
    # 加载环境变量
    supabase_url, supabase_key = load_env()
    
    if not supabase_url or not supabase_key:
        print("❌ 未找到 SUPABASE_URL 或 SUPABASE_KEY")
        return
    
    print(f"✅ Supabase URL: {supabase_url[:30]}...")
    
    # 读取用户数据
    json_file = Path(__file__).parent / "users_export.json"
    with open(json_file, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    print(f"✅ 读取 {len(users)} 条用户数据")
    
    # Supabase REST API端点
    api_url = f"{supabase_url}/rest/v1/gg_douyin_user_search"
    
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates'  # upsert模式
    }
    
    # 分批导入（每批50条）
    batch_size = 50
    total_success = 0
    total_failed = 0
    
    for i in range(0, len(users), batch_size):
        batch = users[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        print(f"\n批次 {batch_num}: 导入 {len(batch)} 条数据...")
        
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=batch,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                total_success += len(batch)
                print(f"   ✅ 成功导入 {len(batch)} 条")
            else:
                total_failed += len(batch)
                print(f"   ❌ 失败: {response.status_code}")
                print(f"   错误信息: {response.text[:200]}")
        
        except Exception as e:
            total_failed += len(batch)
            print(f"   ❌ 异常: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ 导入完成！")
    print(f"   成功: {total_success} 条")
    print(f"   失败: {total_failed} 条")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

