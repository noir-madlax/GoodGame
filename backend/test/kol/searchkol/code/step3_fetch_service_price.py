#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Step 3: 获取星图KOL的服务报价信息
从Step2获取的星图KOL中，调用服务报价接口获取价格和行业标签信息

业务需求:
1. 获取KOL的服务报价数据
2. 重点关注 industry_tags 字段用于业务筛选
3. 保存价格信息到数据库 gg_xingtu_kol_price 表

数据字段:
- industry_tags: 行业标签（如：美妆-护肤，日化-日化洗护）
- price_info: 价格列表（视频、图文等不同类型的报价）
- order_count: 历史订单数（如果有）
"""

import os
import sys
import json
import requests
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 设置后端目录路径
# 当前文件: .../backend/test/kol/searchkol/code/step3_fetch_service_price.py
# backend目录: code(1) -> searchkol(2) -> kol(3) -> test(4) -> backend(5)
backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent


def load_api_key():
    """从环境变量加载TikHub API Key"""
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    return api_key


def get_api_base_url(use_china_domain: bool = True) -> str:
    """获取API基础URL"""
    if use_china_domain:
        return "https://api.tikhub.dev/api/v1"
    else:
        return "https://api.tikhub.io/api/v1"


def load_cookie():
    """从cookie文件加载Cookie"""
    cookie_path = backend_dir / 'test' / 'kol' / 'cookie'
    
    if not cookie_path.exists():
        return None
    
    try:
        with open(cookie_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            # 判断是否是JSON格式
            if content.startswith('[') or content.startswith('{'):
                cookie_list = json.loads(content)
                
                # 转换JSON格式为cookie字符串
                if isinstance(cookie_list, list):
                    cookie_parts = []
                    for cookie_item in cookie_list:
                        if 'name' in cookie_item and 'value' in cookie_item:
                            name = cookie_item['name']
                            value = cookie_item['value']
                            if name:
                                cookie_parts.append(f"{name}={value}")
                    
                    cookie_str = '; '.join(cookie_parts)
                    return cookie_str
                else:
                    return None
            else:
                # 纯文本格式，直接返回
                return content
    except Exception as e:
        print(f"   ⚠️ Cookie加载失败: {e}")
        return None


def fetch_kol_ids_from_db(limit: int = 10) -> list:
    """
    从数据库查询星图KOL的ID列表
    
    从50W-100W粉丝区间查询已确认的星图KOL
    
    Args:
        limit: 返回数量限制
        
    Returns:
        KOL信息列表
    """
    print(f"📊 从数据库查询星图KOL...")
    
    # 从环境变量加载 Supabase 配置
    env_path = backend_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL 或 SUPABASE_KEY 未设置")
        return []
    
    # 构建查询 - 查询50W-100W区间的星图KOL
    # JOIN两个表获取完整信息
    query_string = (
        f"select=m.uid,m.kol_id,u.nickname,u.follower_count"
        f"&m.is_xingtu_kol=eq.true"
        f"&u.follower_count=gte.500001"
        f"&u.follower_count=lte.1000000"
        f"&order=u.follower_count.desc"
        f"&limit={limit}"
    )
    
    # 由于PostgREST不支持直接JOIN，我们分两步查询
    # 第一步：获取星图KOL的UID和kol_id
    mapping_url = f"{supabase_url}/rest/v1/gg_xingtu_kol_mapping?is_xingtu_kol=eq.true&limit=1000&select=uid,kol_id"
    
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}'
    }
    
    try:
        # 获取所有星图KOL的映射
        response = requests.get(mapping_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ 查询映射表失败: HTTP {response.status_code}")
            return []
        
        mappings = response.json()
        kol_map = {m['uid']: m['kol_id'] for m in mappings if m.get('kol_id')}
        
        # 第二步：获取50W-100W粉丝的用户信息
        user_url = f"{supabase_url}/rest/v1/gg_douyin_user_search?follower_count=gte.500001&follower_count=lte.1000000&order=follower_count.desc&limit={limit}&select=uid,nickname,follower_count"
        
        response = requests.get(user_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ 查询用户表失败: HTTP {response.status_code}")
            return []
        
        users = response.json()
        
        # 合并数据 - 只返回有kol_id的用户
        kol_list = []
        for user in users:
            uid = user['uid']
            if uid in kol_map:
                kol_list.append({
                    'uid': uid,
                    'kol_id': kol_map[uid],
                    'nickname': user['nickname'],
                    'follower_count': user['follower_count']
                })
        
        print(f"✅ 查询到 {len(kol_list)} 个星图KOL")
        return kol_list
    
    except Exception as e:
        print(f"❌ 查询异常: {e}")
        return []


def get_kol_service_price(api_key: str, kol_id: str, cookie: str = None) -> dict:
    """
    接口1.4: 获取KOL服务报价
    
    重点关注:
    - industry_tags: 行业标签数组
    - price_info: 价格信息列表
    
    Args:
        api_key: API密钥
        kol_id: 星图KOL ID
        cookie: Cookie字符串
        
    Returns:
        API响应数据
    """
    base_url = get_api_base_url(use_china_domain=True)
    endpoint = "/douyin/xingtu/kol_service_price_v1"
    url = f"{base_url}{endpoint}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    if cookie:
        headers['Cookie'] = cookie
    
    # 参数: kolId（驼峰） + platformChannel=_1（短视频）
    params = {
        'kolId': kol_id,
        'platformChannel': '_1'  # _1=短视频
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"HTTP {response.status_code}",
                "message": response.text[:500]
            }
            
    except Exception as e:
        return {"error": str(e)}


def extract_price_details(price_info: list) -> dict:
    """
    从price_info中提取详细的价格信息
    
    根据 task_category 和 video_type 提取不同类型的服务价格:
    - task_category=1: 短视频任务
    - task_category=6: 直播任务
    - task_category=52: 图文任务
    - task_category=103: 广告投放任务
    
    video_type (短视频):
    - 1: 1-20s短视频
    - 2: 21-60s中视频
    - 71: 60s以上长视频
    - 150: 短直种草
    - 103: 单视频广告
    - 104: 多视频广告
    
    Args:
        price_info: 价格信息列表
        
    Returns:
        详细价格字典
    """
    if not price_info:
        return {
            'video_price_min': None,
            'video_price_max': None,
            'image_price_min': None,
            'image_price_max': None,
            'live_price_min': None,
            'live_price_max': None,
            'video_1_20s_price': None,
            'video_21_60s_price': None,
            'video_60s_plus_price': None,
            'live_streaming_price': None,
            'short_live_price': None,
            'image_post_price': None,
            'ad_single_video_price': None,
            'ad_multi_video_price': None,
            'price_info_count': 0,
            'has_video_service': False,
            'has_live_service': False,
            'has_image_service': False,
            'has_ad_service': False
        }
    
    # 初始化价格变量
    video_prices = []
    image_prices = []
    live_prices = []
    
    # 详细价格字段
    video_1_20s_price = None
    video_21_60s_price = None
    video_60s_plus_price = None
    live_streaming_price = None
    short_live_price = None
    image_post_price = None
    ad_single_video_price = None
    ad_multi_video_price = None
    
    # 服务类型标记
    has_video_service = False
    has_live_service = False
    has_image_service = False
    has_ad_service = False
    
    # 遍历所有价格项目
    for item in price_info:
        price = item.get('price', 0)
        task_category = item.get('task_category', 0)
        video_type = item.get('video_type', 0)
        enable = item.get('enable', False)
        
        # 只处理有效且启用的价格
        if not enable or price <= 0:
            continue
        
        # 短视频任务 (task_category=1)
        if task_category == 1:
            has_video_service = True
            video_prices.append(price)
            
            if video_type == 1:  # 1-20s短视频
                video_1_20s_price = price
            elif video_type == 2:  # 21-60s中视频
                video_21_60s_price = price
            elif video_type == 71:  # 60s以上长视频
                video_60s_plus_price = price
            elif video_type == 150:  # 短直种草
                short_live_price = price
        
        # 直播任务 (task_category=6)
        elif task_category == 6:
            has_live_service = True
            live_prices.append(price)
            if not live_streaming_price:  # 取第一个直播价格
                live_streaming_price = price
        
        # 图文任务 (task_category=52)
        elif task_category == 52:
            has_image_service = True
            image_prices.append(price)
            if not image_post_price:  # 取第一个图文价格
                image_post_price = price
        
        # 广告投放任务 (task_category=103)
        elif task_category == 103:
            has_ad_service = True
            if video_type == 103:  # 单视频广告
                ad_single_video_price = price
            elif video_type == 104:  # 多视频广告
                ad_multi_video_price = price
    
    return {
        'video_price_min': min(video_prices) if video_prices else None,
        'video_price_max': max(video_prices) if video_prices else None,
        'image_price_min': min(image_prices) if image_prices else None,
        'image_price_max': max(image_prices) if image_prices else None,
        'live_price_min': min(live_prices) if live_prices else None,
        'live_price_max': max(live_prices) if live_prices else None,
        'video_1_20s_price': video_1_20s_price,
        'video_21_60s_price': video_21_60s_price,
        'video_60s_plus_price': video_60s_plus_price,
        'live_streaming_price': live_streaming_price,
        'short_live_price': short_live_price,
        'image_post_price': image_post_price,
        'ad_single_video_price': ad_single_video_price,
        'ad_multi_video_price': ad_multi_video_price,
        'price_info_count': len(price_info),
        'has_video_service': has_video_service,
        'has_live_service': has_live_service,
        'has_image_service': has_image_service,
        'has_ad_service': has_ad_service
    }


def save_price_to_db(kol_id: str, price_response: dict) -> bool:
    """
    将KOL服务报价数据写入数据库
    
    保存到 gg_xingtu_kol_price 表
    包括:
    - industry_tags: 行业标签数组
    - 各类服务的详细价格
    - raw_data: 完整原始数据
    
    Args:
        kol_id: 星图KOL ID
        price_response: 服务报价接口返回数据
        
    Returns:
        是否保存成功
    """
    # 加载环境变量
    env_path = backend_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        return False
    
    # 提取数据
    price_data = price_response.get('data', {})
    price_info = price_data.get('price_info', [])
    industry_tags = price_data.get('industry_tags', [])
    
    # 提取详细价格信息
    price_details = extract_price_details(price_info)
    
    # 构建数据 - 结构化字段 + 完整原始数据
    data = {
        "kol_id": kol_id,
        # 基础价格范围
        "video_price_min": price_details['video_price_min'],
        "video_price_max": price_details['video_price_max'],
        "image_price_min": price_details['image_price_min'],
        "image_price_max": price_details['image_price_max'],
        "live_price_min": price_details['live_price_min'],
        "live_price_max": price_details['live_price_max'],
        # 行业标签
        "industry_tags": industry_tags,
        # 详细服务价格
        "video_1_20s_price": price_details['video_1_20s_price'],
        "video_21_60s_price": price_details['video_21_60s_price'],
        "video_60s_plus_price": price_details['video_60s_plus_price'],
        "live_streaming_price": price_details['live_streaming_price'],
        "short_live_price": price_details['short_live_price'],
        "image_post_price": price_details['image_post_price'],
        "ad_single_video_price": price_details['ad_single_video_price'],
        "ad_multi_video_price": price_details['ad_multi_video_price'],
        # 统计信息
        "price_info_count": price_details['price_info_count'],
        "has_video_service": price_details['has_video_service'],
        "has_live_service": price_details['has_live_service'],
        "has_image_service": price_details['has_image_service'],
        "has_ad_service": price_details['has_ad_service'],
        "order_count": None,  # API不返回订单数
        # 完整原始数据
        "raw_data": {
            "industry_tags": industry_tags,
            "price_info": price_info,
            "activity_info": price_data.get('activity_info', []),
            "hot_list_ranks": price_data.get('hot_list_ranks', [])
        },
        "fetch_date": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # 发送请求 - 使用UPSERT语法
    url = f"{supabase_url}/rest/v1/gg_xingtu_kol_price?on_conflict=kol_id"
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates,return=minimal'
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code in [200, 201, 204]:
            print(f"   ✅ 服务报价已保存到数据库")
            if industry_tags:
                print(f"      行业标签: {', '.join(industry_tags)}")
            return True
        else:
            print(f"   ❌ 服务报价保存失败: HTTP {response.status_code}")
            print(f"      {response.text[:200]}")
            return False
    
    except Exception as e:
        print(f"   ❌ 服务报价写入异常: {e}")
        return False


def process_kols(kol_list: list, api_key: str, cookie: str = None, save_to_db: bool = True):
    """
    批量处理KOL的服务报价获取
    
    Args:
        kol_list: KOL信息列表
        api_key: API密钥
        cookie: Cookie (可选但推荐)
        save_to_db: 是否保存到数据库
        
    Returns:
        处理结果列表
    """
    results = []
    total = len(kol_list)
    
    print(f"\n{'='*70}")
    print(f"🚀 开始获取 {total} 个KOL的服务报价")
    print(f"{'='*70}")
    
    success_count = 0
    failed_count = 0
    db_save_success = 0
    db_save_failed = 0
    
    for idx, kol in enumerate(kol_list, 1):
        print(f"\n[{idx}/{total}]")
        print(f"{'='*70}")
        print(f"KOL: {kol['nickname']} (KOL ID: {kol['kol_id']})")
        print(f"粉丝数: {kol['follower_count']:,}")
        print(f"{'='*70}")
        
        # 调用服务报价接口
        print(f"📡 获取服务报价...")
        price_response = get_kol_service_price(api_key, kol['kol_id'], cookie)
        
        # 检查结果
        if price_response.get('error'):
            print(f"   ❌ 获取失败: {price_response.get('error')}")
            result = {
                'kol_id': kol['kol_id'],
                'nickname': kol['nickname'],
                'success': False,
                'error': price_response.get('error')
            }
            failed_count += 1
        else:
            print(f"   ✅ 获取成功")
            
            # 提取关键信息
            data = price_response.get('data', {})
            industry_tags = data.get('industry_tags', [])
            price_info = data.get('price_info', [])
            
            # 提取详细价格
            price_details = extract_price_details(price_info)
            
            # 显示行业标签
            if industry_tags:
                print(f"   📌 行业标签: {', '.join(industry_tags)}")
            
            # 显示服务统计
            services = []
            if price_details['has_video_service']:
                services.append('视频')
            if price_details['has_live_service']:
                services.append('直播')
            if price_details['has_image_service']:
                services.append('图文')
            if price_details['has_ad_service']:
                services.append('广告')
            
            if services:
                print(f"   🎬 服务类型: {', '.join(services)} (共{price_details['price_info_count']}项)")
            
            # 显示详细价格
            if price_details['video_1_20s_price']:
                print(f"   💰 短视频(1-20s): {price_details['video_1_20s_price']/100:.0f}元")
            if price_details['video_21_60s_price']:
                print(f"   💰 中视频(21-60s): {price_details['video_21_60s_price']/100:.0f}元")
            if price_details['video_60s_plus_price']:
                print(f"   💰 长视频(60s+): {price_details['video_60s_plus_price']/100:.0f}元")
            if price_details['short_live_price']:
                print(f"   💰 短直种草: {price_details['short_live_price']/100:.0f}元")
            if price_details['live_streaming_price']:
                print(f"   💰 直播服务: {price_details['live_streaming_price']/100:.0f}元")
            if price_details['image_post_price']:
                print(f"   💰 图文种草: {price_details['image_post_price']/100:.0f}元")
            
            result = {
                'kol_id': kol['kol_id'],
                'nickname': kol['nickname'],
                'follower_count': kol['follower_count'],
                'success': True,
                'industry_tags': industry_tags,
                'price_count': len(price_info),
                'has_video_service': price_details['has_video_service'],
                'has_live_service': price_details['has_live_service'],
                'has_image_service': price_details['has_image_service'],
                'has_ad_service': price_details['has_ad_service'],
                # 请求信息
                'request': {
                    'endpoint': '/api/v1/douyin/xingtu/kol_service_price_v1',
                    'params': {
                        'kolId': kol['kol_id'],
                        'platformChannel': '_1'
                    },
                    'timestamp': datetime.now().isoformat()
                },
                # 完整响应
                'response': price_response
            }
            success_count += 1
            
            # 保存到数据库
            if save_to_db:
                print(f"\n💾 保存数据到数据库...")
                if save_price_to_db(kol['kol_id'], price_response):
                    db_save_success += 1
                else:
                    db_save_failed += 1
        
        results.append(result)
        
        # 每个KOL之间间隔1秒
        if idx < total:
            time.sleep(1)
    
    # 最终统计
    print(f"\n{'='*70}")
    print(f"📊 处理完成统计")
    print(f"{'='*70}")
    print(f"总计KOL数: {total}")
    print(f"获取成功: {success_count} ({success_count/total*100:.1f}%)")
    print(f"获取失败: {failed_count} ({failed_count/total*100:.1f}%)")
    
    if save_to_db:
        print(f"\n数据库写入统计:")
        print(f"成功: {db_save_success}")
        print(f"失败: {db_save_failed}")
    
    return results


def save_results_to_json(results: list, output_dir: str, follower_range: str):
    """
    保存结果到JSON文件
    包含完整的请求体和响应体
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. 保存完整结果（包含请求和响应）
    full_output_file = os.path.join(output_dir, f'step3_service_price_full_{follower_range}_{timestamp}.json')
    full_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "follower_range": follower_range,
            "total_kols": len(results),
            "success_count": sum(1 for r in results if r.get('success')),
            "failed_count": sum(1 for r in results if not r.get('success')),
            "data_source": "TikHub Service Price API (接口1.4)",
            "api_endpoint": "/api/v1/douyin/xingtu/kol_service_price_v1"
        },
        "results": results
    }
    
    with open(full_output_file, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 完整结果已保存: {full_output_file}")
    
    # 2. 保存简化版（仅成功的KOL）
    success_results = [r for r in results if r.get('success')]
    if success_results:
        summary_file = os.path.join(output_dir, f'step3_service_price_summary_{follower_range}_{timestamp}.json')
        summary_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "follower_range": follower_range,
                "kol_count": len(success_results)
            },
            "kols": [
                {
                    "kol_id": r['kol_id'],
                    "nickname": r['nickname'],
                    "industry_tags": r.get('industry_tags', []),
                    "price_count": r.get('price_count', 0),
                    "has_video_service": r.get('has_video_service', False),
                    "has_live_service": r.get('has_live_service', False),
                    "has_ad_service": r.get('has_ad_service', False)
                }
                for r in success_results
            ]
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 汇总结果已保存: {summary_file}")
    
    return full_output_file


def main():
    """主函数"""
    
    # 参数解析
    parser = argparse.ArgumentParser(description='Step3: 获取星图KOL的服务报价信息')
    parser.add_argument('--limit', type=int, default=3, help='处理KOL数量限制（默认3）')
    parser.add_argument('--save-db', action='store_true', default=True, help='是否保存到数据库（默认True）')
    parser.add_argument('--no-save-db', dest='save_db', action='store_false', help='不保存到数据库')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Step 3: 获取星图KOL服务报价信息")
    print("=" * 70)
    
    # 1. 加载配置
    print("\n1️⃣ 加载配置...")
    try:
        api_key = load_api_key()
        print(f"✅ API Key已加载")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # 加载Cookie
    cookie = load_cookie()
    if cookie:
        print(f"✅ Cookie已加载 (长度: {len(cookie)} 字符)")
    else:
        print("⚠️ Cookie未加载，可能影响接口调用")
    
    # 2. 从数据库查询星图KOL
    print(f"\n2️⃣ 从数据库查询星图KOL...")
    print(f"   查询范围: 50W-100W粉丝")
    print(f"   查询数量: {args.limit}")
    
    kol_list = fetch_kol_ids_from_db(limit=args.limit)
    
    if not kol_list:
        print("❌ 未查询到星图KOL，程序退出")
        return
    
    # 3. 获取服务报价
    print(f"\n3️⃣ 开始获取服务报价...")
    print(f"   数据库写入: {'✅ 启用' if args.save_db else '❌ 禁用'}")
    results = process_kols(kol_list, api_key, cookie, save_to_db=args.save_db)
    
    # 4. 保存JSON结果
    print(f"\n4️⃣ 保存JSON结果...")
    
    # 输出目录
    script_dir = Path(__file__).parent.parent
    timestamp_dir = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = script_dir / "output" / f"step3_service_price_{timestamp_dir}"
    
    follower_range = "50w-100w"
    save_results_to_json(results, str(output_dir), follower_range)
    
    print(f"\n✅ 全部完成！")
    print(f"📂 结果目录: {output_dir}")


if __name__ == "__main__":
    main()

