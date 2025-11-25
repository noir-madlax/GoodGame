# 抖音星图 KOL 搜索 API 字段说明文档

**API名称**: search_kol_v1  
**文档版本**: v1.0  
**更新时间**: 2025-11-18  
**官方文档**: https://api.tikhub.io/#/Douyin-Xingtu-API/search_kol_v1_api_v1_douyin_xingtu_search_kol_v1_get

---

## 一、响应结构说明

### 1.1 顶层字段

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

### 1.2 请求参数 (params)

| 参数名 | 说明 |
|--------|------|
| `keyword` | 搜索关键词 |
| `page` | 页码，从1开始 |
| `count` | 每页数量，通常为20 |
| `sort_type` | 排序方式，1=综合排序 |
| `platformSource` | 平台来源，_1=抖音 |

---

## 二、达人数据字段 (authors)

### 2.1 基础信息字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `star_id` | string | 星图达人ID | "6978410895290400808" |
| `id` | string | 达人唯一标识（在attribute_datas中） | 同上 |
| `nick_name` | string | 达人昵称 | "技术员小星星🌟" |
| `avatar_uri` | string | 头像URL | "https://..." |
| `core_user_id` | string | 抖音用户ID | "2410590551941344" |

### 2.2 粉丝与增长数据

| 字段名 | 类型 | 说明 | 单位 |
|--------|------|------|------|
| `follower` | string | 当前粉丝数 | 人 |
| `fans_increment_within_15d` | string | 15天粉丝增量 | 人 |
| `fans_increment_within_30d` | string | 30天粉丝增量 | 人 |
| `fans_increment_rate_within_15d` | string | 15天粉丝增长率 | 小数形式 |

**示例**: 
- follower: "808654" = 80.8万粉丝
- fans_increment_within_15d: "207" = 15天新增207人
- fans_increment_rate_within_15d: "0.00025" = 0.025%增长率

### 2.3 内容互动数据

| 字段名 | 类型 | 说明 | 单位 |
|--------|------|------|------|
| `interact_rate_within_30d` | string | 30天互动率 | 小数形式 |
| `interaction_median_30d` | string | 30天互动数中位数 | 次 |
| `vv_median_30d` | string | 30天播放量中位数 | 次 |
| `play_over_rate_within_30d` | string | 30天完播率 | 小数形式 |

**说明**:
- **互动率** = (点赞+评论+分享) / 播放量
- **中位数**: 统计期内所有作品的中间值，比平均值更能反映真实水平
- **完播率**: 观众完整观看视频的比例

**示例**:
- interact_rate_within_30d: "0.0531" = 5.31%互动率
- play_over_rate_within_30d: "0.0482" = 4.82%完播率

### 2.4 星图评分指标

| 字段名 | 类型 | 说明 | 范围 |
|--------|------|------|------|
| `star_index` | string | 星图综合指数 | 0-100 |
| `link_star_index` | string | 种草指数 | 0-100 |
| `link_spread_index` | string | 传播指数 | 0-100 |
| `link_convert_index` | string | 转化指数 | 0-100 |
| `link_shopping_index` / `link_recommend_index` | string | 推荐/购物指数 | 0-100 |

**说明**:
- **星图指数**: 星图平台的综合评分，越高越好
- **种草指数**: 内容影响用户购买决策的能力
- **传播指数**: 内容被传播、分享的能力
- **转化指数**: 内容带来实际转化的能力

**示例**: star_index: "56.774389197117" ≈ 56.77分

### 2.5 商业合作报价 (重要)

#### 2.5.1 视频类型对照表

| video_type | 类型说明 |
|------------|---------|
| 1 | 1-20秒短视频 |
| 2 | 21-60秒短视频 |
| 71 | 60秒以上长视频 |
| 73 | 直播 |
| 91 | 图文 |
| 92 | CPM计费模式 |
| 150 | 其他特殊类型 |

#### 2.5.2 报价字段

| 字段名 | 类型 | 说明 | 单位 |
|--------|------|------|------|
| `price_1_20` | string | 1-20秒视频报价 | 分（人民币） |
| `price_20_60` | string | 21-60秒视频报价 | 分 |
| `price_60` | string | 60秒以上视频报价 | 分 |

**重要**: 价格单位是"分"，需要除以100转换为元
- price_1_20: "50000" = 500元
- price_20_60: "90000" = 900元
- price_60: "170000" = 1700元

#### 2.5.3 预期数据与CPM/CPE

##### A. 预期播放量

| 字段名 | 说明 |
|--------|------|
| `expected_play_num` | 预期总播放量 |
| `expected_natural_play_num` | 预期自然播放量 |
| `promotion_prospective_vv` | 推广预期播放量 |

**示例**: expected_play_num: "194380" = 预期19.4万播放

##### B. CPM (Cost Per Mille - 每千次播放成本)

| 字段名 | 说明 | 计算公式 |
|--------|------|---------|
| `prospective_1_20_cpm` | 1-20秒视频CPM | 报价 / (预期播放量/1000) |
| `prospective_20_60_cpm` | 21-60秒视频CPM | 报价 / (预期播放量/1000) |
| `prospective_60_cpm` | 60秒+视频CPM | 报价 / (预期播放量/1000) |
| `promotion_prospective_1_20_cpm` | 推广CPM（1-20秒） | 同上 |

**说明**: 
- CPM = 广告主每获得1000次播放需要支付的费用
- CPM越低，性价比越高
- 行业对比用 `*_cpm_by_industry` 字段

**示例**:
```
price_1_20: "50000" (500元)
expected_play_num: "194380"
prospective_1_20_cpm: "257.2281"

计算: 500 / (194380/1000) = 2.57元/千次播放
```

##### C. CPE (Cost Per Engagement - 每次互动成本)

| 字段名 | 说明 | 计算公式 |
|--------|------|---------|
| `sn_prospective_1_20_cpe` | 1-20秒视频CPE | 报价 / (预期播放量 × 互动率) |
| `sn_prospective_20_60_cpe` | 21-60秒视频CPE | 同上 |
| `sn_prospective_60_cpe` | 60秒+视频CPE | 同上 |

**说明**:
- CPE = 广告主每获得一次互动（点赞/评论/分享）需要支付的费用
- CPE越低，互动性价比越高
- 适用于追求用户参与度的营销目标

**示例**:
```
price_1_20: "50000" (500元)
expected_play_num: "194380"
interact_rate: "0.0531" (5.31%)
预期互动次数: 194380 × 0.0531 = 10,313次
sn_prospective_1_20_cpe: "4.853"

计算: 500 / 10313 = 0.0485元/次互动 = 4.85分/次互动
```

##### D. 带前缀说明的字段

| 前缀 | 说明 |
|------|------|
| `sn_*` | Short video Natural（短视频自然数据） |
| `promotion_*` | 推广数据 |
| `pic_*` | 图文数据 |
| `link_*` | 种草链接相关 |

### 2.6 电商数据

| 字段名 | 说明 | 示例值 |
|--------|------|--------|
| `e_commerce_enable` | 是否开通橱窗 | "1"=是, "0"=否 |
| `author_ecom_level` | 电商等级 | "L2", "L3", "L5" |
| `ecom_video_product_num_30d` | 30天带货视频数 | "0", "4" |
| `ecom_gmv_30d_range` | 30天GMV范围 | "3w-20w" |
| `ecom_gpm_30d_range` | 30天GPM范围 | "1000-3000" |
| `ecom_avg_order_value_30d_range` | 平均客单价范围 | "50-200" |

**说明**:
- **GMV**: 商品交易总额
- **GPM**: Gross Profit per Mille，每千次播放带来的利润
- **电商等级**: L0-L5，等级越高电商能力越强

### 2.7 标签与分类

| 字段名 | 说明 | 格式 |
|--------|------|------|
| `tags_relation` | 标签关系 | JSON字符串 |
| `content_theme_labels_180d` | 180天内容主题标签 | JSON数组字符串 |
| `author_type` | 达人类型 | "1"=个人, "2"=机构, "3"=企业 |

**tags_relation 示例**:
```json
{
  "美妆": ["护肤保养", "美妆测评种草"]
}
```

**说明**:
- 第一层是大类（如"美妆"、"时尚"）
- 第二层是具体标签（如"护肤保养"）
- 用于精准定位达人内容方向

### 2.8 地理位置

| 字段名 | 说明 |
|--------|------|
| `province` | 省份 |
| `city` | 城市 |
| `gender` | 性别，"1"=男, "2"=女 |

### 2.9 质量认证标识

| 字段名 | 说明 |
|--------|------|
| `is_excellenct_author` | 是否优质作者 | "0"=否, "1"=是 |
| `is_cpm_project_author` | 是否CPM项目作者 |
| `author_avatar_frame_icon` | 头像框图标等级 | "0", "20" |
| `star_excellent_author` | 星图优质作者 |
| `star_whispers_author` | 星图耳语作者（私域） |

### 2.10 最近作品数据 (last_10_items)

JSON字符串数组，包含最近10个作品的数据：

| 字段名 | 说明 |
|--------|------|
| `item_id` | 作品ID |
| `item_title` | 作品标题 |
| `vv` | 播放量 (Video Views) |
| `like_cnt` | 点赞数 |
| `comment_cnt` | 评论数 |
| `share_cnt` | 分享数 |
| `item_create_time` | 发布时间戳 |
| `is_high_quality_item` | 是否高质量作品 |

### 2.11 特殊业务字段

| 字段名 | 说明 | 备注 |
|--------|------|------|
| `video_brand_boost` | 视频品牌加速 | "true"/"false" |
| `brand_boost_vv` | 品牌加速播放量 | 数值 |
| `is_short_drama` | 是否短剧达人 | "0"=否, "1"=是 |
| `is_black_horse_author` | 是否黑马作者 | "true"/"false" |
| `is_cocreate_author` | 是否共创作者 | "true"/"false" |
| `local_lower_threshold_author` | 本地低门槛作者 | "true"/"false" |

---

## 三、task_infos (任务报价信息)

### 3.1 价格信息 (price_infos)

| 字段名 | 说明 |
|--------|------|
| `video_type` | 视频类型代码（见2.5.1） |
| `price` | 报价（单位：分） |
| `start_time` | 报价生效开始时间戳 |
| `end_time` | 报价生效结束时间戳 |
| `video_type_status` | 状态，1=可用 |
| `task_category` | 任务类型，1=商业推广 |
| `platform_source` | 平台，1=抖音 |

### 3.2 价格额外信息 (price_extra_info)

用于CPM计费模式：

| 字段名 | 说明 |
|--------|------|
| `ceiling_price` | 价格上限（分） |
| `floor_price` | 价格下限（分） |

**示例**:
```json
{
  "video_type": 92,
  "price": 28,
  "price_extra_info": {
    "ceiling_price": "24600",  // 最高246元
    "floor_price": "3280"      // 最低32.8元
  }
}
```

---

## 四、items (代表作品)

展示达人的代表性作品，用于评估内容质量：

| 字段名 | 说明 |
|--------|------|
| `item_id` | 作品ID |
| `video_tag` | 作品标签类型 |
| `vv` | 播放量 |

**video_tag 说明**:
- 3: 高播放作品（百万级）
- 4: 带货作品
- 5: 热门作品（十万级）
- 6: 近期作品

---

## 五、不确定字段说明

以下字段含义不完全明确，建议使用时谨慎：

| 字段名 | 推测含义 | 备注 |
|--------|---------|------|
| `author_thin_mid_word_association_index` | 中间词关联指数 | 格式为JSON，可能用于内容关键词分析 |
| `assign_cpm_suggest_price` | 指定CPM建议价格 | 可能是系统推荐的CPM价格 |
| `assign_task_price_list` | 任务价格列表 | JSON数组，可能是历史价格 |
| `avg_search_after_view_rate_30d` | 30天搜索后观看率 | 可能表示从搜索进入后的观看转化 |
| `search_after_view_index_by_industry` | 行业搜索后观看指数 | 行业对比指标 |
| `expected_cpa3_level` | 预期CPA等级 | "1"-"4"，可能表示成本等级 |
| `grade` | 达人等级 | 通常为"0"，含义不明 |

---

## 六、使用建议

### 6.1 关键指标选择

**评估达人质量**:
1. ✅ `star_index` > 50 (综合评分)
2. ✅ `interact_rate_within_30d` > 0.02 (互动率 > 2%)
3. ✅ `fans_increment_rate_within_15d` > 0 (粉丝正增长)

**评估性价比**:
1. ✅ CPM < 500 (每千次播放成本 < 5元)
2. ✅ CPE < 10 (每次互动成本 < 0.1元)
3. ✅ `link_convert_index` > 60 (转化能力强)

**评估内容相关度**:
1. ✅ 检查 `tags_relation` 中的标签
2. ✅ 查看 `content_theme_labels_180d` 近期内容主题
3. ✅ 分析 `last_10_items` 最近作品标题

### 6.2 价格计算示例

**场景**: 找一个达人合作21-60秒视频

```python
# 原始数据
price_20_60 = 90000  # 单位：分
expected_play_num = 194380
interact_rate = 0.0531

# 转换为元
price_yuan = price_20_60 / 100  # 900元

# 计算CPM
cpm = price_yuan / (expected_play_num / 1000)
# = 900 / 194.38 = 4.63元/千次播放

# 计算CPE
expected_interactions = expected_play_num * interact_rate
cpe = price_yuan / expected_interactions
# = 900 / (194380 * 0.0531) = 900 / 10315.6 = 0.087元/次互动

print(f"投放成本: {price_yuan}元")
print(f"预期播放: {expected_play_num:,}次")
print(f"CPM: {cpm:.2f}元")
print(f"CPE: {cpe:.2f}元")
```

### 6.3 注意事项

1. **价格单位**: 所有price字段单位都是"分"，需要÷100转为元
2. **数值类型**: 很多数值字段是字符串类型，使用前需要转换
3. **中位数优于平均数**: 建议使用median字段而非average
4. **时间范围**: 注意区分15天、30天、180天等不同统计周期
5. **行业对比**: 带`_by_industry`后缀的字段用于行业横向对比

---

## 七、数据质量评估

### 7.1 数据完整性检查

必需字段检查：
- [ ] `id` / `star_id` 存在
- [ ] `nick_name` 存在
- [ ] `follower` 存在
- [ ] `tags_relation` 不为空

### 7.2 数据有效性判断

有效达人标准：
- [ ] follower > 10000 (粉丝 > 1万)
- [ ] vv_median_30d > 0 (有播放数据)
- [ ] tags_relation != "{}" (有标签)
- [ ] price_infos 不为空 (有报价)

---

## 八、更新日志

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2025-11-18 | 首次创建，基于TikHub API和实际数据分析 |

---

**免责声明**: 
- 本文档基于2025年11月的API响应数据和公开信息整理
- 部分字段含义通过逆向分析推测，可能存在偏差
- 抖音星图平台可能随时更新字段定义，请以官方文档为准
- 标记为"不确定"的字段建议谨慎使用

**参考来源**:
- TikHub API 官方文档
- 实际API响应数据分析
- 抖音星图平台公开信息

---

*文档维护: AI Agent*  
*最后更新: 2025-11-18*

