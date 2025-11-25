#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导出用户数据为JSON格式，用于MCP导入
"""

import os
import json
from pathlib import Path
from datetime import datetime


def load_users_from_directory(output_dir: Path, keyword: str):
    """从指定目录加载用户数据"""
    detail_dir = output_dir / "detail"
    
    users = {}
    
    if not detail_dir.exists():
        return users
    
    # 遍历所有page文件
    page_files = sorted(detail_dir.glob("page_*_request_response.json"))
    
    for page_file in page_files:
        with open(page_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        response = data.get('response', {})
        response_data = response.get('data', {})
        inner_data = response_data.get('data', [])
        
        if not isinstance(inner_data, list):
            continue
        
        for item in inner_data:
            user_info = item.get('user_info', {})
            uid = user_info.get('uid')
            
            if not uid:
                continue
            
            # 准备核心字段
            user_record = {
                'uid': str(uid),
                'sec_uid': user_info.get('sec_uid'),
                'nickname': user_info.get('nickname'),
                'unique_id': user_info.get('unique_id'),
                'gender': user_info.get('gender'),
                'follower_count': user_info.get('follower_count'),
                'verification_type': user_info.get('verification_type'),
                'avatar_url': user_info.get('avatar_thumb', {}).get('url_list', [None])[0],
                'signature': user_info.get('signature'),
                'live_status': user_info.get('live_status'),
                
                # 扩展信息
                'extra_info': {
                    'display_info': user_info.get('display_info'),
                    'user_tags': user_info.get('user_tags'),
                    'versatile_display': user_info.get('versatile_display'),
                    'weibo_verify': user_info.get('weibo_verify'),
                    'custom_verify': user_info.get('custom_verify'),
                    'enterprise_verify_reason': user_info.get('enterprise_verify_reason'),
                },
                
                # 完整原始数据
                'raw_data': user_info,
                
                # 搜索信息
                'search_keyword': keyword,
                'search_date': datetime.now().isoformat()
            }
            
            users[uid] = user_record
    
    return users


def main():
    """主函数"""
    print("=" * 60)
    print("导出用户数据为JSON")
    print("=" * 60)
    
    script_dir = Path(__file__).parent.parent
    
    # 收集所有用户数据
    all_users = {}
    
    # 1. 加载"护肤"搜索结果
    output_dir1 = script_dir / "output"
    if output_dir1.exists():
        print(f"\n📂 处理目录: {output_dir1}")
        users = load_users_from_directory(output_dir1, "护肤")
        print(f"   找到 {len(users)} 个用户")
        for uid, user in users.items():
            if uid not in all_users:
                all_users[uid] = user
    
    # 2. 加载"护肤 达人 博主"搜索结果
    output_dirs = list(script_dir.glob("output_kol_full_*"))
    for output_dir in output_dirs:
        print(f"\n📂 处理目录: {output_dir}")
        users = load_users_from_directory(output_dir, "护肤 达人 博主")
        print(f"   找到 {len(users)} 个用户")
        for uid, user in users.items():
            if uid not in all_users:
                all_users[uid] = user
    
    print(f"\n✅ 总共找到 {len(all_users)} 个唯一用户")
    
    # 导出为JSON
    output_file = script_dir / "code" / "users_export.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(list(all_users.values()), f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 已导出到: {output_file}")
    print(f"   文件大小: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    # 统计信息
    follower_counts = [u['follower_count'] for u in all_users.values() if u.get('follower_count')]
    if follower_counts:
        print(f"\n📊 数据统计:")
        print(f"   粉丝数最高: {max(follower_counts):,}")
        print(f"   粉丝数最低: {min(follower_counts):,}")
        print(f"   平均粉丝数: {sum(follower_counts)//len(follower_counts):,}")
    
    print(f"\n{'='*60}")
    print("✅ 导出完成！")


if __name__ == "__main__":
    main()

