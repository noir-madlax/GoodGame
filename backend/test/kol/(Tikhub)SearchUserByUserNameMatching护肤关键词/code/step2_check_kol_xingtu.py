#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Step 2: 从搜索到的用户中检查哪些是星图KOL
从 gg_douyin_user_search 表中筛选10W-50W粉丝的初级KOL，验证是否是星图KOL

业务流程:
1. 从数据库查询10W-50W粉丝的用户
2. 调用星图接口验证是否是KOL
3. 统计KOL比例和分布
4. 保存结果到output目录
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
# 当前文件: .../backend/test/kol/searchkol/code/step2_check_kol_xingtu.py
# backend目录: code -> searchkol -> kol -> test -> backend (向上4级)
# 但searchkol下还有code，所以是: code(1) -> searchkol(2) -> kol(3) -> test(4) -> backend(5)
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
    """
    获取API基础URL
    
    Args:
        use_china_domain: 是否使用中国加速域名
        
    Returns:
        API基础URL
    """
    if use_china_domain:
        return "https://api.tikhub.dev/api/v1"
    else:
        return "https://api.tikhub.io/api/v1"


def load_cookie():
    """
    从cookie文件加载Cookie
    
    支持两种格式:
    1. JSON格式 (浏览器插件导出的格式)
    2. 纯文本格式 (key=value; key2=value2; ...)
    
    Returns:
        Cookie字符串
    """
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
                            # 跳过空名称的cookie
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


def get_xingtu_kol_id(api_key: str, sec_user_id: str, cookie: str = None, use_china_domain: bool = True) -> dict:
    """
    接口1.1: 通过抖音sec_user_id获取星图KOL ID
    
    接口文档: https://api.tikhub.io/#/Douyin-Xingtu-API/get_xingtu_kolid_by_sec_user_id
    
    Args:
        api_key: API密钥
        sec_user_id: 抖音用户的sec_user_id
        cookie: 抖音Cookie (可选但推荐)
        use_china_domain: 是否使用中国加速域名 (默认True，使用api.tikhub.dev)
        
    Returns:
        API响应数据
    """
    base_url = get_api_base_url(use_china_domain)
    endpoint = "/douyin/xingtu/get_xingtu_kolid_by_sec_user_id"
    url = f"{base_url}{endpoint}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 添加Cookie（如果有）
    if cookie:
        headers['Cookie'] = cookie
    
    params = {
        'sec_user_id': sec_user_id
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            error_text = response.text
            try:
                error_json = response.json()
                return {
                    "error": f"HTTP {response.status_code}",
                    "message": error_text[:500],
                    "detail": error_json
                }
            except:
                return {
                    "error": f"HTTP {response.status_code}",
                    "message": error_text[:500]
                }
            
    except Exception as e:
        return {"error": str(e)}


def get_kol_audience_portrait(api_key: str, kol_id: str, cookie: str = None, use_china_domain: bool = True) -> dict:
    """
    接口1.3: 获取KOL受众画像 ✅ (已验证可用)
    
    包含: 性别、年龄、地域、兴趣标签等
    """
    base_url = get_api_base_url(use_china_domain)
    endpoint = "/douyin/xingtu/kol_audience_portrait_v1"
    url = f"{base_url}{endpoint}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    if cookie:
        headers['Cookie'] = cookie
    
    # 使用正确的参数名（驼峰命名）
    params = {
        'kolId': kol_id
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


def get_kol_cp_info(api_key: str, kol_id: str, cookie: str = None, use_china_domain: bool = True) -> dict:
    """
    接口1.5: 获取KOL性价比能力（CP Info）✅ (已验证可用)
    
    包含: 预期CPE、CPM、播放量、热门作品等
    """
    base_url = get_api_base_url(use_china_domain)
    endpoint = "/douyin/xingtu/kol_cp_info_v1"
    url = f"{base_url}{endpoint}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    if cookie:
        headers['Cookie'] = cookie
    
    # 使用正确的参数名（驼峰命名）
    params = {
        'kolId': kol_id
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


def fetch_users_from_db(follower_min: int = 100001, follower_max: int = 500000, limit: int = 10):
    """
    从数据库查询指定粉丝范围的用户
    
    使用 Supabase REST API 直接查询（不需要安装supabase包）
    
    Args:
        follower_min: 最小粉丝数
        follower_max: 最大粉丝数
        limit: 返回数量限制
        
    Returns:
        用户列表
    """
    print(f"📊 从数据库查询粉丝数 {follower_min:,} - {follower_max:,} 的用户...")
    
    # 从环境变量加载 Supabase 配置
    env_path = backend_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL 或 SUPABASE_KEY 未设置")
        return []
    
    # 构建 REST API URL
    # Supabase REST API格式: {url}/rest/v1/{table}?{filters}
    # PostgREST 范围查询使用 and 连接多个条件
    rest_url = f"{supabase_url}/rest/v1/gg_douyin_user_search"
    
    # 构建查询参数
    # PostgREST range query: follower_count=gte.100001&follower_count=lte.500000
    # 但Python dict不支持重复key，所以手动构建URL
    query_string = (
        f"select=uid,sec_uid,nickname,follower_count,signature,avatar_url,verification_type,gender"
        f"&follower_count=gte.{follower_min}"
        f"&follower_count=lte.{follower_max}"
        f"&order=follower_count.desc"
        f"&limit={limit}"
    )
    
    full_url = f"{rest_url}?{query_string}"
    
    # 设置请求头
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}'
    }
    
    try:
        # 发送请求
        response = requests.get(full_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            users = response.json()
            print(f"✅ 查询到 {len(users)} 个用户")
            return users
        else:
            print(f"❌ 查询失败: HTTP {response.status_code}")
            print(f"   错误信息: {response.text[:200]}")
            return []
    
    except Exception as e:
        print(f"❌ 查询异常: {e}")
        return []


def check_single_user_xingtu_status(user: dict, api_key: str, cookie: str = None) -> dict:
    """
    检查单个用户的星图KOL状态并获取画像
    
    Args:
        user: 用户信息
        api_key: API密钥
        cookie: 抖音Cookie (可选但推荐)
        
    Returns:
        包含所有接口数据的字典
    """
    uid = user.get('uid', '')
    sec_uid = user.get('sec_uid', '')
    nickname = user.get('nickname', 'Unknown')
    follower_count = user.get('follower_count', 0)
    
    print(f"\n{'='*70}")
    print(f"检查用户: {nickname} (UID: {uid})")
    print(f"粉丝数: {follower_count:,}")
    print(f"{'='*70}")
    
    result = {
        "uid": uid,
        "sec_uid": sec_uid,
        "nickname": nickname,
        "follower_count": follower_count,
        "signature": user.get('signature', ''),
        "avatar_url": user.get('avatar_url', ''),
        "verification_type": user.get('verification_type', 0),
        "gender": user.get('gender', 0),
        "check_timestamp": datetime.now().isoformat()
    }
    
    # Step 1: 获取星图KOL ID
    print(f"📡 检查是否为星图KOL...")
    print(f"   sec_uid: {sec_uid[:50]}...")
    
    kol_id_response = get_xingtu_kol_id(api_key, sec_uid, cookie)
    
    # 保存原始响应以便调试
    result['kol_id_response'] = kol_id_response
    
    if kol_id_response.get('error'):
        print(f"   ❌ 获取KOL ID失败: {kol_id_response.get('error')}")
        result['error'] = f"获取KOL ID失败: {kol_id_response.get('error')}"
        result['is_xingtu_kol'] = False
        return result
    
    # 检查是否是星图KOL
    data_content = kol_id_response.get('data', {})
    kol_id = data_content.get('id', '')
    
    if not kol_id:
        print(f"   ⚠️ 非星图KOL（未找到kol_id）")
        result['is_xingtu_kol'] = False
        return result
    
    print(f"   ✅ 是星图KOL！KOL ID: {kol_id}")
    result['is_xingtu_kol'] = True
    result['kol_id'] = kol_id
    
    # Step 2: 获取KOL画像数据
    print(f"\n📊 获取星图KOL画像数据...")
    
    xingtu_data = {}
    
    # 2.1 受众画像
    print(f"   [1/2] 获取受众画像...")
    audience = get_kol_audience_portrait(api_key, kol_id, cookie)
    if not audience.get('error'):
        print(f"   ✅ 受众画像获取成功")
        xingtu_data['audience_portrait'] = audience
    else:
        print(f"   ❌ 受众画像获取失败: {audience.get('error')}")
        xingtu_data['audience_portrait'] = audience
    
    time.sleep(0.5)
    
    # 2.2 性价比信息
    print(f"   [2/2] 获取性价比信息...")
    cp_info = get_kol_cp_info(api_key, kol_id, cookie)
    if not cp_info.get('error'):
        print(f"   ✅ 性价比信息获取成功")
        xingtu_data['cp_info'] = cp_info
    else:
        print(f"   ❌ 性价比信息获取失败: {cp_info.get('error')}")
        xingtu_data['cp_info'] = cp_info
    
    result['xingtu_data'] = xingtu_data
    
    # 统计成功率
    success_count = sum(1 for v in xingtu_data.values() if not v.get('error'))
    total_count = len(xingtu_data)
    
    print(f"\n📈 数据获取完成: {success_count}/{total_count} 个接口成功")
    
    return result


def extract_distribution_by_type(distributions: list, target_type: int) -> dict:
    """
    从distributions数组中提取指定类型的分布数据
    
    Args:
        distributions: distributions数组
        target_type: 目标类型（1=性别, 2=年龄, 64=地域, 512=兴趣）
    
    Returns:
        分布数据字典，如果没有则返回None
    """
    for dist in distributions:
        if dist.get('type') == target_type:
            return {
                "type": dist.get('type'),
                "type_display": dist.get('type_display'),
                "description": dist.get('description'),
                "distribution_list": dist.get('distribution_list', []),
                "image": dist.get('image', [])
            }
    
    return None


def save_kol_mapping_to_db(result: dict) -> bool:
    """
    将UID到KOL ID的映射关系写入数据库
    
    使用Supabase REST API进行UPSERT操作
    
    Args:
        result: 用户检查结果
        
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
        print("   ⚠️ 数据库配置未找到，跳过数据库写入")
        return False
    
    # 构建数据
    data = {
        "uid": result['uid'],
        "kol_id": result.get('kol_id'),
        "is_xingtu_kol": result.get('is_xingtu_kol', False),
        "check_date": datetime.now().isoformat(),
        "error_message": result.get('error'),
        "updated_at": datetime.now().isoformat()
    }
    
    # 发送请求 - 使用UPSERT语法
    # Supabase的UPSERT需要在URL中指定on_conflict参数
    url = f"{supabase_url}/rest/v1/gg_xingtu_kol_mapping?on_conflict=uid"
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates,return=minimal'  # UPSERT模式
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code in [200, 201, 204]:
            print(f"   ✅ 映射数据已保存到数据库")
            return True
        else:
            print(f"   ❌ 映射数据保存失败: HTTP {response.status_code}")
            print(f"      {response.text[:200]}")
            return False
    
    except Exception as e:
        print(f"   ❌ 数据库写入异常: {e}")
        return False


def save_kol_audience_to_db(kol_id: str, audience_response: dict) -> bool:
    """
    将KOL受众画像数据写入数据库
    
    解析distributions数组，按类型分类存储
    
    Args:
        kol_id: 星图KOL ID
        audience_response: 受众画像接口返回数据
        
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
    audience_data = audience_response.get('data', {})
    distributions = audience_data.get('distributions', [])
    
    # 提取各类分布数据
    gender_dist = extract_distribution_by_type(distributions, 1)    # 性别
    age_dist = extract_distribution_by_type(distributions, 2)       # 年龄
    region_dist = extract_distribution_by_type(distributions, 64)   # 地域
    interest_dist = extract_distribution_by_type(distributions, 512) # 兴趣
    
    # 构建数据
    data = {
        "kol_id": kol_id,
        "gender_distribution": gender_dist,
        "age_distribution": age_dist,
        "region_distribution": region_dist,
        "interest_tags": interest_dist,
        "raw_data": audience_data,
        "fetch_date": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # 发送请求 - 使用UPSERT语法
    # Supabase的UPSERT需要在URL中指定on_conflict参数
    url = f"{supabase_url}/rest/v1/gg_xingtu_kol_audience?on_conflict=kol_id"
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates,return=minimal'  # UPSERT模式
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code in [200, 201, 204]:
            print(f"   ✅ 受众画像已保存到数据库")
            return True
        else:
            print(f"   ❌ 受众画像保存失败: HTTP {response.status_code}")
            print(f"      {response.text[:200]}")
            return False
    
    except Exception as e:
        print(f"   ❌ 受众画像写入异常: {e}")
        return False


def process_users(users: list, api_key: str, cookie: str = None, save_to_db: bool = True):
    """
    批量处理用户的星图KOL验证
    
    Args:
        users: 用户列表
        api_key: API密钥
        cookie: 抖音Cookie (可选但推荐)
        save_to_db: 是否保存到数据库（默认True）
        
    Returns:
        处理结果列表
    """
    results = []
    total = len(users)
    
    print(f"\n{'='*70}")
    print(f"🚀 开始检查 {total} 个用户的星图KOL状态")
    print(f"{'='*70}")
    
    xingtu_kol_count = 0
    non_xingtu_count = 0
    error_count = 0
    db_save_success_count = 0
    db_save_failed_count = 0
    
    for idx, user in enumerate(users, 1):
        print(f"\n[{idx}/{total}]")
        
        result = check_single_user_xingtu_status(user, api_key, cookie)
        results.append(result)
        
        # 统计
        if result.get('is_xingtu_kol'):
            xingtu_kol_count += 1
        elif result.get('error'):
            error_count += 1
        else:
            non_xingtu_count += 1
        
        # 保存到数据库
        if save_to_db:
            print(f"\n💾 保存数据到数据库...")
            
            # 1. 保存映射关系（所有用户都要保存）
            if save_kol_mapping_to_db(result):
                db_save_success_count += 1
            else:
                db_save_failed_count += 1
            
            # 2. 如果是星图KOL，保存受众画像
            if result.get('is_xingtu_kol'):
                xingtu_data = result.get('xingtu_data', {})
                
                # 保存受众画像
                if 'audience_portrait' in xingtu_data:
                    audience = xingtu_data['audience_portrait']
                    if not audience.get('error'):
                        save_kol_audience_to_db(result['kol_id'], audience)
        
        # 每个用户之间间隔1秒
        if idx < total:
            time.sleep(1)
    
    # 最终统计
    print(f"\n{'='*70}")
    print(f"📊 处理完成统计")
    print(f"{'='*70}")
    print(f"总计用户数: {total}")
    print(f"星图KOL: {xingtu_kol_count} ({xingtu_kol_count/total*100:.1f}%)")
    print(f"非星图KOL: {non_xingtu_count} ({non_xingtu_count/total*100:.1f}%)")
    print(f"检查失败: {error_count} ({error_count/total*100:.1f}%)")
    
    if save_to_db:
        print(f"\n数据库写入统计:")
        print(f"成功: {db_save_success_count}")
        print(f"失败: {db_save_failed_count}")
    
    return results


def save_results(results: list, output_dir: str, follower_range: str):
    """
    保存结果到JSON文件
    
    Args:
        results: 结果列表
        output_dir: 输出目录
        follower_range: 粉丝范围描述（如 "10w-50w"）
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. 保存完整数据
    full_data_file = os.path.join(output_dir, f'step2_xingtu_kol_check_{follower_range}_{timestamp}.json')
    
    # 统计信息
    total_users = len(results)
    xingtu_kols = [r for r in results if r.get('is_xingtu_kol')]
    xingtu_kol_count = len(xingtu_kols)
    
    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "follower_range": follower_range,
            "total_users_checked": total_users,
            "xingtu_kol_count": xingtu_kol_count,
            "xingtu_kol_rate": f"{xingtu_kol_count/total_users*100:.2f}%" if total_users > 0 else "0%",
            "data_source": "TikHub Xingtu API",
            "database_table": "gg_douyin_user_search"
        },
        "summary": {
            "total": total_users,
            "is_xingtu_kol": xingtu_kol_count,
            "non_xingtu_kol": sum(1 for r in results if not r.get('is_xingtu_kol') and not r.get('error')),
            "check_failed": sum(1 for r in results if r.get('error'))
        },
        "results": results
    }
    
    with open(full_data_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 完整数据已保存到: {full_data_file}")
    
    # 2. 保存星图KOL列表（仅包含是星图KOL的用户）
    if xingtu_kols:
        kol_only_file = os.path.join(output_dir, f'step2_xingtu_kol_only_{follower_range}_{timestamp}.json')
        
        kol_only_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "follower_range": follower_range,
                "total_xingtu_kols": xingtu_kol_count,
                "data_source": "TikHub Xingtu API"
            },
            "xingtu_kols": xingtu_kols
        }
        
        with open(kol_only_file, 'w', encoding='utf-8') as f:
            json.dump(kol_only_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 星图KOL列表已保存到: {kol_only_file}")
    
    # 3. 生成分析报告
    report_file = os.path.join(output_dir, f'step2_analysis_report_{follower_range}_{timestamp}.md')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 星图KOL检查分析报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**粉丝范围**: {follower_range}\n\n")
        f.write(f"## 📊 总体统计\n\n")
        f.write(f"- 检查用户总数: {total_users}\n")
        f.write(f"- 星图KOL数量: {xingtu_kol_count} ({xingtu_kol_count/total_users*100:.2f}%)\n")
        f.write(f"- 非星图用户: {sum(1 for r in results if not r.get('is_xingtu_kol') and not r.get('error'))} ({sum(1 for r in results if not r.get('is_xingtu_kol') and not r.get('error'))/total_users*100:.2f}%)\n")
        f.write(f"- 检查失败: {sum(1 for r in results if r.get('error'))} ({sum(1 for r in results if r.get('error'))/total_users*100:.2f}%)\n\n")
        
        if xingtu_kols:
            f.write(f"## ✅ 星图KOL列表\n\n")
            f.write(f"| 序号 | 昵称 | UID | 粉丝数 | KOL ID |\n")
            f.write(f"|------|------|-----|--------|--------|\n")
            
            for idx, kol in enumerate(xingtu_kols, 1):
                nickname = kol.get('nickname', '')
                uid = kol.get('uid', '')
                follower_count = kol.get('follower_count', 0)
                kol_id = kol.get('kol_id', '')
                
                f.write(f"| {idx} | {nickname} | {uid} | {follower_count:,} | {kol_id} |\n")
        
        f.write(f"\n---\n\n")
        f.write(f"*数据来源: gg_douyin_user_search 表*\n")
    
    print(f"📄 分析报告已保存到: {report_file}")
    
    return full_data_file, kol_only_file if xingtu_kols else None, report_file


def main():
    """主函数"""
    
    # 参数解析
    parser = argparse.ArgumentParser(description='从数据库用户中检查星图KOL状态')
    parser.add_argument('--limit', type=int, default=3, help='处理用户数量限制（默认3）')
    parser.add_argument('--follower-min', type=int, default=100001, help='最小粉丝数（默认100001）')
    parser.add_argument('--follower-max', type=int, default=500000, help='最大粉丝数（默认500000）')
    parser.add_argument('--save-db', action='store_true', default=True, help='是否保存到数据库（默认True）')
    parser.add_argument('--no-save-db', dest='save_db', action='store_false', help='不保存到数据库')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Step 2: 从用户中检查星图KOL状态")
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
        print("⚠️ Cookie未加载，可能影响部分接口调用")
    
    # 2. 从数据库查询用户
    print(f"\n2️⃣ 从数据库查询用户...")
    print(f"   粉丝范围: {args.follower_min:,} - {args.follower_max:,}")
    print(f"   查询数量: {args.limit}")
    
    users = fetch_users_from_db(
        follower_min=args.follower_min,
        follower_max=args.follower_max,
        limit=args.limit
    )
    
    if not users:
        print("❌ 未查询到用户，程序退出")
        return
    
    # 3. 检查星图KOL状态
    print(f"\n3️⃣ 开始检查星图KOL状态...")
    print(f"   数据库写入: {'✅ 启用' if args.save_db else '❌ 禁用'}")
    results = process_users(users, api_key, cookie, save_to_db=args.save_db)
    
    # 4. 保存结果
    print(f"\n4️⃣ 保存结果...")
    
    # 输出目录
    script_dir = Path(__file__).parent.parent
    timestamp_dir = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = script_dir / "output" / f"step2_kol_check_{timestamp_dir}"
    
    # 粉丝范围标识
    follower_range = f"{args.follower_min//10000}w-{args.follower_max//10000}w"
    
    save_results(results, str(output_dir), follower_range)
    
    print(f"\n✅ 全部完成！")
    print(f"📂 结果目录: {output_dir}")


if __name__ == "__main__":
    main()

