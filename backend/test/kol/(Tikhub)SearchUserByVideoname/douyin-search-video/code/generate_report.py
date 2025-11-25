#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
汇总分析两个关键词搜索结果的人物画像和重合度
1. 汇总 "护肤保养" (13页) 作者信息
2. 汇总 "皮肤好 专家" (14页) 作者信息
3. 输出重合分析报告
4. 分析作者画像 (基于昵称、ID等基础信息，如果有更多数据可扩展)

注意：数据库重合查询已通过 MCP 完成，结果为 0 (gg_xingtu_kol_base_info)。
脚本将生成最终的 JSON 报告。

作者: AI Agent
创建时间: 2025-11-24
"""

import json
from pathlib import Path
from collections import Counter

def extract_author_personas(directory):
    """从指定目录的JSON文件中提取作者画像信息"""
    authors = {} # uid -> info dict
    
    files = list(Path(directory).glob("video_search_page_*.json"))
    print(f"📂 正在处理目录: {directory.name} (共 {len(files)} 个文件)")
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            api_data = data.get('data', [])
            items = []
            
            if isinstance(api_data, list):
                items = api_data
            elif isinstance(api_data, dict):
                items = api_data.get('data') or api_data.get('aweme_list') or []
            
            for item in items:
                author = None
                if 'author' in item:
                    author = item['author']
                elif 'aweme_info' in item and 'author' in item['aweme_info']:
                    author = item['aweme_info']['author']
                
                if author:
                    uid = str(author.get('uid', ''))
                    if not uid: continue
                    
                    if uid not in authors:
                        authors[uid] = {
                            "uid": uid,
                            "nickname": author.get('nickname', 'Unknown'),
                            "short_id": author.get('short_id'),
                            "unique_id": author.get('unique_id'),
                            "follower_count": author.get('follower_count'), # 注意 API 是否返回此字段
                            "signature": author.get('signature'),
                            "verify_info": author.get('custom_verify', ''),
                            "enterprise_verify": author.get('enterprise_verify_reason', ''),
                            "avatar": author.get('avatar_thumb', {}).get('url_list', [''])[0]
                        }
                        
        except Exception as e:
            print(f"⚠️ 读取文件 {file_path.name} 失败: {e}")
            
    print(f"   ✅ 提取到 {len(authors)} 个唯一作者")
    return authors

def analyze_personas(authors):
    """简单分析作者画像关键词"""
    keywords = []
    verify_types = []
    
    for uid, info in authors.items():
        nickname = info.get('nickname', '')
        signature = info.get('signature', '')
        verify = info.get('verify_info', '') or info.get('enterprise_verify', '')
        
        # 简单的关键词提取逻辑
        text = f"{nickname} {signature} {verify}"
        
        if "医生" in text or "医师" in text or "博士" in text or "主任" in text:
            keywords.append("专业/医生")
        elif "护肤" in text or "美妆" in text:
            keywords.append("美妆/护肤博主")
        elif "测评" in text:
            keywords.append("测评博主")
        elif "品牌" in text or "旗舰店" in text or "官方" in text:
            keywords.append("品牌/机构")
        else:
            keywords.append("普通/其他")
            
        if verify:
            verify_types.append("已认证")
        else:
            verify_types.append("未认证")
            
    return {
        "category_distribution": dict(Counter(keywords)),
        "verify_distribution": dict(Counter(verify_types))
    }

def main():
    script_dir = Path(__file__).parent
    base_output_dir = script_dir.parent / 'output'
    
    dir_hufu = base_output_dir / 'keyword_护肤保养' / 'detail'
    dir_skin = base_output_dir / 'keyword_皮肤好_专家' / 'detail'
    
    # 1. 提取画像
    authors_hufu = extract_author_personas(dir_hufu)
    authors_skin = extract_author_personas(dir_skin)
    
    # 2. 分析画像
    persona_hufu = analyze_personas(authors_hufu)
    persona_skin = analyze_personas(authors_skin)
    
    # 3. 计算重合
    ids_hufu = set(authors_hufu.keys())
    ids_skin = set(authors_skin.keys())
    overlap_ids = ids_skin.intersection(ids_hufu)
    
    overlap_details = []
    for uid in overlap_ids:
        overlap_details.append(authors_skin[uid])
        
    # 4. 生成报告
    report = {
        "summary": {
            "keyword_1": "护肤保养",
            "count_1": len(ids_hufu),
            "keyword_2": "皮肤好 专家",
            "count_2": len(ids_skin),
            "overlap_count": len(overlap_ids),
            "overlap_rate_percent": len(overlap_ids) / len(ids_skin) * 100 if ids_skin else 0
        },
        "database_check": {
            "table": "gg_xingtu_kol_base_info",
            "match_count": 0,
            "note": "通过 MCP 查询，未发现重合作者"
        },
        "personas": {
            "护肤保养": persona_hufu,
            "皮肤好 专家": persona_skin
        },
        "overlap_authors_detail": overlap_details
    }
    
    output_file = base_output_dir / 'final_comparison_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ 最终对比报告已生成: {output_file.name}")
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    print("\n画像分布 (护肤保养):")
    print(json.dumps(persona_hufu, ensure_ascii=False, indent=2))
    print("\n画像分布 (皮肤好 专家):")
    print(json.dumps(persona_skin, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

