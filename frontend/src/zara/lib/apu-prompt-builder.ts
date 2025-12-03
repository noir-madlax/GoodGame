/**
 * APU Prompt 构建器 (前端版本 v2 - 商品描述级别)
 * 将 APU 规则库转换为 LLM Prompt
 * 
 * 使用页面: zara/search API route
 * 功能:
 *   1. 从数据库加载商品描述级别的 APU 规则
 *   2. 构建搜索意图解析 Prompt
 * 
 * APU 五维度结构:
 *   - category: 商品类型（用于筛选）
 *   - product_description: 商品描述（主要索引）
 *   - attribute_keywords: 物理属性
 *   - performance_keywords: 性能
 *   - use_keywords: 使用场景
 */

// Supabase client 类型使用 any 以兼容不同版本的客户端实例

// ============================================================================
// 类型定义
// ============================================================================

/** APU 商品规则（5 维度） */
interface APUProductRule {
  id: number;
  category: string;              // 商品类型
  product_description: string;   // 商品描述（主要索引）
  attribute_keywords: string[];  // 物理属性
  performance_keywords: string[];// 性能
  use_keywords: string[];        // 使用场景
  is_featured: boolean;          // 是否精选示例
}

// ============================================================================
// 缓存
// ============================================================================

// 规则缓存（列表）
let rulesCache: APUProductRule[] | null = null;
// 缓存时间
let cacheTime: number = 0;
// 缓存有效期（5 分钟）
const CACHE_TTL = 5 * 60 * 1000;

// ============================================================================
// 核心函数
// ============================================================================

/**
 * 加载商品描述级别的 APU 规则
 * 带缓存机制，避免频繁查询数据库
 */
export async function loadAPUProductRules(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supabase: any
): Promise<APUProductRule[]> {
  // 检查缓存是否有效
  const now = Date.now();
  if (rulesCache && (now - cacheTime < CACHE_TTL)) {
    return rulesCache;
  }

  // 从新的规则库表加载
  const { data, error } = await supabase
    .from('gg_apu_product_rules')
    .select('*')
    .order('category');

  if (error) {
    console.error('加载 APU 商品规则失败:', error);
    // 如果有旧缓存，返回旧缓存
    if (rulesCache) {
      return rulesCache;
    }
    return [];
  }

  rulesCache = data || [];
  cacheTime = now;

  return rulesCache;
}

/**
 * 构建规则的 Prompt 片段（商品描述级别）
 * 将数据库规则格式化为 LLM 可理解的文本
 * 
 * @param supabase - Supabase 客户端
 * @param maxPerCategory - 每个品类最多展示几个示例
 */
export async function buildRulesPromptSection(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supabase: any,
  maxPerCategory: number = 3
): Promise<string> {
  const rules = await loadAPUProductRules(supabase);

  if (rules.length === 0) {
    return '## 暂无规则库数据\n';
  }

  // 按品类分组
  const categoryRules: Map<string, APUProductRule[]> = new Map();
  for (const rule of rules) {
    if (!categoryRules.has(rule.category)) {
      categoryRules.set(rule.category, []);
    }
    categoryRules.get(rule.category)!.push(rule);
  }

  const sections: string[] = ['## 商品 APU 规则库（商品描述级别）\n'];
  sections.push('以下是各品类的商品示例及其 APU 三维度解析:\n');

  for (const [category, catRules] of categoryRules) {
    let section = `\n### ${category}\n`;

    // 取精选的或前 N 个
    const featured = catRules.filter(r => r.is_featured);
    const examples = featured.length > 0 
      ? featured.slice(0, maxPerCategory) 
      : catRules.slice(0, maxPerCategory);

    for (const rule of examples) {
      const attr = rule.attribute_keywords.join(', ');
      const perf = rule.performance_keywords.join(', ');
      const use = rule.use_keywords.join(', ');

      section += `
**商品描述**: ${rule.product_description}
- Attribute (物理属性): ${attr}
- Performance (性能): ${perf}
- Use (使用场景): ${use}
`;
    }

    sections.push(section);
  }

  return sections.join('\n');
}

/**
 * 构建搜索意图解析的完整 Prompt
 * 
 * @param supabase - Supabase 客户端
 * @param userQuery - 用户输入的搜索文本
 * @returns 完整的 Prompt 文本
 */
export async function buildSearchPrompt(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supabase: any,
  userQuery: string
): Promise<string> {
  const rulesSection = await buildRulesPromptSection(supabase);

  return `你是一个服装搜索助手。请使用 APU 三维度理论理解用户的搜索意图。

## APU 三维度理论

用户搜索时，其意图通常落在三个维度：

1. **Attribute (属性)** - 用户想要什么物理特征？
   例如："纯棉的"、"宽松的"、"长袖的"

2. **Performance (性能)** - 用户关心什么性能？
   例如："穿着舒服"、"保暖的"、"显瘦的"

3. **Use (使用)** - 用户在什么场景使用？
   例如："上班穿"、"约会穿"、"去沙滩"

## 因果关系链（反向推理）
使用场景 → 需要的性能 → 需要的物理属性

例如：
- 去沙滩 → 需要凉爽透气 → 需要轻薄面料
- 上班穿 → 需要得体正式 → 需要修身简约
- 冬天户外 → 需要保暖防风 → 需要厚实羽绒

${rulesSection}

## 用户输入
${userQuery}

## 任务
1. 判断用户主要关注哪个维度 (attribute/performance/use)
2. 从用户输入提取/推理三个维度的需求
3. 参考规则库中的商品描述，匹配用户的自然语言
4. 输出标准化的搜索参数

## 标签库（只能使用以下标签）
- 性别: 女装, 男装, 童装
- 季节: 春季, 夏季, 秋季, 冬季
- 品类: T恤, 针织衫, 外套, 牛仔裤, 连衣裙, 大衣, 卫衣, 衬衫, 休闲裤, 半身裙, 包, 鞋, 棉服, 羽绒服, 开衫, 背心, 西装, 上衣
- 风格: 修身, 宽松, 休闲, 通勤, 基础, 简约, 时尚

## 输出格式 (严格 JSON)
{
  "isSearch": true,
  "primary_dimension": "attribute/performance/use",
  "intent_analysis": {
    "attribute": ["用户需要的物理属性"],
    "performance": ["用户需要的性能"],
    "use": ["用户的使用场景"]
  },
  "causal_reasoning": "反向推理过程说明",
  "extractedTags": ["映射到标签库的标签"],
  "searchText": "融合三维度的向量搜索文本"
}

## 示例

用户输入: "我想要去沙滩，给我推荐下好的连衣裙"
输出:
{
  "isSearch": true,
  "primary_dimension": "use",
  "intent_analysis": {
    "attribute": ["轻薄", "连衣裙", "飘逸"],
    "performance": ["凉爽", "透气", "舒适"],
    "use": ["度假", "沙滩", "夏季"]
  },
  "causal_reasoning": "用户要去沙滩→需要凉爽透气的衣服→需要轻薄飘逸面料的连衣裙",
  "extractedTags": ["女装", "连衣裙", "夏季"],
  "searchText": "女装 连衣裙 轻薄飘逸凉爽透气 度假沙滩夏季"
}

用户输入: "保暖的羽绒服"
输出:
{
  "isSearch": true,
  "primary_dimension": "performance",
  "intent_analysis": {
    "attribute": ["羽绒", "厚实"],
    "performance": ["保暖", "防风", "轻便"],
    "use": ["冬季日常", "户外", "通勤"]
  },
  "causal_reasoning": "用户要保暖→羽绒服保暖性好→适合冬季日常和户外",
  "extractedTags": ["女装", "羽绒服", "冬季"],
  "searchText": "女装 羽绒服 保暖防风轻便 冬季日常户外通勤"
}

用户输入: "宽松的牛仔裤"
输出:
{
  "isSearch": true,
  "primary_dimension": "attribute",
  "intent_analysis": {
    "attribute": ["宽松", "牛仔裤", "阔腿"],
    "performance": ["舒适", "不紧绷", "活动自如"],
    "use": ["日常休闲", "周末", "逛街"]
  },
  "causal_reasoning": "用户要宽松版型→舒适不紧绷→适合日常休闲和周末逛街",
  "extractedTags": ["女装", "牛仔裤", "宽松", "休闲"],
  "searchText": "女装 宽松阔腿牛仔裤 舒适不紧绷 日常休闲周末逛街"
}`;
}

/**
 * 清除规则缓存
 * 在规则更新后调用
 */
export function clearAPURulesCache(): void {
  rulesCache = null;
  cacheTime = 0;
}
