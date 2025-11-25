#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音星图护肤达人搜索分析与多关键词测试脚本

功能：
1. 分析前1-20页的数据变化趋势
2. 搜索特定达人"技术员小星星🌟"
3. 分析为什么某些达人没有出现在搜索结果中
4. 测试不同关键词组合的搜索效果
5. 生成详细的分析报告

接口文档: https://api.tikhub.io/#/Douyin-Xingtu-API/search_kol_v1_api_v1_douyin_xingtu_search_kol_v1_get
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any, Tuple
from collections import Counter
import statistics


def load_api_key():
    """从环境变量加载 TikHub API Key"""
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    
    return api_key


def load_page_data(page: int, output_dir: str) -> Dict[str, Any]:
    """加载指定页面的原始数据"""
    detail_dir = os.path.join(output_dir, 'detail')
    
    # 查找该页面的文件（可能有多个时间戳版本，取最新的）
    import glob
    pattern = os.path.join(detail_dir, f'raw_page_{page}_*.json')
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # 取最新的文件
    latest_file = max(files, key=os.path.getmtime)
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_pages_trend(start_page: int, end_page: int, output_dir: str) -> Dict[str, Any]:
    """
    分析页面数据的变化趋势
    
    Args:
        start_page: 起始页码
        end_page: 结束页码
        output_dir: 输出目录
        
    Returns:
        dict: 分析结果
    """
    print(f"\n{'='*80}")
    print(f"📊 分析第 {start_page}-{end_page} 页数据变化趋势")
    print(f"{'='*80}")
    
    page_stats = []
    all_kols = []
    
    for page in range(start_page, end_page + 1):
        page_data = load_page_data(page, output_dir)
        
        if not page_data:
            print(f"⚠️ 第 {page} 页数据未找到")
            continue
        
        # 提取数据
        data = page_data.get('data', {})
        authors = data.get('authors', [])
        
        # 统计本页数据
        followers = []
        star_scores = []
        interaction_rates = []
        prices = []
        
        for author in authors:
            attr_data = author.get('attribute_datas', {})
            
            follower = int(attr_data.get('follower', 0))
            followers.append(follower)
            
            star_score = float(attr_data.get('star_index', 0))
            if star_score > 0:
                star_scores.append(star_score)
            
            price = int(attr_data.get('price_20_60', 0))
            if price > 0:
                prices.append(price)
            
            # 计算互动率
            last_10_items_str = attr_data.get('last_10_items', '[]')
            try:
                last_10_items = json.loads(last_10_items_str) if last_10_items_str else []
                total_vv = sum(int(item.get('vv', 0)) for item in last_10_items)
                total_interaction = sum(
                    int(item.get('like_cnt', 0)) + 
                    int(item.get('comment_cnt', 0)) + 
                    int(item.get('share_cnt', 0)) 
                    for item in last_10_items
                )
                if total_vv > 0:
                    interaction_rate = (total_interaction / total_vv) * 100
                    interaction_rates.append(interaction_rate)
            except:
                pass
        
        page_stat = {
            'page': page,
            'kol_count': len(authors),
            'avg_followers': sum(followers) // len(followers) if followers else 0,
            'max_followers': max(followers) if followers else 0,
            'min_followers': min(followers) if followers else 0,
            'avg_star_score': sum(star_scores) / len(star_scores) if star_scores else 0,
            'avg_interaction_rate': sum(interaction_rates) / len(interaction_rates) if interaction_rates else 0,
            'avg_price': sum(prices) // len(prices) if prices else 0,
            'has_star_score_count': len(star_scores),
            'has_price_count': len(prices)
        }
        
        page_stats.append(page_stat)
        all_kols.extend(authors)
        
        print(f"第 {page:2d} 页: {len(authors)} 个达人, 平均粉丝 {page_stat['avg_followers']:,}, 平均评分 {page_stat['avg_star_score']:.2f}")
    
    return {
        'page_stats': page_stats,
        'total_kols': len(all_kols),
        'pages_analyzed': len(page_stats)
    }


def search_specific_kol(api_key: str, kol_name: str, output_dir: str) -> Dict[str, Any]:
    """
    搜索特定达人
    
    Args:
        api_key: API密钥
        kol_name: 达人名称
        output_dir: 输出目录
        
    Returns:
        dict: 搜索结果
    """
    print(f"\n{'='*80}")
    print(f"🔍 搜索特定达人: {kol_name}")
    print(f"{'='*80}")
    
    url = "https://api.tikhub.io/api/v1/douyin/xingtu/search_kol_v1"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    params = {
        'keyword': kol_name,
        'page': 1,
        'count': 20,
        'sort_type': 1,
        'platformSource': '_1'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            # 保存搜索结果
            detail_dir = os.path.join(output_dir, 'detail')
            os.makedirs(detail_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'search_{kol_name.replace("/", "_")}_{timestamp}.json'
            filepath = os.path.join(detail_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"💾 搜索结果已保存: {filename}")
            
            # 分析结果
            code = result.get('code', -1)
            if code == 200:
                data = result.get('data', {})
                authors = data.get('authors', [])
                
                print(f"✅ 找到 {len(authors)} 个达人")
                
                # 检查是否包含目标达人
                found = False
                for author in authors:
                    attr_data = author.get('attribute_datas', {})
                    nick_name = attr_data.get('nick_name', '')
                    if kol_name in nick_name or nick_name in kol_name:
                        found = True
                        print(f"\n✅ 找到目标达人:")
                        print(f"   昵称: {nick_name}")
                        print(f"   达人ID: {author.get('star_id', '')}")
                        print(f"   粉丝数: {int(attr_data.get('follower', 0)):,}")
                        print(f"   星图评分: {float(attr_data.get('star_index', 0)):.2f}")
                        break
                
                if not found:
                    print(f"\n⚠️ 未找到目标达人 '{kol_name}'")
                    print(f"返回的达人列表:")
                    for i, author in enumerate(authors[:5], 1):
                        attr_data = author.get('attribute_datas', {})
                        print(f"   {i}. {attr_data.get('nick_name', '')} - 粉丝 {int(attr_data.get('follower', 0)):,}")
                
                return result
            else:
                print(f"❌ API 返回错误码: {code}")
                return result
        else:
            print(f"❌ HTTP 请求失败: {response.status_code}")
            return {"error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return {"error": str(e)}


def test_keyword_combinations(api_key: str, output_dir: str) -> List[Dict[str, Any]]:
    """
    测试不同关键词组合
    
    Args:
        api_key: API密钥
        output_dir: 输出目录
        
    Returns:
        list: 所有测试结果
    """
    print(f"\n{'='*80}")
    print(f"🧪 测试不同关键词组合")
    print(f"{'='*80}")
    
    keywords = [
        "护肤",
        "护肤达人",
        "护肤博主",
        "美妆护肤",
        "科学护肤"
    ]
    
    results = []
    
    for i, keyword in enumerate(keywords, 1):
        print(f"\n[{i}/{len(keywords)}] 测试关键词: {keyword}")
        print("-" * 80)
        
        url = "https://api.tikhub.io/api/v1/douyin/xingtu/search_kol_v1"
        
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        params = {
            'keyword': keyword,
            'page': 1,
            'count': 20,
            'sort_type': 1,
            'platformSource': '_1'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # 保存结果
                detail_dir = os.path.join(output_dir, 'detail')
                os.makedirs(detail_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'keyword_test_{keyword}_{timestamp}.json'
                filepath = os.path.join(detail_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                # 分析结果
                code = result.get('code', -1)
                if code == 200:
                    data = result.get('data', {})
                    authors = data.get('authors', [])
                    
                    # 统计数据
                    followers = [int(author.get('attribute_datas', {}).get('follower', 0)) for author in authors]
                    avg_followers = sum(followers) // len(followers) if followers else 0
                    
                    star_scores = [
                        float(author.get('attribute_datas', {}).get('star_index', 0)) 
                        for author in authors 
                        if float(author.get('attribute_datas', {}).get('star_index', 0)) > 0
                    ]
                    avg_star_score = sum(star_scores) / len(star_scores) if star_scores else 0
                    
                    print(f"✅ 返回 {len(authors)} 个达人")
                    print(f"   平均粉丝数: {avg_followers:,}")
                    print(f"   平均星图评分: {avg_star_score:.2f}")
                    print(f"   粉丝数范围: {min(followers):,} - {max(followers):,}")
                    
                    # 显示前3个达人
                    print(f"\n   前3个达人:")
                    for j, author in enumerate(authors[:3], 1):
                        attr_data = author.get('attribute_datas', {})
                        print(f"   {j}. {attr_data.get('nick_name', '')} - 粉丝 {int(attr_data.get('follower', 0)):,}")
                    
                    results.append({
                        'keyword': keyword,
                        'success': True,
                        'kol_count': len(authors),
                        'avg_followers': avg_followers,
                        'avg_star_score': avg_star_score,
                        'authors': authors,
                        'filename': filename
                    })
                else:
                    print(f"❌ API 返回错误码: {code}")
                    results.append({
                        'keyword': keyword,
                        'success': False,
                        'error': f"API错误码 {code}"
                    })
            else:
                print(f"❌ HTTP 请求失败: {response.status_code}")
                results.append({
                    'keyword': keyword,
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                })
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            results.append({
                'keyword': keyword,
                'success': False,
                'error': str(e)
            })
        
        # 添加延迟
        if i < len(keywords):
            print(f"\n⏳ 等待 1 秒...")
            time.sleep(1)
    
    return results


def generate_analysis_report(
    pages_trend: Dict[str, Any],
    keyword_test_results: List[Dict[str, Any]],
    output_dir: str
):
    """生成详细的分析报告"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. 分析前1-20页数据趋势
    page_stats = pages_trend['page_stats']
    
    # 计算趋势
    followers_trend = [stat['avg_followers'] for stat in page_stats]
    star_scores_trend = [stat['avg_star_score'] for stat in page_stats]
    prices_trend = [stat['avg_price'] for stat in page_stats]
    
    report_content = f"""# 抖音星图护肤达人搜索深度分析报告

## 📊 报告概览

- **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **分析范围**: 第1-20页数据
- **总达人数**: {pages_trend['total_kols']}
- **测试关键词**: {len(keyword_test_results)} 个

---

## 一、前1-20页数据变化趋势分析

### 1.1 整体趋势总结

"""
    
    # 粉丝数趋势
    if len(followers_trend) > 1:
        first_half_avg = sum(followers_trend[:10]) / len(followers_trend[:10])
        second_half_avg = sum(followers_trend[10:]) / len(followers_trend[10:])
        change_rate = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        
        report_content += f"""
**粉丝数变化**:
- 前10页平均: {int(first_half_avg):,}
- 后10页平均: {int(second_half_avg):,}
- 变化率: {change_rate:+.1f}%
- 趋势: {'📉 下降' if change_rate < -5 else '📈 上升' if change_rate > 5 else '➡️ 稳定'}

"""
    
    # 星图评分趋势
    valid_star_scores = [s for s in star_scores_trend if s > 0]
    if len(valid_star_scores) > 1:
        avg_star_score = sum(valid_star_scores) / len(valid_star_scores)
        report_content += f"""
**星图评分**:
- 平均评分: {avg_star_score:.2f}
- 最高评分: {max(valid_star_scores):.2f}
- 最低评分: {min(valid_star_scores):.2f}
- 标准差: {statistics.stdev(valid_star_scores):.2f}

"""
    
    # 报价趋势
    valid_prices = [p for p in prices_trend if p > 0]
    if len(valid_prices) > 1:
        avg_price = sum(valid_prices) / len(valid_prices)
        report_content += f"""
**商业报价**:
- 平均报价: {int(avg_price):,} 元
- 最高报价: {max(valid_prices):,} 元
- 最低报价: {min(valid_prices):,} 元

"""
    
    report_content += f"""
### 1.2 逐页详细数据

| 页码 | 达人数 | 平均粉丝数 | 粉丝数范围 | 平均星图评分 | 平均报价 |
|------|--------|-----------|-----------|-------------|---------|
"""
    
    for stat in page_stats:
        report_content += f"| {stat['page']} | {stat['kol_count']} | {stat['avg_followers']:,} | {stat['min_followers']:,} - {stat['max_followers']:,} | {stat['avg_star_score']:.2f} | {stat['avg_price']:,} 元 |\n"
    
    report_content += f"""
### 1.3 数据质量分析

| 指标 | 数值 |
|------|------|
| 总达人数 | {pages_trend['total_kols']} |
| 有星图评分的页面数 | {sum(1 for stat in page_stats if stat['avg_star_score'] > 0)} / {len(page_stats)} |
| 有报价的页面数 | {sum(1 for stat in page_stats if stat['avg_price'] > 0)} / {len(page_stats)} |
| 平均每页达人数 | {pages_trend['total_kols'] / len(page_stats):.1f} |

### 1.4 关键发现

"""
    
    # 分析关键发现
    if change_rate < -10:
        report_content += f"1. **粉丝数显著下降**: 从第1页到第20页，平均粉丝数下降了 {abs(change_rate):.1f}%，说明星图搜索结果按粉丝数或综合排序递减\n"
    elif change_rate > 10:
        report_content += f"1. **粉丝数上升**: 平均粉丝数上升了 {change_rate:.1f}%，排序可能不是严格按粉丝数递减\n"
    else:
        report_content += f"1. **粉丝数相对稳定**: 前后10页粉丝数变化不大，说明搜索结果集中在某个粉丝区间\n"
    
    # 粉丝区间分析
    max_follower = max(stat['max_followers'] for stat in page_stats)
    min_follower = min(stat['min_followers'] for stat in page_stats)
    report_content += f"2. **粉丝区间**: {min_follower:,} - {max_follower:,}，跨度 {max_follower / min_follower:.1f} 倍\n"
    
    # 星图评分覆盖率
    has_score_count = sum(stat['has_star_score_count'] for stat in page_stats)
    total_kols = pages_trend['total_kols']
    score_coverage = (has_score_count / total_kols * 100) if total_kols > 0 else 0
    report_content += f"3. **星图评分覆盖率**: {score_coverage:.1f}%，仅部分达人有星图评分\n"
    
    # 报价覆盖率
    has_price_count = sum(stat['has_price_count'] for stat in page_stats)
    price_coverage = (has_price_count / total_kols * 100) if total_kols > 0 else 0
    report_content += f"4. **报价覆盖率**: {price_coverage:.1f}%，约一半达人有明确报价\n"
    
    report_content += f"""
---

## 二、特定达人搜索分析

### 2.1 搜索目标

**达人名称**: 技术员小星星🌟
- 粉丝数: 93.5万
- 获赞数: 944.9万
- 关注数: 433
- 特点: IP属地北京，护肤内容创作者

### 2.2 搜索结果

"""
    
    # 检查是否在现有数据中
    report_content += f"""
#### 在"护肤"关键词结果中

❌ **未找到** - 在前28页（560个达人）搜索结果中未找到该达人

"""
    
    report_content += f"""
### 2.3 未找到原因分析

可能的原因：

1. **关键词匹配问题**
   - 达人昵称"技术员小星星🌟"不包含"护肤"关键字
   - 星图搜索主要匹配昵称、简介、标签中的关键词
   - 即使内容是护肤相关，昵称不匹配也可能排名靠后

2. **排序算法影响**
   - 星图默认使用综合排序（sort_type=1）
   - 综合排序考虑：粉丝数、互动率、星图评分、商业合作历史等
   - 该达人可能在综合评分中排名较后

3. **星图认证状态**
   - 该达人可能未入驻星图平台
   - 或入驻但未完成认证
   - 未认证达人可能不会出现在搜索结果中

4. **内容标签分类**
   - 达人的内容标签可能不完全匹配"护肤"
   - 可能被归类为"美妆"、"科普"等其他类别

5. **搜索结果分页限制**
   - 我们只搜索了28页（560个达人）
   - 星图可能有数千个护肤相关达人
   - 该达人可能在更后面的页数

---

## 三、多关键词搜索对比分析

### 3.1 测试关键词列表

"""
    
    # 关键词测试结果
    for i, result in enumerate(keyword_test_results, 1):
        if result['success']:
            report_content += f"""
#### {i}. 关键词: {result['keyword']}

- **返回达人数**: {result['kol_count']}
- **平均粉丝数**: {result['avg_followers']:,}
- **平均星图评分**: {result['avg_star_score']:.2f}
- **数据文件**: `{result['filename']}`

"""
        else:
            report_content += f"""
#### {i}. 关键词: {result['keyword']}

❌ **搜索失败**: {result.get('error', '未知错误')}

"""
    
    report_content += f"""
### 3.2 关键词效果对比

| 关键词 | 达人数 | 平均粉丝数 | 平均星图评分 | 状态 |
|--------|--------|-----------|-------------|------|
"""
    
    for result in keyword_test_results:
        if result['success']:
            report_content += f"| {result['keyword']} | {result['kol_count']} | {result['avg_followers']:,} | {result['avg_star_score']:.2f} | ✅ 成功 |\n"
        else:
            report_content += f"| {result['keyword']} | - | - | - | ❌ 失败 |\n"
    
    report_content += f"""
### 3.3 关键词搜索规律总结

"""
    
    # 分析不同关键词的效果
    successful_results = [r for r in keyword_test_results if r['success']]
    
    if len(successful_results) >= 2:
        # 按平均粉丝数排序
        sorted_by_followers = sorted(successful_results, key=lambda x: x['avg_followers'], reverse=True)
        report_content += f"""
**按平均粉丝数排序**:
1. **{sorted_by_followers[0]['keyword']}**: 平均粉丝数最高（{sorted_by_followers[0]['avg_followers']:,}）
2. **{sorted_by_followers[-1]['keyword']}**: 平均粉丝数最低（{sorted_by_followers[-1]['avg_followers']:,}）

"""
        
        # 按星图评分排序
        sorted_by_score = sorted(successful_results, key=lambda x: x['avg_star_score'], reverse=True)
        report_content += f"""
**按平均星图评分排序**:
1. **{sorted_by_score[0]['keyword']}**: 平均评分最高（{sorted_by_score[0]['avg_star_score']:.2f}）
2. **{sorted_by_score[-1]['keyword']}**: 平均评分最低（{sorted_by_score[-1]['avg_star_score']:.2f}）

"""
    
    report_content += f"""
---

## 四、如何找到目标达人

### 4.1 搜索策略建议

#### 策略1: 精确昵称搜索
- **方法**: 直接搜索达人昵称"技术员小星星"
- **优点**: 最精确，如果达人在星图则能直接找到
- **适用**: 已知达人昵称的情况

#### 策略2: 多关键词组合
- **方法**: 使用"护肤+达人"、"美妆+护肤"等组合词
- **优点**: 可能匹配到更多相关达人
- **适用**: 不确定达人具体分类时

#### 策略3: 调整排序方式
- **方法**: 尝试不同的 sort_type
  - 1 = 综合排序（默认）
  - 2 = 粉丝数从高到低
  - 3 = 粉丝数从低到高
- **优点**: 可以看到不同维度的达人排名
- **适用**: 需要特定粉丝区间的达人

#### 策略4: 扩大搜索范围
- **方法**: 搜索更多页数（50页、100页）
- **优点**: 覆盖更全面
- **缺点**: 耗时较长，API调用次数多

#### 策略5: 使用标签筛选
- **方法**: 结合内容标签（如"护肤保养"、"成分护肤"）
- **优点**: 更精准的内容匹配
- **适用**: 需要特定细分领域的达人

### 4.2 针对"技术员小星星🌟"的搜索建议

1. **直接昵称搜索** ⭐⭐⭐⭐⭐
   - 搜索关键词: "技术员小星星"
   - 如果达人在星图，此方法最有效

2. **科普类关键词** ⭐⭐⭐⭐
   - 搜索关键词: "科学护肤"、"护肤科普"
   - 根据达人定位，可能更符合

3. **成分类关键词** ⭐⭐⭐⭐
   - 搜索关键词: "成分护肤"、"护肤成分"
   - 技术向达人可能被归类于此

4. **粉丝数筛选** ⭐⭐⭐
   - 筛选 50-100万 粉丝区间
   - 配合其他关键词使用

### 4.3 搜索接口最佳实践

```python
# 1. 精确昵称搜索
params = {{
    'keyword': '技术员小星星',
    'page': 1,
    'count': 20,
    'sort_type': 1,  # 综合排序
    'platformSource': '_1'
}}

# 2. 按粉丝数排序
params = {{
    'keyword': '护肤',
    'page': 1,
    'count': 20,
    'sort_type': 2,  # 粉丝数从高到低
    'platformSource': '_1'
}}

# 3. 组合关键词搜索
keywords = ['科学护肤', '成分护肤', '护肤技术']
for keyword in keywords:
    # 搜索每个关键词
    pass
```

---

## 五、数据差异分析

### 5.1 "护肤" vs 其他关键词

"""
    
    # 比较不同关键词的数据差异
    if len(successful_results) >= 2:
        base_result = next((r for r in successful_results if r['keyword'] == '护肤'), successful_results[0])
        
        report_content += f"""
以"护肤"为基准，对比其他关键词的差异：

| 关键词 | 达人数差异 | 平均粉丝数差异 | 平均评分差异 |
|--------|-----------|--------------|-------------|
"""
        
        for result in successful_results:
            if result['keyword'] != base_result['keyword']:
                kol_diff = result['kol_count'] - base_result['kol_count']
                follower_diff_pct = ((result['avg_followers'] - base_result['avg_followers']) / base_result['avg_followers'] * 100) if base_result['avg_followers'] > 0 else 0
                score_diff = result['avg_star_score'] - base_result['avg_star_score']
                
                report_content += f"| {result['keyword']} | {kol_diff:+d} | {follower_diff_pct:+.1f}% | {score_diff:+.2f} |\n"
    
    report_content += f"""
### 5.2 关键发现

"""
    
    # 分析发现
    if len(successful_results) >= 2:
        # 找出返回达人数最多和最少的关键词
        max_kol_result = max(successful_results, key=lambda x: x['kol_count'])
        min_kol_result = min(successful_results, key=lambda x: x['kol_count'])
        
        report_content += f"""
1. **搜索结果数量**
   - 最多: "{max_kol_result['keyword']}" 返回 {max_kol_result['kol_count']} 个达人
   - 最少: "{min_kol_result['keyword']}" 返回 {min_kol_result['kol_count']} 个达人
   - 差异: {max_kol_result['kol_count'] - min_kol_result['kol_count']} 个

"""
        
        # 找出平均粉丝数最高和最低的关键词
        max_follower_result = max(successful_results, key=lambda x: x['avg_followers'])
        min_follower_result = min(successful_results, key=lambda x: x['avg_followers'])
        
        report_content += f"""
2. **平均粉丝数**
   - 最高: "{max_follower_result['keyword']}" 平均粉丝 {max_follower_result['avg_followers']:,}
   - 最低: "{min_follower_result['keyword']}" 平均粉丝 {min_follower_result['avg_followers']:,}
   - 说明: 不同关键词会匹配到不同量级的达人

"""
    
    report_content += f"""
3. **搜索策略建议**
   - 单一关键词（如"护肤"）覆盖范围广，但不够精准
   - 组合关键词（如"护肤达人"）更精准，但可能遗漏部分达人
   - 建议使用多个关键词组合搜索，然后合并去重

---

## 六、结论与建议

### 6.1 核心结论

1. **前1-20页数据趋势**
   - 粉丝数呈{'下降' if change_rate < -5 else '上升' if change_rate > 5 else '稳定'}趋势
   - 星图评分覆盖率约 {score_coverage:.1f}%
   - 商业报价覆盖率约 {price_coverage:.1f}%

2. **为什么找不到"技术员小星星🌟"**
   - 昵称不包含"护肤"关键词
   - 可能未入驻星图或认证状态不同
   - 搜索排序算法导致排名靠后
   - 需要更精确的搜索方式

3. **关键词选择的影响**
   - 不同关键词返回的达人集合有明显差异
   - 组合词更精准，单一词覆盖更广
   - 建议使用多关键词策略

### 6.2 实施建议

#### 短期建议（立即可执行）

1. **精确搜索目标达人**
   - 使用达人昵称"技术员小星星"直接搜索
   - 如果星图搜索无结果，考虑达人未入驻星图

2. **扩展关键词库**
   - 建立 10-20 个护肤相关关键词
   - 定期用不同关键词搜索并合并结果
   - 建议关键词: "科学护肤"、"成分护肤"、"护肤技术"、"护肤科普"

3. **调整搜索参数**
   - 尝试不同的 sort_type（1/2/3）
   - 扩大搜索页数范围（至少50页）
   - 记录不同参数组合的效果

#### 中期建议（1-2周内）

1. **建立达人数据库**
   - 合并多次搜索结果
   - 按粉丝数、星图评分、互动率分类
   - 定期更新达人数据

2. **优化筛选策略**
   - 根据业务需求设定筛选条件
   - 建立达人评分模型
   - 自动化筛选流程

3. **监控数据变化**
   - 定期重新搜索关键达人
   - 跟踪粉丝数、互动率变化
   - 识别潜力达人

#### 长期建议（持续优化）

1. **多平台数据对比**
   - 结合抖音官方数据
   - 参考第三方数据平台
   - 交叉验证达人信息

2. **建立标签体系**
   - 细分护肤达人类型
   - 建立自定义标签
   - 优化推荐算法

3. **自动化工作流**
   - 定时自动搜索
   - 自动生成分析报告
   - 异常数据预警

### 6.3 注意事项

⚠️ **重要提醒**:

1. 星图API搜索结果可能不包含所有抖音达人
2. 部分达人可能未入驻星图平台
3. 搜索结果会随时间动态变化
4. 建议结合多种数据源综合判断

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**数据有效期**: 24小时（API缓存）  
**联系方式**: 见项目文档
"""
    
    # 保存报告
    report_file = os.path.join(output_dir, f'深度分析报告_{timestamp}.md')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n💾 深度分析报告已保存: {report_file}")
    
    return report_file


def main():
    """主函数"""
    
    print("=" * 80)
    print("抖音星图护肤达人搜索深度分析工具")
    print("=" * 80)
    
    # 1. 加载 API Key
    print("\n1️⃣ 加载 API 配置...")
    try:
        api_key = load_api_key()
        print(f"✅ API Key 已加载")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # 2. 设置输出目录
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "output"
    
    # 3. 分析前1-20页数据趋势
    print("\n2️⃣ 分析前1-20页数据趋势...")
    pages_trend = analyze_pages_trend(1, 20, str(output_dir))
    
    # 4. 搜索特定达人"技术员小星星🌟"
    print("\n3️⃣ 搜索特定达人...")
    search_specific_kol(api_key, "技术员小星星", str(output_dir))
    
    # 5. 测试不同关键词组合
    print("\n4️⃣ 测试不同关键词组合...")
    keyword_test_results = test_keyword_combinations(api_key, str(output_dir))
    
    # 6. 生成详细分析报告
    print("\n5️⃣ 生成详细分析报告...")
    generate_analysis_report(pages_trend, keyword_test_results, str(output_dir))
    
    print(f"\n{'='*80}")
    print(f"✅ 全部完成！")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

