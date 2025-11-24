#!/usr/bin/env python3
"""
修复失败的KOL数据导入
重新插入因数值溢出而失败的KOL数据
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client

# Supabase配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("错误: 未找到SUPABASE_URL或SUPABASE_KEY环境变量")
    sys.exit(1)

# 初始化Supabase客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 导入原有的解析函数
sys.path.insert(0, str(Path(__file__).parent))
from import_to_supabase import parse_kol_base_info, parse_kol_price, parse_kol_ecommerce, parse_kol_videos


def fix_kol(kol_id: str):
    """修复单个KOL的数据"""
    print(f"\n🔧 修复 KOL: {kol_id}")
    
    # 查找KOL数据
    detail_dir = Path(__file__).parent.parent / 'output' / 'keyword_护肤保养' / 'detail'
    found = False
    
    for json_file in sorted(detail_dir.glob('raw_page_*.json')):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for author in data.get('data', {}).get('authors', []):
            attr = author.get('attribute_datas', {})
            author_kol_id = attr.get('id') or author.get('star_id')
            
            if str(author_kol_id) == kol_id:
                found = True
                print(f"  ✅ 找到数据 in {json_file.name}")
                fetch_date = datetime.now()
                
                # 重新解析和插入数据
                try:
                    # 1. 基础信息
                    base_info = parse_kol_base_info(author, fetch_date)
                    result = supabase.table('gg_xingtu_kol_base_info').upsert(base_info).execute()
                    print(f"  ✅ 基础信息已保存")
                except Exception as e:
                    print(f"  ❌ 基础信息保存失败: {e}")
                
                try:
                    # 2. 报价信息
                    price_info = parse_kol_price(author, fetch_date)
                    if price_info:
                        result = supabase.table('gg_xingtu_kol_price').upsert(price_info).execute()
                        print(f"  ✅ 报价信息已保存")
                except Exception as e:
                    print(f"  ❌ 报价信息保存失败: {e}")
                
                try:
                    # 3. 电商信息
                    ecom_info = parse_kol_ecommerce(author, fetch_date)
                    if ecom_info:
                        result = supabase.table('gg_xingtu_kol_ecommerce').upsert(ecom_info).execute()
                        print(f"  ✅ 电商信息已保存")
                except Exception as e:
                    print(f"  ❌ 电商信息保存失败: {e}")
                
                try:
                    # 4. 视频数据
                    videos = parse_kol_videos(author, fetch_date)
                    if videos:
                        for video in videos:
                            supabase.table('gg_xingtu_kol_videos').upsert(video).execute()
                        print(f"  ✅ 视频数据已保存 ({len(videos)}条)")
                except Exception as e:
                    print(f"  ❌ 视频数据保存失败: {e}")
                
                return True
    
    if not found:
        print(f"  ❌ 未找到KOL数据")
        return False


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 修复失败的KOL数据")
    print("=" * 80)
    
    # 失败的KOL ID
    failed_kols = ['6611304620004212743']
    
    for kol_id in failed_kols:
        fix_kol(kol_id)
    
    print("\n" + "=" * 80)
    print("✅ 修复完成")
    print("=" * 80)


if __name__ == '__main__':
    main()

