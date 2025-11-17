# 星图API接口调用状态报告

生成时间: 2025-11-13

## 一、执行总结

### ✅ 成功完成的任务

1. **获取星图KOL ID** (接口 1.1)
   - 状态: ✅ **全部成功**
   - 成功数: **5/5**
   - 接口: `get_xingtu_kolid_by_sec_user_id`
   - 参数: `sec_user_id`
   - 输出文件: `kol_ids_only_20251113.json`

### ❌ 遇到的问题

所有后续星图接口（1.2-1.6）均返回 **HTTP 400 错误**：
```
请求失败，请重试。请查看下方文档核对参数，使用默认演示参数测试，并将响应 JSON 提交给支持团队。
```

## 二、已获取的KOL ID数据

| 排名 | 达人名称 | 星图KOL ID | 状态 |
|------|---------|-----------|------|
| 1 | 程十安an | 6831825876674412552 | ✅ |
| 2 | 骆王宇 | 6749073463748591630 | ✅ |
| 3 | 勇仔leo | 6821080910151024654 | ✅ |
| 4 | Daily-cici | 6870169841878171662 | ✅ |
| 5 | 大夏天理性护肤 | 6618403120433070094 | ✅ |

## 三、接口测试详情

### 3.1 接口 1.1: 获取星图KOL ID ✅

- **端点**: `/douyin/xingtu/get_xingtu_kolid_by_sec_user_id`
- **参数**: 
  - `sec_user_id`: 抖音用户的sec_user_id
- **状态**: ✅ **成功**
- **测试结果**: 所有5个KOL都成功获取到星图ID

### 3.2 接口 1.2: 获取KOL基础信息 ❌

- **端点**: `/douyin/xingtu/kol_base_info_v1`
- **参数**: 
  - `kolId`: 星图KOL ID（驼峰命名）
  - `platformChannel`: 平台渠道
    - `_1`: 抖音短视频(Video)
    - `_10`: 抖音直播(Live)
- **状态**: ❌ **HTTP 400**
- **测试**: 尝试了 `_1` 和 `_10`，都返回400错误

### 3.3 接口 1.3: 获取KOL受众画像 ❌

- **端点**: `/douyin/xingtu/kol_audience_portrait_v1`
- **参数**: 
  - `kolId`: 星图KOL ID
- **状态**: ❌ **HTTP 400**
- **备注**: 之前单独测试时成功过，但批量运行时失败

### 3.4 接口 1.4: 获取KOL服务报价 ❌

- **端点**: `/douyin/xingtu/kol_service_price_v1`
- **参数**: 
  - `kolId`: 星图KOL ID
  - `platformChannel`: 平台渠道 (`_1` 或 `_10`)
- **状态**: ❌ **HTTP 400**

### 3.5 接口 1.5: 获取KOL性价比能力 ❌

- **端点**: `/douyin/xingtu/kol_cp_info_v1`
- **参数**: 
  - `kolId`: 星图KOL ID
- **状态**: ❌ **HTTP 400**
- **备注**: 之前单独测试时成功过，但批量运行时失败

### 3.6 接口 1.6: 获取KOL转化能力分析 ❌

- **端点**: `/douyin/xingtu/kol_conversion_ability_analysis_v1`
- **参数**: 
  - `kolId`: 星图KOL ID
  - `_range`: 时间范围
    - `_3`: 90天
- **状态**: ❌ **HTTP 400**

## 四、问题分析

### 可能的原因

1. **Cookie失效** ⚠️
   - Cookie可能已过期
   - 需要重新获取抖音登录态
   
2. **API权限限制** ⚠️
   - 这些接口可能需要企业级或付费API权限
   - 当前API Key可能只有基础查询权限
   
3. **接口参数不完整** ⚠️
   - 可能还有其他必需参数未在文档中明确说明
   - 需要查看TikHub官方示例代码

4. **请求频率限制** ⚠️
   - 可能触发了TikHub的限流机制
   - 需要增加请求间隔或使用缓存

### 验证步骤

接口 1.3 和 1.5 在单独测试时曾经成功，说明：
- ✅ 参数格式正确
- ✅ API Key和Cookie曾经有效
- ❌ 但现在无法访问，可能是权限或Cookie问题

## 五、已创建的工具和脚本

### 5.1 独立接口脚本

所有脚本位于: `backend/test/kol/code/xingtu/`

| 脚本文件 | 接口 | 功能 | 状态 |
|---------|------|------|------|
| `utils.py` | - | 共享工具函数 | ✅ |
| `1_3_audience_portrait.py` | 1.3 | 受众画像 | 📝 已创建 |
| `1_5_cp_info.py` | 1.5 | 性价比能力 | 📝 已创建 |
| `1_2_base_info.py` | 1.2 | 基础信息 | 📝 已创建 |
| `1_4_service_price.py` | 1.4 | 服务报价 | 📝 已创建 |
| `1_6_conversion_ability.py` | 1.6 | 转化能力 | 📝 已创建 |

### 5.2 功能特性

- ✅ 增量获取（避免重复调用）
- ✅ 自动参数测试
- ✅ 结果保存
- ✅ 进度追踪

## 六、下一步建议

### 方案 A: 联系TikHub支持 🎯 **推荐**

1. 联系TikHub Discord支持: https://discord.gg/aMEAS8Xsvz
2. 询问：
   - 这些接口是否需要特殊权限？
   - Cookie失效周期是多久？
   - 是否有完整的调用示例？
   - API Key的权限范围？

### 方案 B: 更新Cookie

1. 重新登录抖音网页版: https://www.douyin.com
2. 使用浏览器插件导出最新Cookie
3. 替换 `backend/test/kol/cookie` 文件
4. 重新运行脚本

### 方案 C: 使用替代数据源

如果星图接口无法使用，考虑：
1. 使用抖音公开API获取基础数据
2. 使用第三方数据服务
3. 人工收集关键数据

## 七、已保存的数据文件

### 主要输出文件

| 文件路径 | 内容 | 状态 |
|---------|------|------|
| `output/xingtu_kol_data/kol_ids_only_20251113.json` | 5个KOL的星图ID | ✅ 完整 |
| `output/kol_user_ids/final_kol_accounts_20251113_182240.json` | 64个KOL的抖音账号信息 | ✅ 完整 |

### 输出数据示例

`kol_ids_only_20251113.json`:
```json
{
  "metadata": {
    "generated_at": "2025-11-13T...",
    "total_kols": 5,
    "data_source": "TikHub Xingtu API"
  },
  "kol_ids": [
    {
      "rank": 1,
      "name": "程十安an",
      "xingtu_kol_id": "6831825876674412552",
      "core_user_id": "95203319762",
      "tag": "时尚",
      ...
    }
  ]
}
```

## 八、技术要点总结

### 成功经验

1. ✅ 参数命名: 使用 **驼峰命名** (`kolId` 而非 `kol_id`)
2. ✅ 域名选择: 使用 **中国加速域名** (`api.tikhub.dev`)
3. ✅ Cookie格式: JSON数组转换为分号分隔的字符串
4. ✅ 增量逻辑: 避免重复获取，节省token

### 参数配置

```python
# 正确的参数格式
params = {
    'kolId': '6831825876674412552',        # 驼峰命名
    'platformChannel': '_1',                # _1=短视频, _10=直播
    '_range': '_3'                         # _3=90天
}

# 请求头
headers = {
    'accept': 'application/json',
    'Authorization': f'Bearer {api_key}',
    'Cookie': cookie_string                # Cookie字符串
}
```

---

**报告完成时间**: 2025-11-13 18:35:00  
**生成工具**: AI Agent  
**状态**: 等待进一步指示或权限确认

