# 小红书蒲公英 Solar 接口测试报告

**测试时间**: 2025-12-09 16:28:35
**测试 userId**: `5d21ab6b000000001201567d`

---

## 一、测试结果汇总

| 接口名称 | 描述 | 状态 | code | 返回字段数 |
|---------|------|------|------|-----------|
| `solar_notes_detail_v2` | KOL 笔记详情列表 (已有文档) | ✅ | 0 | 2 |
| `solar_note_detail` | 笔记详情 (已有文档) | ✅ | 0 | 26 |
| `solar_cooperator_blogger` | 博主合作信息 | ❌ | 301 | 0 |
| `solar_fans_overall_new_history` | 粉丝整体新增历史 | ❌ | HTTP 400 | 0 |
| `solar_fans_profile` | 粉丝画像详情 | ❌ | 301 | 0 |
| `solar_cost_effective_v2` | 性价比分析 V2 | ✅ | 0 | 15 |
| `solar_kol_content_tags` | KOL 内容标签 | ❌ | 500 | 0 |
| `solar_kol_feature_tags` | KOL 特征标签 | ❌ | 500 | 0 |
| `solar_data_summary_v3` | 数据概览 V3 | ❌ | HTTP 400 | 0 |
| `solar_fans_summary_v3` | 粉丝分析 V3 | ❌ | 301 | 0 |
| `solar_notes_rate_v3` | 笔记数据率 V3 | ❌ | HTTP 400 | 0 |
| `solar_similar_kol` | 相似 KOL 推荐 | ❌ | HTTP 400 | 0 |

**成功率**: 3/12 (25.0%)

---

## 二、接口详情

### KOL 笔记详情列表 (已有文档) (`solar_notes_detail_v2`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/dataV2/notesDetail/v1`

**状态**: ✅ (code=0)

**返回字段**:

```
list, total
```

**返回数据示例**:

```json
{
  "list": [
    {
      "readNum": 50,
      "likeNum": 6,
      "collectNum": 4,
      "isAdvertise": false,
      "isVideo": false,
      "noteId": "692d91eb000000001e037005",
      "imgUrl": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k831pi69onqkkdg5n91ldlkiljt20101dg?imageView2/2/w/540/format/jpg/q/75",
      "title": "这时候三千多买二手iphone16还划算吗？",
      "brandName": null,
      "date": "2025-12-01",
      "thirdReadUserNum": 0
    },
    {
      "readNum": 6666,
      "likeNum": 70,
      "collectNum": 27,
      "isAdvertise": false,
      "isVideo": false,
      "noteId": "69240b58000000001e023d03",
      "imgUrl": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k831p8qlbt8jc705n91ldlkiljtfidp5u0?imageView2/2/w/540/format/jpg/q/75",
      "title": "🎄女大圣诞送礼提前大放送～🎁",
      "brandName": null,
      "date": "2025-11-24",
      "thirdReadUserNum": 0
    },
    {
      "readNum": 388,
      "likeNum": 12,
      "collectNum": 7,
      "isAdvertise": false,
      "isVideo": false,
      "noteId": "69206b40000000001f005f90",
      "imgUrl": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k031p5b6cdrig005n91ldlkiljtp52bogo?imageView2/2/w/540/format/jpg/q/75",
      "title": "🛍️实战丹阳眼镜城配镜分享",
      "brandName": "Lina和Bill的眼镜丹阳店",
      "date": "2025-11-21",
      "thirdReadUserNum": 0
    },
    {
      "readNum": 1475,
      "likeNum": 61,
      "collectNum": 18,
      "isAdvertise": false,
      "isVideo": false,
      "noteId": "691d67c4000000001e02ae6c",
      "imgUrl": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k831p2ct02k2gdg5n91ldlkiljtaq2qkhg?imageView2/2/w/540/format/jpg/q/75",
      "title": "🛍️冬季宿舍好物分享～",
      "brandName": null,
      "date": "2025-11-19",
      "thirdReadUserNum": 0
    },
    {
      "readNum": 273,
      "likeNum": 9,
      "collectNum": 4,
      "isAdvertise": false,
      "isVideo": false,
      "noteId": "6912eabd0000000004017f42",
      "imgUrl": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k831oo5amjg06005n91ldlkiljtq6l7g68?i
```

---

### 笔记详情 (已有文档) (`solar_note_detail`)

**端点**: `/api/xiaohongshu-pgy/api/solar/note/noteId/detail/v1`

**状态**: ✅ (code=0)

**返回字段**:

```
noteId, noteLink, userId, headPhoto, name, redId, type, atUserList, title, content, imagesList, videoInfo, time, createTime, impNum, likeNum, favNum, cmtNum, readNum, shareNum, followCnt, reportBrandUserId, reportBrandName, featureTags, userInfo, compClickData
```

**返回数据示例**:

```json
{
  "noteId": "684aae12000000002001f502",
  "noteLink": "https://www.xiaohongshu.com/explore/684aae12000000002001f502?xsec_token=MBeNOjBrcuO0ZgUQpUs50PCnT8Y9wvM0EUVogwRGu4r2E=&xsec_source=pc_pgy",
  "userId": "5d21ab6b000000001201567d",
  "headPhoto": "https://sns-avatar-qc.xhscdn.com/avatar/1040g2jo31l3ar7uj2o0g5n91ldlkiljt8aok490?imageView2/2/w/120/format/jpg",
  "name": "荔枝吱吱",
  "redId": null,
  "type": 1,
  "atUserList": null,
  "title": "Pdd可爱抱枕分享🍰附🔗",
  "content": "#抱枕[话题]# #可爱好物[话题]# #可爱抱枕[话题]# #好物分享[话题]# #沙发抱枕[话题]# #靠枕[话题]# #玩偶[话题]# #软乎乎[话题]# #公仔[话题]# #好物[话题]#",
  "imagesList": [
    {
      "fileId": "notes_pre_post/1040g3k031ikjs3rgg8705n91ldlkiljt4hkeon8",
      "url": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k031ikjs3rgg8705n91ldlkiljt4hkeon8?imageView2/2/w/1080/format/jpg",
      "original": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k031ikjs3rgg8705n91ldlkiljt4hkeon8",
      "width": 1309,
      "height": 1746,
      "latitude": null,
      "longitude": null,
      "traceId": "notes_pre_post/1040g3k031ikjs3rgg8705n91ldlkiljt4hkeon8",
      "sticker": null
    },
    {
      "fileId": "notes_pre_post/1040g3k031ikjs3rgg87g5n91ldlkiljtdkusaeg",
      "url": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k031ikjs3rgg87g5n91ldlkiljtdkusaeg?imageView2/2/w/1080/format/jpg",
      "original": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k031ikjs3rgg87g5n91ldlkiljtdkusaeg",
      "width": 1024,
      "height": 929,
      "latitude": null,
      "longitude": null,
      "traceId": "notes_pre_post/1040g3k031ikjs3rgg87g5n91ldlkiljtdkusaeg",
      "sticker": null
    },
    {
      "fileId": "notes_pre_post/1040g3k031ikjs3rgg8805n91ldlkiljtbbb8bq0",
      "url": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k031ikjs3rgg8805n91ldlkiljtbbb8bq0?imageView2/2/w/1080/format/jpg",
      "original": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k031ikjs3rgg8805n91ldlkiljtbbb8bq0",
      "width": 1024,
      "height": 931,
      "latitude": null,
      
```

---

### 博主合作信息 (`solar_cooperator_blogger`)

**端点**: `/api/xiaohongshu-pgy/api/solar/cooperator/user/blogger/userId/v1`

**状态**: ❌ (code=301)

---

### 粉丝整体新增历史 (`solar_fans_overall_new_history`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/data/userId/fans_overall_new_history/v1`

**状态**: ❌ (code=HTTP 400)

---

### 粉丝画像详情 (`solar_fans_profile`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/data/userId/fans_profile/v1`

**状态**: ❌ (code=301)

---

### 性价比分析 V2 (`solar_cost_effective_v2`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/dataV2/costEffective/v1`

**状态**: ✅ (code=0)

**返回字段**:

```
date, pictureReadCost, videoReadCost, pictureSurpassRate, videoSurpassRate, pictureCase, videoCase, estimatePictureCpm, estimatePictureCpmCompare, estimateVideoCpm, estimateVideoCpmCompare, estimatePictureEngageCost, estimatePictureEngageCostCompare, estimateVideoEngageCost, estimateVideoEngageCostCompare
```

**返回数据示例**:

```json
{
  "date": null,
  "pictureReadCost": "0.76",
  "videoReadCost": null,
  "pictureSurpassRate": 61.53,
  "videoSurpassRate": null,
  "pictureCase": 0,
  "videoCase": 2,
  "estimatePictureCpm": 51.35520684736091,
  "estimatePictureCpmCompare": 0.021100869474307782,
  "estimateVideoCpm": null,
  "estimateVideoCpmCompare": null,
  "estimatePictureEngageCost": 5.0,
  "estimatePictureEngageCostCompare": 0.019557571246860528,
  "estimateVideoEngageCost": null,
  "estimateVideoEngageCostCompare": null
}
```

---

### KOL 内容标签 (`solar_kol_content_tags`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/dataV2/kolContentTags/v1`

**状态**: ❌ (code=500)

---

### KOL 特征标签 (`solar_kol_feature_tags`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/dataV2/kolFeatureTags/v1`

**状态**: ❌ (code=500)

---

### 数据概览 V3 (`solar_data_summary_v3`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/dataV3/dataSummary/v1`

**状态**: ❌ (code=HTTP 400)

---

### 粉丝分析 V3 (`solar_fans_summary_v3`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/dataV3/fansSummary/v1`

**状态**: ❌ (code=301)

---

### 笔记数据率 V3 (`solar_notes_rate_v3`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/dataV3/notesRate/v1`

**状态**: ❌ (code=HTTP 400)

---

### 相似 KOL 推荐 (`solar_similar_kol`)

**端点**: `/api/xiaohongshu-pgy/api/solar/kol/get_similar_kol/v1`

**状态**: ❌ (code=HTTP 400)

---

## 三、与现有接口对比

| Solar 接口 | 对应的现有接口 | 差异说明 |
|-----------|--------------|---------|
| `solar_data_summary_v3` | `get-kol-data-summary/v2` | V3 版本，可能有更多字段 |
| `solar_fans_summary_v3` | `get-kol-fans-summary/v1` | V3 版本，可能有更多字段 |
| `solar_notes_rate_v3` | `get-kol-note-rate/v1` | V3 版本，可能有更多字段 |
| `solar_cost_effective_v2` | `get-kol-cost-effective/v1` | V2 版本，可能有更多字段 |
| `solar_kol_content_tags` | 无 | 新接口：KOL 内容标签 |
| `solar_kol_feature_tags` | 无 | 新接口：KOL 特征标签 |
| `solar_fans_profile` | `get-kol-fans-portrait/v1` | 可能是更详细的粉丝画像 |
| `solar_fans_overall_new_history` | `get-kol-fans-trend/v1` | 可能是更详细的粉丝历史 |
| `solar_cooperator_blogger` | 无 | 新接口：博主合作信息 |
| `solar_similar_kol` | `get-kol-track/v1` | 相似 KOL 推荐 |
