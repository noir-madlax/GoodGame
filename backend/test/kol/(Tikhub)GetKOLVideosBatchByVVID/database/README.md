# 视频详情数据导入工具

本目录包含导入 TikHub 视频详情数据到 Supabase 数据库的脚本。

## 文件说明

- `import_video_details.py` - 单批次数据导入脚本（用于测试）
- `process_all_batches.py` - 批量处理所有批次数据的脚本
- `README.md` - 本说明文件

## 数据库表结构

### gg_xingtu_kol_videos_details

| 字段名 | 类型 | 说明 |
|--------|------|------|
| aweme_id | TEXT | 视频ID（主键） |
| kol_id | TEXT | KOL ID |
| video_desc | TEXT | 视频描述 |
| duration | INTEGER | 视频时长(毫秒) |
| create_time | BIGINT | 创建时间戳 |
| publish_time | BIGINT | 发布时间戳 |
| play_count | BIGINT | 播放量 |
| comment_count | INTEGER | 评论数 |
| share_count | INTEGER | 分享数 |
| digg_count | INTEGER | 点赞数 |
| collect_count | INTEGER | 收藏数 |
| download_count | INTEGER | 下载数 |
| forward_count | INTEGER | 转发数 |
| admire_count | INTEGER | 赞赏数 |
| author_uid | TEXT | 作者UID |
| author_nickname | TEXT | 作者昵称 |
| author_unique_id | TEXT | 作者抖音号 |
| author_follower_count | BIGINT | 作者粉丝数 |
| video_url | TEXT | 视频播放地址 |
| cover_url | TEXT | 封面图片地址 |
| video_width | INTEGER | 视频宽度 |
| video_height | INTEGER | 视频高度 |
| video_ratio | TEXT | 视频比例 |
| video_format | TEXT | 视频格式 |
| can_comment | BOOLEAN | 是否可评论 |
| can_share | BOOLEAN | 是否可分享 |
| can_forward | BOOLEAN | 是否可转发 |
| allow_download | BOOLEAN | 是否允许下载 |
| is_ads | BOOLEAN | 是否广告 |
| is_commerce | BOOLEAN | 是否商业内容 |
| geofencing_regions | JSONB | 地理位置信息 |
| video_data | JSONB | 完整video对象 |
| author_data | JSONB | 完整author对象 |
| text_extra_data | JSONB | 话题标签信息 |
| challenge_data | JSONB | 挑战/话题信息 |
| statistics_data | JSONB | 完整统计数据 |
| control_data | JSONB | 控制权限数据 |
| raw_video_data | JSONB | 完整的API原始返回数据 |
| fetch_source | TEXT | 数据来源 |
| fetch_time | TIMESTAMP | 获取时间 |
| api_version | TEXT | API版本 |
| request_id | TEXT | API请求ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

## 使用方法

### 1. 测试单批数据导入

```bash
python3 import_video_details.py
```

此脚本会：
- 读取 `../output/batch_1_response.json`
- 解析前50条视频数据
- 插入到数据库
- 显示处理结果

### 2. 批量处理所有批次

```bash
python3 process_all_batches.py
```

此脚本会：
- 依次处理 `batch_1_response.json` 到 `batch_13_response.json`
- 为每个批次解析和导入数据
- 使用 upsert 避免重复插入
- 显示总体处理统计

## 环境要求

- Python 3.7+
- 已配置 `.env` 文件（位于 `backend/.env`）
- Supabase 数据库连接正常
- 已创建 `gg_xingtu_kol_videos_details` 表

## 数据流程

1. **数据获取**: 从 TikHub API 获取视频详情
2. **数据解析**: 提取结构化字段和JSON数据
3. **关联查询**: 根据 aweme_id 获取对应的 kol_id
4. **数据插入**: 使用 upsert 批量插入到数据库
5. **重复处理**: 已存在的视频会更新，不会重复插入

## 注意事项

- 脚本会自动跳过无法找到 kol_id 的视频
- 使用 upsert 确保数据更新而非重复插入
- 所有JSON字段都保留了原始API数据，便于后续扩展
- 关键业务字段单独列出，便于查询和索引

## 索引优化

数据库已创建以下索引：
- kol_id 索引
- publish_time 索引
- play_count 降序索引
- digg_count 降序索引
- is_ads 索引
- geofencing_regions GIN索引
- fetch_time 索引
