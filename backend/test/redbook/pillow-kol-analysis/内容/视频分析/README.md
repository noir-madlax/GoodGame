# KOL视频内容分析模块

## 一、目录结构设计

```
内容/视频分析/
├── README.md                          # 本文档
├── 00_设计文档/
│   ├── 视频筛选规则.md                 # 视频筛选策略说明
│   ├── AI分析方案设计.md               # Gemini多模态分析方案
│   └── 数据字段说明.md                 # 详情数据字段解释
│
├── 01_脚本/
│   ├── fetch_video_details.py          # 获取视频详情（含URL）
│   ├── download_videos.py              # 批量下载视频
│   └── export_analysis_data.py         # 导出分析所需数据
│
├── 02_视频数据/
│   ├── video_list.json                 # 所有待分析视频列表
│   └── kol_{kol_id}/                   # 按KOL分目录
│       ├── info.json                   # KOL基本信息
│       ├── videos/                     # 视频文件目录
│       │   ├── {note_id}.mp4          # 视频文件
│       │   └── ...
│       └── details/                    # 视频详情目录
│           ├── {note_id}.json         # 视频详情JSON
│           └── ...
│
├── 03_分析结果/
│   ├── analysis_summary.json           # 分析结果汇总
│   └── kol_{kol_id}/
│       └── {note_id}_analysis.json     # 单个视频分析结果
│
└── 04_报告/
    ├── 内容分析汇总报告.md              # 最终汇总报告
    └── kol_{kol_id}_内容分析.md         # 单个KOL内容分析
```

---

## 二、数据覆盖情况

### 2.1 视频数据统计（32位入选KOL）

| 分类 | KOL数量 | 说明 |
|------|---------|------|
| 有≥5个非广告视频 | 26位 | ✅ 可完整分析 |
| 有1-4个非广告视频 | 4位 | ⚠️ 视频较少 |
| 纯图文博主 | 1位 | ❌ 无视频可分析 |
| 数据缺失 | 1位 | ❓ 需要核实 |

### 2.2 视频不足的KOL（需特殊处理）

| KOL名称 | 非广告视频数 | 处理方案 |
|---------|-------------|----------|
| 汤痴婆🥣 | 0 | 纯图文博主，分析图文内容 |
| 格丽乔 | 1 | 分析仅有的视频 + 图文 |
| 汤圆不要加冰 | 2 | 分析所有视频 + 图文 |
| Qw1ko | 2 | 分析所有视频 + 图文 |
| (缺失名称) | 3 | 需核实数据 |
| 贝贝贝哇 | 5 | 刚好达标 |

---

## 三、视频筛选规则

每位KOL筛选 **5个典型视频** 进行分析：

### 3.1 筛选优先级

1. **非广告视频** - 排除商业合作内容，分析自然创作能力
2. **互动TOP排序** - 按(点赞+收藏+评论)排序，选择表现最好的
3. **时间多样性** - 尽量覆盖不同时间段的内容

### 3.2 筛选SQL

```sql
-- 每位KOL的TOP5非广告视频
WITH ranked_videos AS (
    SELECT 
        kol_id, note_id, title, publish_date,
        (like_num + collect_num + COALESCE(comment_num, 0)) as total_interact,
        ROW_NUMBER() OVER (
            PARTITION BY kol_id 
            ORDER BY (like_num + collect_num + COALESCE(comment_num, 0)) DESC
        ) as rank
    FROM gg_pgy_kol_notes
    WHERE is_video = true AND is_advertise = false
      AND kol_id IN (/*32位入选KOL*/)
)
SELECT * FROM ranked_videos WHERE rank <= 5;
```

---

## 四、数据获取流程

### 4.1 获取视频详情

蒲公英的 `kol_note_list` 不包含视频URL，需要调用以下接口获取：

| 接口 | 用途 | 返回字段 |
|------|------|----------|
| `note_detail_solar` | 蒲公英笔记详情 | 视频数据、封面、正文 |
| `get-note-detail/v7` | XHS原生详情 | 视频URL、图片列表 |

### 4.2 视频下载

获取到视频URL后，使用异步下载：
- 并发控制：5个同时下载
- 重试机制：失败自动重试3次
- 文件命名：`{note_id}.mp4`

---

## 五、技术验证结果 ✅

### 5.1 视频URL获取

| 验证项 | 结果 | 说明 |
|--------|------|------|
| API接口 | ✅ 可用 | 蒲公英 `note_detail_solar` 接口 |
| 视频URL | ✅ 可获取 | 在 `videoInfo.videoUrl` 字段 |
| URL有效期 | ⚠️ 有签名 | URL包含sign和时间戳，可能有时效性 |

### 5.2 视频下载

| 验证项 | 结果 | 说明 |
|--------|------|------|
| 下载可行性 | ✅ 可下载 | HTTP 200，Content-Type: video/mp4 |
| 文件大小 | ✅ 正常 | 测试视频约22MB |
| 需要Headers | ✅ 是 | 需要Referer头 |

### 5.3 使用的API

```
接口: /api/xiaohongshu-pgy/api/solar/note/noteId/detail/v1
参数: noteId
返回: 包含 videoInfo.videoUrl 字段
```

---

## 六、待执行任务

- [ ] 1. 运行 `fetch_video_details.py` 获取32位KOL的TOP5视频详情
- [ ] 2. 运行 `download_videos.py` 批量下载视频
- [ ] 3. 设计Gemini分析提示词
- [ ] 4. 编写Gemini分析脚本
- [ ] 5. 执行AI分析
- [ ] 6. 生成分析报告

---

## 七、执行命令

```bash
cd /Users/rigel/project/hdl-tikhub-goodgame/backend
source .venv/bin/activate

# Step 1: 获取视频详情
python "/Users/rigel/project/hdl-tikhub-goodgame/backend/test/redbook/pillow-kol-analysis/内容/视频分析/01_脚本/fetch_video_details.py"

# Step 2: 下载视频
python "/Users/rigel/project/hdl-tikhub-goodgame/backend/test/redbook/pillow-kol-analysis/内容/视频分析/01_脚本/download_videos.py"
```

---

*创建时间: 2025-12-10*
*最后更新: 2025-12-10*

