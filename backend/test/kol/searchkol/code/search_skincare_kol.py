#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
搜索护肤达人脚本

功能：
1. 调用 TikHub API 的 fetch_user_search_v4 接口搜索"护肤达人"
2. 获取 3 页搜索结果数据
3. 分析腰部达人（粉丝数 10万~100万）的数量和分布
4. 将结果保存到 output 目录

接口文档: https://api.tikhub.io/#/Douyin-Search-API/fetch_user_search_v4_api_v1_douyin_search_fetch_user_search_v4_post
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter


def load_api_key():
    """
    从环境变量加载 TikHub API Key
    
    Returns:
        str: API Key
    
    Raises:
        ValueError: 如果 API Key 未设置
    """
    # 定位到 backend/.env 文件
    # 从 backend/test/kol/searchkol/code/ 需要上 4 级到 backend/
    backend_dir = Path(__file__).parent.parent.parent.parent.parent  # 返回到 backend 目录
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 从 {env_path} 加载环境变量")
    else:
        print(f"⚠️ 未找到 .env 文件: {env_path}")
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置，请在 {env_path} 文件中配置")
    
    return api_key


def fetch_user_search_v4(api_key: str, keyword: str, cursor: int = 0, offset: int = 0, 
                        page: int = 0, search_id: str = "", count: int = 10) -> dict:
    """
    调用 TikHub API 的 fetch_user_search_v4 接口搜索抖音用户
    
    Args:
        api_key: TikHub API 密钥
        keyword: 搜索关键词
        cursor: 游标，用于翻页（首次请求传 0）
        offset: 偏移量，用于翻页（首次请求传 0）
        page: 页码，用于翻页（首次请求传 0，之后每次加 1）
        search_id: 搜索ID，用于翻页（首次请求传空字符串，翻页时使用上次响应的 search_id）
        count: 每页返回的用户数量，默认 10
        
    Returns:
        dict: API 响应的 JSON 数据
    """
    # API 端点
    url = "https://api.tikhub.io/api/v1/douyin/search/fetch_user_search_v4"
    
    # 设置请求头
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 设置请求体（按照 API 文档要求）
    payload = {
        'keyword': keyword,          # 搜索关键词
        'cursor': cursor,            # 游标
        'offset': offset,            # 偏移量
        'page': page,                # 页码
        'search_id': search_id,      # 搜索ID
        'count': count,              # 每页数量
        'search_channel': 'aweme_user_web',  # 搜索渠道
        'sort_type': 0,             # 排序类型：0=综合排序，1=粉丝数排序
        'publish_time': 0           # 发布时间筛选：0=不限
    }
    
    print(f"\n📡 发送搜索请求...")
    print(f"   关键词: {keyword}")
    print(f"   游标 cursor: {cursor}")
    print(f"   偏移量 offset: {offset}")
    print(f"   页码 page: {page}")
    print(f"   搜索ID search_id: {search_id if search_id else '(空)'}")
    print(f"   数量 count: {count}")
    
    try:
        # 发送 POST 请求
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"   状态码: {response.status_code}")
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            
            # 打印响应结构（用于调试）
            print(f"   响应结构: {list(result.keys())}")
            
            # 检查响应代码（TikHub API 返回 200 表示成功）
            code = result.get('code', -1)
            if code == 200:
                data = result.get('data', {})
                
                # 数据结构是嵌套的：data.data 包含用户列表
                inner_data = data.get('data', [])
                config = data.get('config', {})
                
                # 用户列表直接在 data.data 中
                user_list = inner_data if isinstance(inner_data, list) else []
                
                # has_more 在 config 中
                has_more = config.get('has_more', 0) == 1
                
                print(f"   ✅ 成功获取 {len(user_list)} 个用户")
                print(f"   还有更多数据: {has_more}")
                
                # 在结果中添加请求信息，便于调试
                result['_request_payload'] = payload
                return result
            else:
                print(f"   ❌ API 返回错误码: {code}")
                print(f"   完整响应: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
                return result
        else:
            print(f"   ❌ HTTP 请求失败")
            print(f"   错误信息: {response.text[:200]}")
            return {
                "error": f"HTTP {response.status_code}",
                "message": response.text
            }
            
    except requests.exceptions.Timeout:
        print(f"   ❌ 请求超时")
        return {"error": "timeout"}
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 请求异常: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        print(f"   ❌ 未知错误: {str(e)}")
        return {"error": str(e)}


def fetch_multiple_pages(api_key: str, keyword: str, page_count: int = 3, count_per_page: int = 10, 
                        output_dir: str = None) -> tuple:
    """
    获取多页搜索结果（支持去重）
    
    Args:
        api_key: API 密钥
        keyword: 搜索关键词
        page_count: 要获取的页数
        count_per_page: 每页数量
        output_dir: 输出目录（用于保存详细的请求/响应）
        
    Returns:
        tuple: (用户数据列表, 每页详情列表)
    """
    all_users = []
    seen_uids = set()  # 用于去重的 UID 集合
    page_details = []  # 保存每页的详细信息
    
    # 初始化翻页参数（首次请求）
    cursor = 0
    offset = 0
    page = 0
    search_id = ""
    
    print(f"\n{'='*60}")
    print(f"🔍 开始搜索: {keyword}")
    print(f"   目标页数: {page_count}")
    print(f"   每页数量: {count_per_page}")
    print(f"{'='*60}")
    
    for page_num in range(1, page_count + 1):
        print(f"\n[第 {page_num}/{page_count} 页]")
        print(f"   当前翻页参数: cursor={cursor}, offset={offset}, page={page}, search_id={search_id if search_id else '(空)'}")
        print("-" * 60)
        
        # 调用 API
        result = fetch_user_search_v4(api_key, keyword, cursor, offset, page, search_id, count_per_page)
        
        # 检查是否成功（TikHub API 返回 200 表示成功）
        if 'error' in result or result.get('code') != 200:
            print(f"⚠️ 第 {page_num} 页获取失败，停止搜索")
            break
        
        # 提取用户列表（数据结构是嵌套的）
        data = result.get('data', {})
        inner_data = data.get('data', [])
        config = data.get('config', {})
        
        # 用户列表在 data.data 中
        user_list = inner_data if isinstance(inner_data, list) else []
        
        # 保存本页详情（用于输出）
        page_detail = {
            'page_num': page_num,
            'request': result.get('_request_payload', {}),
            'response_code': result.get('code'),
            'user_count': len(user_list),
            'config': config
        }
        page_details.append(page_detail)
        
        # 如果指定了输出目录，保存详细的请求/响应
        if output_dir:
            detail_file = os.path.join(output_dir, 'detail', f'page_{page_num}_request_response.json')
            os.makedirs(os.path.dirname(detail_file), exist_ok=True)
            with open(detail_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'page_num': page_num,
                    'request_payload': result.get('_request_payload', {}),
                    'response': result
                }, f, ensure_ascii=False, indent=2)
            print(f"   💾 已保存详情到: {detail_file}")
        
        if not user_list:
            print(f"⚠️ 第 {page_num} 页没有数据，停止搜索")
            break
        
        # 去重并添加到总列表
        new_users = 0
        duplicate_users = 0
        for user in user_list:
            user_info = user.get('user_info', {})
            uid = user_info.get('uid', '')
            
            if uid and uid not in seen_uids:
                seen_uids.add(uid)
                all_users.append(user)
                new_users += 1
            else:
                duplicate_users += 1
        
        print(f"\n本页统计:")
        print(f"   原始用户数: {len(user_list)}")
        print(f"   新增用户数: {new_users}")
        print(f"   重复用户数: {duplicate_users}")
        
        # 显示本页用户信息（显示前3个）
        if len(user_list) > 0:
            print(f"\n本页用户预览（前3个）:")
            for i, user in enumerate(user_list[:3], 1):
                user_info = user.get('user_info', {})
                nickname = user_info.get('nickname', 'N/A')
                follower_count = user_info.get('follower_count', 0)
                aweme_count = user_info.get('aweme_count', 0)
                print(f"   {i}. {nickname} - 粉丝: {follower_count:,} - 作品: {aweme_count}")
        
        # 检查是否还有更多数据（在 config 中）
        has_more = config.get('has_more', 0) == 1
        next_page_info = config.get('next_page', {})
        
        print(f"\n下一页参数:")
        print(f"   还有更多: {has_more}")
        print(f"   next_page信息: {json.dumps(next_page_info, ensure_ascii=False)}")
        
        if not has_more:
            print(f"\n✅ 已获取所有数据（共 {page_num} 页）")
            break
        
        # 更新翻页参数（从 next_page 中获取）
        # 根据 API 文档：翻页时从上一次响应中获取 cursor、offset 和 search_id，page 每次加 1
        if next_page_info:
            cursor = next_page_info.get('cursor', cursor)
            offset = next_page_info.get('offset', offset)  # 尝试获取 offset
            search_id = next_page_info.get('search_id', search_id)
            
            # 从 search_request_id 获取 search_id（备选）
            if not search_id and 'search_request_id' in next_page_info:
                search_id = next_page_info.get('search_request_id', '')
        
        # page 每次加 1
        page += 1
        
        print(f"\n更新后的翻页参数:")
        print(f"   cursor: {cursor}")
        print(f"   offset: {offset}")
        print(f"   page: {page}")
        print(f"   search_id: {search_id if search_id else '(空)'}")
        
        # 添加延迟，避免请求过快
        if page_num < page_count:
            print(f"\n⏳ 等待 1 秒后继续...")
            time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"✅ 搜索完成！")
    print(f"   去重后用户数: {len(all_users)}")
    print(f"   唯一 UID 数: {len(seen_uids)}")
    print(f"{'='*60}")
    
    return all_users, page_details


def analyze_kol_distribution(users: list) -> dict:
    """
    分析达人的粉丝数分布
    
    定义：
    - 头部达人: 粉丝数 > 100万
    - 腰部达人: 粉丝数 10万 ~ 100万
    - 尾部达人: 粉丝数 1万 ~ 10万
    - 素人: 粉丝数 < 1万
    
    Args:
        users: 用户列表
        
    Returns:
        dict: 分析结果
    """
    print(f"\n{'='*60}")
    print(f"📊 开始分析达人分布")
    print(f"{'='*60}")
    
    # 分类统计
    categories = {
        '头部达人 (>100万)': [],
        '腰部达人 (10万~100万)': [],
        '尾部达人 (1万~10万)': [],
        '素人 (<1万)': []
    }
    
    # 粉丝数区间统计（更细致的区间）
    follower_ranges = {
        '1万以下': 0,
        '1-5万': 0,
        '5-10万': 0,
        '10-20万': 0,
        '20-50万': 0,
        '50-100万': 0,
        '100-200万': 0,
        '200-500万': 0,
        '500万以上': 0
    }
    
    # 遍历用户进行分类
    for user in users:
        # 用户信息在 user_info 中
        user_info = user.get('user_info', {})
        follower_count = user_info.get('follower_count', 0)
        nickname = user_info.get('nickname', 'N/A')
        
        # 分类
        if follower_count > 1_000_000:
            categories['头部达人 (>100万)'].append(user)
        elif follower_count >= 100_000:
            categories['腰部达人 (10万~100万)'].append(user)
        elif follower_count >= 10_000:
            categories['尾部达人 (1万~10万)'].append(user)
        else:
            categories['素人 (<1万)'].append(user)
        
        # 细分区间统计
        if follower_count < 10_000:
            follower_ranges['1万以下'] += 1
        elif follower_count < 50_000:
            follower_ranges['1-5万'] += 1
        elif follower_count < 100_000:
            follower_ranges['5-10万'] += 1
        elif follower_count < 200_000:
            follower_ranges['10-20万'] += 1
        elif follower_count < 500_000:
            follower_ranges['20-50万'] += 1
        elif follower_count < 1_000_000:
            follower_ranges['50-100万'] += 1
        elif follower_count < 2_000_000:
            follower_ranges['100-200万'] += 1
        elif follower_count < 5_000_000:
            follower_ranges['200-500万'] += 1
        else:
            follower_ranges['500万以上'] += 1
    
    # 打印分析结果
    print(f"\n总用户数: {len(users)}")
    print(f"\n达人分类统计:")
    print("-" * 60)
    
    for category, user_list in categories.items():
        count = len(user_list)
        percentage = (count / len(users) * 100) if users else 0
        print(f"  {category}: {count} 人 ({percentage:.1f}%)")
    
    print(f"\n粉丝数区间分布:")
    print("-" * 60)
    
    for range_name, count in follower_ranges.items():
        percentage = (count / len(users) * 100) if users else 0
        bar = '█' * int(percentage / 2)  # 可视化条形图
        print(f"  {range_name:12s}: {count:3d} 人 ({percentage:5.1f}%) {bar}")
    
    # 腰部达人详细分析
    print(f"\n{'='*60}")
    print(f"🎯 腰部达人详细分析 (粉丝数 10万~100万)")
    print(f"{'='*60}")
    
    waist_kols = categories['腰部达人 (10万~100万)']
    print(f"腰部达人总数: {len(waist_kols)}")
    
    if waist_kols:
        # 按粉丝数排序
        waist_kols_sorted = sorted(waist_kols, key=lambda x: x.get('user_info', {}).get('follower_count', 0), reverse=True)
        
        # 统计
        follower_counts = [user.get('user_info', {}).get('follower_count', 0) for user in waist_kols]
        avg_followers = sum(follower_counts) / len(follower_counts)
        max_followers = max(follower_counts)
        min_followers = min(follower_counts)
        
        print(f"\n粉丝数统计:")
        print(f"  平均粉丝数: {avg_followers:,.0f}")
        print(f"  最高粉丝数: {max_followers:,}")
        print(f"  最低粉丝数: {min_followers:,}")
        
        print(f"\n腰部达人 TOP 10:")
        print("-" * 60)
        
        for i, user in enumerate(waist_kols_sorted[:10], 1):
            user_info = user.get('user_info', {})
            nickname = user_info.get('nickname', 'N/A')
            follower_count = user_info.get('follower_count', 0)
            total_favorited = user_info.get('total_favorited', 0)
            aweme_count = user_info.get('aweme_count', 0)
            signature = user_info.get('signature', '')[:30]  # 限制长度
            
            print(f"  {i:2d}. {nickname}")
            print(f"      粉丝: {follower_count:,} | 获赞: {total_favorited:,} | 作品: {aweme_count}")
            if signature:
                print(f"      简介: {signature}...")
    
    # 构建返回结果
    analysis_result = {
        'summary': {
            'total_users': len(users),
            'head_kols': len(categories['头部达人 (>100万)']),
            'waist_kols': len(categories['腰部达人 (10万~100万)']),
            'tail_kols': len(categories['尾部达人 (1万~10万)']),
            'normal_users': len(categories['素人 (<1万)'])
        },
        'follower_ranges': follower_ranges,
        'waist_kol_details': {
            'count': len(waist_kols),
            'avg_followers': avg_followers if waist_kols else 0,
            'max_followers': max_followers if waist_kols else 0,
            'min_followers': min_followers if waist_kols else 0,
            'top_10': waist_kols_sorted[:10] if waist_kols else []
        },
        'categories': {
            category: [
                {
                    'nickname': user.get('user_info', {}).get('nickname'),
                    'follower_count': user.get('user_info', {}).get('follower_count'),
                    'total_favorited': user.get('user_info', {}).get('total_favorited'),
                    'aweme_count': user.get('user_info', {}).get('aweme_count'),
                    'uid': user.get('user_info', {}).get('uid'),
                    'unique_id': user.get('user_info', {}).get('unique_id'),
                    'signature': user.get('user_info', {}).get('signature', '')
                }
                for user in user_list
            ]
            for category, user_list in categories.items()
        }
    }
    
    return analysis_result


def save_results(all_users: list, analysis: dict, page_details: list, output_dir: str, keyword: str):
    """
    保存搜索结果和分析结果到文件
    
    Args:
        all_users: 所有用户数据
        analysis: 分析结果
        page_details: 每页详情列表
        output_dir: 输出目录
        keyword: 搜索关键词
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. 保存原始搜索结果（3页完整数据）
    raw_data_file = os.path.join(output_dir, f'search_results_3pages_{timestamp}.json')
    with open(raw_data_file, 'w', encoding='utf-8') as f:
        json.dump({
            'search_metadata': {
                'keyword': keyword,
                'search_date': datetime.now().isoformat(),
                'total_users': len(all_users),
                'api_interface': 'fetch_user_search_v4'
            },
            'users': all_users
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 原始搜索结果已保存到: {raw_data_file}")
    
    # 2. 保存分析结果
    analysis_file = os.path.join(output_dir, f'waist_kol_analysis_{timestamp}.json')
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis_metadata': {
                'keyword': keyword,
                'analysis_date': datetime.now().isoformat(),
                'total_users': len(all_users)
            },
            'analysis': analysis
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 分析结果已保存到: {analysis_file}")
    
    # 3. 保存腰部达人单独列表（便于查看）
    waist_kols = analysis['categories']['腰部达人 (10万~100万)']
    waist_kol_file = os.path.join(output_dir, f'waist_kols_only_{timestamp}.json')
    with open(waist_kol_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'keyword': keyword,
                'date': datetime.now().isoformat(),
                'count': len(waist_kols)
            },
            'waist_kols': waist_kols
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 腰部达人列表已保存到: {waist_kol_file}")
    
    # 4. 保存分页详情摘要
    page_summary_file = os.path.join(output_dir, f'page_summary_{timestamp}.json')
    with open(page_summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'keyword': keyword,
                'date': datetime.now().isoformat(),
                'total_pages': len(page_details)
            },
            'page_details': page_details
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 分页摘要已保存到: {page_summary_file}")
    
    # 5. 生成简报文件（Markdown 格式）
    report_file = os.path.join(output_dir, f'analysis_report_{timestamp}.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 护肤达人搜索分析报告\n\n")
        f.write(f"**搜索关键词**: {keyword}\n")
        f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**数据来源**: 抖音用户搜索 API (fetch_user_search_v4)\n\n")
        
        f.write(f"## 总体统计\n\n")
        f.write(f"- 总用户数: {analysis['summary']['total_users']}\n")
        f.write(f"- 头部达人 (>100万): {analysis['summary']['head_kols']} 人\n")
        f.write(f"- **腰部达人 (10万~100万): {analysis['summary']['waist_kols']} 人**\n")
        f.write(f"- 尾部达人 (1万~10万): {analysis['summary']['tail_kols']} 人\n")
        f.write(f"- 素人 (<1万): {analysis['summary']['normal_users']} 人\n\n")
        
        f.write(f"## 粉丝数区间分布\n\n")
        f.write(f"| 区间 | 数量 | 占比 |\n")
        f.write(f"|------|------|------|\n")
        total = analysis['summary']['total_users']
        for range_name, count in analysis['follower_ranges'].items():
            percentage = (count / total * 100) if total > 0 else 0
            f.write(f"| {range_name} | {count} | {percentage:.1f}% |\n")
        
        f.write(f"\n## 腰部达人详细信息\n\n")
        waist_details = analysis['waist_kol_details']
        f.write(f"- **总数**: {waist_details['count']} 人\n")
        f.write(f"- **平均粉丝数**: {waist_details['avg_followers']:,.0f}\n")
        f.write(f"- **粉丝数范围**: {waist_details['min_followers']:,} ~ {waist_details['max_followers']:,}\n\n")
        
        if waist_details['top_10']:
            f.write(f"### 腰部达人 TOP 10\n\n")
            f.write(f"| 排名 | 昵称 | 粉丝数 | 获赞数 | 作品数 | 抖音号 |\n")
            f.write(f"|------|------|--------|--------|--------|--------|\n")
            
            for i, user in enumerate(waist_details['top_10'], 1):
                user_info = user.get('user_info', {})
                nickname = user_info.get('nickname', 'N/A')
                follower_count = user_info.get('follower_count', 0)
                total_favorited = user_info.get('total_favorited', 0)
                aweme_count = user_info.get('aweme_count', 0)
                unique_id = user_info.get('unique_id', 'N/A')
                
                f.write(f"| {i} | {nickname} | {follower_count:,} | {total_favorited:,} | {aweme_count} | {unique_id} |\n")
    
    print(f"💾 分析报告已保存到: {report_file}")
    
    print(f"\n{'='*60}")
    print(f"✅ 所有文件保存完成！")
    print(f"{'='*60}")


def main():
    """主函数：搜索护肤达人并分析"""
    
    print("=" * 60)
    print("抖音护肤达人搜索与分析工具")
    print("API 接口: fetch_user_search_v4")
    print("=" * 60)
    
    # 1. 加载 API Key
    print("\n1️⃣ 加载 API 配置...")
    try:
        api_key = load_api_key()
        print(f"✅ API Key 已加载: {api_key[:10]}...{api_key[-10:]}")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # 2. 搜索护肤达人（获取 3 页数据）
    print("\n2️⃣ 开始搜索...")
    keyword = "护肤"
    page_count = 3
    count_per_page = 20  # 每页20个结果
    
    # 准备输出目录
    script_dir = Path(__file__).parent.parent  # backend/test/kol/searchkol/
    output_dir = script_dir / "output"
    
    all_users, page_details = fetch_multiple_pages(api_key, keyword, page_count, count_per_page, str(output_dir))
    
    if not all_users:
        print("❌ 未获取到任何用户数据")
        return
    
    # 3. 分析达人分布
    print("\n3️⃣ 分析达人分布...")
    analysis = analyze_kol_distribution(all_users)
    
    # 4. 保存结果
    print("\n4️⃣ 保存结果...")
    save_results(all_users, analysis, page_details, str(output_dir), keyword)
    
    print("\n✅ 全部完成！")
    print(f"\n📌 关键发现:")
    print(f"   搜索关键词: {keyword}")
    print(f"   总用户数: {len(all_users)}")
    print(f"   腰部达人数: {analysis['summary']['waist_kols']} 人")
    print(f"   腰部达人占比: {(analysis['summary']['waist_kols'] / len(all_users) * 100):.1f}%")


if __name__ == "__main__":
    main()

