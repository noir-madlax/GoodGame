# 抖音星图 KOL 搜索接口文档

## 接口信息

### 基本信息
- **接口名称**: 搜索 KOL V1 / Search KOL V1
- **接口路径**: `/api/v1/douyin/xingtu/search_kol_v1`
- **请求方法**: GET
- **基础URL**: https://api.tikhub.io

### 接口描述
该接口用于在抖音星图平台搜索 KOL（Key Opinion Leader，关键意见领袖）达人信息。

## 请求参数

### Query Parameters（查询参数）

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| keyword | string | 是 | 搜索关键词（达人名称或类别） | "护肤达人" |
| page | integer | 是 | 页码，从 1 开始 | 1 |
| platformSource | string | 是 | 平台来源<br>"_1": 抖音（**注意下划线前缀**） | "_1" |
| sort_type | integer | 否 | 排序类型<br>1: 综合排序<br>2: 粉丝数从高到低<br>3: 粉丝数从低到高 | 1 |
| count | integer | 否 | 每页返回数量<br>建议值: 10-50<br>默认值: 20 | 20 |

### Header Parameters（请求头参数）

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | string | 是 | API 访问令牌<br>格式: "Bearer {token}" |

## 响应参数

### 成功响应 (200)

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "has_more": true,          // 是否有更多数据
    "cursor": 20,              // 下一页的游标值
    "kol_list": [              // KOL 达人列表
      {
        "author_id": "string",           // 达人 ID
        "nickname": "string",            // 达人昵称
        "avatar": "string",              // 头像 URL
        "follower_count": 0,             // 粉丝数
        "aweme_count": 0,                // 作品数
        "total_favorited": 0,            // 总获赞数
        "star_score": 0,                 // 星图评分
        "tags": ["string"],              // 标签列表
        "fans_level": "string",          // 粉丝等级（头部/腰部/尾部）
        "price_info": {                  // 价格信息
          "video_price": 0,              // 视频报价
          "live_price": 0                // 直播报价
        },
        "verify_info": "string",         // 认证信息
        "category": "string"             // 分类
      }
    ]
  }
}
```

### 错误响应

```json
{
  "code": -1,
  "message": "Error message",
  "data": null
}
```

## 粉丝等级分类

根据抖音星图的分类标准：

- **头部达人**: 粉丝数 >= 100万
- **腰部达人**: 10万 <= 粉丝数 < 100万
- **尾部达人**: 粉丝数 < 10万

## 使用示例

### Python 示例

```python
import requests

# 配置
API_BASE_URL = "https://api.tikhub.io"
API_TOKEN = "your_token_here"

# 请求头
headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

# 请求参数
params = {
    "keyword": "护肤达人",
    "page": 1,
    "platformSource": "_1",  # 注意：抖音平台使用 "_1" (带下划线前缀)
    "sort_type": 1,
    "count": 20
}

# 发起请求
response = requests.get(
    f"{API_BASE_URL}/api/v1/douyin/xingtu/search_kol_v1",
    headers=headers,
    params=params
)

# 处理响应
if response.status_code == 200:
    data = response.json()
    if data["code"] == 0:
        print(f"找到 {len(data['data']['kol_list'])} 个达人")
        for kol in data["data"]["kol_list"]:
            print(f"昵称: {kol['nickname']}, 粉丝数: {kol['follower_count']}")
```

## 注意事项

1. **分页处理**: 使用 `page` 参数进行分页，从 1 开始递增（1, 2, 3...）
2. **⚠️ platformSource 参数**: 必须使用 **"_1"**（带下划线前缀），不是 "1"！这是抖音星图平台的标识
3. **限流**: 注意 API 调用频率限制，避免过于频繁的请求
4. **认证**: 所有请求必须在 Header 中包含有效的 Authorization token
5. **数据时效性**: 达人数据可能存在延迟，建议定期更新
6. **错误处理**: 请妥善处理网络异常和 API 错误响应

### platformSource 取值说明

| 值 | 平台 |
|----|------|
| _1 | 抖音 |
| _10 | 其他平台（根据星图支持情况）|

**重要**：必须使用下划线前缀的格式！

## 更新日期
2025-11-14

