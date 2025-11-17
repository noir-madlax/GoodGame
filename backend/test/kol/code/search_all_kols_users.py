#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
搜索全部64个达人的抖音账号信息
使用 fetch_hot_account_search_list 接口
并实现智能筛选逻辑，找出真正的达人主账号

筛选策略：
1. 昵称匹配度（优先级最高）
2. 粉丝数（越多越可能是主账号）
3. 作品数（活跃度）
4. 点赞数（影响力）
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import time
from difflib import SequenceMatcher


def load_api_key():
    """从环境变量加载TikHub API Key"""
    backend_dir = Path(__file__).parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    return api_key


def load_kol_data(json_path: str) -> list:
    """加载达人数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    kols = data.get('kols_ranking', [])
    print(f"✅ 加载了 {len(kols)} 个达人数据")
    
    return kols


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    计算两个名字的相似度（0-1之间）
    
    Args:
        name1: 原始达人名字
        name2: 搜索结果中的昵称
        
    Returns:
        相似度分数（0-1）
    """
    # 去除空格和特殊字符
    name1_clean = name1.strip().lower()
    name2_clean = name2.strip().lower()
    
    # 使用SequenceMatcher计算相似度
    similarity = SequenceMatcher(None, name1_clean, name2_clean).ratio()
    
    return similarity


def select_best_match(kol_name: str, user_list: list) -> dict:
    """
    从多个匹配账号中选择最佳匹配（真正的达人账号）
    
    筛选策略：
    1. 昵称匹配度（权重40%）- 完全匹配或高度相似
    2. 粉丝数（权重30%）- 粉丝越多，影响力越大
    3. 点赞数（权重20%）- 总点赞数反映受欢迎程度
    4. 作品数（权重10%）- 活跃度指标
    
    Args:
        kol_name: 原始达人名字
        user_list: 搜索返回的用户列表
        
    Returns:
        最佳匹配的用户信息（包含评分详情）
    """
    if not user_list:
        return None
    
    # 计算每个候选账号的综合评分
    scored_users = []
    
    # 先找出粉丝数、点赞数、作品数的最大值（用于归一化）
    max_fans = max([u.get('fans_cnt', 0) for u in user_list]) or 1
    max_likes = max([u.get('like_cnt', 0) for u in user_list]) or 1
    max_publish = max([u.get('publish_cnt', 0) for u in user_list]) or 1
    
    for user in user_list:
        nick_name = user.get('nick_name', '')
        fans_cnt = user.get('fans_cnt', 0)
        like_cnt = user.get('like_cnt', 0)
        publish_cnt = user.get('publish_cnt', 0)
        
        # 1. 昵称匹配度（0-1）
        name_similarity = calculate_name_similarity(kol_name, nick_name)
        
        # 2. 粉丝数归一化（0-1）
        fans_score = fans_cnt / max_fans
        
        # 3. 点赞数归一化（0-1）
        likes_score = like_cnt / max_likes
        
        # 4. 作品数归一化（0-1）
        publish_score = publish_cnt / max_publish
        
        # 综合评分（加权）
        total_score = (
            name_similarity * 0.40 +  # 昵称匹配度40%
            fans_score * 0.30 +        # 粉丝数30%
            likes_score * 0.20 +       # 点赞数20%
            publish_score * 0.10       # 作品数10%
        )
        
        # 保存评分详情
        user_with_score = {
            **user,  # 保留原始用户信息
            'match_score': {
                'total': round(total_score, 4),
                'name_similarity': round(name_similarity, 4),
                'fans_score': round(fans_score, 4),
                'likes_score': round(likes_score, 4),
                'publish_score': round(publish_score, 4)
            }
        }
        
        scored_users.append(user_with_score)
    
    # 按总分排序，选择得分最高的
    best_match = max(scored_users, key=lambda x: x['match_score']['total'])
    
    return best_match


def fetch_hot_account_search(api_key: str, keyword: str) -> dict:
    """调用热门账号搜索接口"""
    base_url = "https://api.tikhub.io/api/v1"
    endpoint = "/douyin/billboard/fetch_hot_account_search_list"
    url = f"{base_url}{endpoint}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    params = {
        'keyword': keyword,
        'cursor': 0
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"HTTP {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        return {"error": str(e)}


def search_all_kols(kols: list, api_key: str):
    """
    搜索所有达人的抖音账号
    
    Args:
        kols: 达人列表
        api_key: API密钥
        
    Returns:
        处理结果列表
    """
    results = []
    total = len(kols)
    
    print(f"\n{'='*70}")
    print(f"🔍 开始搜索全部 {total} 个达人的抖音账号")
    print(f"{'='*70}")
    
    # 统计数据
    success_count = 0
    found_count = 0
    multi_match_count = 0
    
    for idx, kol in enumerate(kols, 1):
        name = kol.get('name', 'Unknown')
        rank = kol.get('rank', 0)
        mention_count = kol.get('mention_count', 0)
        
        print(f"\n[{idx}/{total}] 排名#{rank} - {name}")
        print("-" * 70)
        
        # 调用搜索接口
        search_result = fetch_hot_account_search(api_key, name)
        
        # 处理结果
        result_entry = {
            "rank": rank,
            "name": name,
            "mention_count": mention_count,
            "platforms": kol.get('platforms', []),
            "characteristics": kol.get('characteristics', []),
            "professional_backgrounds": kol.get('professional_backgrounds', []),
            "search_timestamp": datetime.now().isoformat()
        }
        
        # 检查是否成功获取数据
        if isinstance(search_result, dict) and not search_result.get('error'):
            success_count += 1
            
            # 提取用户列表
            data_content = search_result.get('data', {})
            inner_data = data_content.get('data', {})
            user_list = inner_data.get('user_list', [])
            
            if user_list and len(user_list) > 0:
                found_count += 1
                
                print(f"   ✅ 找到 {len(user_list)} 个匹配账号")
                
                if len(user_list) > 1:
                    multi_match_count += 1
                
                # 选择最佳匹配
                best_match = select_best_match(name, user_list)
                
                if best_match:
                    match_score = best_match.get('match_score', {})
                    
                    print(f"   🎯 最佳匹配:")
                    print(f"      昵称: {best_match.get('nick_name')}")
                    print(f"      粉丝: {best_match.get('fans_cnt'):,}")
                    print(f"      作品: {best_match.get('publish_cnt')}")
                    print(f"      点赞: {best_match.get('like_cnt'):,}")
                    print(f"      user_id: {best_match.get('user_id')[:40]}...")
                    print(f"      匹配度: {match_score.get('total'):.2%} "
                          f"(昵称:{match_score.get('name_similarity'):.2%} "
                          f"粉丝:{match_score.get('fans_score'):.2%})")
                    
                    # 保存最佳匹配信息
                    result_entry['best_match'] = {
                        'user_id': best_match.get('user_id'),
                        'nick_name': best_match.get('nick_name'),
                        'fans_cnt': best_match.get('fans_cnt'),
                        'like_cnt': best_match.get('like_cnt'),
                        'publish_cnt': best_match.get('publish_cnt'),
                        'avatar_url': best_match.get('avatar_url'),
                        'match_score': match_score
                    }
                    
                    # 保存所有候选账号（前5个）
                    result_entry['all_candidates'] = user_list[:5]
                    result_entry['total_candidates'] = len(user_list)
                else:
                    print(f"   ⚠️ 无法选择最佳匹配")
                    result_entry['error'] = "无法选择最佳匹配"
            else:
                print(f"   ⚠️ 未找到匹配账号")
                result_entry['error'] = "未找到匹配账号"
        else:
            print(f"   ❌ 搜索失败: {search_result.get('error', 'Unknown error')}")
            result_entry['error'] = search_result.get('error', 'Unknown error')
        
        results.append(result_entry)
        
        # 每10个输出一次进度
        if idx % 10 == 0:
            print(f"\n📊 进度: {idx}/{total} ({idx/total*100:.1f}%) - "
                  f"成功:{found_count} 多匹配:{multi_match_count}")
        
        # 避免请求过快，每个请求间隔0.5秒
        if idx < total:
            time.sleep(0.5)
    
    # 最终统计
    print(f"\n{'='*70}")
    print(f"📊 搜索完成统计")
    print(f"{'='*70}")
    print(f"总计达人数: {total}")
    print(f"成功获取响应: {success_count} ({success_count/total*100:.1f}%)")
    print(f"找到匹配账号: {found_count} ({found_count/total*100:.1f}%)")
    print(f"多账号匹配: {multi_match_count} ({multi_match_count/total*100:.1f}%)")
    print(f"平均每人匹配账号数: {sum([r.get('total_candidates', 0) for r in results])/found_count:.1f}" if found_count > 0 else "N/A")
    
    return results


def generate_final_kol_accounts(results: list, output_path: str):
    """
    生成最终的达人账号汇总JSON
    只包含成功找到的真实达人账号
    
    Args:
        results: 搜索结果列表
        output_path: 输出文件路径
    """
    final_kols = []
    
    for result in results:
        # 只包含成功找到最佳匹配的达人
        if 'best_match' in result:
            best_match = result['best_match']
            
            kol_account = {
                "rank": result['rank'],
                "name": result['name'],
                "mention_count": result['mention_count'],
                "platforms": result['platforms'],
                "characteristics": result['characteristics'],
                "professional_backgrounds": result['professional_backgrounds'],
                "douyin_account": {
                    "user_id": best_match['user_id'],
                    "sec_uid": best_match['user_id'],  # user_id即为sec_uid
                    "nick_name": best_match['nick_name'],
                    "fans_count": best_match['fans_cnt'],
                    "like_count": best_match['like_cnt'],
                    "publish_count": best_match['publish_cnt'],
                    "avatar_url": best_match['avatar_url'],
                    "match_quality": {
                        "score": best_match['match_score']['total'],
                        "name_similarity": best_match['match_score']['name_similarity'],
                        "confidence": "high" if best_match['match_score']['total'] > 0.7 else 
                                     "medium" if best_match['match_score']['total'] > 0.5 else "low"
                    }
                },
                "search_info": {
                    "total_candidates": result.get('total_candidates', 0),
                    "search_timestamp": result['search_timestamp']
                }
            }
            
            final_kols.append(kol_account)
    
    # 准备输出数据
    output_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_kols_searched": len(results),
            "total_kols_found": len(final_kols),
            "success_rate": f"{len(final_kols)/len(results)*100:.1f}%",
            "data_source": "TikHub API - fetch_hot_account_search_list",
            "match_strategy": "综合评分（昵称40% + 粉丝30% + 点赞20% + 作品10%）"
        },
        "kol_accounts": final_kols
    }
    
    # 保存到文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 最终达人账号数据已保存到: {output_path}")
    print(f"   成功找到: {len(final_kols)}/{len(results)} 个达人的抖音账号")
    
    return output_data


def save_detailed_results(results: list, output_dir: str):
    """保存详细的搜索结果（包含所有候选账号）"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'all_kols_search_detailed_{timestamp}.json')
    
    output_data = {
        "search_metadata": {
            "search_date": datetime.now().isoformat(),
            "total_kols": len(results),
            "api_interface": "fetch_hot_account_search_list"
        },
        "detailed_results": results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细搜索结果已保存到: {output_file}")
    
    return output_file


def analyze_match_patterns(results: list):
    """
    分析匹配模式，回答为什么有多个匹配账号
    """
    print(f"\n{'='*70}")
    print(f"📈 匹配账号分析")
    print(f"{'='*70}")
    
    # 统计匹配数量分布
    match_counts = [r.get('total_candidates', 0) for r in results if 'total_candidates' in r]
    
    if match_counts:
        print(f"\n匹配账号数量分布:")
        print(f"  平均: {sum(match_counts)/len(match_counts):.1f} 个")
        print(f"  最多: {max(match_counts)} 个")
        print(f"  最少: {min(match_counts)} 个")
        
        # 按匹配数量分组
        single_match = sum(1 for c in match_counts if c == 1)
        multi_match = sum(1 for c in match_counts if c > 1)
        
        print(f"\n  单一匹配: {single_match} 个达人 ({single_match/len(match_counts)*100:.1f}%)")
        print(f"  多个匹配: {multi_match} 个达人 ({multi_match/len(match_counts)*100:.1f}%)")
    
    print(f"\n💡 多账号匹配的常见原因:")
    print(f"  1. 同名账号 - 不同人使用相似或相同的昵称")
    print(f"  2. 同一达人的多个账号 - 主号、小号、合作号等")
    print(f"  3. 模仿账号 - 蹭热度的山寨账号")
    print(f"  4. 昵称部分匹配 - 搜索算法返回相关账号")
    
    print(f"\n🎯 筛选策略:")
    print(f"  1. 昵称匹配度（40%权重）- 完全匹配或高度相似的优先")
    print(f"  2. 粉丝数（30%权重）- 粉丝越多，越可能是主账号")
    print(f"  3. 点赞数（20%权重）- 反映内容受欢迎程度")
    print(f"  4. 作品数（10%权重）- 活跃度指标")
    
    print(f"\n✅ 结论:")
    print(f"  - 通过综合评分，可以有效筛选出真正的达人主账号")
    print(f"  - 对于高匹配度（>70%）的结果，可信度很高")
    print(f"  - 对于低匹配度（<50%）的结果，建议人工复核")


def main():
    """主函数"""
    
    print("=" * 70)
    print("抖音达人账号批量搜索 - 智能匹配版本")
    print("=" * 70)
    
    # 1. 加载配置
    print("\n1️⃣ 加载配置...")
    try:
        api_key = load_api_key()
        print(f"✅ API Key已加载")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # 2. 加载达人数据
    print("\n2️⃣ 加载达人数据...")
    script_dir = Path(__file__).parent.parent
    kol_data_path = script_dir / "output" / "final_kol_data_20251113-163615.json"
    
    if not kol_data_path.exists():
        print(f"❌ 达人数据文件不存在: {kol_data_path}")
        return
    
    kols = load_kol_data(str(kol_data_path))
    
    # 3. 搜索所有达人
    print("\n3️⃣ 开始批量搜索...")
    results = search_all_kols(kols, api_key)
    
    # 4. 分析匹配模式
    analyze_match_patterns(results)
    
    # 5. 保存详细结果
    print("\n4️⃣ 保存结果...")
    output_dir = script_dir / "output" / "kol_user_ids"
    save_detailed_results(results, str(output_dir))
    
    # 6. 生成最终达人账号汇总
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    final_output_path = output_dir / f"final_kol_accounts_{timestamp}.json"
    final_data = generate_final_kol_accounts(results, str(final_output_path))
    
    print(f"\n✅ 全部完成！")
    print(f"   找到 {len(final_data['kol_accounts'])} 个真实达人账号")


if __name__ == "__main__":
    main()

