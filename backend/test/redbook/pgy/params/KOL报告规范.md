# KOL 分析报告规范

> 版本: 1.0
> 创建时间: 2025-12-08
> 适用范围: 小红书蒲公英 KOL 分析

---

## 一、报告结构要求

KOL分析报告必须包含以下**十个维度**，每个维度都有明确的数据来源和展示要求：

### 1. 基础信息 (必需)

**数据来源**: `get-kol-info/v1`

| 必填字段 | API字段 | 说明 |
|----------|---------|------|
| 昵称 | `data.name` | KOL名称 |
| 小红书号 | `data.redId` | 小红书ID |
| 用户ID | `data.userId` | 唯一标识 |
| 性别 | `data.gender` | 男/女 |
| 所在地 | `data.location` | 省市区 |
| 常驻地 | `data.travelAreaList` | 常驻城市 |
| 粉丝数 | `data.fansCount` 或 `data.fansNum` | 粉丝总数 |
| 获赞与收藏 | `data.likeCollectCountInfo` | 总互动数 |
| 商业笔记数 | `data.businessNoteCount` | 商业合作笔记 |
| 笔记总数 | `data.totalNoteCount` | 全部笔记 |
| 内容领域 | `data.contentTags` | 一级+二级标签 |
| 特色标签 | `data.featureTags` | 如"测评" |
| 个人标签 | `data.personalTags` | 如"学生" |
| 蒲公英等级 | `data.currentLevel` | 1-5级 |
| 合作类型 | `data.cooperType` | 1=蒲公英博主, 2=非蒲公英 |

**报价信息**:

| 字段 | API字段 | 说明 |
|------|---------|------|
| 图文报价 | `data.picturePrice` | 单位:元 |
| 视频报价 | `data.videoPrice` | 单位:元 |
| 图文状态 | `data.pictureState` | 1=可接单 |
| 视频状态 | `data.videoState` | 1=可接单 |

**擅长行业**:

| 字段 | API字段 | 说明 |
|------|---------|------|
| 行业列表 | `data.tradeType` | 空格分隔的行业 |

---

### 2. 粉丝画像分析 (必需)

**数据来源**: `get-kol-fans-portrait/v1`

#### 2.1 性别分布

| 字段 | API字段 | 说明 |
|------|---------|------|
| 女性占比 | `data.gender.female` | 0-1的小数 |
| 男性占比 | `data.gender.male` | 0-1的小数 |

**展示要求**: 
- 使用ASCII进度条可视化
- 分析适合的产品类型

#### 2.2 年龄分布

| 字段 | API字段 | 说明 |
|------|---------|------|
| 年龄分布 | `data.ages` | 数组，包含group和percent |

**年龄分组**:
- `<18`: 未成年
- `18-24`: 年轻人/学生
- `25-34`: 职场新人
- `35-44`: 中年
- `>44`: 中老年

**展示要求**:
- 使用ASCII进度条可视化
- 计算核心年龄段占比（如18-34岁合计）
- 分析目标受众特征

#### 2.3 兴趣标签

| 字段 | API字段 | 说明 |
|------|---------|------|
| 兴趣列表 | `data.interests` | 数组，包含name和percent |

**展示要求**:
- 展示TOP10兴趣标签
- 分析与博主内容的匹配度

#### 2.4 地域分布

| 字段 | API字段 | 说明 |
|------|---------|------|
| 省份分布 | `data.provinces` | 数组，包含name和percent |
| 城市分布 | `data.cities` | 数组，包含name和percent |

**展示要求**:
- 展示TOP10省份和城市
- 计算一线城市（北上广深）合计占比
- 分析消费能力

#### 2.5 设备分布

| 字段 | API字段 | 说明 |
|------|---------|------|
| 设备列表 | `data.devices` | 数组，包含name、desc和percent |

**展示要求**:
- 展示主要设备品牌
- 标注消费能力评估（苹果=高，华为=中高，其他=中）
- 分析粉丝消费能力

---

### 3. 粉丝质量分析 (必需)

**数据来源**: `get-kol-fans-summary/v1`

| 指标 | API字段 | 说明 |
|------|---------|------|
| 粉丝总数 | `data.fansNum` | 当前粉丝数 |
| 30天粉丝增长 | `data.fansIncreaseNum` | 净增长数 |
| 粉丝增长率 | `data.fansGrowthRate` | 百分比 |
| 增长超越同行 | `data.fansGrowthBeyondRate` | 百分比 |
| 28天活跃粉丝 | `data.activeFansL28` | 活跃粉丝数 |
| 活跃粉丝率 | `data.activeFansRate` | 百分比 |
| 活跃超越同行 | `data.activeFansBeyondRate` | 百分比 |
| 30天互动粉丝 | `data.engageFansL30` | 互动粉丝数 |
| 互动粉丝率 | `data.engageFansRate` | 百分比 |
| 互动超越同行 | `data.engageFansBeyondRate` | 百分比 |
| 30天阅读粉丝 | `data.readFansIn30` | 阅读粉丝数 |
| 阅读粉丝率 | `data.readFansRate` | 百分比 |
| 阅读超越同行 | `data.readFansBeyondRate` | 百分比 |
| 30天付费粉丝率 | `data.payFansUserRate30d` | 百分比 |
| 30天付费粉丝数 | `data.payFansUserNum30d` | 付费粉丝数 |

**展示要求**:
- 表格展示所有指标
- 添加"同行中位数(估算)"列，根据超越同行比例反推
- 添加评价列（🔥极佳/✅良好/⚠️一般）
- 使用星级评分总结各维度

**同行中位数估算规则**:
- 超越90%+: 同行中位数 ≈ 该KOL数值的 20%-30%
- 超越80%+: 同行中位数 ≈ 该KOL数值的 50%-60%
- 超越70%+: 同行中位数 ≈ 该KOL数值的 70%-80%
- 超越50%+: 同行中位数 ≈ 该KOL数值的 90%-100%

---

### 4. 内容表现分析 (必需)

**数据来源**: `get-kol-note-rate/v1`

#### 4.1 核心数据

| 指标 | API字段 | 说明 |
|------|---------|------|
| 笔记数量 | `data.noteNumber` | 统计笔记数 |
| 曝光中位数 | `data.impMedian` | 曝光中位数 |
| 曝光超越同行 | `data.impMedianBeyondRate` | 百分比 |
| 阅读中位数 | `data.readMedian` | 阅读中位数 |
| 阅读超越同行 | `data.readMedianBeyondRate` | 百分比 |
| 互动中位数 | `data.interactionMedian` | 互动中位数 |
| 互动率 | `data.interactionRate` | 百分比 |
| 互动超越同行 | `data.interactionBeyondRate` | 百分比 |
| 点赞中位数 | `data.likeMedian` | 点赞中位数 |
| 收藏中位数 | `data.collectMedian` | 收藏中位数 |
| 评论中位数 | `data.commentMedian` | 评论中位数 |
| 分享中位数 | `data.shareMedian` | 分享中位数 |

#### 4.2 流量来源

| 指标 | API字段 | 说明 |
|------|---------|------|
| 发现页曝光占比 | `data.pagePercentVo.impHomefeedPercent` | 推荐流量 |
| 搜索页曝光占比 | `data.pagePercentVo.impSearchPercent` | 搜索流量 |
| 关注页曝光占比 | `data.pagePercentVo.impFollowPercent` | 粉丝流量 |
| 详情页曝光占比 | `data.pagePercentVo.impDetailPercent` | 详情页流量 |
| 其他曝光占比 | `data.pagePercentVo.impOtherPercent` | 其他流量 |

**展示要求**:
- 使用ASCII进度条可视化流量来源
- 分析流量结构特点（搜索型/推荐型）

#### 4.3 长期内容表现

| 指标 | API字段 | 说明 |
|------|---------|------|
| 近期笔记数 | `data.longTermCommonNoteVo.noteNumber` | 近期发布数 |
| 近期阅读数 | `data.longTermCommonNoteVo.recentReadNum` | 近期平均阅读 |
| 近期阅读超越同行 | `data.longTermCommonNoteVo.recentReadBeyondRate` | 百分比 |
| 长期阅读数 | `data.longTermCommonNoteVo.longTermReadNum` | 长期平均阅读 |
| 长期阅读超越同行 | `data.longTermCommonNoteVo.longTermReadBeyondRate` | 百分比 |

#### 4.4 内容类型分布

| 指标 | API字段 | 说明 |
|------|---------|------|
| 内容类型 | `data.noteType` | 数组，包含contentTag和percent |

---

### 5. 笔记漏斗分析 (🔥 关键维度)

**数据来源**: `note_detail_solar` (api/solar/note/noteId/detail/v1)

**重要性**: 这是评估KOL内容转化能力的核心指标，必须详细分析！

#### 5.1 漏斗数据字段

| 指标 | API字段 | 说明 |
|------|---------|------|
| 曝光数 | `data.impNum` | 漏斗顶部 |
| 阅读数 | `data.readNum` | 第一层转化 |
| 点赞数 | `data.likeNum` | 互动指标 |
| 收藏数 | `data.favNum` | 互动指标 |
| 评论数 | `data.cmtNum` | 互动指标 |
| 分享数 | `data.shareNum` | 互动指标 |
| 新增关注 | `data.followCnt` | 转化指标 |

#### 5.2 漏斗展示要求

```
曝光数 (impNum):    XXX,XXX
    ↓ XX.XX%
阅读数 (readNum):    XX,XXX
    ↓ X.XX%        ↓ X.XX%        ↓ X.XX%        ↓ X.XX%        ↓ X.XX%
点赞数: X,XXX    收藏数: X,XXX   评论数: XXX     分享数: XXX     新增关注: XXX
```

#### 5.3 转化率计算

| 转化环节 | 计算公式 | 行业参考 |
|----------|----------|----------|
| 曝光→阅读 | readNum / impNum | 5-10% |
| 阅读→点赞 | likeNum / readNum | 5-15% |
| 阅读→收藏 | favNum / readNum | 0.5-2% |
| 阅读→评论 | cmtNum / readNum | 0.2-1% |
| 阅读→分享 | shareNum / readNum | 0.1-0.5% |
| 阅读→关注 | followCnt / readNum | 0.3-1% |

#### 5.4 互动效率计算

| 指标 | 计算公式 | 行业参考 |
|------|----------|----------|
| 总互动数 | likeNum + favNum + cmtNum + shareNum | - |
| 互动率 | 总互动数 / readNum | 3-8% |
| 千次曝光互动 | 总互动数 / impNum * 1000 | 5-15 |
| 千次曝光阅读 | readNum / impNum * 1000 | 50-100 |

#### 5.5 评价标准

| 指标 | 🔥极佳 | ✅正常 | ⚠️偏低 |
|------|--------|--------|--------|
| 曝光→阅读 | >15% | 5-15% | <5% |
| 阅读→点赞 | >15% | 5-15% | <5% |
| 阅读→收藏 | >2% | 0.5-2% | <0.5% |
| 阅读→评论 | >1% | 0.2-1% | <0.2% |
| 阅读→分享 | >0.5% | 0.1-0.5% | <0.1% |
| 阅读→关注 | >1% | 0.3-1% | <0.3% |
| 互动率 | >8% | 3-8% | <3% |

---

### 6. 粉丝增长趋势 (必需)

**数据来源**: `get-kol-fans-trend/v1`

| 指标 | API字段 | 说明 |
|------|---------|------|
| 30天增长数 | `data.fansNumInc` | 净增长 |
| 30天增长率 | `data.fansNumIncRate` | 小数 |
| 每日粉丝数 | `data.list` | 数组，包含num和dateKey |

**展示要求**:
- 使用ASCII曲线图展示30天趋势
- 标注关键增长节点
- 分析增长模式（爆发型/稳健型/下降型）

---

### 7. 性价比分析 (必需)

**数据来源**: `get-kol-cost-effective/v1`

| 指标 | API字段 | 说明 |
|------|---------|------|
| 图文阅读成本 | `data.pictureReadCost` | 元/阅读 |
| 图文超越同行 | `data.pictureSurpassRate` | 百分比 |
| 视频阅读成本 | `data.videoReadCost` | 元/阅读 |
| 视频超越同行 | `data.videoSurpassRate` | 百分比 |
| 图文CPM | `data.estimatePictureCpm` | 千次曝光成本 |
| 图文CPM对比 | `data.estimatePictureCpmCompare` | 与同行对比 |
| 图文互动成本 | `data.estimatePictureEngageCost` | 元/互动 |
| 图文互动成本对比 | `data.estimatePictureEngageCostCompare` | 与同行对比 |

**展示要求**:
- 展示成本效率指标
- 基于报价和中位数计算预估效果
- 给出性价比评价

---

### 8. 热门笔记列表 (🔥 关键维度)

**重要性**: 热门笔记是评估KOL内容能力的直接证据，必须展示完整数据和转化率指标！

#### 8.1 数据来源

| 数据 | API接口 | 说明 |
|------|---------|------|
| 笔记列表 | `get-kol-note-list/v1` | 获取笔记基础数据 |
| 笔记详情 | `note_detail_solar` | 获取曝光数等完整数据 |
| 近期笔记详情 | `get-kol-note-rate/v1` → `data.notes` | 近期笔记含曝光数 |

#### 8.2 笔记列表字段

| 指标 | API字段 | 说明 |
|------|---------|------|
| 笔记ID | `list[].noteId` | 笔记唯一标识 |
| 标题 | `list[].title` | 笔记标题 |
| 阅读数 | `list[].readNum` | 阅读量 |
| 点赞数 | `list[].likeNum` | 点赞数 |
| 收藏数 | `list[].collectNum` | 收藏数 |
| 是否广告 | `list[].isAdvertise` | 是否商业笔记 |
| 发布日期 | `list[].date` | 发布时间 |
| 品牌名称 | `list[].brandName` | 合作品牌 |

#### 8.3 笔记详情字段 (note_detail_solar)

| 指标 | API字段 | 说明 |
|------|---------|------|
| 曝光数 | `data.impNum` | 🔥 关键指标 |
| 阅读数 | `data.readNum` | 🔥 关键指标 |
| 点赞数 | `data.likeNum` | 互动指标 |
| 收藏数 | `data.favNum` | 互动指标 |
| 评论数 | `data.cmtNum` | 互动指标 |
| 分享数 | `data.shareNum` | 互动指标 |
| 新增关注 | `data.followCnt` | 转化指标 |

#### 8.4 展示要求 (必须包含)

**表格1: 热门笔记完整数据**

| 排名 | 标题 | 曝光数 | 阅读数 | 点赞 | 收藏 | 互动总数 | 发布日期 |
|------|------|--------|--------|------|------|----------|----------|
| 1 | xxx | XXX,XXX | XX,XXX | X,XXX | X,XXX | X,XXX | YYYY-MM-DD |
| ... | ... | ... | ... | ... | ... | ... | ... |

> 📢 = 商业合作笔记 | *曝光数为估算值（如无法获取）

**表格2: 热门笔记核心转化率指标**

| 排名 | 曝光→阅读 | 阅读→点赞 | 阅读→收藏 | 互动率 | 收藏率评价 |
|------|-----------|-----------|-----------|--------|------------|
| 1 | XX.XX% | X.XX% | X.XX% | X.XX% | 极佳/良好/一般 |
| ... | ... | ... | ... | ... | ... |

**行业参考**: 曝光→阅读 5-10% | 阅读→点赞 5-15% | 阅读→收藏 0.5-2% | 互动率 3-8%

#### 8.5 转化率计算公式

| 指标 | 计算公式 |
|------|----------|
| 曝光→阅读 | readNum / impNum * 100% |
| 阅读→点赞 | likeNum / readNum * 100% |
| 阅读→收藏 | collectNum / readNum * 100% |
| 互动率 | (likeNum + collectNum) / readNum * 100% |
| 互动总数 | likeNum + collectNum + cmtNum + shareNum |

#### 8.6 曝光数获取策略

1. **优先**: 调用 `note_detail_solar` 获取精确曝光数
2. **备选**: 使用 `get-kol-note-rate/v1` 的 `data.notes` 数组（仅近期笔记）
3. **估算**: 根据已知笔记的曝光→阅读转化率估算其他笔记曝光数

**估算公式**: `估算曝光数 = 阅读数 / 已知转化率`

#### 8.7 分析结论要求

必须包含以下分析：
1. **内容特点**: 热门内容的主题、风格特征
2. **转化能力**: 各转化率与行业参考的对比评价
3. **商业价值**: 商业笔记表现、适合的产品类型

---

### 9. 合作建议 (必需)

基于以上数据分析，给出：

1. **适合的产品类型**: 根据内容领域、粉丝兴趣、热门内容主题
2. **合作成本**: 报价和预估效果
3. **合作响应**: 邀约响应率、合作经验

**数据来源**: `get-kol-data-summary/v1` 或 `v2`

| 指标 | API字段 | 说明 |
|------|---------|------|
| 邀约响应率 | `data.responseRate` | 百分比 |
| 收到邀约数 | `data.inviteNum` | 邀约次数 |
| 近7天活跃 | `data.activeDayInLast7` | 活跃天数 |
| 是否活跃 | `data.isActive` | 布尔值 |
| 是否易联系 | `data.easyConnect` | 布尔值 |
| 博主优势 | `data.kolAdvantage` | 如"品效型博主" |

---

### 10. 综合评分 (必需)

**评分维度**:

| 维度 | 权重 | 评分依据 |
|------|------|----------|
| 粉丝规模 | 15% | 粉丝数量级 |
| 粉丝质量 | 20% | 活跃度、互动率、付费率 |
| 粉丝增长 | 15% | 增长率、超越同行比例 |
| 内容表现 | 20% | 曝光/阅读/互动中位数 |
| 互动能力 | 15% | 互动率、收藏率 |
| 性价比 | 15% | 成本效率 |

**评分标准**:

| 星级 | 分数 | 说明 |
|------|------|------|
| ⭐⭐⭐⭐⭐ | 90-100 | 极佳 |
| ⭐⭐⭐⭐☆ | 75-89 | 优秀 |
| ⭐⭐⭐☆☆ | 60-74 | 良好 |
| ⭐⭐☆☆☆ | 40-59 | 一般 |
| ⭐☆☆☆☆ | <40 | 较差 |

---

## 二、数据获取流程

### 2.1 必需API调用顺序

```
1. get-kol-info/v1          → 基础信息
2. get-kol-fans-portrait/v1 → 粉丝画像
3. get-kol-fans-summary/v1  → 粉丝质量
4. get-kol-fans-trend/v1    → 粉丝趋势
5. get-kol-note-rate/v1     → 内容表现
6. get-kol-note-list/v1     → 笔记列表 (仅蒲公英博主)
7. get-kol-data-summary/v2  → 数据概览
8. get-kol-cost-effective/v1 → 性价比
9. get-kol-core-data/v1     → 核心数据
10. note_detail_solar       → 热门笔记详情 (用于漏斗分析)
```

### 2.2 漏斗分析笔记选择

从 `get-kol-note-list/v1` 返回的笔记列表中，选择**阅读量最高**的笔记进行漏斗分析：

```python
# 选择热门笔记
top_note = max(note_list, key=lambda x: x['readNum'])
note_id = top_note['noteId']

# 调用 note_detail_solar 获取详情
detail = call_api(f'/api/solar/note/noteId/detail/v1?noteId={note_id}')
```

---

## 三、报告格式要求

### 3.1 Markdown格式

- 使用标准Markdown语法
- 表格对齐
- 代码块用于ASCII可视化
- 使用emoji增强可读性

### 3.2 可视化要求

1. **进度条**: 用于百分比展示
```
女性 ████████████████████████████████████████████████ 78.7%
男性 █████████████████████ 21.3%
```

2. **漏斗图**: 用于转化分析
```
曝光数 (impNum):    318,092
    ↓ 18.10%
阅读数 (readNum):    57,580
```

3. **趋势图**: 用于粉丝增长
```
2,031 ┤                                              ╭──
2,000 ┤╯
       └──────────────────────────────────────────────────
        11/08                                      12/07
```

### 3.3 评价标记

| 标记 | 含义 | 使用场景 |
|------|------|----------|
| 🔥 | 极佳/优秀 | 超越90%同行 |
| ✅ | 良好/正常 | 超越50-90%同行 |
| ⚠️ | 一般/偏低 | 低于50%同行 |
| ❌ | 较差 | 低于20%同行 |

---

## 四、行业参考数据

### 4.1 转化率参考

| 指标 | 低 | 中 | 高 |
|------|-----|-----|-----|
| 曝光→阅读 | <5% | 5-10% | >10% |
| 阅读→点赞 | <5% | 5-15% | >15% |
| 阅读→收藏 | <0.5% | 0.5-2% | >2% |
| 阅读→评论 | <0.2% | 0.2-1% | >1% |
| 阅读→分享 | <0.1% | 0.1-0.5% | >0.5% |
| 阅读→关注 | <0.3% | 0.3-1% | >1% |
| 互动率 | <3% | 3-8% | >8% |

### 4.2 粉丝质量参考

| 指标 | 低 | 中 | 高 |
|------|-----|-----|-----|
| 活跃粉丝率 | <50% | 50-70% | >70% |
| 互动粉丝率 | <1% | 1-3% | >3% |
| 阅读粉丝率 | <5% | 5-15% | >15% |
| 付费粉丝率 | <10% | 10-30% | >30% |
| 粉丝增长率(月) | <1% | 1-5% | >5% |

### 4.3 成本效率参考

| 指标 | 高成本 | 中等 | 低成本 |
|------|--------|------|--------|
| 阅读成本 | >¥1 | ¥0.3-1 | <¥0.3 |
| CPM | >¥50 | ¥20-50 | <¥20 |
| 互动成本 | >¥5 | ¥2-5 | <¥2 |

---

## 五、注意事项

### 5.1 数据有效性

- 部分API仅对蒲公英博主有效（如 `get-kol-note-list/v1`）
- 非蒲公英博主需要使用其他API获取笔记列表
- 数据有时效性，建议获取后立即生成报告

### 5.2 漏斗分析重要性

漏斗分析是评估KOL内容转化能力的**核心指标**，必须：
1. 选择热门笔记进行分析
2. 完整展示漏斗各层转化率
3. 与行业参考数据对比
4. 给出明确的评价和结论

### 5.3 同行数据估算

当API返回"超越X%同行"时，可以反推同行中位数：
- 超越95%: 同行中位数 ≈ 该KOL数值的 15%-25%
- 超越80%: 同行中位数 ≈ 该KOL数值的 50%-60%
- 超越50%: 同行中位数 ≈ 该KOL数值的 90%-100%

---

*规范版本: 1.0*
*最后更新: 2025-12-08*
