#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成批量导入SQL语句的脚本
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any


def load_kol_data() -> List[Dict]:
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
            print(f"处理文件 {json_file.name} 失败: {e}")
            continue

    return kol_data


def generate_batch_insert_sql(kol_data: List[Dict], batch_size: int = 10) -> List[str]:
    """生成批量INSERT SQL语句"""
    sql_statements = []

    for i in range(0, len(kol_data), batch_size):
        batch = kol_data[i:i + batch_size]

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

        sql_statements.append(sql)

    return sql_statements


def main():
    """主函数"""
    print("开始加载KOL数据...")
    kol_data = load_kol_data()
    print(f"共加载 {len(kol_data)} 条记录")

    print("生成SQL语句...")
    sql_statements = generate_batch_insert_sql(kol_data, batch_size=5)

    print(f"生成了 {len(sql_statements)} 条SQL语句")

    # 保存到文件
    output_file = Path(__file__).parent / 'batch_import.sql'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- 批量导入72位KOL用户数据到 gg_douyin_user_search 表\n")
        f.write("-- 生成时间: 2025-11-24\n\n")

        for i, sql in enumerate(sql_statements, 1):
            f.write(f"-- 批次 {i}\n")
            f.write(sql)
            f.write("\n\n")

    print(f"SQL语句已保存到: {output_file}")

    # 打印第一条SQL供测试
    if sql_statements:
        print("\n第一条SQL语句预览:")
        print(sql_statements[0][:500] + "...")


if __name__ == '__main__':
    main()
