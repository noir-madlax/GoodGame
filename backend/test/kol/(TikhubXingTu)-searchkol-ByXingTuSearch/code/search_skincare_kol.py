#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音星图护肤达人搜索脚本

功能：
1. 调用 TikHub API 的星图 search_kol_v1 接口搜索"护肤达人"
2. 获取 3 页搜索结果数据
3. 分析腰部达人（粉丝数 10万~100万）的数量和粉丝数分布
4. 将结果保存到 output 目录

接口文档: https://api.tikhub.io/#/Douyin-Xingtu-API/search_kol_v1_api_v1_douyin_xingtu_search_kol_v1_get
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


def load_api_key():
    """
    从环境变量加载 TikHub API Key
    
    Returns:
        str: API Key
    
    Raises:
        ValueError: 如果 API Key 未设置
    """
    # 定位到 backend/.env 文件
    # 从 backend/test/kol/xingtu-searchkol/code/ 需要上 4 级到 backend/
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


def search_kol_v1(api_key: str, keyword: str, page: int = 1, count: int = 20, sort_type: int = 1, platform_source: str = "_1", save_raw: bool = False, output_dir: str = None) -> dict:
    """
    调用 TikHub API 的星图 search_kol_v1 接口搜索 KOL 达人
    
    Args:
        api_key: TikHub API 密钥
        keyword: 搜索关键词
        page: 页码，从 1 开始
        count: 每页返回数量，建议 10-50，默认 20
        sort_type: 排序类型（1=综合排序, 2=粉丝数从高到低, 3=粉丝数从低到高）
        platform_source: 平台来源（"_1"=抖音）
        save_raw: 是否保存原始请求和响应
        output_dir: 输出目录
        
    Returns:
        dict: API 响应的 JSON 数据
    """
    # API 端点（GET 请求）
    url = "https://api.tikhub.io/api/v1/douyin/xingtu/search_kol_v1"
    
    # 设置请求头
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key[:20]}...(隐藏)'  # 用于记录，隐藏完整 key
    }
    
    # 实际请求头
    actual_headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # 设置查询参数（GET 请求的参数）
    params = {
        'keyword': keyword,              # 搜索关键词
        'page': page,                    # 页码
        'count': count,                  # 每页数量
        'sort_type': sort_type,          # 排序类型
        'platformSource': platform_source # 平台来源
    }
    
    print(f"\n📡 发送星图 KOL 搜索请求...")
    print(f"   关键词: {keyword}")
    print(f"   页码: {page}")
    print(f"   数量: {count}")
    print(f"   排序: {sort_type}")
    print(f"   平台: {platform_source}")
    
    try:
        # 发送 GET 请求（使用实际的 headers）
        response = requests.get(url, headers=actual_headers, params=params, timeout=30)
        
        print(f"   状态码: {response.status_code}")
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            
            # 保存原始请求和响应
            if save_raw and output_dir:
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                raw_file = os.path.join(output_dir, f'api_request_response_page_{page}_{timestamp}.json')
                
                raw_data = {
                    'request': {
                        'url': url,
                        'method': 'GET',
                        'headers': headers,  # 使用隐藏 key 的版本
                        'params': params,
                        'timestamp': datetime.now().isoformat()
                    },
                    'response': {
                        'status_code': response.status_code,
                        'headers': dict(response.headers),
                        'body': result,
                        'timestamp': datetime.now().isoformat()
                    }
                }
                
                with open(raw_file, 'w', encoding='utf-8') as f:
                    json.dump(raw_data, f, ensure_ascii=False, indent=2)
                print(f"   💾 原始请求响应已保存: {raw_file}")
            
            # 打印响应结构（用于调试）
            print(f"   响应结构: {list(result.keys())}")
            
            # 检查响应代码
            code = result.get('code', -1)
            message = result.get('message', 'Unknown')

            print(f"   响应消息: code={code}, message={message}")

            # 打印 data 部分的结构
            if 'data' in result:
                data = result.get('data', {})
                if isinstance(data, dict):
                    print(f"   data 结构: {list(data.keys())}")
                else:
                    print(f"   data 类型: {type(data)}")

            if code == 200:  # 星图 API 成功返回 code=200
                data = result.get('data', {})

                # 获取作者列表 (新API结构使用authors而不是kol_list)
                authors = data.get('authors', [])
                # 检查是否有分页信息
                pagination = data.get('pagination', {})
                has_more = pagination.get('has_more', False)
                cursor = pagination.get('cursor', 0)

                print(f"   ✅ 成功获取 {len(authors)} 个作者")
                print(f"   还有更多数据: {has_more}")
                print(f"   下一页游标: {cursor}")

                return result
            else:
                print(f"   ❌ API 返回错误码: {code}")
                print(f"   错误消息: {message}")
                print(f"   完整响应前500字符: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
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


def fetch_multiple_pages(api_key: str, keyword: str, page_count: int = 3, count_per_page: int = 20, output_dir: str = None) -> list:
    """
    获取多页星图 KOL 搜索结果
    
    Args:
        api_key: API 密钥
        keyword: 搜索关键词
        page_count: 要获取的页数
        count_per_page: 每页数量
        output_dir: 输出目录
        
    Returns:
        list: 所有 KOL 数据列表
    """
    all_kols = []
    
    print(f"\n{'='*60}")
    print(f"🔍 开始搜索星图 KOL: {keyword}")
    print(f"   目标页数: {page_count}")
    print(f"   每页数量: {count_per_page}")
    print(f"{'='*60}")
    
    for page in range(1, page_count + 1):
        print(f"\n[第 {page}/{page_count} 页]")
        print("-" * 60)
        
        # 调用星图 KOL 搜索 API（使用 page 参数，保存原始请求响应）
        result = search_kol_v1(api_key, keyword, page=page, count=count_per_page, save_raw=True, output_dir=output_dir)
        
        # 检查是否成功（星图 API 返回 code=200 表示成功）
        if 'error' in result or result.get('code') != 200:
            print(f"⚠️ 第 {page} 页获取失败，停止搜索")
            break
        
        # 提取作者列表
        data = result.get('data', {})
        authors = data.get('authors', [])
        pagination = data.get('pagination', {})
        has_more = pagination.get('has_more', False)

        if not authors:
            print(f"⚠️ 第 {page} 页没有数据，停止搜索")
            break

        # 添加到总列表
        all_kols.extend(authors)

        # 显示本页作者信息
        print(f"\n本页作者预览:")
        for i, author in enumerate(authors[:3], 1):
            attr_data = author.get('attribute_datas', {})
            nickname = attr_data.get('nick_name', 'N/A')
            follower_count = int(attr_data.get('follower', '0'))
            star_score = float(attr_data.get('star_index', '0'))
            fans_level = attr_data.get('grade', 'N/A')
            print(f"   {i}. {nickname} - 粉丝: {follower_count:,} - 星图评分: {star_score:.1f} - 等级: {fans_level}")

        if len(authors) > 3:
            print(f"   ... 还有 {len(authors) - 3} 个作者")
        
        # 检查是否还有更多数据
        if not has_more:
            print(f"\n✅ 已获取所有数据（共 {page} 页）")
            break
        
        # 添加延迟，避免请求过快
        if page < page_count:
            print(f"\n⏳ 等待 1 秒后继续...")
            time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"✅ 搜索完成！共获取 {len(all_kols)} 个 KOL")
    print(f"{'='*60}")
    
    return all_kols


def analyze_kol_distribution(kols: list) -> dict:
    """
    分析 KOL 达人的粉丝数分布
    
    定义：
    - 头部达人: 粉丝数 >= 100万
    - 腰部达人: 10万 <= 粉丝数 < 100万
    - 尾部达人: 1万 <= 粉丝数 < 10万
    - 素人: 粉丝数 < 1万
    
    Args:
        kols: KOL 列表
        
    Returns:
        dict: 分析结果
    """
    print(f"\n{'='*60}")
    print(f"📊 开始分析 KOL 达人分布")
    print(f"{'='*60}")
    
    # 分类统计
    categories = {
        '头部达人 (>=100万)': [],
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
    
    # 遍历作者进行分类
    for author in kols:
        attr_data = author.get('attribute_datas', {})
        follower_count = int(attr_data.get('follower', '0'))
        
        # 分类
        if follower_count >= 1_000_000:
            categories['头部达人 (>=100万)'].append(author)
        elif follower_count >= 100_000:
            categories['腰部达人 (10万~100万)'].append(author)
        elif follower_count >= 10_000:
            categories['尾部达人 (1万~10万)'].append(author)
        else:
            categories['素人 (<1万)'].append(author)
        
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
    print(f"\n总 KOL 数: {len(kols)}")
    print(f"\nKOL 分类统计:")
    print("-" * 60)
    
    for category, kol_list in categories.items():
        count = len(kol_list)
        percentage = (count / len(kols) * 100) if kols else 0
        print(f"  {category}: {count} 人 ({percentage:.1f}%)")
    
    print(f"\n粉丝数区间分布:")
    print("-" * 60)
    
    for range_name, count in follower_ranges.items():
        percentage = (count / len(kols) * 100) if kols else 0
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
        waist_kols_sorted = sorted(waist_kols, key=lambda x: int(x.get('attribute_datas', {}).get('follower', '0')), reverse=True)

        # 统计
        follower_counts = [int(kol.get('attribute_datas', {}).get('follower', '0')) for kol in waist_kols]
        avg_followers = sum(follower_counts) / len(follower_counts)
        max_followers = max(follower_counts)
        min_followers = min(follower_counts)

        print(f"\n粉丝数统计:")
        print(f"  平均粉丝数: {avg_followers:,.0f}")
        print(f"  最高粉丝数: {max_followers:,}")
        print(f"  最低粉丝数: {min_followers:,}")

        print(f"\n腰部达人 TOP 10:")
        print("-" * 60)

        for i, kol in enumerate(waist_kols_sorted[:10], 1):
            attr_data = kol.get('attribute_datas', {})
            nickname = attr_data.get('nick_name', 'N/A')
            follower_count = int(attr_data.get('follower', '0'))
            # 解析last_10_items来获取作品数量（近似值）
            last_10_items = attr_data.get('last_10_items', '[]')
            try:
                items = json.loads(last_10_items) if last_10_items else []
                aweme_count = len(items)
            except:
                aweme_count = 0
            star_score = float(attr_data.get('star_index', '0'))
            fans_level = attr_data.get('grade', 'N/A')

            print(f"  {i:2d}. {nickname}")
            print(f"      粉丝: {follower_count:,} | 作品: {aweme_count} | 星图评分: {star_score:.1f} | 等级: {fans_level}")

            # 检查是否有商业报价信息（在新数据结构中可能不存在）
            # 这里暂时跳过价格信息，因为新API结构中可能没有这个字段
    
    # 构建返回结果
    analysis_result = {
        'summary': {
            'total_kols': len(kols),
            'head_kols': len(categories['头部达人 (>=100万)']),
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
            category: kol_list
            for category, kol_list in categories.items()
        }
    }
    
    return analysis_result


def save_results(all_kols: list, analysis: dict, output_dir: str, keyword: str):
    """
    保存搜索结果和分析结果到文件
    
    Args:
        all_kols: 所有 KOL 数据
        analysis: 分析结果
        output_dir: 输出目录
        keyword: 搜索关键词
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. 保存原始搜索结果（3页完整数据）
    raw_data_file = os.path.join(output_dir, f'xingtu_search_results_3pages_{timestamp}.json')
    with open(raw_data_file, 'w', encoding='utf-8') as f:
        json.dump({
            'search_metadata': {
                'keyword': keyword,
                'search_date': datetime.now().isoformat(),
                'total_kols': len(all_kols),
                'api_interface': 'search_kol_v1',
                'api_source': '抖音星图'
            },
            'kols': all_kols
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 原始搜索结果已保存到: {raw_data_file}")
    
    # 2. 保存分析结果
    analysis_file = os.path.join(output_dir, f'xingtu_waist_kol_analysis_{timestamp}.json')
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis_metadata': {
                'keyword': keyword,
                'analysis_date': datetime.now().isoformat(),
                'total_kols': len(all_kols),
                'api_source': '抖音星图'
            },
            'analysis': analysis
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 分析结果已保存到: {analysis_file}")
    
    # 3. 保存腰部达人单独列表（便于查看）
    waist_kols = analysis['categories']['腰部达人 (10万~100万)']
    waist_kol_file = os.path.join(output_dir, f'xingtu_waist_kols_only_{timestamp}.json')
    with open(waist_kol_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'keyword': keyword,
                'date': datetime.now().isoformat(),
                'count': len(waist_kols),
                'api_source': '抖音星图'
            },
            'waist_kols': waist_kols
        }, f, ensure_ascii=False, indent=2)
    
    print(f"💾 腰部达人列表已保存到: {waist_kol_file}")
    
    # 4. 生成简报文件（Markdown 格式）
    report_file = os.path.join(output_dir, f'xingtu_analysis_report_{timestamp}.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 星图护肤达人搜索分析报告\n\n")
        f.write(f"**搜索关键词**: {keyword}\n")
        f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**数据来源**: 抖音星图 KOL 搜索 API (search_kol_v1)\n\n")
        
        f.write(f"## 总体统计\n\n")
        f.write(f"- 总 KOL 数: {analysis['summary']['total_kols']}\n")
        f.write(f"- 头部达人 (>=100万): {analysis['summary']['head_kols']} 人\n")
        f.write(f"- **腰部达人 (10万~100万): {analysis['summary']['waist_kols']} 人**\n")
        f.write(f"- 尾部达人 (1万~10万): {analysis['summary']['tail_kols']} 人\n")
        f.write(f"- 素人 (<1万): {analysis['summary']['normal_users']} 人\n\n")
        
        f.write(f"## 粉丝数区间分布\n\n")
        f.write(f"| 区间 | 数量 | 占比 |\n")
        f.write(f"|------|------|------|\n")
        total = analysis['summary']['total_kols']
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
            f.write(f"| 排名 | 昵称 | 粉丝数 | 作品数 | 星图评分 | 粉丝等级 |\n")
            f.write(f"|------|------|--------|--------|----------|----------|\n")
            
            for i, kol in enumerate(waist_details['top_10'], 1):
                attr_data = kol.get('attribute_datas', {})
                nickname = attr_data.get('nick_name', 'N/A')
                follower_count = int(attr_data.get('follower', '0'))
                # 解析last_10_items来获取作品数量
                last_10_items = attr_data.get('last_10_items', '[]')
                try:
                    items = json.loads(last_10_items) if last_10_items else []
                    aweme_count = len(items)
                except:
                    aweme_count = 0
                star_score = float(attr_data.get('star_index', '0'))
                fans_level = attr_data.get('grade', 'N/A')

                f.write(f"| {i} | {nickname} | {follower_count:,} | {aweme_count} | {star_score:.1f} | {fans_level} |\n")
    
    print(f"💾 分析报告已保存到: {report_file}")
    
    print(f"\n{'='*60}")
    print(f"✅ 所有文件保存完成！")
    print(f"{'='*60}")


def main():
    """主函数：搜索星图护肤达人并分析"""
    
    print("=" * 60)
    print("抖音星图护肤达人搜索与分析工具")
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
    
    # 2. 搜索护肤达人（获取 3 页数据）
    print("\n2️⃣ 开始搜索...")
    keyword = "护肤"  # 使用简短关键词，星图搜索可能不支持太长的关键词
    page_count = 3
    count_per_page = 20  # 星图 API 建议每页 20 条
    
    # 设置输出目录
    script_dir = Path(__file__).parent.parent  # backend/test/kol/xingtu-searchkol/
    output_dir = script_dir / "output"
    
    all_kols = fetch_multiple_pages(api_key, keyword, page_count, count_per_page, str(output_dir))
    
    if not all_kols:
        print("❌ 未获取到任何 KOL 数据")
        return
    
    # 3. 分析达人分布
    print("\n3️⃣ 分析达人分布...")
    analysis = analyze_kol_distribution(all_kols)
    
    # 4. 保存结果
    print("\n4️⃣ 保存结果...")
    save_results(all_kols, analysis, str(output_dir), keyword)
    
    print("\n✅ 全部完成！")
    print(f"\n📌 关键发现:")
    print(f"   搜索关键词: {keyword}")
    print(f"   总 KOL 数: {len(all_kols)}")
    print(f"   腰部达人数: {analysis['summary']['waist_kols']} 人")
    if len(all_kols) > 0:
        print(f"   腰部达人占比: {(analysis['summary']['waist_kols'] / len(all_kols) * 100):.1f}%")


if __name__ == "__main__":
    main()

