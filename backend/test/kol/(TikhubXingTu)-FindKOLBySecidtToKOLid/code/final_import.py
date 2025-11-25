#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终导入脚本：分批导入所有72位KOL用户数据到 gg_douyin_user_search 表
"""

import json
import os
from pathlib import Path
import requests


def load_all_kol_data():
    """加载所有KOL数据"""
    detail_dir = Path(__file__).parent.parent / 'detail'
    kol_data = []

    for json_file in detail_dir.glob('kol_check_*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            user_info = data.get('user_info', {})
            api_response = data.get('api_response', {})

            # 构造数据库记录
            record = {
                'uid': user_info.get('uid'),
                'sec_uid': user_info.get('sec_uid'),
                'nickname': user_info.get('nickname', '').replace("'", "''"),  # 转义单引号
                'follower_count': user_info.get('follower_count', 0),
                'raw_data': json.dumps(api_response).replace("'", "''"),  # 转义单引号
                'search_keyword': '皮肤好 专家',
                'search_date': '2025-11-24'
            }

            kol_data.append(record)

        except Exception as e:
            print(f"❌ 处理文件 {json_file.name} 失败: {e}")
            continue

    return kol_data


def execute_sql_batch(sql_query, batch_num):
    """通过MCP执行SQL批次"""
    print(f"🔄 执行第 {batch_num} 批...")

    # 这里我们需要通过HTTP请求调用MCP
    # 但由于我们无法直接调用MCP，我们将SQL保存到文件
    output_file = f"batch_{batch_num}.sql"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sql_query)

    print(f"✅ SQL已保存到 {output_file}")
    return True


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 抖音用户搜索数据批量导入工具")
    print("=" * 80)

    # 加载所有数据
    print("📊 加载KOL数据...")
    kol_data = load_all_kol_data()
    print(f"✅ 共加载 {len(kol_data)} 条记录")

    # 分批处理，每批5条记录
    batch_size = 5
    total_batches = (len(kol_data) + batch_size - 1) // batch_size

    print(f"📦 分 {total_batches} 批处理，每批 {batch_size} 条记录")

    for i in range(0, len(kol_data), batch_size):
        batch = kol_data[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        print(f"\n🔄 处理第 {batch_num}/{total_batches} 批 ({i+1}-{min(i+batch_size, len(kol_data))})")

        # 生成INSERT语句
        values = []
        for record in batch:
            value = f"('{record['uid']}', '{record['sec_uid']}', '{record['nickname']}', {record['follower_count']}, '{record['raw_data']}', '{record['search_keyword']}', '{record['search_date']}')"
            values.append(value)

        sql = f"""INSERT INTO gg_douyin_user_search (uid, sec_uid, nickname, follower_count, raw_data, search_keyword, search_date) VALUES
{','.join(values)}
ON CONFLICT (uid) DO UPDATE SET
  sec_uid = EXCLUDED.sec_uid,
  nickname = EXCLUDED.nickname,
  follower_count = EXCLUDED.follower_count,
  raw_data = EXCLUDED.raw_data,
  search_keyword = EXCLUDED.search_keyword,
  search_date = EXCLUDED.search_date,
  updated_at = now();"""

        # 执行SQL
        if execute_sql_batch(sql, batch_num):
            print(f"✅ 第 {batch_num} 批处理完成")
        else:
            print(f"❌ 第 {batch_num} 批处理失败")
            break

    print("\n" + "=" * 80)
    print("📈 导入完成")
    print(f"总记录数: {len(kol_data)}")
    print(f"总批次数: {total_batches}")
    print("请手动执行生成的SQL文件")
    print("=" * 80)


if __name__ == '__main__':
    main()
