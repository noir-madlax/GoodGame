#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音星图护肤达人对比搜索脚本

功能：
1. 使用"美妆护肤"和"护肤保养"两个关键词分别搜索10页数据
2. 将数据保存到不同的目录
3. 分析两个关键词的结果重合度、tag分布情况、tag匹配和关联情况
4. 与之前的搜索结果进行对比分析

作者: AI Agent
创建时间: 2025-11-18
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict, Counter


def load_api_key():
    """
    从环境变量加载 TikHub API Key
    
    Returns:
        str: API Key
    
    Raises:
        ValueError: 如果 API Key 未设置
    """
    # 定位到 backend/.env 文件
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


def search_kol(keyword, page=1, count=20, sort_type=1, api_key=None):
    """
    调用 TikHub API 搜索星图 KOL
    
    Args:
        keyword: 搜索关键词
        page: 页码，从1开始
        count: 每页数量，默认20
        sort_type: 排序方式，1=综合排序
        api_key: API Key
        
    Returns:
        dict: API 响应数据
    """
    url = "https://api.tikhub.io/api/v1/douyin/xingtu/search_kol_v1"
    
    params = {
        "keyword": keyword,
        "page": str(page),
        "count": str(count),
        "sort_type": str(sort_type),
        "platformSource": "_1"  # 抖音平台
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API 请求失败: {e}")
        return None


def fetch_keyword_data(keyword, pages=10, api_key=None, output_dir=None):
    """
    获取指定关键词的多页数据
    
    Args:
        keyword: 搜索关键词
        pages: 获取页数
        api_key: API Key
        output_dir: 输出目录
        
    Returns:
        list: 所有达人数据列表
    """
    all_authors = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 创建输出目录
    detail_dir = output_dir / 'detail'
    detail_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"开始获取关键词 '{keyword}' 的数据，共 {pages} 页")
    print(f"{'='*60}\n")
    
    for page in range(1, pages + 1):
        print(f"📄 正在获取第 {page}/{pages} 页...")
        
        data = search_kol(keyword=keyword, page=page, api_key=api_key)
        
        if data and data.get('code') == 200:
            # 保存原始数据
            filename = f"raw_page_{page}_{timestamp}.json"
            filepath = detail_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 提取达人数据
            authors = data.get('data', {}).get('authors', [])
            all_authors.extend(authors)
            
            print(f"✅ 第 {page} 页获取成功，达人数: {len(authors)}")
            print(f"   已保存到: {filepath}")
            
        else:
            print(f"❌ 第 {page} 页获取失败")
            if data:
                print(f"   错误信息: {data.get('message', 'Unknown error')}")
        
        # 避免请求过快
        if page < pages:
            time.sleep(2)
    
    print(f"\n✅ 关键词 '{keyword}' 数据获取完成，共 {len(all_authors)} 个达人\n")
    
    return all_authors


def analyze_authors_tags(authors, keyword):
    """
    分析达人的标签分布
    
    Args:
        authors: 达人列表
        keyword: 关键词名称
        
    Returns:
        dict: 分析结果
    """
    tag_counts = Counter()  # 标签计数
    category_tags = defaultdict(Counter)  # 分类 -> 标签计数
    author_tags = {}  # 达人ID -> 标签列表
    
    for author in authors:
        author_id = author.get('attribute_datas', {}).get('id', 'unknown')
        tags_relation_str = author.get('attribute_datas', {}).get('tags_relation', '{}')
        
        try:
            tags_relation = json.loads(tags_relation_str)
            author_tag_list = []
            
            for category, tags in tags_relation.items():
                if isinstance(tags, list):
                    for tag in tags:
                        tag_counts[tag] += 1
                        category_tags[category][tag] += 1
                        author_tag_list.append(tag)
                else:
                    tag_counts[tags] += 1
                    category_tags[category][tags] += 1
                    author_tag_list.append(tags)
            
            author_tags[author_id] = author_tag_list
            
        except json.JSONDecodeError:
            pass
    
    return {
        'tag_counts': tag_counts,
        'category_tags': category_tags,
        'author_tags': author_tags,
        'total_authors': len(authors)
    }


def calculate_overlap(authors1, authors2):
    """
    计算两个达人列表的重合度
    
    Args:
        authors1: 第一个达人列表
        authors2: 第二个达人列表
        
    Returns:
        dict: 重合度分析结果
    """
    ids1 = set(a.get('attribute_datas', {}).get('id') for a in authors1)
    ids2 = set(a.get('attribute_datas', {}).get('id') for a in authors2)
    
    overlap = ids1 & ids2
    only_in_1 = ids1 - ids2
    only_in_2 = ids2 - ids1
    
    return {
        'total_1': len(ids1),
        'total_2': len(ids2),
        'overlap_count': len(overlap),
        'overlap_rate_1': len(overlap) / len(ids1) * 100 if ids1 else 0,
        'overlap_rate_2': len(overlap) / len(ids2) * 100 if ids2 else 0,
        'only_in_1': len(only_in_1),
        'only_in_2': len(only_in_2),
        'overlap_ids': overlap
    }


def compare_with_original(new_authors, original_dir):
    """
    与原始搜索结果进行对比
    
    Args:
        new_authors: 新搜索的达人列表
        original_dir: 原始数据目录
        
    Returns:
        dict: 对比结果
    """
    # 读取原始数据
    original_authors = []
    detail_dir = original_dir / 'detail'
    
    if not detail_dir.exists():
        print(f"⚠️ 原始数据目录不存在: {detail_dir}")
        return None
    
    for file in detail_dir.glob('raw_page_*.json'):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                authors = data.get('data', {}).get('authors', [])
                original_authors.extend(authors)
        except Exception as e:
            print(f"⚠️ 读取文件失败 {file}: {e}")
    
    if not original_authors:
        print("⚠️ 未找到原始数据")
        return None
    
    # 计算重合度
    overlap = calculate_overlap(new_authors, original_authors)
    
    return {
        'original_total': len(original_authors),
        'new_total': len(new_authors),
        'overlap': overlap
    }


def generate_analysis_report(keyword1, authors1, analysis1, 
                            keyword2, authors2, analysis2,
                            overlap_result, 
                            original_comparison1, original_comparison2,
                            output_base_dir):
    """
    生成对比分析报告
    
    Args:
        keyword1: 第一个关键词
        authors1: 第一个关键词的达人列表
        analysis1: 第一个关键词的分析结果
        keyword2: 第二个关键词
        authors2: 第二个关键词的达人列表
        analysis2: 第二个关键词的分析结果
        overlap_result: 两个关键词的重合度结果
        original_comparison1: 关键词1与原始数据的对比结果
        original_comparison2: 关键词2与原始数据的对比结果
        output_base_dir: 输出基础目录
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_base_dir / f'对比分析报告_{timestamp}.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 抖音星图护肤达人关键词对比分析报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**对比关键词**: \n")
        f.write(f"- 关键词1: {keyword1}\n")
        f.write(f"- 关键词2: {keyword2}\n\n")
        f.write(f"{'='*80}\n\n")
        
        # 1. 数据概览
        f.write(f"## 一、数据概览\n\n")
        f.write(f"| 关键词 | 总达人数 | 有标签达人数 | 标签种类数 |\n")
        f.write(f"|--------|---------|-------------|------------|\n")
        f.write(f"| {keyword1} | {analysis1['total_authors']} | {len(analysis1['author_tags'])} | {len(analysis1['tag_counts'])} |\n")
        f.write(f"| {keyword2} | {analysis2['total_authors']} | {len(analysis2['author_tags'])} | {len(analysis2['tag_counts'])} |\n\n")
        
        # 2. 重合度分析
        f.write(f"## 二、两个关键词的重合度分析\n\n")
        f.write(f"### 2.1 达人重合情况\n\n")
        f.write(f"| 指标 | 数值 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| {keyword1} 总达人数 | {overlap_result['total_1']} |\n")
        f.write(f"| {keyword2} 总达人数 | {overlap_result['total_2']} |\n")
        f.write(f"| 重合达人数 | {overlap_result['overlap_count']} |\n")
        f.write(f"| {keyword1} 重合率 | {overlap_result['overlap_rate_1']:.2f}% |\n")
        f.write(f"| {keyword2} 重合率 | {overlap_result['overlap_rate_2']:.2f}% |\n")
        f.write(f"| 仅在 {keyword1} | {overlap_result['only_in_1']} |\n")
        f.write(f"| 仅在 {keyword2} | {overlap_result['only_in_2']} |\n\n")
        
        # 3. 与原始数据对比
        f.write(f"## 三、与原始'护肤'搜索结果的对比\n\n")
        
        if original_comparison1:
            f.write(f"### 3.1 '{keyword1}' 与原始数据的重合度\n\n")
            f.write(f"| 指标 | 数值 |\n")
            f.write(f"|------|------|\n")
            f.write(f"| 原始数据总达人数 | {original_comparison1['original_total']} |\n")
            f.write(f"| {keyword1} 总达人数 | {original_comparison1['new_total']} |\n")
            f.write(f"| 重合达人数 | {original_comparison1['overlap']['overlap_count']} |\n")
            f.write(f"| 重合率（相对原始数据） | {original_comparison1['overlap']['overlap_rate_1']:.2f}% |\n")
            f.write(f"| 重合率（相对新数据） | {original_comparison1['overlap']['overlap_rate_2']:.2f}% |\n\n")
        
        if original_comparison2:
            f.write(f"### 3.2 '{keyword2}' 与原始数据的重合度\n\n")
            f.write(f"| 指标 | 数值 |\n")
            f.write(f"|------|------|\n")
            f.write(f"| 原始数据总达人数 | {original_comparison2['original_total']} |\n")
            f.write(f"| {keyword2} 总达人数 | {original_comparison2['new_total']} |\n")
            f.write(f"| 重合达人数 | {original_comparison2['overlap']['overlap_count']} |\n")
            f.write(f"| 重合率（相对原始数据） | {original_comparison2['overlap']['overlap_rate_1']:.2f}% |\n")
            f.write(f"| 重合率（相对新数据） | {original_comparison2['overlap']['overlap_rate_2']:.2f}% |\n\n")
        
        # 4. 标签分布对比
        f.write(f"## 四、标签分布对比\n\n")
        
        f.write(f"### 4.1 '{keyword1}' 标签分布（前20名）\n\n")
        f.write(f"| 标签 | 达人数 | 占比 |\n")
        f.write(f"|------|--------|------|\n")
        for tag, count in analysis1['tag_counts'].most_common(20):
            rate = count / analysis1['total_authors'] * 100
            f.write(f"| {tag} | {count} | {rate:.2f}% |\n")
        f.write(f"\n")
        
        f.write(f"### 4.2 '{keyword2}' 标签分布（前20名）\n\n")
        f.write(f"| 标签 | 达人数 | 占比 |\n")
        f.write(f"|------|--------|------|\n")
        for tag, count in analysis2['tag_counts'].most_common(20):
            rate = count / analysis2['total_authors'] * 100
            f.write(f"| {tag} | {count} | {rate:.2f}% |\n")
        f.write(f"\n")
        
        # 5. 护肤相关标签统计
        f.write(f"## 五、护肤相关标签统计\n\n")
        
        skincare_keywords = ['护肤', '美妆', '保养', '皮肤', '面部', '化妆', '美容']
        
        f.write(f"### 5.1 '{keyword1}' 护肤相关标签\n\n")
        f.write(f"| 标签 | 达人数 | 占比 |\n")
        f.write(f"|------|--------|------|\n")
        skincare_tags1 = {tag: count for tag, count in analysis1['tag_counts'].items() 
                         if any(kw in tag for kw in skincare_keywords)}
        for tag, count in sorted(skincare_tags1.items(), key=lambda x: x[1], reverse=True):
            rate = count / analysis1['total_authors'] * 100
            f.write(f"| {tag} | {count} | {rate:.2f}% |\n")
        f.write(f"| **合计** | **{sum(skincare_tags1.values())}** | **{sum(skincare_tags1.values())/analysis1['total_authors']*100:.2f}%** |\n\n")
        
        f.write(f"### 5.2 '{keyword2}' 护肤相关标签\n\n")
        f.write(f"| 标签 | 达人数 | 占比 |\n")
        f.write(f"|------|--------|------|\n")
        skincare_tags2 = {tag: count for tag, count in analysis2['tag_counts'].items() 
                         if any(kw in tag for kw in skincare_keywords)}
        for tag, count in sorted(skincare_tags2.items(), key=lambda x: x[1], reverse=True):
            rate = count / analysis2['total_authors'] * 100
            f.write(f"| {tag} | {count} | {rate:.2f}% |\n")
        f.write(f"| **合计** | **{sum(skincare_tags2.values())}** | **{sum(skincare_tags2.values())/analysis2['total_authors']*100:.2f}%** |\n\n")
        
        # 6. 分类标签对比
        f.write(f"## 六、分类标签对比\n\n")
        
        f.write(f"### 6.1 '{keyword1}' 分类统计\n\n")
        f.write(f"| 分类 | 标签种类 | 总达人数 |\n")
        f.write(f"|------|---------|----------|\n")
        for category, tags_counter in sorted(analysis1['category_tags'].items(), 
                                            key=lambda x: sum(x[1].values()), reverse=True):
            f.write(f"| {category} | {len(tags_counter)} | {sum(tags_counter.values())} |\n")
        f.write(f"\n")
        
        f.write(f"### 6.2 '{keyword2}' 分类统计\n\n")
        f.write(f"| 分类 | 标签种类 | 总达人数 |\n")
        f.write(f"|------|---------|----------|\n")
        for category, tags_counter in sorted(analysis2['category_tags'].items(), 
                                            key=lambda x: sum(x[1].values()), reverse=True):
            f.write(f"| {category} | {len(tags_counter)} | {sum(tags_counter.values())} |\n")
        f.write(f"\n")
        
        # 7. 结论与建议
        f.write(f"## 七、结论与建议\n\n")
        
        # 计算护肤相关度
        skincare_rate1 = sum(skincare_tags1.values()) / analysis1['total_authors'] * 100
        skincare_rate2 = sum(skincare_tags2.values()) / analysis2['total_authors'] * 100
        
        f.write(f"### 7.1 关键词效果评估\n\n")
        f.write(f"| 关键词 | 护肤相关标签占比 | 评价 |\n")
        f.write(f"|--------|-----------------|------|\n")
        f.write(f"| {keyword1} | {skincare_rate1:.2f}% | {'✅ 推荐' if skincare_rate1 > 50 else '⚠️ 一般' if skincare_rate1 > 30 else '❌ 不推荐'} |\n")
        f.write(f"| {keyword2} | {skincare_rate2:.2f}% | {'✅ 推荐' if skincare_rate2 > 50 else '⚠️ 一般' if skincare_rate2 > 30 else '❌ 不推荐'} |\n\n")
        
        f.write(f"### 7.2 优化建议\n\n")
        
        if skincare_rate1 > skincare_rate2:
            f.write(f"1. **推荐使用 '{keyword1}'** 进行搜索，护肤相关度更高（{skincare_rate1:.2f}%）\n")
        else:
            f.write(f"1. **推荐使用 '{keyword2}'** 进行搜索，护肤相关度更高（{skincare_rate2:.2f}%）\n")
        
        f.write(f"2. 两个关键词的重合率为 {overlap_result['overlap_rate_1']:.2f}%，")
        if overlap_result['overlap_rate_1'] < 50:
            f.write(f"建议**同时使用两个关键词**以获得更全面的达人覆盖\n")
        else:
            f.write(f"重合度较高，选择其中一个即可\n")
        
        f.write(f"3. 重点关注以下标签的达人：\n")
        # 找出最相关的标签
        all_skincare_tags = set(skincare_tags1.keys()) | set(skincare_tags2.keys())
        for tag in sorted(all_skincare_tags, 
                         key=lambda t: skincare_tags1.get(t, 0) + skincare_tags2.get(t, 0), 
                         reverse=True)[:5]:
            count1 = skincare_tags1.get(tag, 0)
            count2 = skincare_tags2.get(tag, 0)
            f.write(f"   - **{tag}**: {keyword1}({count1}人) + {keyword2}({count2}人)\n")
        
        f.write(f"\n")
        f.write(f"---\n\n")
        f.write(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    print(f"✅ 对比分析报告已生成: {report_path}")


def main():
    """
    主函数
    """
    print("\n" + "="*80)
    print("抖音星图护肤达人关键词对比搜索工具")
    print("="*80 + "\n")
    
    try:
        # 1. 加载 API Key
        api_key = load_api_key()
        print(f"✅ API Key 加载成功\n")
        
        # 2. 设置输出目录
        script_dir = Path(__file__).parent
        base_output_dir = script_dir.parent / 'output'
        
        # 创建两个关键词的输出目录
        keyword1 = "美妆护肤"
        keyword2 = "护肤保养"
        
        output_dir1 = base_output_dir / f'keyword_{keyword1}'
        output_dir2 = base_output_dir / f'keyword_{keyword2}'
        
        output_dir1.mkdir(parents=True, exist_ok=True)
        output_dir2.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 输出目录:")
        print(f"   关键词1: {output_dir1}")
        print(f"   关键词2: {output_dir2}\n")
        
        # 3. 获取两个关键词的数据
        print(f"⏳ 开始获取数据...\n")
        
        authors1 = fetch_keyword_data(keyword1, pages=10, api_key=api_key, output_dir=output_dir1)
        authors2 = fetch_keyword_data(keyword2, pages=10, api_key=api_key, output_dir=output_dir2)
        
        # 4. 分析标签
        print(f"📊 分析标签分布...\n")
        analysis1 = analyze_authors_tags(authors1, keyword1)
        analysis2 = analyze_authors_tags(authors2, keyword2)
        
        # 5. 计算重合度
        print(f"🔍 计算重合度...\n")
        overlap_result = calculate_overlap(authors1, authors2)
        
        print(f"两个关键词的重合度:")
        print(f"  - {keyword1}: {len(authors1)} 人")
        print(f"  - {keyword2}: {len(authors2)} 人")
        print(f"  - 重合: {overlap_result['overlap_count']} 人 ({overlap_result['overlap_rate_1']:.2f}%)\n")
        
        # 6. 与原始数据对比
        print(f"📈 与原始'护肤'搜索结果对比...\n")
        original_dir = base_output_dir
        
        original_comparison1 = compare_with_original(authors1, original_dir)
        original_comparison2 = compare_with_original(authors2, original_dir)
        
        if original_comparison1:
            print(f"'{keyword1}' 与原始数据重合: {original_comparison1['overlap']['overlap_count']} 人")
        if original_comparison2:
            print(f"'{keyword2}' 与原始数据重合: {original_comparison2['overlap']['overlap_count']} 人\n")
        
        # 7. 生成报告
        print(f"📝 生成对比分析报告...\n")
        generate_analysis_report(
            keyword1, authors1, analysis1,
            keyword2, authors2, analysis2,
            overlap_result,
            original_comparison1, original_comparison2,
            base_output_dir
        )
        
        print(f"\n{'='*80}")
        print(f"✅ 所有任务完成！")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

