#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音星图护肤达人搜索与结构化分析脚本 V2

功能：
1. 调用 TikHub API 的星图 search_kol_v1 接口搜索"护肤达人"
2. 获取 3 页搜索结果数据，分别保存每页的原始返回
3. 结构化解析关键业务数据
4. 检查3页数据是否重复
5. 输出关键达人信息到独立 JSON 文件

接口文档: https://api.tikhub.io/#/Douyin-Xingtu-API/search_kol_v1_api_v1_douyin_xingtu_search_kol_v1_get

数据说明：
- 原始返回保存在 output/detail/ 目录下，文件名：raw_page_{page}.json
- 解析后的关键业务数据保存在 output/detail/ 目录下，文件名：parsed_kol_data.json
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any


def load_api_key():
    """
    从环境变量加载 TikHub API Key
    
    Returns:
        str: API Key
    
    Raises:
        ValueError: 如果 API Key 未设置
    """
    # 定位到 backend/.env 文件
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


def fetch_kol_page(api_key: str, keyword: str, page: int, count: int = 20) -> Dict[str, Any]:
    """
    调用 TikHub API 的星图 search_kol_v1 接口获取一页 KOL 数据
    
    Args:
        api_key: TikHub API 密钥
        keyword: 搜索关键词
        page: 页码，从 1 开始
        count: 每页返回数量，默认 20
        
    Returns:
        dict: API 响应的完整 JSON 数据
    """
    # API 端点
    url = "https://api.tikhub.io/api/v1/douyin/xingtu/search_kol_v1"
    
    # 请求头
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 查询参数
    params = {
        'keyword': keyword,
        'page': page,
        'count': count,
        'sort_type': 1,  # 综合排序
        'platformSource': '_1'  # 抖音平台
    }
    
    print(f"\n📡 发送请求: 第 {page} 页...")
    print(f"   关键词: {keyword}")
    print(f"   每页数量: {count}")
    
    try:
        # 发送 GET 请求
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"   HTTP 状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # 检查 API 返回码
            code = result.get('code', -1)
            message = result.get('message_zh', result.get('message', 'Unknown'))
            
            print(f"   API 返回码: {code}")
            print(f"   返回消息: {message}")
            
            if code == 200:
                # 获取作者列表
                data = result.get('data', {})
                authors = data.get('authors', [])
                pagination = data.get('pagination', {})
                
                print(f"   ✅ 成功获取 {len(authors)} 个达人")
                print(f"   还有更多数据: {pagination.get('has_more', False)}")
                
                return result
            else:
                print(f"   ❌ API 返回错误")
                return result
        else:
            print(f"   ❌ HTTP 请求失败: {response.text[:200]}")
            return {
                "error": f"HTTP {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        print(f"   ❌ 请求异常: {str(e)}")
        return {"error": str(e)}


def parse_kol_data(author: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析单个达人的关键业务数据
    
    Args:
        author: 原始达人数据
        
    Returns:
        dict: 解析后的关键业务数据
    """
    attr_data = author.get('attribute_datas', {})
    
    # 解析标签
    tags_relation_str = attr_data.get('tags_relation', '{}')
    try:
        tags_relation = json.loads(tags_relation_str) if tags_relation_str else {}
    except:
        tags_relation = {}
    
    # 解析最近10个作品
    last_10_items_str = attr_data.get('last_10_items', '[]')
    try:
        last_10_items = json.loads(last_10_items_str) if last_10_items_str else []
    except:
        last_10_items = []
    
    # 计算作品平均数据
    total_vv = 0
    total_like = 0
    total_comment = 0
    total_share = 0
    item_count = len(last_10_items)
    
    for item in last_10_items:
        total_vv += int(item.get('vv', 0))
        total_like += int(item.get('like_cnt', 0))
        total_comment += int(item.get('comment_cnt', 0))
        total_share += int(item.get('share_cnt', 0))
    
    avg_vv = total_vv // item_count if item_count > 0 else 0
    avg_like = total_like // item_count if item_count > 0 else 0
    avg_comment = total_comment // item_count if item_count > 0 else 0
    avg_share = total_share // item_count if item_count > 0 else 0
    
    # 解析报价信息
    task_infos = author.get('task_infos', [])
    price_info = {}
    
    if task_infos:
        task_info = task_infos[0]
        price_infos = task_info.get('price_infos', [])
        
        for price in price_infos:
            video_type = price.get('video_type', 0)
            price_value = price.get('price', 0)
            
            if video_type == 1:
                price_info['视频定制'] = price_value
            elif video_type == 2:
                price_info['图文定制'] = price_value
    
    # 构建关键业务数据
    kol_data = {
        # 基本信息
        '达人ID': author.get('star_id', ''),
        '昵称': attr_data.get('nick_name', ''),
        '头像': attr_data.get('avatar_uri', ''),
        '性别': '女' if attr_data.get('gender', '') == '2' else '男' if attr_data.get('gender', '') == '1' else '未知',
        '地区': f"{attr_data.get('province', '')} {attr_data.get('city', '')}".strip(),
        
        # 粉丝数据
        '粉丝数': int(attr_data.get('follower', 0)),
        '15天粉丝增量': int(attr_data.get('fans_increment_within_15d', 0)),
        '30天粉丝增量': attr_data.get('fans_increment_within_30d', '0'),
        '15天粉丝增长率': float(attr_data.get('fans_increment_rate_within_15d', 0)),
        
        # 星图数据
        '星图评分': float(attr_data.get('star_index', 0)),
        '粉丝等级': attr_data.get('grade', '0'),
        '达人类型': '个人' if attr_data.get('author_type', '') == '1' else '机构' if attr_data.get('author_type', '') == '2' else '未知',
        '账号状态': '正常' if attr_data.get('author_status', '') == '1' else '异常',
        
        # 内容标签
        '内容标签': tags_relation,
        
        # 作品数据
        '近期作品数': item_count,
        '平均播放量': avg_vv,
        '平均点赞数': avg_like,
        '平均评论数': avg_comment,
        '平均分享数': avg_share,
        '互动率': round((avg_like + avg_comment + avg_share) / avg_vv * 100, 2) if avg_vv > 0 else 0,
        
        # 电商数据
        '电商等级': attr_data.get('author_ecom_level', ''),
        '电商启用': attr_data.get('e_commerce_enable', '0') == '1',
        '30天带货视频数': int(attr_data.get('ecom_video_product_num_30d', 0)),
        '30天带货GMV区间': attr_data.get('ecom_gmv_30d_range', ''),
        '30天平均客单价区间': attr_data.get('ecom_avg_order_value_30d_range', ''),
        
        # 商业报价
        '报价信息': price_info,
        '1-20秒视频报价': int(attr_data.get('price_1_20', 0)),
        '20-60秒视频报价': int(attr_data.get('price_20_60', 0)),
        '60秒以上视频报价': int(attr_data.get('price_60', 0)),
        
        # 预估数据
        '预估播放量': int(attr_data.get('expected_play_num', 0)),
        '预估自然播放量': int(attr_data.get('expected_natural_play_num', 0)),
        
        # 特殊标记
        '是否黑马达人': attr_data.get('is_black_horse_author', 'false') == 'true',
        '是否优质达人': attr_data.get('is_excellenct_author', '0') == '1',
        '是否短剧达人': attr_data.get('is_short_drama', '0') == '1',
        '是否支持共创': attr_data.get('is_cocreate_author', 'false') == 'true',
        
        # 最近10个作品详情
        '最近作品列表': last_10_items
    }
    
    return kol_data


def save_raw_response(response_data: Dict[str, Any], page: int, output_dir: str):
    """
    保存原始 API 响应到 detail 目录
    
    Args:
        response_data: API 响应数据
        page: 页码
        output_dir: 输出目录
    """
    detail_dir = os.path.join(output_dir, 'detail')
    os.makedirs(detail_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'raw_page_{page}_{timestamp}.json'
    filepath = os.path.join(detail_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)
    
    print(f"   💾 原始返回已保存: {filepath}")


def check_duplicate_authors(all_pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    检查3页数据中是否有重复的达人
    
    Args:
        all_pages_data: 所有页面的数据列表
        
    Returns:
        dict: 重复检查结果
    """
    print(f"\n{'='*60}")
    print(f"🔍 检查数据重复情况")
    print(f"{'='*60}")
    
    # 收集所有达人ID
    author_ids_by_page = []
    
    for i, page_data in enumerate(all_pages_data, 1):
        data = page_data.get('data', {})
        authors = data.get('authors', [])
        
        author_ids = [author.get('star_id', '') for author in authors]
        author_ids_by_page.append({
            'page': i,
            'count': len(author_ids),
            'ids': author_ids
        })
        
        print(f"\n第 {i} 页:")
        print(f"  达人数量: {len(author_ids)}")
    
    # 检查跨页重复
    all_ids = []
    for page_info in author_ids_by_page:
        all_ids.extend(page_info['ids'])
    
    unique_ids = set(all_ids)
    total_count = len(all_ids)
    unique_count = len(unique_ids)
    duplicate_count = total_count - unique_count
    
    print(f"\n总计:")
    print(f"  总达人数: {total_count}")
    print(f"  唯一达人数: {unique_count}")
    print(f"  重复达人数: {duplicate_count}")
    
    # 找出重复的达人ID
    duplicate_ids = []
    for author_id in unique_ids:
        count = all_ids.count(author_id)
        if count > 1:
            duplicate_ids.append({
                'id': author_id,
                'count': count
            })
    
    if duplicate_ids:
        print(f"\n⚠️ 发现 {len(duplicate_ids)} 个重复的达人:")
        for dup in duplicate_ids[:5]:  # 只显示前5个
            print(f"  ID: {dup['id']} (出现 {dup['count']} 次)")
        if len(duplicate_ids) > 5:
            print(f"  ... 还有 {len(duplicate_ids) - 5} 个重复达人")
    else:
        print(f"\n✅ 没有发现重复的达人")
    
    return {
        'total_count': total_count,
        'unique_count': unique_count,
        'duplicate_count': duplicate_count,
        'duplicate_ids': duplicate_ids,
        'pages': author_ids_by_page
    }


def main():
    """主函数：获取3页数据并结构化分析"""
    
    print("=" * 60)
    print("抖音星图护肤达人搜索与结构化分析工具 V2")
    print("API 接口: search_kol_v1")
    print("=" * 60)
    
    # 1. 加载 API Key
    print("\n1️⃣ 加载 API 配置...")
    try:
        api_key = load_api_key()
        print(f"✅ API Key 已加载: {api_key[:10]}...{api_key[-10:]}")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # 2. 设置输出目录
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "output"
    
    # 3. 获取3页数据
    print("\n2️⃣ 开始获取3页数据...")
    keyword = "护肤"
    page_count = 3
    count_per_page = 20
    
    all_pages_data = []
    all_parsed_kols = []
    
    for page in range(1, page_count + 1):
        print(f"\n{'='*60}")
        print(f"第 {page}/{page_count} 页")
        print(f"{'='*60}")
        
        # 获取数据
        response_data = fetch_kol_page(api_key, keyword, page, count_per_page)
        
        # 检查是否成功
        if 'error' in response_data or response_data.get('code') != 200:
            print(f"⚠️ 第 {page} 页获取失败")
            continue
        
        # 保存原始返回
        save_raw_response(response_data, page, str(output_dir))
        
        # 保存到列表
        all_pages_data.append(response_data)
        
        # 解析关键业务数据
        data = response_data.get('data', {})
        authors = data.get('authors', [])
        
        print(f"\n   开始解析关键业务数据...")
        for author in authors:
            parsed_kol = parse_kol_data(author)
            all_parsed_kols.append(parsed_kol)
        
        print(f"   ✅ 解析完成 {len(authors)} 个达人")
        
        # 添加延迟
        if page < page_count:
            print(f"\n   ⏳ 等待 1 秒...")
            time.sleep(1)
    
    if not all_pages_data:
        print("\n❌ 未获取到任何数据")
        return
    
    # 4. 检查重复
    print("\n3️⃣ 检查数据重复...")
    duplicate_check = check_duplicate_authors(all_pages_data)
    
    # 5. 保存解析后的关键业务数据
    print(f"\n4️⃣ 保存解析后的数据...")
    
    detail_dir = os.path.join(output_dir, 'detail')
    os.makedirs(detail_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    parsed_file = os.path.join(detail_dir, f'parsed_kol_data_{timestamp}.json')
    
    # 构建输出数据结构
    output_data = {
        '说明': {
            '数据来源': '抖音星图 KOL 搜索 API (search_kol_v1)',
            '接口文档': 'https://api.tikhub.io/#/Douyin-Xingtu-API/search_kol_v1_api_v1_douyin_xingtu_search_kol_v1_get',
            '搜索关键词': keyword,
            '获取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '数据页数': page_count,
            '每页数量': count_per_page,
            '总达人数': len(all_parsed_kols),
            '唯一达人数': duplicate_check['unique_count'],
            '重复达人数': duplicate_check['duplicate_count']
        },
        '数据字段说明': {
            '基本信息': ['达人ID', '昵称', '头像', '性别', '地区'],
            '粉丝数据': ['粉丝数', '15天粉丝增量', '30天粉丝增量', '15天粉丝增长率'],
            '星图数据': ['星图评分', '粉丝等级', '达人类型', '账号状态'],
            '内容标签': ['内容标签'],
            '作品数据': ['近期作品数', '平均播放量', '平均点赞数', '平均评论数', '平均分享数', '互动率'],
            '电商数据': ['电商等级', '电商启用', '30天带货视频数', '30天带货GMV区间', '30天平均客单价区间'],
            '商业报价': ['报价信息', '1-20秒视频报价', '20-60秒视频报价', '60秒以上视频报价'],
            '预估数据': ['预估播放量', '预估自然播放量'],
            '特殊标记': ['是否黑马达人', '是否优质达人', '是否短剧达人', '是否支持共创'],
            '作品详情': ['最近作品列表']
        },
        '重复检查结果': duplicate_check,
        '达人数据': all_parsed_kols
    }
    
    with open(parsed_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 解析后的数据已保存: {parsed_file}")
    
    # 6. 生成分析报告
    print(f"\n{'='*60}")
    print(f"📊 关键数据分析")
    print(f"{'='*60}")
    
    # 粉丝数统计
    follower_counts = [kol['粉丝数'] for kol in all_parsed_kols]
    avg_followers = sum(follower_counts) // len(follower_counts) if follower_counts else 0
    max_followers = max(follower_counts) if follower_counts else 0
    min_followers = min(follower_counts) if follower_counts else 0
    
    print(f"\n粉丝数统计:")
    print(f"  平均粉丝数: {avg_followers:,}")
    print(f"  最高粉丝数: {max_followers:,}")
    print(f"  最低粉丝数: {min_followers:,}")
    
    # 星图评分统计
    star_scores = [kol['星图评分'] for kol in all_parsed_kols if kol['星图评分'] > 0]
    avg_star_score = sum(star_scores) / len(star_scores) if star_scores else 0
    
    print(f"\n星图评分统计:")
    print(f"  平均星图评分: {avg_star_score:.2f}")
    print(f"  最高星图评分: {max(star_scores):.2f}" if star_scores else "  无数据")
    print(f"  最低星图评分: {min(star_scores):.2f}" if star_scores else "  无数据")
    
    # 互动率统计
    interaction_rates = [kol['互动率'] for kol in all_parsed_kols if kol['互动率'] > 0]
    avg_interaction_rate = sum(interaction_rates) / len(interaction_rates) if interaction_rates else 0
    
    print(f"\n互动率统计:")
    print(f"  平均互动率: {avg_interaction_rate:.2f}%")
    print(f"  最高互动率: {max(interaction_rates):.2f}%" if interaction_rates else "  无数据")
    
    # 报价统计
    prices_20_60 = [kol['20-60秒视频报价'] for kol in all_parsed_kols if kol['20-60秒视频报价'] > 0]
    avg_price = sum(prices_20_60) // len(prices_20_60) if prices_20_60 else 0
    
    print(f"\n商业报价统计 (20-60秒视频):")
    print(f"  平均报价: {avg_price:,} 元")
    print(f"  最高报价: {max(prices_20_60):,} 元" if prices_20_60 else "  无数据")
    print(f"  最低报价: {min(prices_20_60):,} 元" if prices_20_60 else "  无数据")
    
    # TOP 5 达人
    print(f"\n{'='*60}")
    print(f"🏆 TOP 5 护肤达人 (按粉丝数排序)")
    print(f"{'='*60}")
    
    sorted_kols = sorted(all_parsed_kols, key=lambda x: x['粉丝数'], reverse=True)
    
    for i, kol in enumerate(sorted_kols[:5], 1):
        print(f"\n{i}. {kol['昵称']}")
        print(f"   粉丝数: {kol['粉丝数']:,}")
        print(f"   星图评分: {kol['星图评分']:.2f}")
        print(f"   平均播放量: {kol['平均播放量']:,}")
        print(f"   互动率: {kol['互动率']}%")
        print(f"   20-60秒视频报价: {kol['20-60秒视频报价']:,} 元")
        print(f"   内容标签: {kol['内容标签']}")
    
    print(f"\n{'='*60}")
    print(f"✅ 全部完成！")
    print(f"{'='*60}")
    print(f"\n📁 文件保存位置:")
    print(f"   原始返回: {os.path.join(output_dir, 'detail', 'raw_page_*.json')}")
    print(f"   解析数据: {parsed_file}")


if __name__ == "__main__":
    main()

