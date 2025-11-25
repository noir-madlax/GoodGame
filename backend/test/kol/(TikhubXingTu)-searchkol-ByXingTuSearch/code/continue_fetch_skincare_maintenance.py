#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
继续获取"护肤保养"关键词数据到28页

功能：
1. 检查已有的页面数据
2. 继续获取缺失的页面直到28页
3. 与原始"护肤"数据进行全面对比分析
4. 查找目标达人"技术员小星星"
5. 统计完全无关的达人

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


def search_kol(keyword, page=1, count=20, sort_type=1, api_key=None):
    """调用 TikHub API 搜索星图 KOL"""
    url = "https://api.tikhub.io/api/v1/douyin/xingtu/search_kol_v1"
    
    params = {
        "keyword": keyword,
        "page": str(page),
        "count": str(count),
        "sort_type": str(sort_type),
        "platformSource": "_1"
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


def get_existing_pages(detail_dir):
    """获取已存在的页码列表"""
    existing_pages = []
    for file in Path(detail_dir).glob('raw_page_*.json'):
        try:
            page_num = int(file.stem.split('_')[2])
            existing_pages.append(page_num)
        except:
            pass
    return sorted(existing_pages)


def fetch_missing_pages(keyword, target_pages, output_dir, api_key):
    """获取缺失的页面数据"""
    detail_dir = output_dir / 'detail'
    detail_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查已有页面
    existing_pages = get_existing_pages(detail_dir)
    missing_pages = [p for p in range(1, target_pages + 1) if p not in existing_pages]
    
    print(f"\n{'='*60}")
    print(f"关键词: '{keyword}'")
    print(f"目标页数: {target_pages}")
    print(f"已有页面: {len(existing_pages)} 页 - {existing_pages}")
    print(f"缺失页面: {len(missing_pages)} 页 - {missing_pages}")
    print(f"{'='*60}\n")
    
    if not missing_pages:
        print("✅ 所有页面已存在，无需获取")
        return []
    
    all_new_authors = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for page in missing_pages:
        print(f"📄 正在获取第 {page}/{target_pages} 页...")
        
        data = search_kol(keyword=keyword, page=page, api_key=api_key)
        
        if data and data.get('code') == 200:
            filename = f"raw_page_{page}_{timestamp}.json"
            filepath = detail_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            authors = data.get('data', {}).get('authors', [])
            all_new_authors.extend(authors)
            
            print(f"✅ 第 {page} 页获取成功，达人数: {len(authors)}")
            print(f"   已保存到: {filepath}")
        else:
            print(f"⚠️ 第 {page} 页获取失败或无数据")
            if data:
                print(f"   错误信息: {data.get('message', 'Unknown error')}")
        
        # 避免请求过快
        if page != missing_pages[-1]:
            time.sleep(2)
    
    print(f"\n✅ 新增数据获取完成，共 {len(all_new_authors)} 个达人\n")
    return all_new_authors


def load_all_authors(detail_dir):
    """加载目录下所有达人数据"""
    authors = []
    author_ids = set()
    
    for file in sorted(Path(detail_dir).glob('raw_page_*.json')):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                page_authors = data.get('data', {}).get('authors', [])
                
                for author in page_authors:
                    author_id = author.get('attribute_datas', {}).get('id')
                    if author_id and author_id not in author_ids:
                        authors.append(author)
                        author_ids.add(author_id)
        except Exception as e:
            print(f"⚠️ 读取文件失败 {file}: {e}")
    
    return authors


def find_target_author(authors, target_name):
    """查找目标达人"""
    for author in authors:
        nick_name = author.get('attribute_datas', {}).get('nick_name', '')
        if target_name in nick_name:
            return author
    return None


def analyze_tags(authors):
    """分析标签分布"""
    tag_counts = Counter()
    category_tags = defaultdict(Counter)
    author_tags = {}
    
    skincare_keywords = ['护肤', '美妆', '保养', '皮肤', '面部', '化妆', '美容']
    
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
            
            author_tags[author_id] = {
                'nick_name': author.get('attribute_datas', {}).get('nick_name', ''),
                'tags': author_tag_list,
                'has_skincare': any(any(kw in tag for kw in skincare_keywords) for tag in author_tag_list)
            }
        except:
            author_tags[author_id] = {
                'nick_name': author.get('attribute_datas', {}).get('nick_name', ''),
                'tags': [],
                'has_skincare': False
            }
    
    return tag_counts, category_tags, author_tags


def generate_comparison_report(original_authors, maintenance_authors, 
                               target_author_found, output_dir):
    """生成详细对比报告"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f'护肤vs护肤保养_详细对比_{timestamp}.md'
    
    # 分析数据
    orig_ids = {a.get('attribute_datas', {}).get('id'): a for a in original_authors}
    maint_ids = {a.get('attribute_datas', {}).get('id'): a for a in maintenance_authors}
    
    overlap_ids = set(orig_ids.keys()) & set(maint_ids.keys())
    only_orig_ids = set(orig_ids.keys()) - set(maint_ids.keys())
    only_maint_ids = set(maint_ids.keys()) - set(orig_ids.keys())
    
    # 标签分析
    orig_tag_counts, orig_category_tags, orig_author_tags = analyze_tags(original_authors)
    maint_tag_counts, maint_category_tags, maint_author_tags = analyze_tags(maintenance_authors)
    
    # 统计无关达人
    orig_unrelated = [aid for aid, info in orig_author_tags.items() if not info['has_skincare']]
    maint_unrelated = [aid for aid, info in maint_author_tags.items() if not info['has_skincare']]
    
    skincare_keywords = ['护肤', '美妆', '保养', '皮肤', '面部', '化妆', '美容']
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 护肤 vs 护肤保养 - 28页数据详细对比分析报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**数据范围**: 28页数据\n\n")
        f.write("="*80 + "\n\n")
        
        # 一、数据概览
        f.write("## 一、数据概览\n\n")
        f.write("### 1.1 基础统计\n\n")
        f.write("| 数据集 | 总达人数 | 去重后 | 有标签 | 标签种类 |\n")
        f.write("|--------|---------|--------|--------|----------|\n")
        f.write(f"| 护肤 | {len(original_authors)} | {len(orig_ids)} | {len(orig_author_tags)} | {len(orig_tag_counts)} |\n")
        f.write(f"| 护肤保养 | {len(maintenance_authors)} | {len(maint_ids)} | {len(maint_author_tags)} | {len(maint_tag_counts)} |\n\n")
        
        # 二、重合度分析
        f.write("## 二、重合度分析\n\n")
        f.write("### 2.1 达人重合情况\n\n")
        f.write("| 指标 | 数值 |\n")
        f.write("|------|------|\n")
        f.write(f"| 护肤总达人数 | {len(orig_ids)} |\n")
        f.write(f"| 护肤保养总达人数 | {len(maint_ids)} |\n")
        f.write(f"| 重合达人数 | {len(overlap_ids)} |\n")
        f.write(f"| 重合率（相对护肤） | {len(overlap_ids)/len(orig_ids)*100:.2f}% |\n")
        f.write(f"| 重合率（相对护肤保养） | {len(overlap_ids)/len(maint_ids)*100:.2f}% |\n")
        f.write(f"| 仅在护肤 | {len(only_orig_ids)} |\n")
        f.write(f"| 仅在护肤保养 | {len(only_maint_ids)} |\n\n")
        
        # 三、目标达人查找
        f.write("## 三、目标达人查找\n\n")
        f.write("### 3.1 技术员小星星\n\n")
        
        if target_author_found['in_original']:
            author = target_author_found['original_data']
            f.write("**在'护肤'搜索中**: ✅ 找到\n\n")
            f.write(f"- 达人ID: {author.get('attribute_datas', {}).get('id')}\n")
            f.write(f"- 昵称: {author.get('attribute_datas', {}).get('nick_name')}\n")
            f.write(f"- 粉丝数: {author.get('attribute_datas', {}).get('follower')}\n")
            tags_str = author.get('attribute_datas', {}).get('tags_relation', '{}')
            f.write(f"- 标签: {tags_str}\n\n")
        else:
            f.write("**在'护肤'搜索中**: ❌ 未找到\n\n")
        
        if target_author_found['in_maintenance']:
            author = target_author_found['maintenance_data']
            f.write("**在'护肤保养'搜索中**: ✅ 找到\n\n")
            f.write(f"- 达人ID: {author.get('attribute_datas', {}).get('id')}\n")
            f.write(f"- 昵称: {author.get('attribute_datas', {}).get('nick_name')}\n")
            f.write(f"- 粉丝数: {author.get('attribute_datas', {}).get('follower')}\n")
            tags_str = author.get('attribute_datas', {}).get('tags_relation', '{}')
            f.write(f"- 标签: {tags_str}\n\n")
        else:
            f.write("**在'护肤保养'搜索中**: ❌ 未找到\n\n")
        
        # 四、标签分布对比
        f.write("## 四、标签分布对比\n\n")
        
        f.write("### 4.1 '护肤' 标签分布（前30名）\n\n")
        f.write("| 排名 | 标签 | 达人数 | 占比 |\n")
        f.write("|------|------|--------|------|\n")
        for idx, (tag, count) in enumerate(orig_tag_counts.most_common(30), 1):
            rate = count / len(orig_ids) * 100
            skincare_mark = "✅" if any(kw in tag for kw in skincare_keywords) else ""
            f.write(f"| {idx} | {tag} {skincare_mark} | {count} | {rate:.2f}% |\n")
        f.write("\n")
        
        f.write("### 4.2 '护肤保养' 标签分布（前30名）\n\n")
        f.write("| 排名 | 标签 | 达人数 | 占比 |\n")
        f.write("|------|------|--------|------|\n")
        for idx, (tag, count) in enumerate(maint_tag_counts.most_common(30), 1):
            rate = count / len(maint_ids) * 100
            skincare_mark = "✅" if any(kw in tag for kw in skincare_keywords) else ""
            f.write(f"| {idx} | {tag} {skincare_mark} | {count} | {rate:.2f}% |\n")
        f.write("\n")
        
        # 五、护肤相关度统计
        f.write("## 五、护肤相关度统计\n\n")
        
        orig_skincare_tags = {tag: count for tag, count in orig_tag_counts.items() 
                             if any(kw in tag for kw in skincare_keywords)}
        maint_skincare_tags = {tag: count for tag, count in maint_tag_counts.items() 
                              if any(kw in tag for kw in skincare_keywords)}
        
        f.write("### 5.1 '护肤' 护肤相关标签\n\n")
        f.write("| 标签 | 达人数 | 占比 |\n")
        f.write("|------|--------|------|\n")
        for tag, count in sorted(orig_skincare_tags.items(), key=lambda x: x[1], reverse=True):
            rate = count / len(orig_ids) * 100
            f.write(f"| {tag} | {count} | {rate:.2f}% |\n")
        f.write(f"| **合计** | **{sum(orig_skincare_tags.values())}** | **{sum(orig_skincare_tags.values())/len(orig_ids)*100:.2f}%** |\n\n")
        
        f.write("### 5.2 '护肤保养' 护肤相关标签\n\n")
        f.write("| 标签 | 达人数 | 占比 |\n")
        f.write("|------|--------|------|\n")
        for tag, count in sorted(maint_skincare_tags.items(), key=lambda x: x[1], reverse=True):
            rate = count / len(maint_ids) * 100
            f.write(f"| {tag} | {count} | {rate:.2f}% |\n")
        f.write(f"| **合计** | **{sum(maint_skincare_tags.values())}** | **{sum(maint_skincare_tags.values())/len(maint_ids)*100:.2f}%** |\n\n")
        
        # 六、完全无关达人统计
        f.write("## 六、完全无关达人统计\n\n")
        f.write(f"**定义**: 标签中不包含任何护肤相关关键词（{', '.join(skincare_keywords)}）的达人\n\n")
        
        f.write("### 6.1 '护肤' 中的无关达人\n\n")
        f.write(f"- 总数: {len(orig_unrelated)} 人\n")
        f.write(f"- 占比: {len(orig_unrelated)/len(orig_ids)*100:.2f}%\n\n")
        
        if len(orig_unrelated) > 0:
            f.write("前20个无关达人示例:\n\n")
            f.write("| 昵称 | 标签 |\n")
            f.write("|------|------|\n")
            for aid in list(orig_unrelated)[:20]:
                info = orig_author_tags[aid]
                tags_str = ', '.join(info['tags']) if info['tags'] else '无标签'
                f.write(f"| {info['nick_name']} | {tags_str} |\n")
            f.write("\n")
        
        f.write("### 6.2 '护肤保养' 中的无关达人\n\n")
        f.write(f"- 总数: {len(maint_unrelated)} 人\n")
        f.write(f"- 占比: {len(maint_unrelated)/len(maint_ids)*100:.2f}%\n\n")
        
        if len(maint_unrelated) > 0:
            f.write("前20个无关达人示例:\n\n")
            f.write("| 昵称 | 标签 |\n")
            f.write("|------|------|\n")
            for aid in list(maint_unrelated)[:20]:
                info = maint_author_tags[aid]
                tags_str = ', '.join(info['tags']) if info['tags'] else '无标签'
                f.write(f"| {info['nick_name']} | {tags_str} |\n")
            f.write("\n")
        
        # 七、结论与建议
        f.write("## 七、结论与建议\n\n")
        
        overlap_rate = len(overlap_ids) / len(orig_ids) * 100
        orig_skincare_rate = sum(orig_skincare_tags.values()) / len(orig_ids) * 100
        maint_skincare_rate = sum(maint_skincare_tags.values()) / len(maint_ids) * 100
        
        f.write(f"1. **数据重合度**: {overlap_rate:.2f}%，说明")
        if overlap_rate > 80:
            f.write("'护肤保养'基本是'护肤'的子集\n")
        elif overlap_rate > 50:
            f.write("两者有较高重合度，但'护肤保养'更精准\n")
        else:
            f.write("两者差异较大，可互补使用\n")
        
        f.write(f"\n2. **护肤相关度对比**:\n")
        f.write(f"   - 护肤: {orig_skincare_rate:.2f}%\n")
        f.write(f"   - 护肤保养: {maint_skincare_rate:.2f}%\n")
        f.write(f"   - {'✅ 护肤保养' if maint_skincare_rate > orig_skincare_rate else '⚠️ 护肤'} 相关度更高\n")
        
        f.write(f"\n3. **无关达人占比**:\n")
        f.write(f"   - 护肤: {len(orig_unrelated)/len(orig_ids)*100:.2f}%\n")
        f.write(f"   - 护肤保养: {len(maint_unrelated)/len(maint_ids)*100:.2f}%\n")
        
        f.write(f"\n4. **目标达人查找**: ")
        if target_author_found['in_original'] or target_author_found['in_maintenance']:
            f.write("✅ 技术员小星星已找到\n")
        else:
            f.write("❌ 技术员小星星未找到\n")
        
        f.write("\n---\n\n")
        f.write(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    print(f"✅ 对比报告已生成: {report_path}")
    return report_path


def main():
    """主函数"""
    print("\n" + "="*80)
    print("继续获取'护肤保养'数据并进行详细对比分析")
    print("="*80 + "\n")
    
    try:
        # 1. 加载 API Key
        api_key = load_api_key()
        
        # 2. 设置目录
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / 'output'
        
        maintenance_dir = output_dir / 'keyword_护肤保养'
        original_detail_dir = output_dir / 'detail'
        
        # 3. 继续获取"护肤保养"数据到28页
        print("⏳ 继续获取'护肤保养'数据...\n")
        fetch_missing_pages('护肤保养', 28, maintenance_dir, api_key)
        
        # 4. 加载所有数据
        print("\n📊 加载数据进行对比分析...\n")
        
        original_authors = load_all_authors(original_detail_dir)
        maintenance_authors = load_all_authors(maintenance_dir / 'detail')
        
        print(f"✅ 护肤: {len(original_authors)} 人")
        print(f"✅ 护肤保养: {len(maintenance_authors)} 人\n")
        
        # 5. 查找目标达人
        print("🔍 查找目标达人'技术员小星星'...\n")
        
        target_in_orig = find_target_author(original_authors, '技术员小星星')
        target_in_maint = find_target_author(maintenance_authors, '技术员小星星')
        
        target_author_found = {
            'in_original': target_in_orig is not None,
            'original_data': target_in_orig,
            'in_maintenance': target_in_maint is not None,
            'maintenance_data': target_in_maint
        }
        
        if target_in_orig:
            print(f"✅ 在'护肤'中找到: {target_in_orig.get('attribute_datas', {}).get('nick_name')}")
        else:
            print(f"❌ 在'护肤'中未找到")
        
        if target_in_maint:
            print(f"✅ 在'护肤保养'中找到: {target_in_maint.get('attribute_datas', {}).get('nick_name')}")
        else:
            print(f"❌ 在'护肤保养'中未找到")
        
        print()
        
        # 6. 生成对比报告
        print("📝 生成详细对比报告...\n")
        report_path = generate_comparison_report(
            original_authors, 
            maintenance_authors,
            target_author_found,
            output_dir
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

