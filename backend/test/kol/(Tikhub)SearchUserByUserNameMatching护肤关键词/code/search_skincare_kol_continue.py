#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
继续搜索护肤达人脚本（从第4页开始）

功能：
1. 从第4页开始继续搜索
2. 逐页分析腰部达人情况
3. 检查数据重复情况
4. 如果没有更多数据则停止
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
                    
                    # 如果不是最后一次尝试，继续重试
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
                
                # 如果不是最后一次尝试，继续重试
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
            
            # 如果不是最后一次尝试，继续重试
            if attempt < max_retries - 1:
                continue
            return error_result
    
    # 所有尝试都失败
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


def load_previous_uids(output_dir: str) -> set:
    """加载之前已经获取的用户UID"""
    previous_uids = set()
    
    # 读取之前的搜索结果
    search_files = [f for f in os.listdir(output_dir) if f.startswith('search_results_3pages_')]
    if search_files:
        latest_file = sorted(search_files)[-1]
        file_path = os.path.join(output_dir, latest_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            users = data.get('users', [])
            
            for user in users:
                user_info = user.get('user_info', {})
                uid = user_info.get('uid', '')
                if uid:
                    previous_uids.add(uid)
    
    return previous_uids


def main():
    """主函数：继续搜索第21-30页（从上次参数继续）"""
    
    print("=" * 60)
    print("抖音护肤达人搜索工具 - 继续搜索（第21-30页）")
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
    
    # 2. 准备输出目录
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "output"
    detail_dir = output_dir / "detail"
    os.makedirs(detail_dir, exist_ok=True)
    
    # 3. 加载之前的UID（用于去重检测）
    print("\n2️⃣ 加载已有数据...")
    previous_uids = load_previous_uids(str(output_dir))
    print(f"✅ 已加载 {len(previous_uids)} 个已有用户UID")
    
    # 4. 从第20页的响应中读取参数，继续请求
    print("\n3️⃣ 从上次结果继续搜索...")
    keyword = "护肤"
    count_per_page = 20
    
    # 读取第20页的响应，获取翻页参数
    page_20_file = detail_dir / 'page_20_request_response.json'
    if not page_20_file.exists():
        print(f"❌ 未找到第20页的响应文件: {page_20_file}")
        return
    
    with open(page_20_file, 'r', encoding='utf-8') as f:
        page_20_data = json.load(f)
    
    # 提取翻页参数
    response_data = page_20_data.get('response', {}).get('data', {})
    config = response_data.get('config', {})
    next_page_info = config.get('next_page', {})
    
    cursor = next_page_info.get('cursor', 0)
    offset = next_page_info.get('offset', 0)
    search_id = next_page_info.get('search_id', '') or next_page_info.get('search_request_id', '')
    page = 20  # 从第20页继续，下一页是21
    
    print(f"✅ 从第20页继续，参数: cursor={cursor}, offset={offset}, page={page}, search_id={search_id[:20]}...")
    
    all_new_users = []
    all_page_analyses = []
    total_duplicates = 0
    
    for page_num in range(21, 31):  # 第21-30页
        print(f"\n{'='*60}")
        print(f"[第 {page_num} 页]")
        print(f"{'='*60}")
        
        # 调用 API（支持重试）
        result = fetch_user_search_v4(api_key, keyword, cursor, offset, page, search_id, count_per_page, max_retries=4)
        
        # 检查是否有错误
        has_error = 'error' in result or result.get('code') != 200
        
        # 无论成功还是失败，都保存详细信息
        if has_error:
            # 保存错误响应到 error_ 开头的文件
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
        
        # 检查重复
        new_users = []
        duplicate_count = 0
        
        for user in user_list:
            user_info = user.get('user_info', {})
            uid = user_info.get('uid', '')
            
            if uid in previous_uids:
                duplicate_count += 1
            else:
                if uid:
                    previous_uids.add(uid)
                new_users.append(user)
        
        all_new_users.extend(new_users)
        total_duplicates += duplicate_count
        
        print(f"\n📊 本页统计:")
        print(f"   原始用户数: {len(user_list)}")
        print(f"   新增用户数: {len(new_users)}")
        print(f"   重复用户数: {duplicate_count}")
        
        # 分析本页的腰部达人
        page_analysis = analyze_page_waist_kols(user_list, page_num)
        all_page_analyses.append(page_analysis)
        
        print(f"\n🎯 本页腰部达人分析 (10万~100万粉丝):")
        print(f"   腰部达人数: {page_analysis['waist_kol_count']}")
        print(f"   占本页比例: {(page_analysis['waist_kol_count']/len(user_list)*100):.1f}%")
        
        if page_analysis['waist_kols']:
            print(f"\n   本页腰部达人 TOP 5:")
            for i, kol in enumerate(page_analysis['waist_kols'][:5], 1):
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
        
        # 请求间隔2秒（遵守RPS限流）
        if page_num < 30:
            print(f"\n⏳ 等待 2 秒后继续（遵守 RPS 限流）...")
            time.sleep(2)
    
    # 5. 保存汇总结果
    print(f"\n{'='*60}")
    print(f"4️⃣ 保存汇总结果...")
    print(f"{'='*60}")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存新增用户数据
    new_users_file = output_dir / f'search_results_pages_21_to_{page_num}_{timestamp}.json'
    with open(new_users_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'keyword': keyword,
                'search_date': datetime.now().isoformat(),
                'page_range': f'21-{page_num}',
                'total_new_users': len(all_new_users),
                'total_duplicates': total_duplicates,
                'request_interval': '2秒',
                'retry_policy': '失败后重试最多4次，第1次2秒，后续10-20-40秒'
            },
            'users': all_new_users
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 新增用户数据: {new_users_file.name}")
    
    # 保存逐页分析结果
    page_analysis_file = output_dir / f'page_by_page_analysis_pages_21_to_{page_num}_{timestamp}.json'
    with open(page_analysis_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'keyword': keyword,
                'analysis_date': datetime.now().isoformat(),
                'page_range': f'21-{page_num}',
                'total_pages': len(all_page_analyses),
                'request_interval': '2秒',
                'retry_policy': '失败后重试最多4次，第1次2秒，后续10-20-40秒'
            },
            'page_analyses': all_page_analyses
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 逐页分析结果: {page_analysis_file.name}")
    
    # 生成汇总报告
    report_file = output_dir / f'continue_search_report_pages_21_to_{page_num}_{timestamp}.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 护肤达人继续搜索报告（第21-{page_num}页）\n\n")
        f.write(f"**搜索关键词**: {keyword}\n")
        f.write(f"**搜索时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**页面范围**: 第21页 - 第{page_num}页\n")
        f.write(f"**请求间隔**: 2秒\n")
        f.write(f"**重试策略**: 失败后重试最多4次，第1次2秒，后续10-20-40秒\n\n")
        
        f.write(f"## 总体统计\n\n")
        f.write(f"- 新增用户数: {len(all_new_users)}\n")
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
            
            if analysis['waist_kols']:
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
        else:
            f.write(f"- 平均每页腰部达人数: 0\n")
    
    print(f"💾 汇总报告: {report_file.name}")
    
    # 最终总结
    print(f"\n{'='*60}")
    print(f"✅ 全部完成！")
    print(f"{'='*60}")
    print(f"📌 汇总信息:")
    print(f"   搜索页面: 第21页 - 第{page_num}页")
    print(f"   新增用户: {len(all_new_users)} 人")
    print(f"   重复用户: {total_duplicates} 人")
    print(f"   新增腰部达人: {total_waist_kols} 人")
    print(f"   请求间隔: 2秒")
    print(f"   重试策略: 失败后重试最多4次，第1次2秒，后续10-20-40秒")


if __name__ == "__main__":
    main()

