#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CSV 数据导入脚本

将 MCN 提供的 KOL 筛选表导入到 gg_pgy_kol_base_info 表
"""

import os
import re
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client


def load_supabase_client() -> Client:
    """加载 Supabase 客户端"""
    backend_dir = Path(__file__).parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("请在 .env 文件中配置 SUPABASE_URL 和 SUPABASE_KEY")
    
    return create_client(url, key)


def extract_kol_id_from_pgy_link(pgy_link: str) -> Optional[str]:
    """从蒲公英链接提取 KOL ID
    
    示例链接:
    https://pgy.xiaohongshu.com/solar/pre-trade/blogger-detail/63c4e411000000002600430e
    https://pgy.xiaohongshu.com/solar/pre-trade/blogger-detail/63c4e411000000002600430e?track_id=xxx
    """
    if not pgy_link or pgy_link.strip() == '':
        return None
    
    # 匹配 blogger-detail/ 后面的 ID
    pattern = r'blogger-detail/([a-f0-9]+)'
    match = re.search(pattern, pgy_link)
    
    if match:
        return match.group(1)
    
    return None


def extract_user_id_from_xhs_link(xhs_link: str) -> Optional[str]:
    """从小红书链接提取用户 ID
    
    示例链接:
    https://www.xiaohongshu.com/user/profile/63c4e411000000002600430e
    """
    if not xhs_link or xhs_link.strip() == '':
        return None
    
    # 匹配 profile/ 后面的 ID
    pattern = r'profile/([a-f0-9]+)'
    match = re.search(pattern, xhs_link)
    
    if match:
        return match.group(1)
    
    return None


def parse_price(price_str: str) -> Optional[str]:
    """解析价格字符串"""
    if not price_str or price_str.strip() == '':
        return None
    return price_str.strip()


def parse_fans_wan(fans_str: str) -> Optional[float]:
    """解析粉丝数（万）"""
    if not fans_str or fans_str.strip() == '':
        return None
    
    try:
        # 移除可能的逗号和空格
        cleaned = fans_str.strip().replace(',', '')
        return float(cleaned)
    except ValueError:
        return None


def parse_csv_row(row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
    """解析 CSV 行数据
    
    CSV 列结构:
    0: 空列（行前缀，如"反馈："、"xqx"等）
    1: 达人昵称
    2: 方向
    3: 小红书链接
    4: 蒲公英链接
    5: 粉丝数（w）
    6: 赞藏评（w）
    7: 图文非报备
    8: 视频非报备
    9: 是否选中
    10: 备注
    11: 达人创作方向
    12: xqx反馈
    13: wyy反馈
    """
    # 跳过空行或标题行
    if len(row) < 5:
        return None
    
    # 获取达人昵称（第2列，索引1）
    kol_name = row[1].strip() if len(row) > 1 else ''
    
    # 跳过没有昵称的行
    if not kol_name or kol_name == '达人昵称':
        return None
    
    # 获取蒲公英链接（第5列，索引4）
    pgy_link = row[4].strip() if len(row) > 4 else ''
    
    # 提取 KOL ID
    kol_id = extract_kol_id_from_pgy_link(pgy_link)
    
    # 如果没有蒲公英链接，尝试从小红书链接提取
    if not kol_id:
        xhs_link = row[3].strip() if len(row) > 3 else ''
        kol_id = extract_user_id_from_xhs_link(xhs_link)
    
    # 如果还是没有 ID，跳过这行
    if not kol_id:
        print(f"  ⚠️ 跳过: {kol_name} - 无法提取 KOL ID")
        return None
    
    # 构建数据字典
    data = {
        'kol_id': kol_id,
        'kol_name': kol_name,
        'csv_row_prefix': row[0].strip() if len(row) > 0 else None,
        'csv_direction': row[2].strip() if len(row) > 2 else None,
        'csv_xiaohongshu_link': row[3].strip() if len(row) > 3 else None,
        'csv_pgy_link': pgy_link if pgy_link else None,
        'csv_fans_wan': parse_fans_wan(row[5]) if len(row) > 5 else None,
        'csv_like_collect_wan': parse_fans_wan(row[6]) if len(row) > 6 else None,
        'csv_picture_price': parse_price(row[7]) if len(row) > 7 else None,
        'csv_video_price': parse_price(row[8]) if len(row) > 8 else None,
        'csv_is_selected': row[9].strip() if len(row) > 9 else None,
        'csv_remark': row[10].strip() if len(row) > 10 else None,
        'csv_creator_direction': row[11].strip() if len(row) > 11 else None,
        'csv_xqx_feedback': row[12].strip() if len(row) > 12 else None,
        'csv_wyy_feedback': row[13].strip() if len(row) > 13 else None,
        'api_fetch_status': 'not_fetched',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
    }
    
    # 移除 None 值
    data = {k: v for k, v in data.items() if v is not None and v != ''}
    
    return data


def read_csv_file(csv_path: str) -> List[Dict[str, Any]]:
    """读取 CSV 文件并解析"""
    records = []
    skipped = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)  # 跳过标题行
        
        for row_num, row in enumerate(reader, start=2):
            data = parse_csv_row(row, headers)
            if data:
                records.append(data)
            else:
                skipped += 1
    
    return records, skipped


def import_to_supabase(client: Client, records: List[Dict[str, Any]]) -> Dict[str, int]:
    """导入数据到 Supabase"""
    stats = {
        'inserted': 0,
        'updated': 0,
        'failed': 0,
        'duplicates': []
    }
    
    # 检查重复的 kol_id
    kol_ids = [r['kol_id'] for r in records]
    seen = set()
    duplicates = set()
    for kol_id in kol_ids:
        if kol_id in seen:
            duplicates.add(kol_id)
        seen.add(kol_id)
    
    if duplicates:
        print(f"\n⚠️ 发现 {len(duplicates)} 个重复的 KOL ID:")
        for dup in list(duplicates)[:5]:
            # 找到所有使用这个 ID 的记录
            dup_records = [r for r in records if r['kol_id'] == dup]
            names = [r.get('kol_name', 'N/A') for r in dup_records]
            print(f"   - {dup}: {names}")
        stats['duplicates'] = list(duplicates)
    
    # 去重，保留第一个
    unique_records = {}
    for record in records:
        kol_id = record['kol_id']
        if kol_id not in unique_records:
            unique_records[kol_id] = record
    
    print(f"\n📊 去重后记录数: {len(unique_records)}")
    
    # 使用 upsert 导入
    for kol_id, record in unique_records.items():
        try:
            result = client.table('gg_pgy_kol_base_info').upsert(
                record,
                on_conflict='kol_id'
            ).execute()
            
            if result.data:
                stats['inserted'] += 1
            else:
                stats['failed'] += 1
                print(f"  ❌ 导入失败: {record.get('kol_name', kol_id)}")
        except Exception as e:
            stats['failed'] += 1
            print(f"  ❌ 导入异常: {record.get('kol_name', kol_id)} - {str(e)[:50]}")
    
    return stats


def verify_import(client: Client, expected_count: int) -> Dict[str, Any]:
    """验证导入结果"""
    # 查询总记录数
    result = client.table('gg_pgy_kol_base_info').select('kol_id', count='exact').execute()
    actual_count = result.count if result.count else len(result.data)
    
    # 查询有 kol_name 的记录数
    result_with_name = client.table('gg_pgy_kol_base_info').select(
        'kol_id', count='exact'
    ).not_.is_('kol_name', 'null').execute()
    with_name_count = result_with_name.count if result_with_name.count else len(result_with_name.data)
    
    # 查询有蒲公英链接的记录数
    result_with_pgy = client.table('gg_pgy_kol_base_info').select(
        'kol_id', count='exact'
    ).not_.is_('csv_pgy_link', 'null').execute()
    with_pgy_count = result_with_pgy.count if result_with_pgy.count else len(result_with_pgy.data)
    
    return {
        'expected': expected_count,
        'actual': actual_count,
        'with_name': with_name_count,
        'with_pgy_link': with_pgy_count,
        'match': actual_count >= expected_count
    }


def main():
    """主函数"""
    print("=" * 60)
    print("📥 CSV 数据导入脚本")
    print("=" * 60)
    
    # CSV 文件路径
    csv_path = Path(__file__).parent / "NazzleNest&星辰文化合作表 副本 - 筛号表.csv"
    
    if not csv_path.exists():
        print(f"❌ CSV 文件不存在: {csv_path}")
        return
    
    print(f"\n📄 CSV 文件: {csv_path.name}")
    
    # 1. 读取 CSV
    print("\n[1/3] 读取 CSV 文件...")
    records, skipped = read_csv_file(str(csv_path))
    print(f"  ✅ 解析成功: {len(records)} 条记录")
    print(f"  ⏭️ 跳过: {skipped} 行（空行/无效行）")
    
    if not records:
        print("❌ 没有有效记录，退出")
        return
    
    # 2. 连接数据库并导入
    print("\n[2/3] 导入到数据库...")
    client = load_supabase_client()
    stats = import_to_supabase(client, records)
    
    print(f"\n📊 导入统计:")
    print(f"  ✅ 成功: {stats['inserted']}")
    print(f"  ❌ 失败: {stats['failed']}")
    if stats['duplicates']:
        print(f"  ⚠️ 重复 ID: {len(stats['duplicates'])}")
    
    # 3. 验证导入
    print("\n[3/3] 验证导入结果...")
    verify_result = verify_import(client, len(set(r['kol_id'] for r in records)))
    
    print(f"\n📋 验证结果:")
    print(f"  预期记录数: {verify_result['expected']}")
    print(f"  实际记录数: {verify_result['actual']}")
    print(f"  有昵称记录: {verify_result['with_name']}")
    print(f"  有蒲公英链接: {verify_result['with_pgy_link']}")
    
    if verify_result['match']:
        print(f"\n✅ 导入验证通过！")
    else:
        print(f"\n⚠️ 导入数量不匹配，请检查")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
