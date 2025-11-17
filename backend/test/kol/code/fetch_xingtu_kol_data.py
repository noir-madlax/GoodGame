#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取星图KOL数据的完整流程
1. 通过 uid 获取星图 kol_id (接口1.1)
2. 使用 kol_id 调用星图接口 (接口1.2-1.6)
   - 1.2 KOL基础信息
   - 1.3 KOL受众画像
   - 1.4 KOL服务报价
   - 1.5 KOL内容定位
   - 1.6 KOL转化能力分析
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import time


def load_api_key():
    """从环境变量加载TikHub API Key"""
    backend_dir = Path(__file__).parent.parent.parent.parent
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
    backend_dir = Path(__file__).parent.parent.parent.parent
    cookie_path = backend_dir / 'test' / 'kol' / 'cookie'
    
    if not cookie_path.exists():
        return None
    
    # 尝试读取JSON格式的cookie文件
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


def load_kol_accounts(json_path: str, limit: int = 5) -> list:
    """
    从final_kol_accounts JSON文件中加载达人账号数据
    
    Args:
        json_path: JSON文件路径
        limit: 加载数量限制
        
    Returns:
        达人账号列表
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    kol_accounts = data.get('kol_accounts', [])
    
    # 只取前limit个
    kol_accounts = kol_accounts[:limit]
    
    print(f"✅ 加载了 {len(kol_accounts)} 个达人账号数据")
    
    return kol_accounts


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
            print(f"   ⚠️ 详细错误信息: {error_text[:300]}")
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
        print(f"   ⚠️ 异常信息: {str(e)}")
        return {"error": str(e)}


def get_kol_base_info(api_key: str, kol_id: str, cookie: str = None, use_china_domain: bool = True) -> dict:
    """
    接口1.2: 获取KOL基础信息
    
    包含: 账号状态、粉丝数、认证信息、擅长领域等
    注意: 此接口可能需要特殊权限，当前可能返回400错误
    """
    base_url = get_api_base_url(use_china_domain)
    endpoint = "/douyin/xingtu/kol_base_info_v1"
    url = f"{base_url}{endpoint}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    if cookie:
        headers['Cookie'] = cookie
    
    # 使用正确的参数名（驼峰命名）
    params = {
        'kolId': kol_id,
        'platformChannel': 'douyin'
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


def get_kol_service_price(api_key: str, kol_id: str, cookie: str = None, use_china_domain: bool = True) -> dict:
    """
    接口1.4: 获取KOL服务报价
    
    包含: 视频、直播、图文报价、历史订单数
    注意: 此接口可能需要特殊权限，当前可能返回400错误
    """
    base_url = get_api_base_url(use_china_domain)
    endpoint = "/douyin/xingtu/kol_service_price_v1"
    url = f"{base_url}{endpoint}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    if cookie:
        headers['Cookie'] = cookie
    
    # 使用正确的参数名（驼峰命名）
    params = {
        'kolId': kol_id,
        'platformChannel': 'douyin'
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


def get_kol_conversion_ability(api_key: str, kol_id: str, cookie: str = None, use_china_domain: bool = True) -> dict:
    """
    接口1.6: 获取KOL转化能力分析
    
    包含: 转化率、互动数据、GMV能力
    注意: 此接口可能需要特殊权限，当前可能返回400错误
    """
    base_url = get_api_base_url(use_china_domain)
    endpoint = "/douyin/xingtu/kol_conversion_ability_analysis_v1"
    url = f"{base_url}{endpoint}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    if cookie:
        headers['Cookie'] = cookie
    
    # 使用正确的参数名（驼峰命名）
    params = {
        'kolId': kol_id,
        '_range': '30'
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


def fetch_single_kol_xingtu_data(kol_account: dict, api_key: str, cookie: str = None) -> dict:
    """
    获取单个KOL的完整星图数据
    
    流程:
    1. 获取星图KOL ID
    2. 如果是星图KOL，调用5个星图接口
    
    Args:
        kol_account: 达人账号信息
        api_key: API密钥
        cookie: 抖音Cookie (可选但推荐)
        
    Returns:
        包含所有接口数据的字典
    """
    name = kol_account.get('name', 'Unknown')
    rank = kol_account.get('rank', 0)
    douyin_account = kol_account.get('douyin_account', {})
    sec_user_id = douyin_account.get('sec_uid', '') or douyin_account.get('user_id', '')
    
    print(f"\n{'='*70}")
    print(f"处理达人 #{rank} - {name}")
    print(f"{'='*70}")
    
    result = {
        "rank": rank,
        "name": name,
        "sec_user_id": sec_user_id,
        "nick_name": douyin_account.get('nick_name', ''),
        "fans_count": douyin_account.get('fans_count', 0),
        "timestamp": datetime.now().isoformat()
    }
    
    # Step 1: 获取星图KOL ID
    print(f"\n📡 步骤1: 获取星图KOL ID...")
    print(f"   sec_user_id: {sec_user_id[:40]}...")
    
    kol_id_response = get_xingtu_kol_id(api_key, sec_user_id, cookie)
    
    # 保存原始响应以便调试
    result['kol_id_response'] = kol_id_response
    
    if kol_id_response.get('error'):
        print(f"   ❌ 获取KOL ID失败: {kol_id_response.get('error')}")
        result['error'] = f"获取KOL ID失败: {kol_id_response.get('error')}"
        result['is_xingtu_kol'] = False
        return result
    
    # 检查是否是星图KOL
    data_content = kol_id_response.get('data', {})
    # 星图KOL ID在data.id字段中
    kol_id = data_content.get('id', '')
    
    if not kol_id:
        print(f"   ⚠️ 不是星图KOL（未找到kol_id）")
        result['is_xingtu_kol'] = False
        result['kol_id_response'] = kol_id_response
        return result
    
    print(f"   ✅ 成功获取KOL ID: {kol_id}")
    result['is_xingtu_kol'] = True
    result['kol_id'] = kol_id
    result['kol_id_response'] = kol_id_response
    
    # Step 2: 调用5个星图接口
    print(f"\n📊 步骤2: 获取星图详细数据...")
    
    xingtu_data = {}
    
    # 2.1 基础信息
    print(f"   [1/5] 获取基础信息...")
    base_info = get_kol_base_info(api_key, kol_id, cookie)
    if not base_info.get('error'):
        print(f"   ✅ 基础信息获取成功")
        xingtu_data['base_info'] = base_info
    else:
        print(f"   ❌ 基础信息获取失败: {base_info.get('error')}")
        xingtu_data['base_info'] = base_info
    
    time.sleep(0.5)  # 避免请求过快
    
    # 2.2 受众画像
    print(f"   [2/5] 获取受众画像...")
    audience = get_kol_audience_portrait(api_key, kol_id, cookie)
    if not audience.get('error'):
        print(f"   ✅ 受众画像获取成功")
        xingtu_data['audience_portrait'] = audience
    else:
        print(f"   ❌ 受众画像获取失败: {audience.get('error')}")
        xingtu_data['audience_portrait'] = audience
    
    time.sleep(0.5)
    
    # 2.3 服务报价
    print(f"   [3/5] 获取服务报价...")
    price = get_kol_service_price(api_key, kol_id, cookie)
    if not price.get('error'):
        print(f"   ✅ 服务报价获取成功")
        xingtu_data['service_price'] = price
    else:
        print(f"   ❌ 服务报价获取失败: {price.get('error')}")
        xingtu_data['service_price'] = price
    
    time.sleep(0.5)
    
    # 2.4 内容定位
    print(f"   [4/5] 获取内容定位...")
    cp_info = get_kol_cp_info(api_key, kol_id, cookie)
    if not cp_info.get('error'):
        print(f"   ✅ 内容定位获取成功")
        xingtu_data['cp_info'] = cp_info
    else:
        print(f"   ❌ 内容定位获取失败: {cp_info.get('error')}")
        xingtu_data['cp_info'] = cp_info
    
    time.sleep(0.5)
    
    # 2.5 转化能力分析
    print(f"   [5/5] 获取转化能力分析...")
    conversion = get_kol_conversion_ability(api_key, kol_id, cookie)
    if not conversion.get('error'):
        print(f"   ✅ 转化能力分析获取成功")
        xingtu_data['conversion_ability'] = conversion
    else:
        print(f"   ❌ 转化能力分析获取失败: {conversion.get('error')}")
        xingtu_data['conversion_ability'] = conversion
    
    result['xingtu_data'] = xingtu_data
    
    # 统计成功率
    success_count = sum(1 for v in xingtu_data.values() if not v.get('error'))
    total_count = len(xingtu_data)
    
    print(f"\n📈 数据获取完成: {success_count}/{total_count} 个接口成功")
    
    return result


def process_kols(kol_accounts: list, api_key: str, cookie: str = None):
    """
    批量处理达人的星图数据获取
    
    Args:
        kol_accounts: 达人账号列表
        api_key: API密钥
        cookie: 抖音Cookie (可选但推荐)
        
    Returns:
        处理结果列表
    """
    results = []
    total = len(kol_accounts)
    
    print(f"\n{'='*70}")
    print(f"🚀 开始获取 {total} 个达人的星图数据")
    print(f"{'='*70}")
    
    xingtu_kol_count = 0
    non_xingtu_kol_count = 0
    error_count = 0
    
    for idx, kol_account in enumerate(kol_accounts, 1):
        print(f"\n[{idx}/{total}]")
        
        result = fetch_single_kol_xingtu_data(kol_account, api_key, cookie)
        results.append(result)
        
        # 统计
        if result.get('is_xingtu_kol'):
            xingtu_kol_count += 1
        elif result.get('error'):
            error_count += 1
        else:
            non_xingtu_kol_count += 1
        
        # 每个达人之间间隔1秒
        if idx < total:
            time.sleep(1)
    
    # 最终统计
    print(f"\n{'='*70}")
    print(f"📊 处理完成统计")
    print(f"{'='*70}")
    print(f"总计达人数: {total}")
    print(f"星图KOL: {xingtu_kol_count} ({xingtu_kol_count/total*100:.1f}%)")
    print(f"非星图KOL: {non_xingtu_kol_count} ({non_xingtu_kol_count/total*100:.1f}%)")
    print(f"获取失败: {error_count} ({error_count/total*100:.1f}%)")
    
    return results


def save_results(results: list, output_dir: str):
    """保存结果到JSON文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'xingtu_kol_data_{timestamp}.json')
    
    # 准备输出数据
    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_kols": len(results),
            "xingtu_kols": sum(1 for r in results if r.get('is_xingtu_kol')),
            "data_source": "TikHub Xingtu API"
        },
        "kol_data": results
    }
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 星图数据已保存到: {output_file}")
    
    return output_file


def main():
    """主函数"""
    
    print("=" * 70)
    print("抖音达人星图数据获取")
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
    
    # 2. 加载达人账号数据
    print("\n2️⃣ 加载达人账号数据...")
    script_dir = Path(__file__).parent.parent
    kol_accounts_path = script_dir / "output" / "kol_user_ids" / "final_kol_accounts_20251113_182240.json"
    
    if not kol_accounts_path.exists():
        print(f"❌ 达人账号文件不存在: {kol_accounts_path}")
        return
    
    # 只处理前5个达人
    kol_accounts = load_kol_accounts(str(kol_accounts_path), limit=5)
    
    # 3. 获取星图数据
    print("\n3️⃣ 开始获取星图数据...")
    results = process_kols(kol_accounts, api_key, cookie)
    
    # 4. 保存结果
    print("\n4️⃣ 保存结果...")
    output_dir = script_dir / "output" / "xingtu_kol_data"
    save_results(results, str(output_dir))
    
    print(f"\n✅ 全部完成！")


if __name__ == "__main__":
    main()

