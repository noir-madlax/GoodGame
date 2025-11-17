# 星图KOL接口调用说明

## 问题分析

### 当前问题
所有星图接口调用都返回 **400错误**：
```json
{
  "code": 400,
  "message": "Request failed. Please retry.",
  "message_zh": "请求失败，请重试。请查看下方文档核对参数"
}
```

### 根本原因

根据TikHub API文档（`backend/test/kol/doc/接口依赖关系与数据流.md`），**星图接口需要Cookie**才能访问：

| 接口 | Cookie是否必需 | 无Cookie影响 |
|------|--------------|-------------|
| 1.1 获取KOL ID | **推荐** | 可能失败 ❌ |
| 1.2 基础信息 | **推荐** | 数据不全 |
| 1.3 受众画像 | **必需** | 无法获取 ❌ |
| 1.4 服务报价 | **必需** | 无法获取 ❌ |
| 1.5 内容定位 | **必需** | 无法获取 ❌ |
| 1.6 转化能力 | **必需** | 无法获取 ❌ |

**结论**: 没有Cookie，星图接口无法正常工作。

---

## 解决方案

### 方案1: 获取抖音Cookie（推荐）

#### 步骤1: 获取Cookie

1. **打开抖音网页版**
   - 访问：https://www.douyin.com
   - 或访问星图平台：https://star.toutiao.com

2. **登录账号**
   - 使用抖音账号登录
   - 建议使用有星图权限的账号

3. **获取Cookie**
   - 方法1: 使用浏览器开发者工具
     - 按F12打开开发者工具
     - 切换到 Network 标签
     - 刷新页面
     - 选择任意请求
     - 找到 Request Headers 中的 Cookie
     - 复制完整Cookie字符串
   
   - 方法2: 使用浏览器插件
     - 安装 "EditThisCookie" 或类似插件
     - 导出Cookie为JSON格式

#### 步骤2: 保存Cookie

创建Cookie文件：
```bash
# 创建cookie目录
mkdir -p backend/test/kol/cookie

# 创建cookie文件
touch backend/test/kol/cookie/douyin_cookie.txt
```

将Cookie粘贴到文件中，格式如下：
```
ttwid=xxx; sessionid=xxx; passport_csrf_token=xxx; ...
```

#### 步骤3: 修改代码使用Cookie

在脚本中添加Cookie到请求头：
```python
def load_cookie():
    """从文件加载Cookie"""
    cookie_path = Path(__file__).parent.parent / "cookie" / "douyin_cookie.txt"
    
    if not cookie_path.exists():
        return None
    
    with open(cookie_path, 'r') as f:
        cookie = f.read().strip()
    
    return cookie

# 在请求头中添加Cookie
headers = {
    'accept': 'application/json',
    'Authorization': f'Bearer {api_key}',
    'Cookie': cookie  # ← 添加Cookie
}
```

---

### 方案2: 使用其他可用接口（临时方案）

如果无法获取Cookie，可以使用**不需要Cookie的接口**获取达人数据：

#### 可用接口：

1. **✅ 热门账号搜索** (已成功)
   - 接口: `fetch_hot_account_search_list`
   - 返回: 基础信息（粉丝、作品、点赞数）
   - 优势: 不需要Cookie

2. **✅ 通用搜索** (已验证)
   - 接口: `fetch_general_search_v3`
   - 返回: 用户基础信息和视频列表
   - 优势: 不需要Cookie

3. **⚠️ 用户详情接口**（需验证）
   - 可能可以获取更详细的用户信息
   - 需要测试是否需要Cookie

#### 数据对比：

| 数据项 | 热门账号搜索 | 星图接口 |
|--------|------------|----------|
| 昵称 | ✅ | ✅ |
| 粉丝数 | ✅ | ✅ |
| 作品数 | ✅ | ✅ |
| 获赞数 | ✅ | ✅ |
| 头像 | ✅ | ✅ |
| **受众画像** | ❌ | ✅ |
| **服务报价** | ❌ | ✅ |
| **内容定位** | ❌ | ✅ |
| **转化能力** | ❌ | ✅ |
| **认证信息** | ❌ | ✅ |

---

## 当前进展

### ✅ 已完成

1. **达人账号搜索** (63/64成功)
   - 文件: `final_kol_accounts_20251113_182240.json`
   - 包含：user_id, 昵称, 粉丝数, 作品数, 点赞数等

2. **智能账号匹配**
   - 综合评分系统
   - 自动筛选真实主账号

### ❌ 受阻

1. **星图KOL ID获取** (失败)
   - 原因: 缺少Cookie
   - 影响: 无法调用后续星图接口

2. **星图详细数据** (未执行)
   - 依赖: KOL ID
   - 状态: 等待Cookie

---

## 下一步建议

### 选择1: 如果能获取Cookie（推荐）

1. 按照上述步骤获取Cookie
2. 修改代码添加Cookie支持
3. 重新运行星图接口获取详细数据
4. 获取完整的KOL画像（受众、报价、转化能力等）

**优势**: 
- 获取最完整的数据
- 支持商务分析
- 数据权威性高

### 选择2: 使用现有数据（快速方案）

1. 使用已获取的63个达人基础数据
2. 通过其他接口补充信息：
   - 获取达人的作品列表
   - 分析作品内容和风格
   - 评估粉丝互动情况

**优势**:
- 无需额外认证
- 可以立即开始
- 基础数据已足够做初步分析

---

## 技术参考

### Cookie格式示例

```
Cookie: ttwid=1%7CxxxA; sessionid=xxxB; passport_csrf_token=xxxC; sid_guard=xxxD; uid_tt=xxxE; uid_tt_ss=xxxF; sid_tt=xxxG; ssid_ucp_v1=xxxH; ...
```

### Cookie有效期

- **有效期**: 通常7-30天
- **建议**: 定期更新Cookie
- **注意**: Cookie包含敏感信息，不要提交到公开仓库

### 环境变量配置

可以将Cookie存储在 `.env` 文件中：
```bash
# backend/.env
DOUYIN_COOKIE=ttwid=xxx;sessionid=xxx;...
```

在代码中读取：
```python
cookie = os.getenv('DOUYIN_COOKIE')
```

---

## 当前可用数据

即使没有星图数据，我们已经成功获取了：

### ✅ 63个达人的基础信息

```json
{
  "name": "程十安an",
  "rank": 1,
  "mention_count": 3,
  "platforms": ["抖音"],
  "characteristics": ["变美教程", "干货分享", ...],
  "douyin_account": {
    "user_id": "MS4wLjAB...",
    "nick_name": "程十安an",
    "fans_count": 22133832,
    "like_count": 162303056,
    "publish_count": 319,
    "match_quality": {
      "score": 0.7739,
      "confidence": "high"
    }
  }
}
```

### 可以进行的分析

即使没有星图数据，现有数据也足以：

1. **影响力评估**
   - 粉丝规模排名
   - 内容受欢迎程度（点赞数）
   - 内容活跃度（作品数）

2. **达人分类**
   - 按粉丝数分级
   - 按专业背景分类
   - 按特征标签分组

3. **初步筛选**
   - 找出头部达人
   - 识别垂直领域KOL
   - 评估匹配质量

---

## 总结

**问题**: 星图接口需要Cookie才能访问  
**状态**: 当前无法调用星图接口  
**影响**: 无法获取受众画像、服务报价等高级数据  
**建议**: 优先获取Cookie以解锁完整功能  
**备选**: 使用现有基础数据进行初步分析

---

**更新时间**: 2025-11-13  
**文件位置**: `backend/test/kol/output/xingtu_kol_data/`

