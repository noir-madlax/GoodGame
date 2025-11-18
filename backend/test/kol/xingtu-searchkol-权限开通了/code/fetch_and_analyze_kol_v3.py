#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音星图护肤达人搜索与结构化分析脚本 V3

功能：
1. 调用 TikHub API 的星图 search_kol_v1 接口搜索"护肤达人"
2. 支持自定义页数和起始页，跳过已下载的页面
3. 结构化解析关键业务数据
4. 合并所有页面数据并生成详细分析报告

接口文档: https://api.tikhub.io/#/Douyin-Xingtu-API/search_kol_v1_api_v1_douyin_xingtu_search_kol_v1_get
"""

import os
import json
import requests
import time
import glob
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any, Tuple
from collections import Counter


def load_api_key():
    """从环境变量加载 TikHub API Key"""
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 从 {env_path} 加载环境变量")
    else:
        print(f"⚠️ 未找到 .env 文件: {env_path}")
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    
    return api_key


def get_existing_pages(output_dir: str) -> List[int]:
    """
    检查已存在的页面文件
    
    Args:
        output_dir: 输出目录
        
    Returns:
        list: 已存在的页码列表
    """
    detail_dir = os.path.join(output_dir, 'detail')
    if not os.path.exists(detail_dir):
        return []
    
    # 查找所有 raw_page_*.json 文件
    pattern = os.path.join(detail_dir, 'raw_page_*.json')
    existing_files = glob.glob(pattern)
    
    existing_pages = []
    for filepath in existing_files:
        filename = os.path.basename(filepath)
        # 提取页码：raw_page_1_20251118_113605.json -> 1
        parts = filename.split('_')
        if len(parts) >= 3 and parts[0] == 'raw' and parts[1] == 'page':
            try:
                page_num = int(parts[2])
                existing_pages.append(page_num)
            except ValueError:
                continue
    
    return sorted(existing_pages)


def fetch_kol_page(api_key: str, keyword: str, page: int, count: int = 20) -> Dict[str, Any]:
    """调用 TikHub API 获取一页 KOL 数据"""
    url = "https://api.tikhub.io/api/v1/douyin/xingtu/search_kol_v1"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    params = {
        'keyword': keyword,
        'page': page,
        'count': count,
        'sort_type': 1,
        'platformSource': '_1'
    }
    
    print(f"\n📡 发送请求: 第 {page} 页...")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            code = result.get('code', -1)
            
            if code == 200:
                data = result.get('data', {})
                authors = data.get('authors', [])
                print(f"   ✅ 成功获取 {len(authors)} 个达人")
                return result
            else:
                print(f"   ❌ API 返回错误码: {code}")
                return result
        else:
            print(f"   ❌ HTTP 请求失败: {response.status_code}")
            return {"error": f"HTTP {response.status_code}", "message": response.text}
            
    except Exception as e:
        print(f"   ❌ 请求异常: {str(e)}")
        return {"error": str(e)}


def parse_kol_data(author: Dict[str, Any]) -> Dict[str, Any]:
    """解析单个达人的关键业务数据"""
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
    
    # 构建关键业务数据
    kol_data = {
        '达人ID': author.get('star_id', ''),
        '昵称': attr_data.get('nick_name', ''),
        '头像': attr_data.get('avatar_uri', ''),
        '性别': '女' if attr_data.get('gender', '') == '2' else '男' if attr_data.get('gender', '') == '1' else '未知',
        '地区': f"{attr_data.get('province', '')} {attr_data.get('city', '')}".strip(),
        '粉丝数': int(attr_data.get('follower', 0)),
        '15天粉丝增量': int(attr_data.get('fans_increment_within_15d', 0)),
        '30天粉丝增量': attr_data.get('fans_increment_within_30d', '0'),
        '15天粉丝增长率': float(attr_data.get('fans_increment_rate_within_15d', 0)),
        '星图评分': float(attr_data.get('star_index', 0)),
        '粉丝等级': attr_data.get('grade', '0'),
        '达人类型': '个人' if attr_data.get('author_type', '') == '1' else '机构' if attr_data.get('author_type', '') == '2' else '未知',
        '账号状态': '正常' if attr_data.get('author_status', '') == '1' else '异常',
        '内容标签': tags_relation,
        '近期作品数': item_count,
        '平均播放量': avg_vv,
        '平均点赞数': avg_like,
        '平均评论数': avg_comment,
        '平均分享数': avg_share,
        '互动率': round((avg_like + avg_comment + avg_share) / avg_vv * 100, 2) if avg_vv > 0 else 0,
        '电商等级': attr_data.get('author_ecom_level', ''),
        '电商启用': attr_data.get('e_commerce_enable', '0') == '1',
        '30天带货视频数': int(attr_data.get('ecom_video_product_num_30d', 0)),
        '30天带货GMV区间': attr_data.get('ecom_gmv_30d_range', ''),
        '30天平均客单价区间': attr_data.get('ecom_avg_order_value_30d_range', ''),
        '1-20秒视频报价': int(attr_data.get('price_1_20', 0)),
        '20-60秒视频报价': int(attr_data.get('price_20_60', 0)),
        '60秒以上视频报价': int(attr_data.get('price_60', 0)),
        '预估播放量': int(attr_data.get('expected_play_num', 0)),
        '预估自然播放量': int(attr_data.get('expected_natural_play_num', 0)),
        '是否黑马达人': attr_data.get('is_black_horse_author', 'false') == 'true',
        '是否优质达人': attr_data.get('is_excellenct_author', '0') == '1',
        '是否短剧达人': attr_data.get('is_short_drama', '0') == '1',
        '是否支持共创': attr_data.get('is_cocreate_author', 'false') == 'true',
    }
    
    return kol_data


def save_raw_response(response_data: Dict[str, Any], page: int, output_dir: str):
    """保存原始 API 响应到 detail 目录"""
    detail_dir = os.path.join(output_dir, 'detail')
    os.makedirs(detail_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'raw_page_{page}_{timestamp}.json'
    filepath = os.path.join(detail_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)
    
    print(f"   💾 已保存: {filename}")


def load_all_pages_data(output_dir: str) -> Tuple[List[Dict], List[int]]:
    """
    加载所有已保存的页面数据
    
    Returns:
        tuple: (所有页面的原始数据列表, 页码列表)
    """
    detail_dir = os.path.join(output_dir, 'detail')
    pattern = os.path.join(detail_dir, 'raw_page_*.json')
    existing_files = glob.glob(pattern)
    
    # 按页码排序
    page_data_map = {}
    for filepath in existing_files:
        filename = os.path.basename(filepath)
        parts = filename.split('_')
        if len(parts) >= 3:
            try:
                page_num = int(parts[2])
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    page_data_map[page_num] = data
            except (ValueError, json.JSONDecodeError):
                continue
    
    # 按页码排序
    sorted_pages = sorted(page_data_map.keys())
    all_pages_data = [page_data_map[page] for page in sorted_pages]
    
    return all_pages_data, sorted_pages


def generate_detailed_analysis(all_parsed_kols: List[Dict], total_pages: int, output_dir: str):
    """生成详细的数据分析报告"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print(f"\n{'='*80}")
    print(f"📊 开始生成详细数据分析")
    print(f"{'='*80}")
    
    total_count = len(all_parsed_kols)
    
    # ========== 1. 粉丝数分析 ==========
    follower_counts = [kol['粉丝数'] for kol in all_parsed_kols]
    avg_followers = sum(follower_counts) // len(follower_counts) if follower_counts else 0
    max_followers = max(follower_counts) if follower_counts else 0
    min_followers = min(follower_counts) if follower_counts else 0
    median_followers = sorted(follower_counts)[len(follower_counts)//2] if follower_counts else 0
    
    # 粉丝数区间分布
    follower_ranges = {
        '0-1万': 0, '1-5万': 0, '5-10万': 0, '10-20万': 0,
        '20-50万': 0, '50-100万': 0, '100-200万': 0, '200-500万': 0,
        '500-1000万': 0, '1000万+': 0
    }
    
    for count in follower_counts:
        if count < 10000:
            follower_ranges['0-1万'] += 1
        elif count < 50000:
            follower_ranges['1-5万'] += 1
        elif count < 100000:
            follower_ranges['5-10万'] += 1
        elif count < 200000:
            follower_ranges['10-20万'] += 1
        elif count < 500000:
            follower_ranges['20-50万'] += 1
        elif count < 1000000:
            follower_ranges['50-100万'] += 1
        elif count < 2000000:
            follower_ranges['100-200万'] += 1
        elif count < 5000000:
            follower_ranges['200-500万'] += 1
        elif count < 10000000:
            follower_ranges['500-1000万'] += 1
        else:
            follower_ranges['1000万+'] += 1
    
    # ========== 2. 星图评分分析 ==========
    star_scores = [kol['星图评分'] for kol in all_parsed_kols if kol['星图评分'] > 0]
    avg_star_score = sum(star_scores) / len(star_scores) if star_scores else 0
    max_star_score = max(star_scores) if star_scores else 0
    min_star_score = min(star_scores) if star_scores else 0
    
    # 星图评分区间分布
    star_ranges = {
        '0-40分': 0, '40-50分': 0, '50-60分': 0,
        '60-70分': 0, '70-80分': 0, '80-90分': 0, '90-100分': 0
    }
    
    for score in star_scores:
        if score < 40:
            star_ranges['0-40分'] += 1
        elif score < 50:
            star_ranges['40-50分'] += 1
        elif score < 60:
            star_ranges['50-60分'] += 1
        elif score < 70:
            star_ranges['60-70分'] += 1
        elif score < 80:
            star_ranges['70-80分'] += 1
        elif score < 90:
            star_ranges['80-90分'] += 1
        else:
            star_ranges['90-100分'] += 1
    
    # ========== 3. 互动率分析 ==========
    interaction_rates = [kol['互动率'] for kol in all_parsed_kols if kol['互动率'] > 0]
    avg_interaction_rate = sum(interaction_rates) / len(interaction_rates) if interaction_rates else 0
    max_interaction_rate = max(interaction_rates) if interaction_rates else 0
    min_interaction_rate = min(interaction_rates) if interaction_rates else 0
    
    # 互动率区间分布
    interaction_ranges = {
        '0-1%': 0, '1-3%': 0, '3-5%': 0, '5-10%': 0, '10%+': 0
    }
    
    for rate in interaction_rates:
        if rate < 1:
            interaction_ranges['0-1%'] += 1
        elif rate < 3:
            interaction_ranges['1-3%'] += 1
        elif rate < 5:
            interaction_ranges['3-5%'] += 1
        elif rate < 10:
            interaction_ranges['5-10%'] += 1
        else:
            interaction_ranges['10%+'] += 1
    
    # ========== 4. 报价分析 ==========
    prices_20_60 = [kol['20-60秒视频报价'] for kol in all_parsed_kols if kol['20-60秒视频报价'] > 0]
    avg_price = sum(prices_20_60) // len(prices_20_60) if prices_20_60 else 0
    max_price = max(prices_20_60) if prices_20_60 else 0
    min_price = min(prices_20_60) if prices_20_60 else 0
    
    # 报价区间分布
    price_ranges = {
        '0-1万': 0, '1-3万': 0, '3-5万': 0, '5-10万': 0,
        '10-20万': 0, '20-50万': 0, '50万+': 0
    }
    
    for price in prices_20_60:
        if price < 10000:
            price_ranges['0-1万'] += 1
        elif price < 30000:
            price_ranges['1-3万'] += 1
        elif price < 50000:
            price_ranges['3-5万'] += 1
        elif price < 100000:
            price_ranges['5-10万'] += 1
        elif price < 200000:
            price_ranges['10-20万'] += 1
        elif price < 500000:
            price_ranges['20-50万'] += 1
        else:
            price_ranges['50万+'] += 1
    
    # ========== 5. 内容标签统计 ==========
    all_tags = []
    for kol in all_parsed_kols:
        tags = kol['内容标签']
        if isinstance(tags, dict):
            for category, sub_tags in tags.items():
                all_tags.append(category)
                if isinstance(sub_tags, list):
                    all_tags.extend(sub_tags)
    
    tag_counter = Counter(all_tags)
    top_10_tags = tag_counter.most_common(10)
    
    # ========== 6. 地区分布 ==========
    provinces = [kol['地区'].split()[0] if kol['地区'] else '未知' for kol in all_parsed_kols]
    province_counter = Counter(provinces)
    top_10_provinces = province_counter.most_common(10)
    
    # ========== 7. 性别分布 ==========
    genders = [kol['性别'] for kol in all_parsed_kols]
    gender_counter = Counter(genders)
    
    # ========== 8. 达人类型分布 ==========
    types = [kol['达人类型'] for kol in all_parsed_kols]
    type_counter = Counter(types)
    
    # ========== 9. 电商数据分析 ==========
    ecom_enabled_count = sum(1 for kol in all_parsed_kols if kol['电商启用'])
    ecom_gmv_ranges = [kol['30天带货GMV区间'] for kol in all_parsed_kols if kol['30天带货GMV区间']]
    gmv_counter = Counter(ecom_gmv_ranges)
    
    # ========== 10. 特殊标记统计 ==========
    black_horse_count = sum(1 for kol in all_parsed_kols if kol['是否黑马达人'])
    excellent_count = sum(1 for kol in all_parsed_kols if kol['是否优质达人'])
    short_drama_count = sum(1 for kol in all_parsed_kols if kol['是否短剧达人'])
    cocreate_count = sum(1 for kol in all_parsed_kols if kol['是否支持共创'])
    
    # ========== 生成分析报告 ==========
    report_content = f"""# 抖音星图护肤达人数据分析报告

## 📊 数据概览

- **搜索关键词**: 护肤保养
- **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **数据页数**: {total_pages} 页
- **总达人数**: {total_count} 个
- **数据来源**: 抖音星图 KOL 搜索 API (search_kol_v1)

---

## 一、粉丝数据分析

### 1.1 粉丝数统计

| 指标 | 数值 |
|------|------|
| 平均粉丝数 | {avg_followers:,} |
| 中位数粉丝数 | {median_followers:,} |
| 最高粉丝数 | {max_followers:,} |
| 最低粉丝数 | {min_followers:,} |
| 粉丝总数 | {sum(follower_counts):,} |

### 1.2 粉丝数区间分布

| 区间 | 数量 | 占比 | 可视化 |
|------|------|------|--------|
"""
    
    for range_name, count in follower_ranges.items():
        percentage = (count / total_count * 100) if total_count > 0 else 0
        bar = '█' * int(percentage / 2)
        report_content += f"| {range_name} | {count} | {percentage:.1f}% | {bar} |\n"
    
    report_content += f"""
### 1.3 粉丝增长分析

| 指标 | 数值 |
|------|------|
| 平均15天粉丝增量 | {sum(kol['15天粉丝增量'] for kol in all_parsed_kols) // total_count:,} |
| 平均15天增长率 | {sum(kol['15天粉丝增长率'] for kol in all_parsed_kols) / total_count * 100:.2f}% |
| 增长达人数 | {sum(1 for kol in all_parsed_kols if kol['15天粉丝增量'] > 0)} |
| 下降达人数 | {sum(1 for kol in all_parsed_kols if kol['15天粉丝增量'] < 0)} |

---

## 二、星图评分分析

### 2.1 评分统计

| 指标 | 数值 |
|------|------|
| 平均星图评分 | {avg_star_score:.2f} |
| 最高星图评分 | {max_star_score:.2f} |
| 最低星图评分 | {min_star_score:.2f} |
| 有评分达人数 | {len(star_scores)} |

### 2.2 评分区间分布

| 区间 | 数量 | 占比 | 可视化 |
|------|------|------|--------|
"""
    
    for range_name, count in star_ranges.items():
        percentage = (count / len(star_scores) * 100) if star_scores else 0
        bar = '█' * int(percentage / 2)
        report_content += f"| {range_name} | {count} | {percentage:.1f}% | {bar} |\n"
    
    report_content += f"""
---

## 三、内容互动分析

### 3.1 互动率统计

| 指标 | 数值 |
|------|------|
| 平均互动率 | {avg_interaction_rate:.2f}% |
| 最高互动率 | {max_interaction_rate:.2f}% |
| 最低互动率 | {min_interaction_rate:.2f}% |
| 有互动数据达人数 | {len(interaction_rates)} |

### 3.2 互动率区间分布

| 区间 | 数量 | 占比 | 可视化 |
|------|------|------|--------|
"""
    
    for range_name, count in interaction_ranges.items():
        percentage = (count / len(interaction_rates) * 100) if interaction_rates else 0
        bar = '█' * int(percentage / 2)
        report_content += f"| {range_name} | {count} | {percentage:.1f}% | {bar} |\n"
    
    report_content += f"""
### 3.3 作品数据统计

| 指标 | 数值 |
|------|------|
| 平均播放量 | {sum(kol['平均播放量'] for kol in all_parsed_kols) // total_count:,} |
| 平均点赞数 | {sum(kol['平均点赞数'] for kol in all_parsed_kols) // total_count:,} |
| 平均评论数 | {sum(kol['平均评论数'] for kol in all_parsed_kols) // total_count:,} |
| 平均分享数 | {sum(kol['平均分享数'] for kol in all_parsed_kols) // total_count:,} |

---

## 四、商业报价分析

### 4.1 报价统计（20-60秒视频）

| 指标 | 数值 |
|------|------|
| 平均报价 | {avg_price:,} 元 |
| 最高报价 | {max_price:,} 元 |
| 最低报价 | {min_price:,} 元 |
| 有报价达人数 | {len(prices_20_60)} |
| 无报价达人数 | {total_count - len(prices_20_60)} |

### 4.2 报价区间分布

| 区间 | 数量 | 占比 | 可视化 |
|------|------|------|--------|
"""
    
    for range_name, count in price_ranges.items():
        percentage = (count / len(prices_20_60) * 100) if prices_20_60 else 0
        bar = '█' * int(percentage / 2)
        report_content += f"| {range_name} | {count} | {percentage:.1f}% | {bar} |\n"
    
    report_content += f"""
---

## 五、内容标签分析

### 5.1 TOP 10 热门标签

| 排名 | 标签 | 出现次数 |
|------|------|----------|
"""
    
    for i, (tag, count) in enumerate(top_10_tags, 1):
        report_content += f"| {i} | {tag} | {count} |\n"
    
    report_content += f"""
---

## 六、地区分布分析

### 6.1 TOP 10 省份/城市

| 排名 | 地区 | 达人数 | 占比 |
|------|------|--------|------|
"""
    
    for i, (province, count) in enumerate(top_10_provinces, 1):
        percentage = (count / total_count * 100) if total_count > 0 else 0
        report_content += f"| {i} | {province} | {count} | {percentage:.1f}% |\n"
    
    report_content += f"""
---

## 七、达人属性分析

### 7.1 性别分布

| 性别 | 数量 | 占比 |
|------|------|------|
"""
    
    for gender, count in gender_counter.items():
        percentage = (count / total_count * 100) if total_count > 0 else 0
        report_content += f"| {gender} | {count} | {percentage:.1f}% |\n"
    
    report_content += f"""
### 7.2 达人类型分布

| 类型 | 数量 | 占比 |
|------|------|------|
"""
    
    for type_name, count in type_counter.items():
        percentage = (count / total_count * 100) if total_count > 0 else 0
        report_content += f"| {type_name} | {count} | {percentage:.1f}% |\n"
    
    report_content += f"""
---

## 八、电商能力分析

### 8.1 电商启用情况

| 指标 | 数值 |
|------|------|
| 开通电商达人数 | {ecom_enabled_count} |
| 电商开通率 | {(ecom_enabled_count / total_count * 100):.1f}% |
| 未开通电商达人数 | {total_count - ecom_enabled_count} |

### 8.2 30天带货GMV区间分布

| GMV区间 | 数量 |
|----------|------|
"""
    
    for gmv_range, count in gmv_counter.most_common():
        report_content += f"| {gmv_range} | {count} |\n"
    
    report_content += f"""
---

## 九、特殊标记统计

| 标记类型 | 数量 | 占比 |
|----------|------|------|
| 黑马达人 | {black_horse_count} | {(black_horse_count / total_count * 100):.1f}% |
| 优质达人 | {excellent_count} | {(excellent_count / total_count * 100):.1f}% |
| 短剧达人 | {short_drama_count} | {(short_drama_count / total_count * 100):.1f}% |
| 支持共创 | {cocreate_count} | {(cocreate_count / total_count * 100):.1f}% |

---

## 十、TOP 20 护肤达人榜单

### 10.1 按粉丝数排名

| 排名 | 昵称 | 粉丝数 | 星图评分 | 互动率 | 20-60秒报价 |
|------|------|--------|----------|--------|-------------|
"""
    
    sorted_by_followers = sorted(all_parsed_kols, key=lambda x: x['粉丝数'], reverse=True)
    for i, kol in enumerate(sorted_by_followers[:20], 1):
        report_content += f"| {i} | {kol['昵称']} | {kol['粉丝数']:,} | {kol['星图评分']:.2f} | {kol['互动率']}% | {kol['20-60秒视频报价']:,} 元 |\n"
    
    report_content += f"""
### 10.2 按星图评分排名

| 排名 | 昵称 | 星图评分 | 粉丝数 | 互动率 | 20-60秒报价 |
|------|------|----------|--------|--------|-------------|
"""
    
    sorted_by_star = sorted(all_parsed_kols, key=lambda x: x['星图评分'], reverse=True)
    for i, kol in enumerate(sorted_by_star[:20], 1):
        report_content += f"| {i} | {kol['昵称']} | {kol['星图评分']:.2f} | {kol['粉丝数']:,} | {kol['互动率']}% | {kol['20-60秒视频报价']:,} 元 |\n"
    
    report_content += f"""
### 10.3 按互动率排名

| 排名 | 昵称 | 互动率 | 粉丝数 | 星图评分 | 20-60秒报价 |
|------|------|--------|--------|----------|-------------|
"""
    
    sorted_by_interaction = sorted(all_parsed_kols, key=lambda x: x['互动率'], reverse=True)
    for i, kol in enumerate(sorted_by_interaction[:20], 1):
        report_content += f"| {i} | {kol['昵称']} | {kol['互动率']}% | {kol['粉丝数']:,} | {kol['星图评分']:.2f} | {kol['20-60秒视频报价']:,} 元 |\n"
    
    report_content += f"""
---

## 十一、性价比分析

### 11.1 高性价比达人（综合评分 = 星图评分 × 互动率 / 报价）

| 排名 | 昵称 | 粉丝数 | 星图评分 | 互动率 | 20-60秒报价 | 性价比指数 |
|------|------|--------|----------|--------|-------------|-----------|
"""
    
    # 计算性价比（星图评分 × 互动率 / 报价，报价为0的跳过）
    kols_with_price = [kol for kol in all_parsed_kols if kol['20-60秒视频报价'] > 0 and kol['星图评分'] > 0]
    for kol in kols_with_price:
        kol['性价比指数'] = (kol['星图评分'] * kol['互动率']) / (kol['20-60秒视频报价'] / 1000)
    
    sorted_by_value = sorted(kols_with_price, key=lambda x: x['性价比指数'], reverse=True)
    for i, kol in enumerate(sorted_by_value[:20], 1):
        report_content += f"| {i} | {kol['昵称']} | {kol['粉丝数']:,} | {kol['星图评分']:.2f} | {kol['互动率']}% | {kol['20-60秒视频报价']:,} 元 | {kol['性价比指数']:.4f} |\n"
    
    report_content += f"""
---

## 十二、数据洞察与建议

### 12.1 市场洞察

1. **粉丝分布**: 主要集中在 {max(follower_ranges, key=follower_ranges.get)} 区间，占比 {max(follower_ranges.values()) / total_count * 100:.1f}%
2. **星图评分**: 平均评分 {avg_star_score:.2f}，大部分达人在 50-70 分区间
3. **互动情况**: 平均互动率 {avg_interaction_rate:.2f}%，高互动率（>5%）达人占比 {sum(1 for r in interaction_rates if r > 5) / len(interaction_rates) * 100:.1f}%
4. **商业价值**: 平均报价 {avg_price:,} 元，报价差异较大反映出市场分层明显

### 12.2 选择建议

#### 预算充足（10万+）
- 关注：粉丝 100万+ 且星图评分 70+ 的达人
- 优势：品牌影响力大，曝光量高
- 代表：{sorted_by_followers[0]['昵称']}、{sorted_by_followers[1]['昵称']} 等

#### 预算中等（3-10万）
- 关注：粉丝 20-100万，互动率 >3% 的达人
- 优势：性价比高，用户粘性好
- 建议：选择星图评分 60+ 的达人

#### 预算有限（3万以下）
- 关注：粉丝 10-50万，高互动率（>5%）达人
- 优势：精准触达，转化率可能更高
- 建议：优先选择垂直领域深耕的达人

### 12.3 投放策略

1. **多达人组合**: 头部（1-2个）+ 腰部（3-5个）+ 尾部（5-10个）
2. **测试优化**: 先小规模测试，根据数据优化达人选择
3. **内容共创**: 优先选择支持共创的达人（{cocreate_count} 个）
4. **电商带货**: 如需带货，选择已开通电商的达人（{ecom_enabled_count} 个）

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**数据有效期**: 24小时（API缓存）  
**数据来源**: 抖音星图 KOL 搜索 API
"""
    
    # 保存报告
    report_file = os.path.join(output_dir, f'数据分析总结_{timestamp}.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n💾 详细分析报告已保存: {report_file}")
    
    return report_file


def main():
    """主函数：获取多页数据并生成详细分析"""
    
    print("=" * 80)
    print("抖音星图护肤达人搜索与结构化分析工具 V3")
    print("=" * 80)
    
    # 参数配置
    KEYWORD = "护肤保养"
    TOTAL_PAGES = 28  # 总共要获取的页数
    COUNT_PER_PAGE = 20
    
    # 1. 加载 API Key
    print("\n1️⃣ 加载 API 配置...")
    try:
        api_key = load_api_key()
        print(f"✅ API Key 已加载")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # 2. 设置输出目录
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "output" / "keyword_护肤保养"
    
    # 3. 检查已存在的页面
    print(f"\n2️⃣ 检查已下载的页面...")
    existing_pages = get_existing_pages(str(output_dir))
    
    if existing_pages:
        print(f"✅ 发现已下载的页面: {existing_pages}")
        print(f"   共 {len(existing_pages)} 页")
    else:
        print(f"   未发现已下载的页面")
    
    # 4. 确定需要下载的页面
    pages_to_fetch = [p for p in range(1, TOTAL_PAGES + 1) if p not in existing_pages]
    
    if pages_to_fetch:
        print(f"\n3️⃣ 开始获取新页面...")
        print(f"   需要获取: 第 {pages_to_fetch[0]} - {pages_to_fetch[-1]} 页，共 {len(pages_to_fetch)} 页")
        
        for page in pages_to_fetch:
            print(f"\n{'='*80}")
            print(f"第 {page}/{TOTAL_PAGES} 页")
            print(f"{'='*80}")
            
            # 获取数据
            response_data = fetch_kol_page(api_key, KEYWORD, page, COUNT_PER_PAGE)
            
            # 检查是否成功
            if 'error' in response_data or response_data.get('code') != 200:
                print(f"⚠️ 第 {page} 页获取失败")
                continue
            
            # 保存原始返回
            save_raw_response(response_data, page, str(output_dir))
            
            # 添加延迟
            if page < pages_to_fetch[-1]:
                print(f"   ⏳ 等待 1 秒...")
                time.sleep(1)
    else:
        print(f"\n3️⃣ 所有页面已下载完成，无需重新获取")
    
    # 5. 加载所有页面数据
    print(f"\n4️⃣ 加载所有页面数据...")
    all_pages_data, loaded_pages = load_all_pages_data(str(output_dir))
    
    print(f"✅ 成功加载 {len(all_pages_data)} 页数据")
    print(f"   页码: {loaded_pages}")
    
    # 6. 解析所有达人数据
    print(f"\n5️⃣ 解析达人数据...")
    all_parsed_kols = []
    
    for page_data in all_pages_data:
        data = page_data.get('data', {})
        authors = data.get('authors', [])
        
        for author in authors:
            parsed_kol = parse_kol_data(author)
            all_parsed_kols.append(parsed_kol)
    
    print(f"✅ 成功解析 {len(all_parsed_kols)} 个达人")
    
    # 7. 检查重复
    all_ids = [kol['达人ID'] for kol in all_parsed_kols]
    unique_ids = set(all_ids)
    duplicate_count = len(all_ids) - len(unique_ids)
    
    print(f"\n6️⃣ 数据重复检查...")
    print(f"   总达人数: {len(all_ids)}")
    print(f"   唯一达人数: {len(unique_ids)}")
    print(f"   重复达人数: {duplicate_count}")
    
    if duplicate_count == 0:
        print(f"   ✅ 无重复数据")
    else:
        print(f"   ⚠️ 发现 {duplicate_count} 个重复达人")
    
    # 8. 保存完整的解析数据
    print(f"\n7️⃣ 保存完整数据...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    detail_dir = os.path.join(output_dir, 'detail')
    parsed_file = os.path.join(detail_dir, f'parsed_kol_data_all_{timestamp}.json')
    
    output_data = {
        '说明': {
            '数据来源': '抖音星图 KOL 搜索 API (search_kol_v1)',
            '搜索关键词': KEYWORD,
            '获取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '数据页数': len(loaded_pages),
            '页码列表': loaded_pages,
            '总达人数': len(all_parsed_kols),
            '唯一达人数': len(unique_ids),
            '重复达人数': duplicate_count
        },
        '达人数据': all_parsed_kols
    }
    
    with open(parsed_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 完整数据已保存: {parsed_file}")
    
    # 9. 生成详细分析报告
    print(f"\n8️⃣ 生成详细分析报告...")
    generate_detailed_analysis(all_parsed_kols, len(loaded_pages), str(output_dir))
    
    print(f"\n{'='*80}")
    print(f"✅ 全部完成！")
    print(f"{'='*80}")
    print(f"\n📊 数据概览:")
    print(f"   总页数: {len(loaded_pages)}")
    print(f"   总达人数: {len(all_parsed_kols)}")
    print(f"   唯一达人数: {len(unique_ids)}")


if __name__ == "__main__":
    main()

