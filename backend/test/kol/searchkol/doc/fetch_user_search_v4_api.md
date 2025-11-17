# 抖音用户搜索接口 V4 (fetch_user_search_v4)

## 接口概述

该接口用于搜索抖音用户，支持通过关键词搜索并返回匹配的用户列表。这是 V4 版本的用户搜索接口，提供了更完善的搜索功能和分页支持。

## 接口信息

- **接口地址**: `https://api.tikhub.io/api/v1/douyin/search/fetch_user_search_v4`
- **请求方法**: `POST`
- **接口文档**: https://api.tikhub.io/#/Douyin-Search-API/fetch_user_search_v4_api_v1_douyin_search_fetch_user_search_v4_post
- **API 类别**: Douyin Search API
- **需要认证**: 是（Bearer Token）

## 请求参数

### Headers

```json
{
  "accept": "application/json",
  "Authorization": "Bearer YOUR_API_KEY",
  "Content-Type": "application/json"
}
```

### Request Body (JSON)

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| keyword | string | 是 | 搜索关键词 | "护肤达人" |
| offset | integer | 否 | 分页偏移量，从 0 开始 | 0 |
| count | integer | 否 | 每页返回的用户数量，默认 10，建议 10-20 | 10 |
| search_channel | string | 否 | 搜索渠道，默认为 "aweme_user_web" | "aweme_user_web" |
| sort_type | integer | 否 | 排序类型：0=综合排序，1=粉丝数排序 | 0 |
| publish_time | integer | 否 | 发布时间筛选：0=不限，1=一天内，7=一周内，182=半年内 | 0 |

### 请求示例

```json
{
  "keyword": "护肤达人",
  "offset": 0,
  "count": 10,
  "search_channel": "aweme_user_web",
  "sort_type": 0,
  "publish_time": 0
}
```

## 响应参数

### 响应结构

```json
{
  "code": 0,
  "router": "fetch_user_search_v4",
  "data": {
    "user_list": [...],
    "has_more": true,
    "cursor": 10,
    "log_pb": {...}
  }
}
```

### 响应字段说明

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| code | integer | 响应状态码，0 表示成功 |
| router | string | 路由标识 |
| data | object | 响应数据主体 |
| data.user_list | array | 用户列表数组 |
| data.has_more | boolean | 是否还有更多数据 |
| data.cursor | integer | 下一页的游标值（用于 offset） |

### User 对象字段

每个用户对象包含以下主要字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| uid | string | 用户唯一ID |
| sec_uid | string | 用户安全ID（用于 API 调用） |
| short_id | string | 用户短ID（抖音号） |
| unique_id | string | 用户唯一标识（抖音号） |
| nickname | string | 用户昵称 |
| signature | string | 个人简介 |
| avatar_thumb | object | 头像信息 |
| follower_count | integer | 粉丝数量 |
| total_favorited | integer | 获赞总数 |
| aweme_count | integer | 作品数量 |
| favoriting_count | integer | 关注数量 |
| verification_type | integer | 认证类型 |
| custom_verify | string | 认证信息 |
| enterprise_verify_reason | string | 企业认证信息 |
| user_tags | array | 用户标签 |
| white_cover_url | array | 背景图 URL |

## 响应示例

```json
{
  "code": 0,
  "router": "fetch_user_search_v4",
  "data": {
    "user_list": [
      {
        "uid": "123456789",
        "sec_uid": "MS4wLjABAAAA...",
        "short_id": "0",
        "unique_id": "skincare_master",
        "nickname": "护肤小达人",
        "signature": "专注护肤知识分享",
        "follower_count": 500000,
        "total_favorited": 1000000,
        "aweme_count": 200,
        "favoriting_count": 100,
        "verification_type": 1,
        "custom_verify": "护肤博主",
        "user_tags": [
          {
            "tag_id": "1",
            "tag_name": "护肤"
          }
        ]
      }
    ],
    "has_more": true,
    "cursor": 10
  }
}
```

## 分页处理

1. **首次请求**: `offset = 0`
2. **后续请求**: 使用响应中的 `data.cursor` 作为下一次请求的 `offset`
3. **结束条件**: 当 `data.has_more = false` 时，表示没有更多数据

### 分页示例代码

```python
offset = 0
all_users = []

while True:
    response = fetch_user_search_v4(keyword="护肤达人", offset=offset, count=10)
    
    if response['code'] != 0:
        break
    
    data = response.get('data', {})
    user_list = data.get('user_list', [])
    all_users.extend(user_list)
    
    # 检查是否还有更多数据
    if not data.get('has_more', False):
        break
    
    # 更新偏移量
    offset = data.get('cursor', offset + len(user_list))
```

## 错误处理

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 401 | 未授权，API Key 无效 | 检查 Authorization Header |
| 429 | 请求过于频繁 | 降低请求频率，添加延迟 |
| 500 | 服务器内部错误 | 重试请求或联系技术支持 |

### 错误响应示例

```json
{
  "code": 401,
  "message": "Unauthorized",
  "detail": "Invalid API key"
}
```

## 使用建议

1. **关键词优化**: 使用精确的关键词可以获得更好的搜索结果
2. **分页大小**: 建议 `count` 设置为 10-20，过大可能影响性能
3. **请求频率**: 建议在请求之间添加适当延迟（如 1-2 秒）
4. **数据缓存**: 对于重复搜索的关键词，建议缓存结果
5. **错误重试**: 实现指数退避的重试机制
6. **粉丝数筛选**: 可以结合 `sort_type=1` 按粉丝数排序，便于筛选不同级别的达人

## 腰部达人定义

根据行业标准，达人分级通常为：

- **头部达人**: 粉丝数 > 100万
- **腰部达人**: 粉丝数 10万 ~ 100万
- **尾部达人**: 粉丝数 1万 ~ 10万
- **素人**: 粉丝数 < 1万

## 注意事项

1. API Key 需要妥善保管，不要泄露
2. 搜索结果可能因抖音平台规则变化而有所不同
3. 部分用户数据可能因隐私设置而不可见
4. 建议定期更新缓存数据以保证准确性
5. 大批量搜索时注意 API 配额限制

---

**文档版本**: v1.0  
**最后更新**: 2024-11-14  
**API 版本**: V4

