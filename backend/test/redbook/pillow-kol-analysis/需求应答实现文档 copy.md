# KOL 筛选需求应答实现文档

## 概述

本文档基于用户需求 (`request.md`) 和蒲公英 API 返回的数据，详细分析每个筛选需求点，包括：
- 需求理解
- 数据来源
- 处理方案

---

## 第一方面：通用数据维度

### 需求点 1：粉丝数量的增长趋势

#### 1.1 需求理解
评估博主的粉丝增长情况，判断账号是否处于上升期、平稳期还是下降期。增长趋势反映了博主的内容吸引力和账号健康度。

#### 1.2 数据来源
| API | 字段 | 说明 |
|-----|------|------|
| `kol_fans_trend` | `fansNumInc` | 30天粉丝增长数 |
| `kol_fans_trend` | `fansNumIncRate` | 30天粉丝增长率 |
| `kol_fans_trend` | `list` | 每日粉丝数列表（30天） |
| `kol_fans_summary` | `fansGrowthRate` | 粉丝增长率（百分比字符串） |
| `kol_fans_summary` | `fansGrowthBeyondRate` | 增长率超越同行百分比 |
| `kol_data_summary_v1/v2` | `fans30GrowthRate` | 30天粉丝增长率 |
| `kol_data_summary_v1/v2` | `fans30GrowthBeyondRate` | 增长率超越同行百分比 |

#### 1.3 处理方案

```python
def analyze_fans_growth_trend(kol_data):
    """分析粉丝增长趋势"""
    # 1. 获取30天粉丝趋势数据
    fans_trend = kol_data['apis']['kol_fans_trend']['data']
    fans_list = fans_trend['list']  # [{num: 8636, dateKey: "2025-11-09"}, ...]
    
    # 2. 计算关键指标
    result = {
        '30天增长数': fans_trend['fansNumInc'],
        '30天增长率': f"{fans_trend['fansNumIncRate'] * 100:.2f}%",
        '趋势判断': '',
        '日均增长': 0,
        '增长稳定性': ''
    }
    
    # 3. 计算日均增长
    if len(fans_list) >= 2:
        daily_changes = [fans_list[i]['num'] - fans_list[i-1]['num'] 
                        for i in range(1, len(fans_list))]
        result['日均增长'] = sum(daily_changes) / len(daily_changes)
        
        # 4. 计算增长稳定性（标准差）
        import statistics
        if len(daily_changes) > 1:
            std_dev = statistics.stdev(daily_changes)
            result['增长稳定性'] = '稳定' if std_dev < abs(result['日均增长']) else '波动较大'
    
    # 5. 趋势判断
    growth_rate = fans_trend['fansNumIncRate']
    if growth_rate > 0.1:
        result['趋势判断'] = '快速增长'
    elif growth_rate > 0.03:
        result['趋势判断'] = '稳定增长'
    elif growth_rate > 0:
        result['趋势判断'] = '缓慢增长'
    elif growth_rate == 0:
        result['趋势判断'] = '停滞'
    else:
        result['趋势判断'] = '下降'
    
    return result
```

**实际数据示例（椰椰小饭团）：**
- 30天粉丝增长：1842 人
- 增长率：21.33%
- 趋势：从 8636 → 10478（持续稳定增长）
- 判定：快速增长期，账号健康

---

### 需求点 2：发帖频率

#### 2.1 需求理解
评估博主的内容产出能力和活跃度。高频发帖的博主通常更容易保持粉丝粘性，但也要考虑内容质量。

#### 2.2 数据来源
| API | 字段 | 说明 |
|-----|------|------|
| `kol_note_list` | `list` | 笔记列表（含发布日期） |
| `kol_note_rate` | `noteNumber` | 近期笔记数量 |
| `kol_data_summary_v1/v2` | `noteNumber` | 笔记总数 |
| `kol_data_summary_v1/v2` | `activeDayInLast7` | 近7天活跃天数 |
| `kol_info` | `businessNoteCount` | 商业笔记数 |

#### 2.3 处理方案

```python
from datetime import datetime, timedelta
from collections import Counter

def analyze_posting_frequency(kol_data):
    """分析发帖频率"""
    note_list = kol_data['apis']['kol_note_list']['data']['list']
    
    # 1. 统计近30天发帖数
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    
    recent_notes = []
    for note in note_list:
        note_date = datetime.strptime(note['date'], '%Y-%m-%d')
        if note_date >= thirty_days_ago:
            recent_notes.append(note)
    
    # 2. 计算每周发帖数
    week_counts = Counter()
    for note in recent_notes:
        note_date = datetime.strptime(note['date'], '%Y-%m-%d')
        week_num = note_date.isocalendar()[1]
        week_counts[week_num] += 1
    
    avg_weekly = len(recent_notes) / 4 if len(recent_notes) > 0 else 0
    
    result = {
        '近30天发帖数': len(recent_notes),
        '平均每周发帖': round(avg_weekly, 1),
        '频率评级': '',
        '每周详情': dict(week_counts)
    }
    
    # 3. 频率评级
    if avg_weekly >= 5:
        result['频率评级'] = '高频（优秀）'
    elif avg_weekly >= 3:
        result['频率评级'] = '中高频（达标）'
    elif avg_weekly >= 1:
        result['频率评级'] = '低频（需关注）'
    else:
        result['频率评级'] = '极低频（不推荐）'
    
    return result
```

**实际数据示例（JellyBonnie）：**
- 近30天发帖：约14篇
- 平均每周：约3.5篇
- 频率评级：中高频（达标）

---

### 需求点 3：阅读、点赞、评论的平均值&中位数（过去一个月）

#### 3.1 需求理解
通过平均值和中位数两个维度评估博主的数据表现。中位数比平均值更能反映真实水平，避免被个别爆文拉高。

#### 3.2 数据来源
| API | 字段 | 说明 |
|-----|------|------|
| `kol_note_rate` | `readMedian` | 阅读中位数 |
| `kol_note_rate` | `interactionMedian` | 互动中位数 |
| `kol_note_rate` | `likeMedian` | 点赞中位数 |
| `kol_note_rate` | `collectMedian` | 收藏中位数 |
| `kol_note_rate` | `commentMedian` | 评论中位数 |
| `kol_note_list` | `list[].readNum` | 每篇阅读数 |
| `kol_note_list` | `list[].likeNum` | 每篇点赞数 |
| `kol_note_list` | `list[].collectNum` | 每篇收藏数 |
| `kol_info` | `clickMidNum` | 阅读中位数 |
| `kol_info` | `interMidNum` | 互动中位数 |

#### 3.3 处理方案

```python
import statistics

def analyze_engagement_metrics(kol_data):
    """分析阅读、点赞、评论的平均值&中位数"""
    note_list = kol_data['apis']['kol_note_list']['data']['list']
    note_rate = kol_data['apis'].get('kol_note_rate', {}).get('data', {})
    
    # 1. 筛选近30天笔记
    recent_notes = filter_recent_notes(note_list, days=30)
    
    # 2. 提取各项数据
    reads = [n['readNum'] for n in recent_notes if n.get('readNum')]
    likes = [n['likeNum'] for n in recent_notes if n.get('likeNum')]
    collects = [n['collectNum'] for n in recent_notes if n.get('collectNum')]
    
    # 3. 计算统计值
    result = {
        '阅读': {
            '平均值': round(statistics.mean(reads), 1) if reads else 0,
            '中位数': round(statistics.median(reads), 1) if reads else 0,
            '官方中位数': note_rate.get('readMedian', 0)
        },
        '点赞': {
            '平均值': round(statistics.mean(likes), 1) if likes else 0,
            '中位数': round(statistics.median(likes), 1) if likes else 0,
            '官方中位数': note_rate.get('likeMedian', 0)
        },
        '收藏': {
            '平均值': round(statistics.mean(collects), 1) if collects else 0,
            '中位数': round(statistics.median(collects), 1) if collects else 0,
            '官方中位数': note_rate.get('collectMedian', 0)
        },
        '评论': {
            '官方中位数': note_rate.get('commentMedian', 0)
        },
        '互动总计': {
            '官方中位数': note_rate.get('interactionMedian', 0),
            '超越同行': note_rate.get('interactionBeyondRate', '0') + '%'
        }
    }
    
    return result
```

**实际数据示例（JellyBonnie）：**
- 阅读中位数：241
- 互动中位数：167
- 点赞中位数：82
- 收藏中位数：64
- 评论中位数：21
- 互动超越同行：98.6%

---

## 第二方面：人工筛选维度（数据层面）

### 需求点 4：粉丝数据 vs 阅读、评论、互动数据

#### 4.1 需求理解
在非投流情况下：
- **单篇阅读数据 > 粉丝数据的30%** → 说明内容有传播力，能触达非粉丝用户
- **单篇评论数据 > 20条** → 说明内容有互动性，粉丝愿意参与讨论

这两个指标反映了博主的"真实影响力"，而非仅仅是粉丝数的堆砌。

#### 4.2 数据来源
| API | 字段 | 说明 |
|-----|------|------|
| `kol_info` | `fansCount` | 粉丝总数 |
| `kol_note_list` | `list[].readNum` | 每篇阅读数 |
| `kol_note_list` | `list[].isAdvertise` | 是否为广告（投流标识） |
| `kol_note_rate` | `notes[].readNum` | 近期笔记阅读数 |
| `kol_note_rate` | `commentMedian` | 评论中位数 |

#### 4.3 处理方案

```python
def analyze_reach_vs_fans(kol_data):
    """分析阅读/粉丝比率"""
    fans_count = kol_data['apis']['kol_info']['data']['fansCount']
    note_list = kol_data['apis']['kol_note_list']['data']['list']
    
    # 1. 筛选非广告笔记（非投流）
    organic_notes = [n for n in note_list if not n.get('isAdvertise', False)]
    
    # 2. 计算达标率
    threshold_read = fans_count * 0.3  # 阅读阈值：粉丝数的30%
    threshold_comment = 20  # 评论阈值：20条
    
    read_pass = 0
    comment_pass = 0
    
    for note in organic_notes[:20]:  # 取最近20篇非广告笔记
        if note.get('readNum', 0) > threshold_read:
            read_pass += 1
        # 注意：note_list 没有单篇评论数，需要从 note_rate 获取
    
    result = {
        '粉丝数': fans_count,
        '阅读阈值（30%粉丝数）': round(threshold_read),
        '非广告笔记数': len(organic_notes),
        '阅读达标数': read_pass,
        '阅读达标率': f"{read_pass / min(len(organic_notes), 20) * 100:.1f}%" if organic_notes else '0%',
        '评论中位数': kol_data['apis'].get('kol_note_rate', {}).get('data', {}).get('commentMedian', 0),
        '评论达标': '是' if kol_data['apis'].get('kol_note_rate', {}).get('data', {}).get('commentMedian', 0) >= 20 else '否'
    }
    
    # 3. 综合评级
    read_rate = read_pass / min(len(organic_notes), 20) if organic_notes else 0
    comment_ok = result['评论中位数'] >= 20
    
    if read_rate >= 0.5 and comment_ok:
        result['综合评级'] = '优秀（高传播力+高互动）'
    elif read_rate >= 0.3 or comment_ok:
        result['综合评级'] = '良好（有一定传播力或互动）'
    else:
        result['综合评级'] = '一般（需关注）'
    
    return result
```

**实际数据示例（一颗土豆呀）：**
- 粉丝数：23,725
- 阅读阈值（30%）：7,118
- 阅读中位数：8,526（超过阈值 ✓）
- 评论中位数：102（远超20条 ✓）
- 综合评级：优秀

---

### 需求点 5：数据波动性（月内不止一篇爆文）

#### 5.1 需求理解
避免"一篇爆文"博主——单篇爆文可能拉高平均数，但不能代表博主的稳定产出能力。需要确保：
- 月内有多篇表现优异的笔记
- 数据分布相对均匀，而非极端

#### 5.2 数据来源
| API | 字段 | 说明 |
|-----|------|------|
| `kol_note_list` | `list[].readNum` | 每篇阅读数 |
| `kol_note_list` | `list[].likeNum` | 每篇点赞数 |
| `kol_note_rate` | `hundredLikePercent` | 百赞率（超100赞的笔记占比） |
| `kol_note_rate` | `thousandLikePercent` | 千赞率（超1000赞的笔记占比） |

#### 5.3 处理方案

```python
import statistics

def analyze_data_volatility(kol_data):
    """分析数据波动性"""
    note_list = kol_data['apis']['kol_note_list']['data']['list']
    note_rate = kol_data['apis'].get('kol_note_rate', {}).get('data', {})
    
    # 1. 获取近30天笔记数据
    recent_notes = filter_recent_notes(note_list, days=30)
    reads = [n['readNum'] for n in recent_notes if n.get('readNum')]
    likes = [n['likeNum'] for n in recent_notes if n.get('likeNum')]
    
    if not reads:
        return {'error': '无有效数据'}
    
    # 2. 计算统计指标
    read_mean = statistics.mean(reads)
    read_median = statistics.median(reads)
    read_max = max(reads)
    read_std = statistics.stdev(reads) if len(reads) > 1 else 0
    
    # 3. 判断是否有极端爆文（最大值超过平均值的5倍）
    has_extreme_outlier = read_max > read_mean * 5
    
    # 4. 计算平均值/中位数偏离度（偏离越大说明数据越不均匀）
    mean_median_ratio = read_mean / read_median if read_median > 0 else 0
    
    # 5. 统计"爆文"数量（定义：超过中位数2倍的笔记）
    hot_threshold = read_median * 2
    hot_notes = [n for n in recent_notes if n.get('readNum', 0) > hot_threshold]
    
    result = {
        '笔记数': len(recent_notes),
        '阅读平均值': round(read_mean),
        '阅读中位数': round(read_median),
        '阅读最大值': read_max,
        '阅读标准差': round(read_std),
        '变异系数': round(read_std / read_mean, 2) if read_mean > 0 else 0,
        '平均/中位比': round(mean_median_ratio, 2),
        '爆文数量': len(hot_notes),
        '百赞率': note_rate.get('hundredLikePercent', '0') + '%',
        '千赞率': note_rate.get('thousandLikePercent', '0') + '%',
        '存在极端爆文': '是' if has_extreme_outlier else '否',
        '数据稳定性评级': ''
    }
    
    # 6. 稳定性评级
    cv = result['变异系数']  # 变异系数
    if cv < 0.5 and len(hot_notes) >= 2:
        result['数据稳定性评级'] = '优秀（稳定多爆文）'
    elif cv < 1.0 and len(hot_notes) >= 1:
        result['数据稳定性评级'] = '良好（相对稳定）'
    elif has_extreme_outlier:
        result['数据稳定性评级'] = '风险（单篇爆文拉高）'
    else:
        result['数据稳定性评级'] = '一般'
    
    return result
```

**实际数据示例（JellyBonnie）：**
- 百赞率：14.3%
- 千赞率：0.0%
- 数据相对稳定，无极端爆文

---

### 需求点 6：数据趋势（粉丝、阅读、互动趋势）

#### 6.1 需求理解
观察博主各项数据的变化趋势：
- 粉丝是否持续增长
- 阅读/互动是否有下滑趋势
- 账号是否处于"巅峰后下滑"阶段

#### 6.2 数据来源
| API | 字段 | 说明 |
|-----|------|------|
| `kol_fans_trend` | `list` | 每日粉丝数（30天） |
| `kol_core_data` | `dailyData` | 每日曝光/阅读/互动数据 |
| `kol_note_rate` | `longTermCommonNoteVo` | 长期非商业笔记表现 |
| `kol_note_rate` | `longTermCooperateNoteVo` | 长期商业笔记表现 |

#### 6.3 处理方案

```python
import numpy as np

def analyze_data_trends(kol_data):
    """分析数据趋势"""
    # 1. 粉丝趋势
    fans_trend = kol_data['apis']['kol_fans_trend']['data']['list']
    fans_numbers = [item['num'] for item in fans_trend]
    
    # 2. 核心数据趋势（如果有）
    core_data = kol_data['apis'].get('kol_core_data', {}).get('data', {})
    daily_data = core_data.get('dailyData', [])
    
    # 3. 计算趋势斜率（线性回归）
    def calc_trend_slope(values):
        if len(values) < 2:
            return 0
        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)
        return slope
    
    fans_slope = calc_trend_slope(fans_numbers)
    
    result = {
        '粉丝趋势': {
            '起始粉丝': fans_numbers[0] if fans_numbers else 0,
            '当前粉丝': fans_numbers[-1] if fans_numbers else 0,
            '趋势斜率': round(fans_slope, 2),
            '趋势方向': '上升' if fans_slope > 0 else ('下降' if fans_slope < 0 else '平稳')
        }
    }
    
    # 4. 互动趋势（如果有 daily_data）
    if daily_data:
        engages = [d.get('engage', 0) for d in daily_data]
        reads = [d.get('read', 0) for d in daily_data]
        
        result['互动趋势'] = {
            '趋势斜率': round(calc_trend_slope(engages), 2),
            '趋势方向': '上升' if calc_trend_slope(engages) > 0 else '下降'
        }
        result['阅读趋势'] = {
            '趋势斜率': round(calc_trend_slope(reads), 2),
            '趋势方向': '上升' if calc_trend_slope(reads) > 0 else '下降'
        }
    
    # 5. 综合趋势评级
    if fans_slope > 10:  # 日均涨粉10+
        result['综合趋势评级'] = '强势上升'
    elif fans_slope > 0:
        result['综合趋势评级'] = '稳定上升'
    elif fans_slope > -10:
        result['综合趋势评级'] = '基本平稳'
    else:
        result['综合趋势评级'] = '下降趋势（需警惕）'
    
    return result
```

**实际数据示例（椰椰小饭团）：**
- 起始粉丝：8,636
- 当前粉丝：10,478
- 30天涨粉：1,842
- 趋势方向：强势上升

---

### 需求点 7：发文频率（每周 > 3篇）

#### 7.1 需求理解
用户明确要求发文频率最好每周大于3篇。这是筛选的硬性指标之一。

#### 7.2 数据来源
同"需求点2：发帖频率"

#### 7.3 处理方案

```python
def check_posting_frequency_requirement(kol_data, min_weekly=3):
    """检查发帖频率是否达标（每周>=3篇）"""
    note_list = kol_data['apis']['kol_note_list']['data']['list']
    
    # 统计近4周的发帖情况
    recent_notes = filter_recent_notes(note_list, days=28)
    weekly_count = len(recent_notes) / 4
    
    result = {
        '4周总发帖数': len(recent_notes),
        '平均每周发帖': round(weekly_count, 1),
        '达标要求': f'每周>={min_weekly}篇',
        '是否达标': weekly_count >= min_weekly,
        '达标状态': '✓ 达标' if weekly_count >= min_weekly else '✗ 不达标'
    }
    
    return result
```

---

## 第二方面：人工筛选维度（内容层面）

### 需求点 8：博主颜值、家居风格

#### 8.1 需求理解
评估维度：
- 博主是否美观/有亲和力
- 家居风格是否高级（温馨软装 > 工业风硬装）
- 内容是否符合产品调性

#### 8.2 数据来源
| API | 字段 | 说明 |
|-----|------|------|
| `kol_info` | `headPhoto` | 博主头像URL |
| `kol_info` | `contentTags` | 内容标签（如"家居家装"） |
| `kol_note_list` | `list[].imgUrl` | 笔记封面图URL |
| `kol_note_list` | `list[].title` | 笔记标题 |

#### 8.3 处理方案

**⚠️ 限制说明**：API 无法直接判断"美不美"或"风格高级"，这需要人工或 AI 视觉分析。

```python
def prepare_visual_review_data(kol_data):
    """准备人工/AI视觉审核数据"""
    kol_info = kol_data['apis']['kol_info']['data']
    note_list = kol_data['apis']['kol_note_list']['data']['list']
    
    result = {
        '博主信息': {
            '昵称': kol_info.get('name'),
            '头像': kol_info.get('headPhoto'),
            '性别': kol_info.get('gender'),
            '内容标签': [tag.get('taxonomy1Tag') for tag in kol_info.get('contentTags', [])]
        },
        '家居相关笔记': [],
        '是否家居类博主': '家居家装' in str(kol_info.get('contentTags', []))
    }
    
    # 筛选家居相关笔记
    home_keywords = ['家居', '装修', '软装', '卧室', '客厅', '收纳', '床品', '抱枕']
    for note in note_list[:20]:
        title = note.get('title', '')
        if any(kw in title for kw in home_keywords):
            result['家居相关笔记'].append({
                '标题': title,
                '封面': note.get('imgUrl'),
                '日期': note.get('date')
            })
    
    return result
```

**建议方案**：
1. **方案A（人工审核）**：导出头像URL和近期笔记封面，由运营人工判断
2. **方案B（AI辅助）**：接入 GPT-4V 或 Gemini Vision 分析图片风格

---

### 需求点 9：剪辑情况（多种风格）

#### 9.1 需求理解
评估博主是否有多样化的内容呈现能力，避免单一风格导致用户疲劳。

#### 9.2 数据来源
| API | 字段 | 说明 |
|-----|------|------|
| `kol_note_list` | `list[].isVideo` | 是否为视频 |
| `kol_note_rate` | `videoNoteNumber` | 视频笔记数量 |
| `kol_info` | `featureTags` | 特征标签（如"测评"、"开箱"、"沉浸式"） |

#### 9.3 处理方案

```python
def analyze_content_diversity(kol_data):
    """分析内容多样性"""
    kol_info = kol_data['apis']['kol_info']['data']
    note_list = kol_data['apis']['kol_note_list']['data']['list']
    note_rate = kol_data['apis'].get('kol_note_rate', {}).get('data', {})
    
    # 1. 图文/视频比例
    video_notes = [n for n in note_list if n.get('isVideo', False)]
    image_notes = [n for n in note_list if not n.get('isVideo', False)]
    
    # 2. 内容风格标签
    feature_tags = kol_info.get('featureTags', [])
    
    result = {
        '笔记总数': len(note_list),
        '视频数': len(video_notes),
        '图文数': len(image_notes),
        '视频占比': f"{len(video_notes) / len(note_list) * 100:.1f}%" if note_list else '0%',
        '内容风格标签': feature_tags,
        '风格多样性': '丰富' if len(feature_tags) >= 3 else ('一般' if len(feature_tags) >= 1 else '单一')
    }
    
    return result
```

**实际数据示例（JellyBonnie）：**
- 特征标签：["眼部护理", "职场生活", "测评", "祛黄", "隔离防晒", "开箱", "沉浸式"]
- 风格多样性：丰富（7种风格标签）

---

### 需求点 10：口播能力（卖点表达）

#### 10.1 需求理解
评估博主是否能清晰表达产品卖点，这对于商业合作效果至关重要。

#### 10.2 数据来源
| API | 字段 | 说明 |
|-----|------|------|
| `kol_note_list` | `list[].isVideo` | 是否为视频 |
| `kol_note_rate` | `videoFullViewRate` | 视频完播率 |
| `kol_note_rate` | `videoFullViewBeyondRate` | 完播率超越同行 |
| `kol_info` | `businessNoteCount` | 商业笔记数（经验） |

#### 10.3 处理方案

**⚠️ 限制说明**：API 无法直接评估"口播能力"，但可通过以下间接指标推断：

```python
def infer_presentation_ability(kol_data):
    """推断口播/表达能力"""
    kol_info = kol_data['apis']['kol_info']['data']
    note_rate = kol_data['apis'].get('kol_note_rate', {}).get('data', {})
    note_list = kol_data['apis']['kol_note_list']['data']['list']
    
    result = {
        '商业合作经验': {
            '商业笔记数': kol_info.get('businessNoteCount', 0),
            '经验等级': ''
        },
        '视频表现': {
            '视频完播率': note_rate.get('videoFullViewRate', '0') + '%',
            '完播率超越同行': note_rate.get('videoFullViewBeyondRate', '0') + '%'
        },
        '推断评估': ''
    }
    
    # 经验等级
    biz_count = kol_info.get('businessNoteCount', 0)
    if biz_count >= 100:
        result['商业合作经验']['经验等级'] = '资深（100+商业笔记）'
    elif biz_count >= 30:
        result['商业合作经验']['经验等级'] = '熟练（30-100商业笔记）'
    elif biz_count >= 10:
        result['商业合作经验']['经验等级'] = '有经验（10-30商业笔记）'
    else:
        result['商业合作经验']['经验等级'] = '新手（<10商业笔记）'
    
    # 综合推断
    video_rate = float(note_rate.get('videoFullViewRate', '0'))
    if video_rate >= 30 and biz_count >= 30:
        result['推断评估'] = '口播能力可能较强（高完播+丰富经验）'
    elif video_rate >= 20 or biz_count >= 10:
        result['推断评估'] = '口播能力可能中等'
    else:
        result['推断评估'] = '需人工验证'
    
    return result
```

**建议方案**：
1. 查看博主近期视频内容，人工判断口播清晰度
2. 参考视频完播率（高完播可能说明表达吸引人）
3. 查看商业笔记数量（经验丰富的博主通常表达更专业）

---

## 综合筛选评分模型

基于以上需求点，可以构建一个综合评分模型：

```python
def calculate_kol_score(kol_data):
    """计算KOL综合评分"""
    scores = {}
    
    # 1. 粉丝增长趋势（权重15%）
    fans_growth = analyze_fans_growth_trend(kol_data)
    if fans_growth['趋势判断'] == '快速增长':
        scores['粉丝增长'] = 100
    elif fans_growth['趋势判断'] == '稳定增长':
        scores['粉丝增长'] = 80
    elif fans_growth['趋势判断'] == '缓慢增长':
        scores['粉丝增长'] = 60
    else:
        scores['粉丝增长'] = 30
    
    # 2. 发帖频率（权重10%）
    posting = check_posting_frequency_requirement(kol_data)
    if posting['平均每周发帖'] >= 5:
        scores['发帖频率'] = 100
    elif posting['平均每周发帖'] >= 3:
        scores['发帖频率'] = 80
    elif posting['平均每周发帖'] >= 1:
        scores['发帖频率'] = 50
    else:
        scores['发帖频率'] = 20
    
    # 3. 阅读/粉丝比（权重20%）
    reach = analyze_reach_vs_fans(kol_data)
    # ... 类似评分逻辑
    
    # 4. 数据稳定性（权重15%）
    volatility = analyze_data_volatility(kol_data)
    # ... 类似评分逻辑
    
    # 5. 内容多样性（权重10%）
    diversity = analyze_content_diversity(kol_data)
    # ... 类似评分逻辑
    
    # 6. 互动数据（权重20%）
    engagement = analyze_engagement_metrics(kol_data)
    # ... 类似评分逻辑
    
    # 7. 商业经验（权重10%）
    experience = infer_presentation_ability(kol_data)
    # ... 类似评分逻辑
    
    # 计算加权总分
    weights = {
        '粉丝增长': 0.15,
        '发帖频率': 0.10,
        '阅读粉丝比': 0.20,
        '数据稳定性': 0.15,
        '内容多样性': 0.10,
        '互动数据': 0.20,
        '商业经验': 0.10
    }
    
    total_score = sum(scores.get(k, 0) * v for k, v in weights.items())
    
    return {
        '各项得分': scores,
        '综合得分': round(total_score, 1),
        '推荐等级': '强烈推荐' if total_score >= 80 else ('推荐' if total_score >= 60 else '观望')
    }
```

---

## 数据字段快速参考表

| 需求 | 关键字段 | API |
|------|----------|-----|
| 粉丝增长趋势 | `fansNumInc`, `fansNumIncRate`, `list` | `kol_fans_trend` |
| 发帖频率 | `list[].date`, `noteNumber` | `kol_note_list`, `kol_data_summary` |
| 阅读中位数 | `readMedian`, `clickMidNum` | `kol_note_rate`, `kol_info` |
| 互动中位数 | `interactionMedian`, `interMidNum` | `kol_note_rate`, `kol_info` |
| 评论中位数 | `commentMedian` | `kol_note_rate` |
| 粉丝数 | `fansCount`, `fansNum` | `kol_info`, `kol_fans_summary` |
| 单篇阅读数 | `list[].readNum`, `notes[].readNum` | `kol_note_list`, `kol_note_rate` |
| 是否广告 | `list[].isAdvertise` | `kol_note_list` |
| 爆文率 | `hundredLikePercent`, `thousandLikePercent` | `kol_note_rate` |
| 每日数据趋势 | `dailyData` | `kol_core_data` |
| 视频/图文 | `list[].isVideo`, `videoNoteNumber` | `kol_note_list`, `kol_note_rate` |
| 内容标签 | `contentTags`, `featureTags` | `kol_info` |
| 商业经验 | `businessNoteCount` | `kol_info` |
| 视频完播率 | `videoFullViewRate` | `kol_note_rate` |

---

## 实施建议

### 阶段一：数据筛选（自动化）
使用上述字段进行初筛，过滤明显不达标的博主：
- 粉丝增长为负
- 发帖频率 < 每周1篇
- 阅读/粉丝比 < 10%
- 评论中位数 < 5

### 阶段二：深度分析（半自动化）
对初筛通过的博主进行深度分析：
- 计算综合评分
- 生成数据报告
- 标注需人工审核的项目

### 阶段三：人工审核（内容层面）
人工完成以下项目：
- 查看博主主页和近期视频
- 评估颜值/风格匹配度
- 评估口播能力

---

## 附录：数据示例

### 示例1：椰椰小饭团（优质博主）
- 粉丝：10,478
- 30天增长：1,842（+21.33%）
- 阅读中位数：12,128（超越93.2%同行）
- 互动中位数：868（超越92.2%同行）
- 评分：强烈推荐

### 示例2：JellyBonnie（中等博主）
- 粉丝：8,183
- 30天增长：-10（-0.12%）
- 阅读中位数：241（超越83.3%同行）
- 互动中位数：167（超越98.6%同行）
- 评分：推荐（粉丝增长需关注）

### 示例3：一颗土豆呀（高互动博主）
- 粉丝：23,725
- 30天增长：2,448（+11.5%）
- 阅读中位数：8,526（超越94.5%同行）
- 互动中位数：1,073（超越97.2%同行）
- 评分：强烈推荐

---

*文档生成时间：2025-12-09*
*数据来源：蒲公英 API*
