#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crunchbase HTML DIV 文件解析器

用于解析从 Crunchbase 网页爬取的 DIV 文件，提取公司6列关键数据：
1. organization_name - 公司名称
2. industries - 行业分类（可能有多个）
3. last_funding_type - 最近融资类型
4. last_funding_date - 最近融资日期
5. headquarters_location - 总部位置（城市、省/州、国家）
6. description - 公司描述

使用方法:
    python parse_crunchbase_div.py <div_file_path>
    
示例:
    python parse_crunchbase_div.py div15
"""

import re
import json
import sys
import html
from pathlib import Path


def parse_crunchbase_div(content: str) -> list[dict]:
    """
    解析 Crunchbase DIV HTML 内容，提取公司数据
    
    参数:
        content: DIV 文件的 HTML 内容（单行）
        
    返回:
        公司数据列表，每个元素包含6列关键数据
    """
    companies = []
    
    # 正则表达式模式定义
    # 1. 公司名称: title="XXX" aria-label="XXX"
    company_name_pattern = re.compile(r'title="([^"]+)" aria-label="\1"')
    
    # 2. 行业分类: categories/xxx" ... > Industry Name</a>
    industry_pattern = re.compile(r'categories/[^"]*"[^>]*>\s*([^<]+)</a>')
    
    # 3. 融资类型: funding_type/xxx">Type</
    funding_type_pattern = re.compile(r'funding_type/([^"]+)">([^<]+)</')
    
    # 4. 融资日期: funding_at/xxx">Date</
    funding_date_pattern = re.compile(r'funding_at/([^"]+)">([^<]+)</')
    
    # 5. 位置: location_identifiers/xxx" ...> Location</a>
    location_pattern = re.compile(r'location_identifiers/[^"]*"[^>]*>\s*([^<]+)</a>')
    
    # 6. 描述: short_description ... title="Description"
    description_pattern = re.compile(r'column-id-short_description[^>]*>.*?title="([^"]*)"')
    
    # 按 grid-row 分割，每个 grid-row 代表一个公司
    # 使用 <grid-row 作为分隔符
    rows = re.split(r'<grid-row[^>]*>', content)
    
    for row in rows[1:]:  # 跳过第一个空元素
        company = {}
        
        # 1. 提取公司名称（只取第一个匹配，是主要的公司名）
        name_match = company_name_pattern.search(row)
        if name_match:
            company['organization_name'] = name_match.group(1).strip()
        else:
            continue  # 如果没有公司名，跳过这一行
        
        # 2. 提取行业分类（可能有多个）
        # 需要在 column-id-categories 区域内查找
        categories_section = re.search(r'column-id-categories[^>]*>(.*?)(?=</grid-cell>|column-id-)', row, re.DOTALL)
        if categories_section:
            industries = industry_pattern.findall(categories_section.group(1))
            company['industries'] = [ind.strip() for ind in industries if ind.strip()]
        else:
            company['industries'] = []
        
        # 3. 提取融资类型
        # 在 column-id-last_funding_type 区域内查找
        funding_type_section = re.search(r'column-id-last_funding_type[^>]*>(.*?)(?=</grid-cell>|column-id-)', row, re.DOTALL)
        if funding_type_section:
            type_match = re.search(r'funding_type/[^"]*">([^<]+)</', funding_type_section.group(1))
            if type_match:
                company['last_funding_type'] = type_match.group(1).strip()
            else:
                company['last_funding_type'] = None
        else:
            company['last_funding_type'] = None
        
        # 4. 提取融资日期
        # 在 column-id-last_funding_at 区域内查找
        funding_date_section = re.search(r'column-id-last_funding_at[^>]*>(.*?)(?=</grid-cell>|column-id-)', row, re.DOTALL)
        if funding_date_section:
            date_match = re.search(r'funding_at/[^"]*">([^<]+)</', funding_date_section.group(1))
            if date_match:
                company['last_funding_date'] = date_match.group(1).strip()
            else:
                company['last_funding_date'] = None
        else:
            company['last_funding_date'] = None
        
        # 5. 提取总部位置（可能有多级：城市、省/州、国家）
        # 在 column-id-location_identifiers 区域内查找
        location_section = re.search(r'column-id-location_identifiers[^>]*>(.*?)(?=</grid-cell>|column-id-)', row, re.DOTALL)
        if location_section:
            locations = location_pattern.findall(location_section.group(1))
            if locations:
                # 去除首尾空格，组合成完整地址
                locations = [loc.strip() for loc in locations if loc.strip()]
                company['headquarters_location'] = ', '.join(locations)
            else:
                company['headquarters_location'] = None
        else:
            company['headquarters_location'] = None
        
        # 6. 提取公司描述
        # 在 column-id-short_description 区域内查找
        desc_section = re.search(r'column-id-short_description[^>]*>(.*?)(?=</grid-cell>|column-id-)', row, re.DOTALL)
        if desc_section:
            desc_match = re.search(r'title="([^"]*)"', desc_section.group(1))
            if desc_match:
                # 解码 HTML 实体，如 &amp; -> &
                company['description'] = html.unescape(desc_match.group(1).strip())
            else:
                company['description'] = None
        else:
            company['description'] = None
        
        companies.append(company)
    
    return companies


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python parse_crunchbase_div.py <div_file_path>")
        print("示例: python parse_crunchbase_div.py div15")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    # 如果没有完整路径，使用当前目录
    if not input_file.is_absolute():
        input_file = Path(__file__).parent / input_file
    
    if not input_file.exists():
        print(f"错误: 文件不存在 - {input_file}")
        sys.exit(1)
    
    # 读取文件内容
    print(f"正在读取文件: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析数据
    print("正在解析数据...")
    companies = parse_crunchbase_div(content)
    
    # 输出统计信息
    print(f"\n解析完成! 共找到 {len(companies)} 家公司")
    
    # 保存为 JSON 文件
    output_file = input_file.with_suffix('.json')
    result = {
        "total_count": len(companies),
        "source_file": input_file.name,
        "companies": companies
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到: {output_file}")
    
    # 打印前几条数据预览
    print("\n=== 数据预览 (前6条) ===")
    for i, company in enumerate(companies[:6], 1):
        print(f"\n--- 公司 {i}: {company.get('organization_name', 'N/A')} ---")
        print(f"  行业: {', '.join(company.get('industries', [])) or 'N/A'}")
        print(f"  融资类型: {company.get('last_funding_type', 'N/A')}")
        print(f"  融资日期: {company.get('last_funding_date', 'N/A')}")
        print(f"  总部位置: {company.get('headquarters_location', 'N/A')}")
        desc = company.get('description', '')
        if desc and len(desc) > 60:
            desc = desc[:60] + '...'
        print(f"  描述: {desc or 'N/A'}")
    
    return companies


if __name__ == '__main__':
    main()

