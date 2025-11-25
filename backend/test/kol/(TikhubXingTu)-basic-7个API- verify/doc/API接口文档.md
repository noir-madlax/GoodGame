# TikHub API 接口文档 - 抖音星图与创作者数据

## 文档概述

本文档详细记录了用于获取抖音达人数据的TikHub API接口信息，包括星图API（Xingtu）、创作者V2 API（Creator V2）和Web搜索API。

**文档更新时间**: 2025-11-13
**API基础域名**: 
- `https://api.tikhub.io`
- `https://open.tikhub.cn`
- `https://tikhub.io`

---

## 一、抖音星图 API (Douyin-Xingtu-API)

### 1.1 获取星图KOL ID

**接口名称**: `get_xingtu_kolid_by_uid`

**接口地址**: `GET /api/v1/douyin/xingtu/get_xingtu_kolid_by_uid`

**接口文档**: https://api.tikhub.io/#/Douyin-Xingtu-API/get_xingtu_kolid_by_uid_api_v1_douyin_xingtu_get_xingtu_kolid_by_uid_get

**功能描述**: 
- 通过抖音用户的UID（用户ID）获取对应的星图平台KOL ID
- 星图KOL ID是访问星图其他接口的必要参数
- 只有在星图平台注册的达人才能获取到有效的KOL ID

**请求方式**: GET

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| uid | string | 是 | 抖音用户的UID，可从用户主页URL或API获取 |

**请求示例**:
```bash
GET /api/v1/douyin/xingtu/get_xingtu_kolid_by_uid?uid=MS4wLjABAAAA0XYDGdylDyDP8Y0O-j5mBESef2okd6YsZHMTYDwoKE8
Authorization: Bearer {API_KEY}
```

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| kol_id | string | 星图平台的KOL ID，用于后续星图接口调用 |
| uid | string | 原始抖音UID |

**注意事项**:
- 非星图达人返回空或错误信息
- KOL ID是后续所有星图接口的必要参数

---

### 1.2 KOL基础信息

**接口名称**: `kol_base_info_v1`

**接口地址**: `GET /api/v1/douyin/xingtu/kol_base_info_v1`

**接口文档**: https://api.tikhub.io/#/Douyin-Xingtu-API/kol_base_info_v1_api_v1_douyin_xingtu_kol_base_info_v1_get

**功能描述**: 
- 获取KOL在星图平台的基础信息
- 包含账号状态、粉丝数、认证信息、擅长领域等
- 提供商务合作的基础参考数据

**请求方式**: GET

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kol_id | string | 是 | 星图KOL ID，从1.1接口获取 |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 抖音登录Cookie（可选，某些信息需要登录态） |

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| kol_id | string | 星图KOL ID |
| nickname | string | KOL昵称 |
| avatar_url | string | 头像URL |
| follower_count | integer | 粉丝数 |
| aweme_count | integer | 作品数 |
| total_favorited | integer | 获赞总数 |
| gender | integer | 性别(0:未知, 1:男, 2:女) |
| age | integer | 年龄 |
| province | string | 省份 |
| city | string | 城市 |
| signature | string | 个人签名 |
| unique_id | string | 抖音号 |
| verification_type | integer | 认证类型 |
| account_cert_info | string | 认证信息文本 |
| tags | array | 擅长标签/领域 |
| star_level | integer | 星图达人等级 |

**响应示例**:
```json
{
  "kol_id": "123456789",
  "nickname": "护肤小能手",
  "follower_count": 1500000,
  "tags": ["美妆", "护肤", "种草"],
  "star_level": 5
}
```

---

### 1.3 KOL受众画像

**接口名称**: `kol_audience_portrait_v1`

**接口地址**: `GET /api/v1/douyin/xingtu/kol_audience_portrait_v1`

**接口文档**: https://api.tikhub.io/#/Douyin-Xingtu-API/kol_audience_portrait_v1_api_v1_douyin_xingtu_kol_audience_portrait_v1_get

**功能描述**: 
- 获取KOL粉丝的受众画像数据
- 包含粉丝性别、年龄、地域、活跃时间、兴趣标签等
- 用于评估KOL与品牌/产品的匹配度

**请求方式**: GET

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kol_id | string | 是 | 星图KOL ID |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 抖音登录Cookie（强烈建议，受众数据需要登录态） |

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| gender_distribution | object | 性别分布 {male: 比例, female: 比例} |
| age_distribution | array | 年龄分布 [{age_range: "18-24", ratio: 0.35}, ...] |
| province_distribution | array | 省份分布（Top省份及占比） |
| city_distribution | array | 城市分布（Top城市及占比） |
| device_distribution | object | 设备分布（iOS/Android比例） |
| active_time | array | 活跃时间段分布 |
| interest_tags | array | 粉丝兴趣标签 |
| fan_quality_score | float | 粉丝质量评分（0-100） |

**响应示例**:
```json
{
  "gender_distribution": {
    "male": 0.25,
    "female": 0.75
  },
  "age_distribution": [
    {"age_range": "18-24", "ratio": 0.45},
    {"age_range": "25-30", "ratio": 0.35}
  ],
  "interest_tags": ["美妆", "护肤", "时尚", "穿搭"]
}
```

---

### 1.4 KOL服务报价

**接口名称**: `kol_service_price_v1`

**接口地址**: `GET /api/v1/douyin/xingtu/kol_service_price_v1`

**接口文档**: https://api.tikhub.io/#/Douyin-Xingtu-API/kol_service_price_v1_api_v1_douyin_xingtu_kol_service_price_v1_get

**功能描述**: 
- 获取KOL在星图平台的服务报价信息
- 包含视频定制、直播、图文等不同类型的合作报价
- 显示历史成交价格区间

**请求方式**: GET

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kol_id | string | 是 | 星图KOL ID |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 抖音登录Cookie（建议提供） |

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| video_price | object | 视频定制报价 |
| video_price.min | integer | 最低价格（分） |
| video_price.max | integer | 最高价格（分） |
| video_price.avg | integer | 平均成交价（分） |
| live_price | object | 直播报价 |
| image_text_price | object | 图文报价 |
| service_types | array | 支持的服务类型列表 |
| negotiable | boolean | 是否可议价 |
| historical_orders | integer | 历史接单数 |

**响应示例**:
```json
{
  "video_price": {
    "min": 500000,
    "max": 1000000,
    "avg": 750000
  },
  "service_types": ["视频定制", "直播带货", "图文种草"],
  "historical_orders": 156
}
```

---

### 1.5 KOL内容定位信息

**接口名称**: `kol_cp_info_v1`

**接口地址**: `GET /api/v1/douyin/xingtu/kol_cp_info_v1`

**接口文档**: https://api.tikhub.io/#/Douyin-Xingtu-API/kol_cp_info_v1_api_v1_douyin_xingtu_kol_cp_info_v1_get

**功能描述**: 
- 获取KOL的内容定位(Content Positioning)信息
- 包含内容风格、擅长品类、合作案例等
- CP = Content Positioning，内容定位

**请求方式**: GET

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kol_id | string | 是 | 星图KOL ID |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 抖音登录Cookie |

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| content_categories | array | 内容分类/垂直领域 |
| content_style | array | 内容风格标签 |
| suitable_industries | array | 适合合作的行业 |
| cooperation_cases | array | 合作案例列表 |
| case.brand_name | string | 品牌名称 |
| case.campaign_type | string | 合作类型 |
| case.performance | object | 案例效果数据 |

**响应示例**:
```json
{
  "content_categories": ["美妆护肤", "生活方式"],
  "content_style": ["测评", "种草", "教程"],
  "suitable_industries": ["美妆", "护肤品", "个护"],
  "cooperation_cases": [
    {
      "brand_name": "某护肤品牌",
      "campaign_type": "产品测评",
      "performance": {
        "view_count": 2500000,
        "like_count": 150000
      }
    }
  ]
}
```

---

### 1.6 KOL转化能力分析

**接口名称**: `kol_conversion_ability_analysis_v1`

**接口地址**: `GET /api/v1/douyin/xingtu/kol_conversion_ability_analysis_v1`

**接口文档**: https://api.tikhub.io/#/Douyin-Xingtu-API/kol_conversion_ability_analysis_v1_api_v1_douyin_xingtu_kol_conversion_ability_analysis_v1_get

**功能描述**: 
- 分析KOL的商业转化能力
- 包含带货转化率、互动转化、引流能力等核心指标
- 用于评估ROI和投放效果预估

**请求方式**: GET

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| kol_id | string | 是 | 星图KOL ID |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 抖音登录Cookie（必需） |

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| conversion_rate | float | 整体转化率（购买/点击） |
| avg_video_ctr | float | 视频平均点击率 |
| avg_comment_rate | float | 平均评论率 |
| avg_share_rate | float | 平均分享率 |
| fan_loyalty_score | float | 粉丝忠诚度评分 |
| gmv_capability | object | GMV能力评估 |
| gmv_capability.level | string | GMV能力等级 |
| gmv_capability.estimated_gmv | integer | 预估单次GMV |
| traffic_cost | float | 千次曝光成本（CPM） |
| engagement_score | float | 互动质量评分 |

**响应示例**:
```json
{
  "conversion_rate": 0.035,
  "avg_video_ctr": 0.08,
  "gmv_capability": {
    "level": "A",
    "estimated_gmv": 500000
  },
  "fan_loyalty_score": 82.5,
  "engagement_score": 87.3
}
```

---

## 二、抖音创作者 V2 API (Douyin-Creator-V2-API)

### 2.1 获取作品概览数据

**接口名称**: `fetch_item_overview_data`

**接口地址**: `POST /api/v1/douyin/creator_v2/fetch_item_overview_data`

**接口文档**: https://api.tikhub.io/#/Douyin-Creator-V2-API/fetch_item_overview_data_api_v1_douyin_creator_v2_fetch_item_overview_data_post

**功能描述**: 
- 获取单个作品的概览数据
- 包含播放量、点赞数、评论数、分享数等核心指标
- 需要创作者自己的登录态或授权

**请求方式**: POST

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| item_id | string | 是 | 作品ID（aweme_id） |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 创作者登录Cookie（必需） |

**请求体示例**:
```json
{
  "item_id": "7505583378596646180"
}
```

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| item_id | string | 作品ID |
| play_count | integer | 播放量 |
| digg_count | integer | 点赞数 |
| comment_count | integer | 评论数 |
| share_count | integer | 分享数 |
| collect_count | integer | 收藏数 |
| forward_count | integer | 转发数 |
| download_count | integer | 下载数 |
| create_time | integer | 发布时间戳 |
| statistics_updated_at | integer | 数据更新时间 |

**响应示例**:
```json
{
  "item_id": "7505583378596646180",
  "play_count": 1250000,
  "digg_count": 85000,
  "comment_count": 3200,
  "share_count": 12000
}
```

---

### 2.2 获取作品观看趋势

**接口名称**: `fetch_item_watch_trend`

**接口地址**: `POST /api/v1/douyin/creator_v2/fetch_item_watch_trend`

**接口文档**: https://api.tikhub.io/#/Douyin-Creator-V2-API/fetch_item_watch_trend_api_v1_douyin_creator_v2_fetch_item_watch_trend_post

**功能描述**: 
- 获取作品的观看趋势数据
- 显示播放量随时间的变化曲线
- 可分析作品的传播生命周期

**请求方式**: POST

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| item_id | string | 是 | 作品ID |
| start_date | string | 否 | 开始日期 YYYY-MM-DD |
| end_date | string | 否 | 结束日期 YYYY-MM-DD |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 创作者登录Cookie（必需） |

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| item_id | string | 作品ID |
| trend_data | array | 趋势数据点数组 |
| trend_data[].date | string | 日期 |
| trend_data[].play_count | integer | 当日播放量 |
| trend_data[].cumulative_play | integer | 累计播放量 |
| peak_date | string | 播放高峰日期 |
| total_days | integer | 统计天数 |

**响应示例**:
```json
{
  "item_id": "7505583378596646180",
  "trend_data": [
    {"date": "2025-11-01", "play_count": 150000, "cumulative_play": 150000},
    {"date": "2025-11-02", "play_count": 280000, "cumulative_play": 430000}
  ],
  "peak_date": "2025-11-02"
}
```

---

### 2.3 获取作品弹幕分析

**接口名称**: `fetch_item_danmaku_analysis`

**接口地址**: `POST /api/v1/douyin/creator_v2/fetch_item_danmaku_analysis`

**接口文档**: https://api.tikhub.io/#/Douyin-Creator-V2-API/fetch_item_danmaku_analysis_api_v1_douyin_creator_v2_fetch_item_danmaku_analysis_post

**功能描述**: 
- 分析作品中的弹幕数据
- 包含弹幕热词、情感分析、互动高峰时刻
- 了解观众的实时反馈点

**请求方式**: POST

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| item_id | string | 是 | 作品ID |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 创作者登录Cookie（必需） |

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| item_id | string | 作品ID |
| total_danmaku_count | integer | 弹幕总数 |
| hot_keywords | array | 高频关键词 [{word: string, count: integer}] |
| sentiment_analysis | object | 情感分析 {positive: 比例, neutral: 比例, negative: 比例} |
| peak_moments | array | 弹幕高峰时刻（秒） |
| user_engagement_rate | float | 弹幕参与率 |

**响应示例**:
```json
{
  "item_id": "7505583378596646180",
  "total_danmaku_count": 8500,
  "hot_keywords": [
    {"word": "好用", "count": 320},
    {"word": "想买", "count": 285}
  ],
  "sentiment_analysis": {
    "positive": 0.75,
    "neutral": 0.20,
    "negative": 0.05
  },
  "peak_moments": [15, 45, 120]
}
```

---

### 2.4 获取作品受众画像

**接口名称**: `fetch_item_audience_portrait`

**接口地址**: `POST /api/v1/douyin/creator_v2/fetch_item_audience_portrait`

**接口文档**: https://api.tikhub.io/#/Douyin-Creator-V2-API/fetch_item_audience_portrait_api_v1_douyin_creator_v2_fetch_item_audience_portrait_post

**功能描述**: 
- 获取单个作品的观众画像数据
- 了解该作品触达的人群特征
- 与账号整体受众对比，分析内容受众偏好

**请求方式**: POST

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| item_id | string | 是 | 作品ID |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 创作者登录Cookie（必需） |

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| item_id | string | 作品ID |
| gender_distribution | object | 性别分布 |
| age_distribution | array | 年龄分布 |
| province_distribution | array | 省份分布（Top 10） |
| city_distribution | array | 城市分布（Top 10） |
| interest_tags | array | 观众兴趣标签 |
| new_follower_ratio | float | 新粉丝占比 |
| fan_overlap_rate | float | 与账号粉丝重合度 |

**响应示例**:
```json
{
  "item_id": "7505583378596646180",
  "gender_distribution": {"male": 0.3, "female": 0.7},
  "age_distribution": [
    {"age_range": "18-24", "ratio": 0.5},
    {"age_range": "25-30", "ratio": 0.3}
  ],
  "new_follower_ratio": 0.35
}
```

---

## 三、抖音 Web 搜索 API (Douyin-Web-API)

### 3.1 通用搜索

**接口名称**: `fetch_general_search_result`

**接口地址**: `GET /api/v1/douyin/web/fetch_general_search_result`

**接口文档**: https://api.tikhub.io/#/Douyin-Web-API/fetch_general_search_result_api_v1_douyin_web_fetch_general_search_result_get

**功能描述**: 
- 通过关键词搜索抖音内容
- 返回视频、用户、话题等综合搜索结果
- 支持排序和筛选（如按热度、时间、类型）

**请求方式**: GET

**请求参数**:
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| keyword | string | 是 | 搜索关键词 |
| offset | integer | 否 | 偏移量，默认0 |
| count | integer | 否 | 返回数量，默认20 |
| sort_type | integer | 否 | 排序类型：0=综合，1=最新，2=最热 |
| publish_time | integer | 否 | 发布时间筛选：0=不限，1=一天内，7=一周内，30=一月内 |
| filter_duration | integer | 否 | 视频时长筛选：0=不限，1=1分钟内，2=1-5分钟，3=5分钟以上 |

**请求头要求**:
| 参数名 | 说明 |
|--------|------|
| Authorization | Bearer {API_KEY} |
| Cookie | 抖音登录Cookie（可选，提供更完整数据） |

**响应字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| has_more | boolean | 是否有更多结果 |
| cursor | integer | 下一页游标 |
| data | array | 搜索结果数组 |
| data[].type | string | 结果类型：video/user/topic |
| data[].aweme_info | object | 视频信息（type=video时） |
| data[].user_info | object | 用户信息（type=user时） |

**视频结果字段** (data[].aweme_info):
| 字段名 | 类型 | 说明 |
|--------|------|------|
| aweme_id | string | 视频ID |
| desc | string | 视频描述 |
| author | object | 作者信息 |
| author.uid | string | 作者UID |
| author.sec_uid | string | 作者SecUID |
| author.nickname | string | 作者昵称 |
| author.avatar_url | string | 作者头像 |
| statistics | object | 数据统计 |
| statistics.play_count | integer | 播放量 |
| statistics.digg_count | integer | 点赞数 |
| statistics.comment_count | integer | 评论数 |
| statistics.share_count | integer | 分享数 |
| create_time | integer | 发布时间戳 |
| video_url | string | 视频播放地址 |
| cover_url | string | 封面图URL |

**用户结果字段** (data[].user_info):
| 字段名 | 类型 | 说明 |
|--------|------|------|
| uid | string | 用户UID |
| sec_uid | string | 用户SecUID |
| nickname | string | 昵称 |
| signature | string | 个性签名 |
| avatar_url | string | 头像URL |
| follower_count | integer | 粉丝数 |
| total_favorited | integer | 获赞总数 |
| aweme_count | integer | 作品数 |
| unique_id | string | 抖音号 |
| verification_type | integer | 认证类型 |

**请求示例**:
```bash
GET /api/v1/douyin/web/fetch_general_search_result?keyword=抖音 护肤达人 排行榜&count=20&sort_type=2
Authorization: Bearer {API_KEY}
```

**响应示例**:
```json
{
  "has_more": true,
  "cursor": 20,
  "data": [
    {
      "type": "user",
      "user_info": {
        "uid": "123456",
        "sec_uid": "MS4wLjABAAAA...",
        "nickname": "护肤小能手",
        "follower_count": 1500000,
        "verification_type": 1,
        "signature": "专业护肤知识分享"
      }
    },
    {
      "type": "video",
      "aweme_info": {
        "aweme_id": "7505583378596646180",
        "desc": "2025最火护肤达人排行榜",
        "author": {
          "nickname": "美妆榜单",
          "uid": "789012"
        },
        "statistics": {
          "play_count": 2500000,
          "digg_count": 180000
        }
      }
    }
  ]
}
```

**注意事项**:
- 搜索结果受Cookie登录态影响，未登录可能返回较少结果
- offset 和 cursor 配合使用进行翻页
- 用户类型结果可直接获取 sec_uid 用于后续星图接口调用

---

## 四、接口调用流程

### 4.1 完整调研流程

**Step 1: 搜索达人**
```
使用接口: 3.1 通用搜索 (fetch_general_search_result)
输入: keyword = "抖音 护肤达人 排行榜"
输出: 用户列表，获取 uid 和 sec_uid
```

**Step 2: 获取星图KOL ID**
```
使用接口: 1.1 获取星图KOL ID (get_xingtu_kolid_by_uid)
输入: uid (从 Step 1 获取)
输出: kol_id
```

**Step 3: 获取KOL详细信息**（并行调用以下接口）
```
3a. 使用接口: 1.2 KOL基础信息 (kol_base_info_v1)
3b. 使用接口: 1.3 KOL受众画像 (kol_audience_portrait_v1)
3c. 使用接口: 1.4 KOL服务报价 (kol_service_price_v1)
3d. 使用接口: 1.5 KOL内容定位 (kol_cp_info_v1)
3e. 使用接口: 1.6 KOL转化能力分析 (kol_conversion_ability_analysis_v1)
输入: kol_id (从 Step 2 获取)
输出: 完整的KOL画像数据
```

**Step 4: 获取代表作品详细数据**（可选）
```
4a. 使用接口: 2.1 作品概览数据 (fetch_item_overview_data)
4b. 使用接口: 2.2 作品观看趋势 (fetch_item_watch_trend)
4c. 使用接口: 2.3 作品弹幕分析 (fetch_item_danmaku_analysis)
4d. 使用接口: 2.4 作品受众画像 (fetch_item_audience_portrait)
输入: item_id (作品ID，从用户主页或搜索结果获取)
输出: 作品级别的详细分析数据
注意: 需要创作者本人登录态，第三方可能无法调用
```

### 4.2 接口依赖关系图

```
搜索关键词
    ↓
[3.1 通用搜索] → uid/sec_uid
    ↓
[1.1 获取星图KOL ID] → kol_id
    ↓
    ├─→ [1.2 KOL基础信息]
    ├─→ [1.3 KOL受众画像]
    ├─→ [1.4 KOL服务报价]
    ├─→ [1.5 KOL内容定位]
    └─→ [1.6 KOL转化能力分析]

(可选) item_id
    ↓
    ├─→ [2.1 作品概览数据]
    ├─→ [2.2 作品观看趋势]
    ├─→ [2.3 作品弹幕分析]
    └─→ [2.4 作品受众画像]
```

---

## 五、认证与授权

### 5.1 API Key 认证
所有接口均需在请求头中携带:
```
Authorization: Bearer {tikhub_API_KEY}
```

### 5.2 Cookie 认证
部分接口需要抖音登录态Cookie（尤其是星图和创作者接口）:
- 从浏览器开发者工具中导出Cookie
- 以JSON格式保存（参考 `backend/test/kol/cookie` 文件）
- 在请求头中携带: `Cookie: {cookie_string}`

**获取Cookie方法**:
1. 浏览器登录 douyin.com
2. F12 打开开发者工具 → Network
3. 刷新页面，查看请求头中的 Cookie
4. 关键Cookie字段：sessionid, sid_guard, uid_tt

### 5.3 权限说明

| 接口类型 | API Key | Cookie | 说明 |
|---------|---------|--------|------|
| Web搜索 | ✓ | 可选 | Cookie可提升结果质量 |
| 星图基础信息 | ✓ | 推荐 | Cookie获取更完整数据 |
| 星图受众/报价 | ✓ | 必需 | 需要登录态 |
| 创作者V2 | ✓ | 必需 | 仅创作者本人或授权账号 |

---

## 六、错误码说明

| HTTP状态码 | 错误含义 | 解决方法 |
|-----------|---------|---------|
| 401 | API Key无效或过期 | 检查API Key是否正确 |
| 403 | Cookie过期或无权限 | 重新登录获取Cookie |
| 404 | 接口路径错误 | 检查URL是否正确 |
| 429 | 请求频率超限 | 降低请求频率，添加延时 |
| 500 | 服务器内部错误 | 稍后重试或联系技术支持 |

**常见业务错误**:
- `kol_id not found`: 该用户未在星图注册
- `invalid uid`: UID格式错误或用户不存在
- `permission denied`: Cookie权限不足

---

## 七、最佳实践

### 7.1 请求优化
1. **并行请求**: 对于无依赖关系的接口（如多个星图接口），使用并行请求提升效率
2. **请求延时**: 避免频繁请求被限流，建议每次请求间隔 1-2 秒
3. **错误重试**: 网络异常时自动重试 2-3 次
4. **域名轮询**: 使用多个TikHub域名提升可用性

### 7.2 数据保存
1. **保存原始响应**: 完整保存API返回的JSON，便于后续分析
2. **文件命名规范**: `接口名_时间戳_输入参数.json`
3. **记录请求参数**: 在输出文件中包含请求的输入信息

### 7.3 Cookie管理
1. **定期更新**: Cookie有效期通常7-30天，需定期更新
2. **安全存储**: Cookie包含敏感信息，不要提交到公开仓库
3. **环境变量**: 通过.env文件管理Cookie和API Key

---

## 八、数据字段对照表

### 8.1 用户ID字段说明
| 字段名 | 说明 | 获取来源 | 用途 |
|--------|------|---------|------|
| uid | 抖音用户数字ID | 用户主页、搜索结果 | 星图接口输入 |
| sec_uid | 加密的用户ID | 用户主页URL、API | 大部分抖音API |
| kol_id | 星图KOL ID | 星图接口转换 | 星图专用接口 |
| unique_id | 抖音号(@xxx) | 用户资料 | 用户搜索 |

### 8.2 统计数据字段说明
| 字段名 | 说明 | 单位 |
|--------|------|------|
| follower_count | 粉丝数 | 个 |
| total_favorited | 获赞总数 | 个 |
| aweme_count | 作品数 | 个 |
| play_count | 播放量 | 次 |
| digg_count | 点赞数 | 个 |
| comment_count | 评论数 | 条 |
| share_count | 分享数 | 次 |
| collect_count | 收藏数 | 次 |

---

## 附录A: 快速开始示例

### Python示例代码
```python
import requests
import json

API_KEY = "your_tikhub_api_key"
COOKIE = "your_douyin_cookie"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Cookie": COOKIE
}

# 1. 搜索达人
search_url = "https://api.tikhub.io/api/v1/douyin/web/fetch_general_search_result"
search_params = {"keyword": "护肤达人", "count": 10}
response = requests.get(search_url, headers=headers, params=search_params)
search_results = response.json()

# 2. 获取星图KOL ID
uid = search_results["data"][0]["user_info"]["uid"]
kolid_url = f"https://api.tikhub.io/api/v1/douyin/xingtu/get_xingtu_kolid_by_uid"
kolid_params = {"uid": uid}
response = requests.get(kolid_url, headers=headers, params=kolid_params)
kol_data = response.json()
kol_id = kol_data["kol_id"]

# 3. 获取KOL基础信息
baseinfo_url = f"https://api.tikhub.io/api/v1/douyin/xingtu/kol_base_info_v1"
baseinfo_params = {"kol_id": kol_id}
response = requests.get(baseinfo_url, headers=headers, params=baseinfo_params)
base_info = response.json()

print(json.dumps(base_info, ensure_ascii=False, indent=2))
```

---

**文档维护**: 本文档基于TikHub API官方文档整理，如有接口更新请及时同步
**技术支持**: https://api.tikhub.io/docs

