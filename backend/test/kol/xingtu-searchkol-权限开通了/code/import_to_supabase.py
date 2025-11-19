#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
星图KOL数据导入Supabase脚本
从新接口 search_kol_v1 的返回数据导入到数据库

使用方法:
    python import_to_supabase.py

依赖:
    pip install python-dotenv supabase
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# 加载环境变量
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / '.env')

# Supabase配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("错误: 未找到SUPABASE_URL或SUPABASE_KEY环境变量")
    sys.exit(1)

# 创建Supabase客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数"""
    if value is None or value == '':
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """安全转换为布尔值"""
    if value is None or value == '':
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes')
    return bool(value)


def parse_json_field(value: Any) -> Optional[Dict]:
    """解析JSON字符串字段"""
    if value is None or value == '':
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def timestamp_to_datetime(ts: Any) -> Optional[datetime]:
    """时间戳转datetime"""
    if ts is None or ts == '':
        return None
    try:
        ts_int = int(float(str(ts)))
        return datetime.fromtimestamp(ts_int)
    except (ValueError, TypeError, OSError):
        return None


def parse_kol_base_info(author: Dict, fetch_date: datetime) -> Dict:
    """
    解析KOL基础信息
    从author的attribute_datas中提取字段
    """
    attr = author.get('attribute_datas', {})
    
    # 解析内容标签
    tags_relation = parse_json_field(attr.get('tags_relation'))
    content_theme_labels_str = attr.get('content_theme_labels_180d', '[]')
    content_theme_labels = parse_json_field(content_theme_labels_str)
    
    # 解析last_10_items统计平均值
    last_10_items_str = attr.get('last_10_items', '[]')
    last_10_items = parse_json_field(last_10_items_str) or []
    
    recent_works_count = len(last_10_items)
    avg_play = 0
    avg_like = 0
    avg_comment = 0
    avg_share = 0
    
    if last_10_items:
        total_vv = sum(safe_int(item.get('vv')) for item in last_10_items)
        total_like = sum(safe_int(item.get('like_cnt')) for item in last_10_items)
        total_comment = sum(safe_int(item.get('comment_cnt')) for item in last_10_items)
        total_share = sum(safe_int(item.get('share_cnt')) for item in last_10_items)
        
        avg_play = total_vv // recent_works_count if recent_works_count > 0 else 0
        avg_like = total_like // recent_works_count if recent_works_count > 0 else 0
        avg_comment = total_comment // recent_works_count if recent_works_count > 0 else 0
        avg_share = total_share // recent_works_count if recent_works_count > 0 else 0
    
    return {
        'kol_id': attr.get('id') or author.get('star_id'),  # 使用id或star_id
        'kol_name': attr.get('nick_name'),
        'kol_avatar': attr.get('avatar_uri'),
        'fans_count': safe_int(attr.get('follower')),
        'aweme_count': None,  # 新接口没有直接提供
        'vertical_category': None,  # 新接口没有直接提供
        'tags': None,  # 暂不处理tags数组
        
        # 互动数据
        'interact_rate_30d': safe_float(attr.get('interact_rate_within_30d')),
        'interaction_median_30d': safe_int(attr.get('interaction_median_30d')),
        'vv_median_30d': safe_int(attr.get('vv_median_30d')),
        'play_over_rate_30d': safe_float(attr.get('play_over_rate_within_30d')),
        
        # 粉丝增长
        'fans_increment_15d': safe_int(attr.get('fans_increment_within_15d')),
        'fans_increment_30d': safe_float(attr.get('fans_increment_within_30d')),
        'fans_increment_rate_15d': safe_float(attr.get('fans_increment_rate_within_15d')),
        
        # 预估数据
        'expected_play_num': safe_int(attr.get('expected_play_num')),
        'expected_natural_play_num': safe_int(attr.get('expected_natural_play_num')),
        
        # 星图评分
        'star_index': safe_float(attr.get('star_index')),
        'link_shopping_index': safe_float(attr.get('link_shopping_index') or attr.get('link_recommend_index_by_industry')),
        'link_convert_index': safe_float(attr.get('link_convert_index')),
        'link_spread_index': safe_float(attr.get('link_spread_index')),
        'link_star_index': safe_float(attr.get('link_star_index')),
        
        # 特殊标记
        'is_black_horse': safe_bool(attr.get('is_black_horse_author')),
        'is_excellent': safe_bool(attr.get('is_excellenct_author')),
        'is_cocreate': safe_bool(attr.get('is_cocreate_author')),
        'is_short_drama': safe_bool(attr.get('is_short_drama')),
        
        # 电商能力基础
        'ecom_level': attr.get('author_ecom_level'),
        'ecom_enabled': safe_bool(attr.get('e_commerce_enable')),
        
        # 内容标签
        'content_tags': tags_relation,
        'content_theme_labels': content_theme_labels,
        
        # 地理位置
        'province': attr.get('province') or None,
        'city': attr.get('city') or None,
        'gender': safe_int(attr.get('gender')) if attr.get('gender') else None,
        
        # 达人类型
        'author_type': safe_int(attr.get('author_type')) if attr.get('author_type') else None,
        'account_status': safe_int(attr.get('author_status')) if attr.get('author_status') else None,
        
        # 近期作品统计
        'recent_works_count': recent_works_count,
        'avg_play_count': avg_play,
        'avg_like_count': avg_like,
        'avg_comment_count': avg_comment,
        'avg_share_count': avg_share,
        
        # 元数据
        'raw_data': author,  # 保存完整原始数据
        'fetch_date': fetch_date.isoformat(),  # 转换为ISO格式字符串
    }


def parse_kol_price(author: Dict, fetch_date: datetime) -> Dict:
    """
    解析KOL报价信息
    从attribute_datas和task_infos中提取
    """
    attr = author.get('attribute_datas', {})
    task_infos = author.get('task_infos', [])
    
    # 基础报价字段 (从attribute_datas)
    price_data = {
        'kol_id': attr.get('id') or author.get('star_id'),
        'video_1_20s_price': safe_int(attr.get('price_1_20')),
        'video_21_60s_price': safe_int(attr.get('price_20_60')),
        'video_60s_plus_price': safe_int(attr.get('price_60')),
        
        # 预估CPM
        'prospective_cpm_1_20s': safe_float(attr.get('prospective_1_20_cpm')),
        'prospective_cpm_20_60s': safe_float(attr.get('prospective_20_60_cpm')),
        'prospective_cpm_60s_plus': safe_float(attr.get('prospective_60_cpm')),
        
        # 预估CPE
        'prospective_cpe_1_20s': safe_float(attr.get('sn_prospective_1_20_cpe')),
        'prospective_cpe_20_60s': safe_float(attr.get('sn_prospective_20_60_cpe')),
        'prospective_cpe_60s_plus': safe_float(attr.get('sn_prospective_60_cpe')),
        
        'fetch_date': fetch_date.isoformat(),  # 转换为ISO格式字符串
        'raw_data': {'attribute_datas': attr, 'task_infos': task_infos},
    }
    
    # 从task_infos中提取价格历史和范围信息
    # 找20-60秒视频的price_extra_info
    for task_info in task_infos:
        price_infos = task_info.get('price_infos', [])
        for price_info in price_infos:
            video_type = price_info.get('video_type')
            if video_type == 2:  # 20-60秒
                extra_info = price_info.get('price_extra_info', {})
                price_data['price_last_month_20_60s'] = safe_int(extra_info.get('price_last_month'))
                price_data['price_discount_range_20_60s'] = safe_int(extra_info.get('price_discount_range'))
                price_data['price_margin_last_20_60s'] = safe_int(extra_info.get('price_margin_last'))
                # 转换时间为ISO格式字符串或None
                start_time = timestamp_to_datetime(price_info.get('start_time'))
                end_time = timestamp_to_datetime(price_info.get('end_time'))
                price_data['price_start_time'] = start_time.isoformat() if start_time else None
                price_data['price_end_time'] = end_time.isoformat() if end_time else None
            elif video_type == 92:  # CPM模式有ceiling和floor
                extra_info = price_info.get('price_extra_info', {})
                price_data['ceiling_price'] = safe_int(extra_info.get('ceiling_price'))
                price_data['floor_price'] = safe_int(extra_info.get('floor_price'))
    
    return price_data


def parse_kol_ecommerce(author: Dict, fetch_date: datetime) -> Dict:
    """解析KOL电商数据"""
    attr = author.get('attribute_datas', {})
    
    return {
        'kol_id': attr.get('id') or author.get('star_id'),
        'ecom_level': attr.get('author_ecom_level'),
        'ecom_enabled': safe_bool(attr.get('e_commerce_enable')),
        'gmv_30d_range': attr.get('ecom_gmv_30d_range') or None,
        'gpm_30d_range': attr.get('ecom_gpm_30d_range') or None,
        'avg_order_value_30d_range': attr.get('ecom_avg_order_value_30d_range') or None,
        'ecom_video_num_30d': safe_int(attr.get('ecom_video_product_num_30d')),
        'star_ecom_video_num_30d': safe_int(attr.get('star_ecom_video_num_30d')),
        'ecom_video_product_num_30d': safe_int(attr.get('ecom_video_product_num_30d')),
        'raw_data': attr,
        'fetch_date': fetch_date.isoformat(),  # 转换为ISO格式字符串
    }


def parse_kol_videos(author: Dict, fetch_date: datetime) -> List[Dict]:
    """
    解析KOL视频数据
    从items和last_10_items两个来源
    """
    attr = author.get('attribute_datas', {})
    kol_id = attr.get('id') or author.get('star_id')
    
    videos = []
    fetch_date_str = fetch_date.isoformat()  # 转换为ISO格式字符串
    
    # 1. 解析items (代表作品)
    items = author.get('items', [])
    for item in items:
        videos.append({
            'kol_id': kol_id,
            'item_id': item.get('item_id'),
            'video_tag': safe_int(item.get('video_tag')),
            'vv': safe_int(item.get('vv')),
            'source': 'items',
            'fetch_date': fetch_date_str,
        })
    
    # 2. 解析last_10_items (最近10个作品)
    last_10_items_str = attr.get('last_10_items', '[]')
    last_10_items = parse_json_field(last_10_items_str) or []
    
    for item in last_10_items:
        # 转换时间为ISO格式字符串或None
        publish_time = timestamp_to_datetime(item.get('item_publish_time'))
        create_time = timestamp_to_datetime(item.get('item_create_time'))
        
        videos.append({
            'kol_id': kol_id,
            'item_id': item.get('item_id'),
            'video_tag': None,  # last_10_items中没有video_tag
            'vv': safe_int(item.get('vv')),
            'comment_cnt': safe_int(item.get('comment_cnt')),
            'like_cnt': safe_int(item.get('like_cnt')),
            'share_cnt': safe_int(item.get('share_cnt')),
            'item_title': item.get('item_title'),
            'item_publish_time': publish_time.isoformat() if publish_time else None,
            'item_create_time': create_time.isoformat() if create_time else None,
            'is_high_quality': safe_bool(item.get('is_high_quality_item')),
            'source': 'last_10_items',
            'fetch_date': fetch_date_str,
        })
    
    return videos


def import_page_data(page_file: Path) -> Dict[str, int]:
    """
    导入单页数据到数据库
    
    返回:
        统计信息字典
    """
    print(f"\n📄 正在处理文件: {page_file.name}")
    
    # 读取JSON文件
    with open(page_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    authors = data.get('data', {}).get('authors', [])
    fetch_date = datetime.now()
    
    stats = {
        'total_kols': len(authors),
        'success_base': 0,
        'success_price': 0,
        'success_ecom': 0,
        'success_videos': 0,
        'error_base': 0,
        'error_price': 0,
        'error_ecom': 0,
        'error_videos': 0,
    }
    
    for idx, author in enumerate(authors, 1):
        try:
            kol_id = author.get('attribute_datas', {}).get('id') or author.get('star_id')
            print(f"  [{idx}/{len(authors)}] 处理KOL: {kol_id}")
            
            # 1. 导入基础信息
            try:
                base_info = parse_kol_base_info(author, fetch_date)
                result = supabase.table('gg_xingtu_kol_base_info').upsert(
                    base_info, 
                    on_conflict='kol_id'
                ).execute()
                stats['success_base'] += 1
                print(f"    ✅ 基础信息已保存")
            except Exception as e:
                stats['error_base'] += 1
                print(f"    ❌ 基础信息保存失败: {str(e)}")
            
            # 2. 导入报价信息
            try:
                price_info = parse_kol_price(author, fetch_date)
                result = supabase.table('gg_xingtu_kol_price').upsert(
                    price_info,
                    on_conflict='kol_id'
                ).execute()
                stats['success_price'] += 1
                print(f"    ✅ 报价信息已保存")
            except Exception as e:
                stats['error_price'] += 1
                print(f"    ❌ 报价信息保存失败: {str(e)}")
            
            # 3. 导入电商信息
            try:
                ecom_info = parse_kol_ecommerce(author, fetch_date)
                result = supabase.table('gg_xingtu_kol_ecommerce').upsert(
                    ecom_info,
                    on_conflict='kol_id'
                ).execute()
                stats['success_ecom'] += 1
                print(f"    ✅ 电商信息已保存")
            except Exception as e:
                stats['error_ecom'] += 1
                print(f"    ❌ 电商信息保存失败: {str(e)}")
            
            # 4. 导入视频数据
            try:
                videos = parse_kol_videos(author, fetch_date)
                if videos:
                    # 批量插入，如果存在则忽略
                    for video in videos:
                        try:
                            supabase.table('gg_xingtu_kol_videos').insert(video).execute()
                        except Exception:
                            # 忽略重复键错误
                            pass
                    stats['success_videos'] += len(videos)
                    print(f"    ✅ 视频数据已保存 ({len(videos)}条)")
            except Exception as e:
                stats['error_videos'] += 1
                print(f"    ❌ 视频数据保存失败: {str(e)}")
            
        except Exception as e:
            print(f"    ❌ KOL数据处理失败: {str(e)}")
    
    return stats


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 星图KOL数据导入工具")
    print("=" * 80)
    
    # 数据目录
    detail_dir = Path(__file__).parent.parent / 'output' / 'keyword_护肤保养' / 'detail'
    
    # 导入全部104页数据
    page_files = sorted(detail_dir.glob('raw_page_*.json'))
    
    if not page_files:
        print("❌ 未找到数据文件")
        return
    
    print(f"\n📊 找到 {len(page_files)} 个页面文件")
    
    total_stats = {
        'total_kols': 0,
        'success_base': 0,
        'success_price': 0,
        'success_ecom': 0,
        'success_videos': 0,
        'error_base': 0,
        'error_price': 0,
        'error_ecom': 0,
        'error_videos': 0,
    }
    
    for page_file in page_files:
        stats = import_page_data(page_file)
        for key in total_stats:
            total_stats[key] += stats[key]
    
    # 打印汇总统计
    print("\n" + "=" * 80)
    print("📈 导入统计汇总")
    print("=" * 80)
    print(f"总KOL数: {total_stats['total_kols']}")
    print(f"\n基础信息:")
    print(f"  ✅ 成功: {total_stats['success_base']}")
    print(f"  ❌ 失败: {total_stats['error_base']}")
    print(f"\n报价信息:")
    print(f"  ✅ 成功: {total_stats['success_price']}")
    print(f"  ❌ 失败: {total_stats['error_price']}")
    print(f"\n电商信息:")
    print(f"  ✅ 成功: {total_stats['success_ecom']}")
    print(f"  ❌ 失败: {total_stats['error_ecom']}")
    print(f"\n视频数据:")
    print(f"  ✅ 成功: {total_stats['success_videos']}条")
    print(f"  ❌ 失败: {total_stats['error_videos']}")
    print("=" * 80)


if __name__ == '__main__':
    main()

