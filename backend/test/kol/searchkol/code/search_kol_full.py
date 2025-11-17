#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整搜索护肤达人博主脚本（1-30页）

功能：
1. 搜索关键词：护肤 达人 博主
2. 获取1-30页数据
3. 请求间隔2秒
4. 失败重试最多4次（第1次2秒，后续10-20-40秒）
5. 输出到独立目录
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


def load_api_key():
    """从环境变量加载 TikHub API Key"""
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 从 {env_path} 加载环境变量")
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    
    return api_key


def fetch_user_search_v4(api_key: str, keyword: str, cursor: int = 0, offset: int = 0, 
                        page: int = 0, search_id: str = "", count: int = 10, 
                        max_retries: int = 4) -> dict:
    """
    调用 TikHub API 的 fetch_user_search_v4 接口（支持重试）
    
    Args:
        max_retries: 最大重试次数（第1次间隔2秒，后续10秒、20秒、40秒）
    """
    url = "https://api.tikhub.io/api/v1/douyin/search/fetch_user_search_v4"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'keyword': keyword,
        'cursor': cursor,
        'offset': offset,
        'page': page,
        'search_id': search_id,
        'count': count,
        'search_channel': 'aweme_user_web',
        'sort_type': 0,
        'publish_time': 0
    }
    
    # 重试间隔（秒）：第1次2秒，后续10-20-40秒
    retry_delays = [2, 10, 20, 40]
    
    for attempt in range(max_retries):
        if attempt > 0:
            delay = retry_delays[attempt - 1]
            print(f"   🔄 第 {attempt + 1} 次尝试（等待 {delay} 秒）...")
            time.sleep(delay)
        else:
            print(f"\n📡 发送请求: cursor={cursor}, offset={offset}, page={page}, search_id={search_id[:20] if search_id else '(空)'}...")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                code = result.get('code', -1)
                
                if code == 200:
                    result['_request_payload'] = payload
                    result['_request_headers'] = {k: v if k != 'Authorization' else f"{v[:20]}..." for k, v in headers.items()}
                    result['_attempt'] = attempt + 1
                    print(f"   ✅ 请求成功（尝试 {attempt + 1} 次）")
                    return result
                else:
                    print(f"   ❌ API 返回错误码: {code}")
                    result['_request_payload'] = payload
                    result['_request_headers'] = {k: v if k != 'Authorization' else f"{v[:20]}..." for k, v in headers.items()}
                    result['_attempt'] = attempt + 1
                    result['_error'] = f"API error code: {code}"
                    
                    if attempt < max_retries - 1:
                        continue
                    return result
            else:
                print(f"   ❌ HTTP 请求失败: {response.status_code}")
                error_result = {
                    "error": f"HTTP {response.status_code}",
                    "response_text": response.text[:500],
                    "_request_payload": payload,
                    "_request_headers": {k: v if k != 'Authorization' else f"{v[:20]}..." for k, v in headers.items()},
                    "_attempt": attempt + 1
                }
                
                if attempt < max_retries - 1:
                    continue
                return error_result
                
        except Exception as e:
            print(f"   ❌ 请求异常: {str(e)}")
            error_result = {
                "error": str(e),
                "_request_payload": payload,
                "_request_headers": {k: v if k != 'Authorization' else f"{v[:20]}..." for k, v in headers.items()},
                "_attempt": attempt + 1
            }
            
            if attempt < max_retries - 1:
                continue
            return error_result
    
    return {
        "error": "All retry attempts failed",
        "_request_payload": payload,
        "_request_headers": {k: v if k != 'Authorization' else f"{v[:20]}..." for k, v in headers.items()},
        "_attempt": max_retries
    }


def analyze_page_waist_kols(users: list, page_num: int) -> dict:
    """分析单页的腰部达人情况"""
    waist_kols = []
    
    for user in users:
        user_info = user.get('user_info', {})
        follower_count = user_info.get('follower_count', 0)
        
        # 腰部达人定义：10万~100万粉丝
        if 100_000 <= follower_count <= 1_000_000:
            waist_kols.append({
                'nickname': user_info.get('nickname', 'N/A'),
                'follower_count': follower_count,
                'uid': user_info.get('uid', ''),
                'unique_id': user_info.get('unique_id', ''),
                'signature': user_info.get('signature', '')[:50]
            })
    
    # 按粉丝数排序
    waist_kols.sort(key=lambda x: x['follower_count'], reverse=True)
    
    return {
        'page_num': page_num,
        'total_users': len(users),
        'waist_kol_count': len(waist_kols),
        'waist_kols': waist_kols
    }


def main():
    """主函数：完整搜索1-30页"""
    
    print("=" * 60)
    print("抖音护肤达人博主搜索工具 - 完整搜索（1-30页）")
    print("关键词：护肤 达人 博主")
    print("说明：请求间隔2秒，失败后重试最多4次（第1次2秒，后续10-20-40秒）")
    print("=" * 60)
    
    # 1. 加载 API Key
    print("\n1️⃣ 加载 API 配置...")
    try:
        api_key = load_api_key()
        print(f"✅ API Key 已加载")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # 2. 准备输出目录（使用新目录）
    script_dir = Path(__file__).parent.parent
    timestamp_prefix = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = script_dir / f"output_kol_full_{timestamp_prefix}"
    detail_dir = output_dir / "detail"
    os.makedirs(detail_dir, exist_ok=True)
    print(f"\n2️⃣ 输出目录: {output_dir}")
    
    # 3. 开始搜索
    print("\n3️⃣ 开始搜索...")
    keyword = "护肤 达人 博主"
    count_per_page = 20
    
    # 初始化翻页参数
    cursor = 0
    offset = 0
    page = 0
    search_id = ""
    
    all_users = []
    seen_uids = set()
    all_page_analyses = []
    total_duplicates = 0
    
    for page_num in range(1, 31):  # 第1-30页
        print(f"\n{'='*60}")
        print(f"[第 {page_num} 页]")
        print(f"{'='*60}")
        
        # 调用 API（支持重试）
        result = fetch_user_search_v4(api_key, keyword, cursor, offset, page, search_id, count_per_page, max_retries=4)
        
        # 检查是否有错误
        has_error = 'error' in result or result.get('code') != 200
        
        # 无论成功还是失败，都保存详细信息
        if has_error:
            # 保存错误响应
            error_file = detail_dir / f'error_page_{page_num}_request_response.json'
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'page_num': page_num,
                    'request_payload': result.get('_request_payload', {}),
                    'request_headers': result.get('_request_headers', {}),
                    'error': result.get('error', 'Unknown error'),
                    'attempt': result.get('_attempt', 1),
                    'response': result
                }, f, ensure_ascii=False, indent=2)
            print(f"💾 已保存错误详情到: {error_file.name}")
            print(f"⚠️ 第 {page_num} 页获取失败（已重试{result.get('_attempt', 1)}次），停止搜索")
            break
        
        # 提取数据
        data = result.get('data', {})
        inner_data = data.get('data', [])
        config = data.get('config', {})
        user_list = inner_data if isinstance(inner_data, list) else []
        
        if not user_list:
            # 保存空数据的详情
            detail_file = detail_dir / f'page_{page_num}_request_response.json'
            with open(detail_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'page_num': page_num,
                    'request_payload': result.get('_request_payload', {}),
                    'request_headers': result.get('_request_headers', {}),
                    'response': result
                }, f, ensure_ascii=False, indent=2)
            print(f"💾 已保存详情到: {detail_file.name}")
            print(f"⚠️ 第 {page_num} 页没有数据，停止搜索")
            break
        
        print(f"✅ 获取到 {len(user_list)} 个用户")
        
        # 保存详细请求/响应
        detail_file = detail_dir / f'page_{page_num}_request_response.json'
        with open(detail_file, 'w', encoding='utf-8') as f:
            json.dump({
                'page_num': page_num,
                'request_payload': result.get('_request_payload', {}),
                'request_headers': result.get('_request_headers', {}),
                'attempt': result.get('_attempt', 1),
                'response': result
            }, f, ensure_ascii=False, indent=2)
        print(f"💾 已保存详情到: {detail_file.name}")
        
        # 检查重复并添加用户
        new_users = 0
        duplicate_count = 0
        
        for user in user_list:
            user_info = user.get('user_info', {})
            uid = user_info.get('uid', '')
            
            if uid and uid not in seen_uids:
                seen_uids.add(uid)
                all_users.append(user)
                new_users += 1
            else:
                duplicate_count += 1
        
        total_duplicates += duplicate_count
        
        print(f"\n📊 本页统计:")
        print(f"   原始用户数: {len(user_list)}")
        print(f"   新增用户数: {new_users}")
        print(f"   重复用户数: {duplicate_count}")
        
        # 分析本页的腰部达人
        page_analysis = analyze_page_waist_kols(user_list, page_num)
        all_page_analyses.append(page_analysis)
        
        print(f"\n🎯 本页腰部达人分析 (10万~100万粉丝):")
        print(f"   腰部达人数: {page_analysis['waist_kol_count']}")
        print(f"   占本页比例: {(page_analysis['waist_kol_count']/len(user_list)*100):.1f}%")
        
        if page_analysis['waist_kols']:
            print(f"\n   本页腰部达人 TOP 3:")
            for i, kol in enumerate(page_analysis['waist_kols'][:3], 1):
                print(f"   {i}. {kol['nickname']} - 粉丝: {kol['follower_count']:,}")
        
        # 检查是否还有更多数据
        has_more = config.get('has_more', 0) == 1
        next_page_info = config.get('next_page', {})
        
        if not has_more:
            print(f"\n✅ 已获取所有数据，共 {page_num} 页")
            break
        
        # 更新翻页参数
        if next_page_info:
            cursor = next_page_info.get('cursor', cursor)
            if not search_id and 'search_request_id' in next_page_info:
                search_id = next_page_info.get('search_request_id', '')
            elif not search_id and 'search_id' in next_page_info:
                search_id = next_page_info.get('search_id', '')
        
        page += 1
        
        # 请求间隔2秒
        if page_num < 30:
            print(f"\n⏳ 等待 2 秒后继续...")
            time.sleep(2)
    
    # 4. 保存汇总结果
    print(f"\n{'='*60}")
    print(f"4️⃣ 保存汇总结果...")
    print(f"{'='*60}")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存所有用户数据
    all_users_file = output_dir / f'all_users_{timestamp}.json'
    with open(all_users_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'keyword': keyword,
                'search_date': datetime.now().isoformat(),
                'total_pages': len(all_page_analyses),
                'total_unique_users': len(all_users),
                'total_duplicates': total_duplicates,
                'request_interval': '2秒',
                'retry_policy': '失败后重试最多4次，第1次2秒，后续10-20-40秒'
            },
            'users': all_users
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 所有用户数据: {all_users_file.name}")
    
    # 保存逐页分析结果
    page_analysis_file = output_dir / f'page_by_page_analysis_{timestamp}.json'
    with open(page_analysis_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'keyword': keyword,
                'analysis_date': datetime.now().isoformat(),
                'total_pages': len(all_page_analyses),
                'request_interval': '2秒',
                'retry_policy': '失败后重试最多4次，第1次2秒，后续10-20-40秒'
            },
            'page_analyses': all_page_analyses
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 逐页分析结果: {page_analysis_file.name}")
    
    # 生成汇总报告
    report_file = output_dir / f'search_report_{timestamp}.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 护肤达人博主搜索报告\n\n")
        f.write(f"**搜索关键词**: {keyword}\n")
        f.write(f"**搜索时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**页面范围**: 第1页 - 第{len(all_page_analyses)}页\n")
        f.write(f"**请求间隔**: 2秒\n")
        f.write(f"**重试策略**: 失败后重试最多4次，第1次2秒，后续10-20-40秒\n\n")
        
        f.write(f"## 总体统计\n\n")
        f.write(f"- 唯一用户数: {len(all_users)}\n")
        f.write(f"- 重复用户数: {total_duplicates}\n")
        f.write(f"- 总页数: {len(all_page_analyses)}\n\n")
        
        f.write(f"## 逐页分析\n\n")
        
        total_waist_kols = 0
        for analysis in all_page_analyses:
            total_waist_kols += analysis['waist_kol_count']
            
            f.write(f"### 第 {analysis['page_num']} 页\n\n")
            f.write(f"- 用户总数: {analysis['total_users']}\n")
            f.write(f"- 腰部达人数: {analysis['waist_kol_count']}\n")
            f.write(f"- 腰部达人占比: {(analysis['waist_kol_count']/analysis['total_users']*100):.1f}%\n\n")
            
            if analysis['waist_kols'] and len(analysis['waist_kols']) > 0:
                f.write(f"#### TOP 3 腰部达人\n\n")
                f.write(f"| 排名 | 昵称 | 粉丝数 | 抖音号 |\n")
                f.write(f"|------|------|--------|--------|\n")
                
                for i, kol in enumerate(analysis['waist_kols'][:3], 1):
                    f.write(f"| {i} | {kol['nickname']} | {kol['follower_count']:,} | {kol['unique_id']} |\n")
                
                f.write(f"\n")
        
        f.write(f"## 腰部达人汇总\n\n")
        f.write(f"- 总腰部达人数: {total_waist_kols}\n")
        if all_page_analyses:
            f.write(f"- 平均每页腰部达人数: {(total_waist_kols/len(all_page_analyses)):.1f}\n")
    
    print(f"💾 汇总报告: {report_file.name}")
    
    # 最终总结
    print(f"\n{'='*60}")
    print(f"✅ 全部完成！")
    print(f"{'='*60}")
    print(f"📌 汇总信息:")
    print(f"   搜索关键词: {keyword}")
    print(f"   搜索页数: 第1页 - 第{len(all_page_analyses)}页")
    print(f"   唯一用户数: {len(all_users)} 人")
    print(f"   重复用户数: {total_duplicates} 人")
    print(f"   腰部达人数: {total_waist_kols} 人")
    print(f"   输出目录: {output_dir}")


if __name__ == "__main__":
    main()

