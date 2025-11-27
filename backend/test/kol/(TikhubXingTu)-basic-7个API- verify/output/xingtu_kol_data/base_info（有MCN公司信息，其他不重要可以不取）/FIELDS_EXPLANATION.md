# 接口1.2 - KOL基础信息字段说明

**接口**: `kol_base_info_v1`  
**文档**: https://api.tikhub.io/#/Douyin-Xingtu-API/kol_base_info_v1_api_v1_douyin_xingtu_kol_base_info_v1_get

---

## 响应结构

### 顶层字段
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `kol_info` | Object | KOL基本标识信息 | ✅ 用于识别和分类KOL |
| `interface` | String | 接口名称 | ❌ 技术字段，无业务意义 |
| `timestamp` | String | 请求时间戳 | ❌ 技术字段，记录请求时间 |
| `success` | Boolean | 请求是否成功 | ❌ 技术字段，标识API调用状态 |
| `result` | Object | API返回结果 | ✅ 包含核心业务数据 |

---

## result 字段

### 元数据字段（技术字段）
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `code` | Integer | 响应状态码，200表示成功 | ❌ 技术字段 |
| `request_id` | String | 请求唯一标识符 | ❌ 技术字段，用于追踪和调试 |
| `message` | String | 英文响应消息 | ❌ 技术字段 |
| `message_zh` | String | 中文响应消息 | ❌ 技术字段 |
| `support` | String | 支持渠道链接 | ❌ 技术字段 |
| `time` | String | 服务器处理时间 | ❌ 技术字段 |
| `time_stamp` | Integer | Unix时间戳 | ❌ 技术字段 |
| `time_zone` | String | 时区 | ❌ 技术字段 |
| `docs` | String | API文档链接 | ❌ 技术字段 |
| `cache_message` | String | 缓存说明（英文） | ❌ 技术字段 |
| `cache_message_zh` | String | 缓存说明（中文） | ❌ 技术字段 |
| `cache_url` | String | 缓存访问URL | ❌ 技术字段，可用于24小时内免费重复访问 |
| `router` | String | API路由路径 | ❌ 技术字段 |
| `params` | Object | 请求参数 | ❌ 技术字段 |

---

## data 字段（核心业务数据）

### 基础信息字段
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `id` | String | 星图KOL ID | ✅ **核心** - KOL在星图平台的唯一标识 |
| `core_user_id` | String | 抖音核心用户ID | ✅ **核心** - KOL在抖音的原始ID |
| `sec_uid` | String | 抖音加密用户ID | ✅ **重要** - 用于API调用和链接构建 |
| `nick_name` | String | 昵称 | ✅ **核心** - KOL显示名称 |
| `unique_id` | String | 抖音号 | ✅ **重要** - 用户自定义的唯一抖音号 |
| `short_id` | String | 短ID | ✅ 数字形式的简短标识 |
| `avatar_uri` | String | 头像URL | ✅ 用于展示KOL头像 |

### 粉丝与影响力数据
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `follower` | Integer | 粉丝数 | ✅ **核心** - KOL影响力的直接指标 |
| `avg_play` | Integer | 平均播放量 | ✅ **重要** - 内容传播能力指标 |
| `is_star` | Boolean | 是否明星达人 | ✅ **重要** - 标识顶级KOL |

### 认证与资质信息
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `author_type` | Integer | 作者类型 (0:普通 1:企业 2:个人认证) | ✅ **重要** - 账号性质分类 |
| `grade` | Integer | 达人等级 | ✅ 星图平台评级 |
| `is_visible` | Boolean | 是否公开可见 | ✅ 影响合作可见性 |
| `status` | Integer | 账号状态 (1:正常 其他:异常) | ✅ **核心** - 账号可用性 |
| `task_status` | Integer | 任务接单状态 | ✅ **重要** - 是否可接任务 |

### 地域与个人信息
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `gender` | Integer | 性别 (0:未知 1:男 2:女) | ✅ **重要** - 用于受众匹配 |
| `province` | String | 省份 | ✅ 地域定位 |
| `city` | String | 城市 | ✅ 地域定位 |

### 内容与标签
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `category_id` | String | 分类ID | ✅ **重要** - 内容垂直领域 |
| `tags` | String/Array | 标签（JSON字符串） | ✅ **核心** - KOL擅长领域 |
| `tags_ids` | String/Array | 标签ID列表 | ✅ 标签的机器标识 |
| `tags_level_two` | String/Array | 二级标签 | ✅ 更细分的领域标签 |
| `tags_ids_level_two` | String/Array | 二级标签ID | ✅ 二级标签的机器标识 |
| `tags_relation` | Object | 标签关系映射 | ✅ **重要** - 展示标签层级关系 |
| `aweme_tags` | Array | 作品标签 | ✅ 内容特征标签 |
| `live_labels_v2` | Object | 直播标签V2 | ✅ 直播内容分类 |
| `live_order_labels` | Object | 直播订单标签 | ✅ 直播带货分类 |
| `tags_author_style` | String/Array | 作者风格标签 | ✅ 内容风格特征 |

### MCN与商务信息
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `mcn_id` | String | MCN机构ID | ✅ **重要** - 所属MCN |
| `mcn_name` | String | MCN机构名称 | ✅ **重要** - 合作联系方 |
| `mcn_logo` | String | MCN Logo URL | ✅ 机构标识 |
| `mcn_introduction` | String | MCN机构介绍 | ✅ 了解背景实力 |
| `has_phone` | Boolean | 是否有联系电话 | ✅ 联系便利性 |
| `lowest_price` | Integer | 最低报价（分） | ✅ **核心** - 商务合作起步价 |

### 平台与服务能力
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `platform` | Array | 支持的平台列表 (1:抖音 5:其他) | ✅ **重要** - 可合作平台 |
| `platform_channel` | Array | 支持的渠道 (1:短视频 10:直播) | ✅ **核心** - 可提供的服务类型 |
| `platform_source` | Integer | 平台来源 | ❌ 技术字段 |
| `opened_task_category` | String/Array | 已开通任务类型 | ✅ **重要** - 可接任务类型 |
| `e_commerce_enable` | Boolean | 是否开通电商 | ✅ **重要** - 带货能力标识 |

### 在线与活跃状态
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `is_online` | Boolean | 是否在线 | ✅ 实时响应能力 |
| `online_status` | Integer | 在线状态码 | ✅ 详细在线状态 |
| `create_time` | String | 创建时间（Unix时间戳） | ✅ 账号历史 |
| `modify_time` | String | 最后修改时间 | ✅ 信息更新时效 |

### 星图特殊标签
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `star_tags` | Array | 明星标签 | ✅ 特殊身份标识 |
| `is_plan_author` | Boolean | 是否计划作者 | ⚠️ 平台特殊标识 |
| `is_game_author` | Boolean | 是否游戏作者 | ✅ 游戏垂类标识 |
| `creator_type` | Integer | 创作者类型 | ✅ 创作者分类 |

### 协议与认证
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `protocol_id` | String | 协议版本ID | ❌ 技术字段 |
| `author_avatar_frame_icon` | Integer | 头像框图标 | ⚠️ 展示相关，业务意义较小 |

### 其他技术字段
| 字段 | 类型 | 说明 | 业务意义 |
|------|------|------|---------|
| `base64_qrcode` | String | Base64编码的二维码 | ⚠️ 可用于生成KOL二维码 |
| `qrcode_url` | String | 二维码URL | ⚠️ 二维码链接 |
| `base_resp` | Object | 基础响应状态 | ❌ 技术字段 |
| `appeal_id` | String | 申诉ID | ❌ 技术字段 |
| `abandon_sign_result` | Integer | 放弃签约结果 | ❌ 技术字段 |

---

## 业务价值总结

### 🔥 高价值字段（必看）
1. **身份标识**: `id`, `nick_name`, `sec_uid`, `unique_id`
2. **影响力指标**: `follower` (粉丝数), `avg_play` (平均播放量)
3. **商务信息**: `lowest_price` (最低报价), `platform_channel` (服务类型)
4. **内容定位**: `tags` (标签), `category_id` (分类)
5. **合作对接**: `mcn_name` (MCN机构), `has_phone` (有无联系方式)

### ⚡ 重要字段（需关注）
1. **资质认证**: `author_type` (认证类型), `status` (账号状态)
2. **服务能力**: `opened_task_category` (可接任务), `e_commerce_enable` (电商能力)
3. **受众匹配**: `gender` (性别), `province` (地域)

### 📋 参考字段（了解即可）
1. **平台技术**: `platform_source`, `protocol_id`
2. **展示辅助**: `avatar_uri`, `qrcode_url`

---

**数据更新**: 2025-11-14  
**API版本**: v1

