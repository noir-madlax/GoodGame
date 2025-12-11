# API调用优化方案

> **目标**: 减少不必要的API调用，避免对不合格KOL浪费资源

---

## 一、原方案问题

### 枕头项目的流程

```
所有KOL → 获取全部10个API → 导入数据库 → 分析筛选
```

### 问题
1. **所有KOL都获取了10个API数据**
2. 部分不合格的KOL（如非蒲公英博主、数据表现差）也消耗了完整的API调用
3. 按27个KOL计算，共270次API调用

---

## 二、优化方案

### 新流程

```
所有KOL → 获取3个筛选API → 执行筛选 → 通过的KOL → 获取7个详细API
```

### 分阶段API

#### 阶段2: 筛选必要API（3个）

| API | 端点 | 筛选价值 |
|-----|------|----------|
| `kol_info` | `/api/xiaohongshu-pgy/get-kol-info/v1` | 是否蒲公英博主、基本信息、粉丝数 |
| `kol_note_rate` | `/api/xiaohongshu-pgy/get-kol-note-rate/v1` | 阅读/互动中位数、发帖数量 |
| `kol_fans_trend` | `/api/xiaohongshu-pgy/get-kol-fans-trend/v1` | 30天粉丝增长趋势 |

**为什么选这3个?**
- `kol_info`: 可以判断是否是蒲公英博主（API返回code=0），获取粉丝数
- `kol_note_rate`: 可以快速评估数据表现，包含阅读中位数、互动中位数
- `kol_fans_trend`: 可以判断增长趋势，筛选掉持续下跌的博主

#### 阶段4: 详细API（7个，仅通过筛选的KOL）

| API | 端点 | 用途 |
|-----|------|------|
| `kol_fans_portrait` | `/api/xiaohongshu-pgy/get-kol-fans-portrait/v1` | 粉丝画像分析 |
| `kol_fans_summary` | `/api/xiaohongshu-pgy/get-kol-fans-summary/v1` | 粉丝质量评估 |
| `kol_note_list` | `/api/xiaohongshu-pgy/get-kol-note-list/v1` | 获取笔记列表用于分析 |
| `kol_data_summary_v1` | `/api/xiaohongshu-pgy/get-kol-data-summary/v1` | 数据汇总 |
| `kol_data_summary_v2` | `/api/xiaohongshu-pgy/get-kol-data-summary/v2` | 数据汇总V2 |
| `kol_cost_effective` | `/api/xiaohongshu-pgy/get-kol-cost-effective/v1` | 性价比分析 |
| `kol_core_data` | `/api/xiaohongshu-pgy/get-kol-core-data/v1` | 核心数据（日维度） |

---

## 三、成本对比

### 本项目（15人）

| 方案 | 计算 | API调用次数 |
|------|------|-------------|
| **原方案** | 15 × 10 | 150次 |
| **优化方案** | 15 × 3 + 12 × 7 | 129次 |
| **节省** | | **21次 (14%)** |

*假设12人通过筛选，3人被淘汰*

### 淘汰率对节省的影响

| 淘汰人数 | 通过人数 | API调用 | 节省 |
|----------|----------|---------|------|
| 0人 | 15人 | 15×3 + 15×7 = 150 | 0 |
| 3人 | 12人 | 15×3 + 12×7 = 129 | 21 (14%) |
| 5人 | 10人 | 15×3 + 10×7 = 115 | 35 (23%) |
| 7人 | 8人 | 15×3 + 8×7 = 101 | 49 (33%) |

---

## 四、筛选条件

### 基础筛选条件（阶段3）

```python
def should_pass_screening(kol_data: dict) -> tuple[bool, str]:
    """
    判断KOL是否通过基础筛选
    返回: (是否通过, 原因)
    """
    # 1. 必须是蒲公英博主
    if kol_data.get('kol_info', {}).get('code') != 0:
        return False, "非蒲公英博主"
    
    info = kol_data['kol_info'].get('data', {})
    
    # 2. 粉丝数范围（可配置）
    fans_count = info.get('fansCount', 0)
    if fans_count < 10000:  # 最低1万粉
        return False, f"粉丝数过少: {fans_count}"
    
    # 3. 数据表现
    note_rate = kol_data.get('kol_note_rate', {}).get('data', {})
    read_median = note_rate.get('readMedian', 0)
    if read_median < 1000:  # 阅读中位数至少1000
        return False, f"阅读中位数过低: {read_median}"
    
    # 4. 粉丝趋势
    fans_trend = kol_data.get('kol_fans_trend', {}).get('data', {})
    trend_list = fans_trend.get('list', [])
    if len(trend_list) >= 2:
        recent = trend_list[-1].get('num', 0)
        old = trend_list[0].get('num', 0)
        if recent < old * 0.9:  # 下跌超过10%
            return False, "粉丝持续下跌"
    
    return True, "通过"
```

---

## 五、实现要点

### 5.1 数据存储

```
01_KOL数据获取/
├── 01_基础筛选数据/
│   ├── kol_{id}/
│   │   ├── kol_info.json
│   │   ├── kol_note_rate.json
│   │   └── kol_fans_trend.json
│   └── ...
├── 02_详细数据/
│   ├── kol_{id}/
│   │   ├── all_data.json  # 完整数据
│   │   └── ...
│   └── ...
└── screening_result.json  # 筛选结果
```

### 5.2 筛选结果格式

```json
{
  "screening_date": "2025-12-11",
  "total_kols": 15,
  "passed": 12,
  "failed": 3,
  "results": [
    {
      "kol_id": "xxx",
      "kol_name": "哩哩Lilyy",
      "passed": true,
      "reason": "通过",
      "fans_count": 50000,
      "read_median": 5000
    },
    {
      "kol_id": "yyy",
      "kol_name": "xxx",
      "passed": false,
      "reason": "非蒲公英博主",
      "fans_count": null,
      "read_median": null
    }
  ]
}
```

---

## 六、待确认事项

1. **粉丝数范围**: 能量棒品牌对KOL粉丝数的要求是多少？
2. **阅读数门槛**: 最低阅读中位数要求是多少？
3. **是否需要其他筛选条件**: 如内容领域、地域等？

---

*最后更新: 2025-12-11*
