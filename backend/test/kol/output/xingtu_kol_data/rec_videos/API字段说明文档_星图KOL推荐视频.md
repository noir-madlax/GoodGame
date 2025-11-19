# 抖音星图 KOL 推荐视频 API 字段说明文档

**API名称**: kol_rec_videos_v1  
**文档版本**: v1.0  
**更新时间**: 2025-11-18  
**官方文档**: https://api.tikhub.io/#/Douyin-Xingtu-API/kol_rec_videos_v1_api_v1_douyin_xingtu_kol_rec_videos_v1_get

---

## 一、接口说明

### 1.1 功能描述

获取KOL的推荐视频列表，包括代表作品、最新视频和个人热门视频，用于展示KOL的内容质量和创作能力。

### 1.2 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| `kolId` | string | 是 | KOL的星图ID | "6831825876674412552" |
| `count` | int | 否 | 返回视频数量，默认10 | 10 |
| `cursor` | int | 否 | 分页游标，默认0（第一页） | 0 |

---

## 二、响应结构说明

### 2.1 顶层字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `code` | int | 响应状态码，200表示成功 |
| `request_id` | string | 请求唯一标识符 |
| `message` | string | 英文响应消息 |
| `message_zh` | string | 中文响应消息 |
| `time` | string | 请求时间（美国西部时间） |
| `time_stamp` | int | Unix时间戳 |
| `time_zone` | string | 时区信息 |
| `cache_url` | string | 缓存结果URL，24小时有效 |
| `router` | string | API路由路径 |
| `params` | object | 请求参数 |
| `data` | object | 返回的数据主体 |

---

## 三、核心数据字段 (data)

### 3.1 基础响应字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `base_resp` | object | 基础响应信息 |
| `base_resp.status_code` | int | 状态码，0表示成功 |
| `base_resp.status_message` | string | 状态消息 |

### 3.2 视频列表字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `masterpiece_videos` | array | 代表作品列表（多个） |
| `newest_video` | object | 最新视频（单个） |
| `personal_hot_video` | object | 个人热门视频（单个） |

**业务含义**:
- **masterpiece_videos**: 系统推荐的该KOL最具代表性的作品，通常是高质量、高互动的视频
- **newest_video**: KOL最近发布的视频，反映最新内容方向
- **personal_hot_video**: KOL个人热度最高的视频，通常是爆款作品

**注意**: 
- 如果KOL没有符合条件的视频，对应字段可能为空数组 `[]` 或不返回
- `masterpiece_videos` 可能包含0-10个视频

---

## 四、视频对象字段说明

每个视频对象（无论是在 `masterpiece_videos`、`newest_video` 还是 `personal_hot_video` 中）包含以下字段：

### 4.1 基础信息

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `id` | string | 视频ID（抖音aweme_id） | "7514876356103032127" |
| `video_id` | string | 视频唯一标识符 | "v0300fg10000d15312nog65r6b04o42g" |
| `author_id` | string | 作者ID | "103912811112" |
| `title` | string | 视频标题 | "女明星们怎么这么会喝！..." |
| `url` | string | 视频分享链接（完整URL） | "https://www.iesdouyin.com/share/video/..." |
| `cover_uri` | string | 封面图片URI | "tos-cn-i-dy/fda5f68563e8409b8f7e48727d4d4294" |

**说明**:
- `id`: 抖音视频的aweme_id，可用于其他API调用
- `video_id`: 视频的唯一标识符，格式通常为 `v0300fg10000...`
- `cover_uri`: 封面图片路径，可能需要拼接CDN域名才能访问完整图片

### 4.2 时间和时长

| 字段名 | 类型 | 说明 | 单位 |
|--------|------|------|------|
| `create_time` | string | 视频发布时间戳（Unix时间戳） | 秒 |
| `duration` | float | 视频时长 | 秒 |

**示例**:
```json
{
  "create_time": "1749693606",  // 2025-06-11 左右
  "duration": 80.406             // 80.4秒
}
```

**转换方法**:
```python
from datetime import datetime

# 时间戳转日期
create_time = 1749693606
date = datetime.fromtimestamp(create_time)
print(date.strftime('%Y-%m-%d %H:%M:%S'))

# 时长格式化
duration = 80.406
minutes = int(duration // 60)
seconds = int(duration % 60)
print(f"{minutes}分{seconds}秒")
```

---

## 五、视频统计数据 (stats)

### 5.1 互动数据

| 字段名 | 类型 | 说明 | 单位 |
|--------|------|------|------|
| `watch_cnt` | string | 播放量 | 次 |
| `like_cnt` | string | 点赞数 | 次 |
| `comment_cnt` | string | 评论数 | 次 |
| `share_cnt` | string | 分享数 | 次 |
| `favorite_cnt` | string | 收藏数 | 次 |

**示例**:
```json
{
  "watch_cnt": "486773",
  "like_cnt": "18728",
  "comment_cnt": "105",
  "share_cnt": "1251",
  "favorite_cnt": "6345"
}
```

**业务含义**:
- **watch_cnt**: 视频的总播放次数
- **like_cnt**: 点赞次数，反映内容受欢迎程度
- **comment_cnt**: 评论数，反映用户参与度
- **share_cnt**: 分享次数，反映内容传播力
- **favorite_cnt**: 收藏次数，反映内容价值和用户留存意愿

### 5.2 计算指标

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `interact_rate` | float | 互动率（小数形式） |
| `avg_watch_dura` | string | 平均观看时长 |

**示例**:
```json
{
  "interact_rate": 0.0412,
  "avg_watch_dura": "0"
}
```

**interact_rate 计算公式**:
```
互动率 = (点赞数 + 评论数 + 分享数) / 播放量

示例:
(18728 + 105 + 1251) / 486773 = 0.0412 = 4.12%
```

**说明**:
- `interact_rate`: 直接以小数形式提供，0.0412即4.12%
- `avg_watch_dura`: 平均观看时长，"0"表示数据不可用或未统计
- 互动率越高，说明内容越能激发用户参与

---

## 六、使用建议

### 6.1 视频质量评估

**高质量视频标准**:
1. ✅ `interact_rate` > 0.02 (互动率 > 2%)
2. ✅ `watch_cnt` > 100000 (播放量 > 10万)
3. ✅ `like_cnt / watch_cnt` > 0.03 (点赞率 > 3%)
4. ✅ `comment_cnt / watch_cnt` > 0.001 (评论率 > 0.1%)

**爆款视频标准**:
1. ✅ `watch_cnt` > 1000000 (播放量 > 100万)
2. ✅ `interact_rate` > 0.05 (互动率 > 5%)
3. ✅ `favorite_cnt / like_cnt` > 0.2 (收藏点赞比 > 20%)

### 6.2 KOL内容能力评估

**通过推荐视频评估KOL**:

1. **内容质量**:
   - 查看 `masterpiece_videos` 的平均 `interact_rate`
   - 代表作品互动率越高，说明内容质量越好

2. **内容稳定性**:
   - 对比 `masterpiece_videos` 和 `newest_video` 的数据差异
   - 差异小说明内容质量稳定，投放风险低

3. **爆款能力**:
   - 查看 `personal_hot_video` 的数据
   - 如果热门视频数据远超平均，说明有爆款能力但不稳定

4. **内容方向**:
   - 分析 `title` 字段中的关键词和话题标签
   - 确认是否与品牌需求匹配

### 6.3 数据处理示例

**Python示例: 计算视频综合得分**

```python
def calculate_video_score(video):
    """
    计算视频综合得分（满分100）
    """
    stats = video['stats']
    
    # 基础数据
    watch_cnt = int(stats['watch_cnt'])
    like_cnt = int(stats['like_cnt'])
    comment_cnt = int(stats['comment_cnt'])
    share_cnt = int(stats['share_cnt'])
    favorite_cnt = int(stats['favorite_cnt'])
    interact_rate = stats['interact_rate']
    
    # 得分计算
    score = 0
    
    # 播放量得分（最高30分）
    if watch_cnt > 1000000:
        score += 30
    elif watch_cnt > 500000:
        score += 25
    elif watch_cnt > 100000:
        score += 20
    else:
        score += (watch_cnt / 100000) * 20
    
    # 互动率得分（最高40分）
    score += min(interact_rate * 1000, 40)
    
    # 互动数得分（最高30分）
    total_interact = like_cnt + comment_cnt + share_cnt + favorite_cnt
    score += min((total_interact / watch_cnt) * 600, 30)
    
    return round(score, 2)


# 使用示例
video = {
    "id": "7514876356103032127",
    "title": "女明星们怎么这么会喝！",
    "stats": {
        "watch_cnt": "486773",
        "like_cnt": "18728",
        "comment_cnt": "105",
        "share_cnt": "1251",
        "favorite_cnt": "6345",
        "interact_rate": 0.0412
    }
}

score = calculate_video_score(video)
print(f"视频综合得分: {score}/100")
```

### 6.4 注意事项

1. **数据时效性**:
   - 视频数据会随时间变化
   - 缓存有效期为24小时
   - 需要定期更新获取最新数据

2. **视频可用性**:
   - `masterpiece_videos` 可能为空数组
   - 部分KOL可能没有 `newest_video` 或 `personal_hot_video`
   - 需要在代码中做好空值判断

3. **URL访问**:
   - `url` 字段包含完整的抖音分享链接
   - 链接包含tracking参数，可能影响统计
   - 建议提取 `video_id` 构建标准URL

4. **封面图片**:
   - `cover_uri` 只是图片路径，不是完整URL
   - 可能需要拼接CDN域名: `https://p3-pc.douyinpic.com/img/{cover_uri}`

5. **数据类型**:
   - 统计数据（如 `watch_cnt`、`like_cnt`）是字符串类型
   - 使用前需要转换为整数: `int(watch_cnt)`

---

## 七、数据结构示例

### 7.1 完整响应示例

```json
{
  "code": 200,
  "request_id": "6303aa1a-8e34-4677-a708-25176309eb83",
  "data": {
    "base_resp": {
      "status_code": 0,
      "status_message": ""
    },
    "masterpiece_videos": [
      {
        "id": "7514876356103032127",
        "video_id": "v0300fg10000d15312nog65r6b04o42g",
        "author_id": "103912811112",
        "title": "女明星们怎么这么会喝！",
        "cover_uri": "tos-cn-i-dy/fda5f68563e8409b8f7e48727d4d4294",
        "create_time": "1749693606",
        "duration": 80.406,
        "url": "https://www.iesdouyin.com/share/video/7514876356103032127/...",
        "stats": {
          "watch_cnt": "486773",
          "like_cnt": "18728",
          "comment_cnt": "105",
          "share_cnt": "1251",
          "favorite_cnt": "6345",
          "interact_rate": 0.0412,
          "avg_watch_dura": "0"
        }
      }
    ],
    "newest_video": {
      "id": "7568679748835020042",
      "video_id": "v0300fg10000d44liufog65rhh87q000",
      "author_id": "103912811112",
      "title": "双十一购物战绩播报！来吃电子榨菜！",
      "cover_uri": "tos-cn-i-dy/25e75413962a44ec9a4f1086d9928d1c",
      "create_time": "1762221687",
      "duration": 213.185,
      "url": "https://www.iesdouyin.com/share/video/7568679748835020042/...",
      "stats": {
        "watch_cnt": "401162",
        "like_cnt": "7919",
        "comment_cnt": "154",
        "share_cnt": "28",
        "favorite_cnt": "490",
        "interact_rate": 0.0201,
        "avg_watch_dura": "0"
      }
    },
    "personal_hot_video": {
      "id": "7537154819920891170",
      "video_id": "v0200fg10000d2cldv7og65sqo3745h0",
      "author_id": "103912811112",
      "title": "夏日降温必备！原来夏天可以这么爽！",
      "cover_uri": "tos-cn-i-dy/c561fbf96bf24bc4aad9fb7026d7c4b1",
      "create_time": "1754880623",
      "duration": 118.187,
      "url": "https://www.iesdouyin.com/share/video/7537154819920891170/...",
      "stats": {
        "watch_cnt": "488805",
        "like_cnt": "19607",
        "comment_cnt": "1881",
        "share_cnt": "373",
        "favorite_cnt": "1387",
        "interact_rate": 0.0447,
        "avg_watch_dura": "0"
      }
    }
  }
}
```

### 7.2 空数据示例

当KOL没有推荐视频时：

```json
{
  "code": 200,
  "data": {
    "base_resp": {
      "status_code": 0,
      "status_message": ""
    },
    "masterpiece_videos": []
  }
}
```

---

## 八、常见问题 (FAQ)

### Q1: masterpiece_videos 为什么是空的？

**可能原因**:
1. KOL是新账号，内容产出较少
2. KOL的视频质量不符合推荐标准
3. KOL近期没有发布视频
4. 数据统计延迟

### Q2: 如何判断视频是否是商业合作内容？

**方法**:
- 本接口不直接标识是否为商业内容
- 可以结合 `title` 中的话题标签判断
- 或调用其他接口获取视频详情

### Q3: interact_rate 和自己计算的互动率不一致？

**说明**:
- API返回的 `interact_rate` 可能包含其他互动行为（如关注）
- 不同时间获取的数据会有差异
- 建议以API返回值为准

### Q4: 为什么 avg_watch_dura 总是0？

**说明**:
- 该字段可能不对所有账号开放
- 或者该数据需要更高权限才能获取
- 目前测试中该字段普遍为"0"，含义待确认

---

## 九、更新日志

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2025-11-18 | 首次创建，基于TikHub API实际响应数据整理 |

---

**免责声明**: 
- 本文档基于2025年11月的API响应数据和实际测试整理
- 部分字段含义通过数据分析推测，如 `avg_watch_dura` 含义待官方确认
- 抖音星图平台可能随时更新字段定义，请以官方文档为准

**参考来源**:
- TikHub API 官方文档
- 实际API响应数据分析
- 抖音视频互动数据业务逻辑推断

---

*文档维护: AI Agent*  
*最后更新: 2025-11-18*

