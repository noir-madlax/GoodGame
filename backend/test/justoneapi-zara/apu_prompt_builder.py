"""
APU Prompt 构建器 (v2 - 商品描述级别)
将 APU 规则库转换为 LLM Prompt

使用页面: 商品入库解析、用户搜索意图解析
功能:
  1. 从数据库加载商品描述级别的 APU 规则
  2. 构建入库解析 Prompt
  3. 构建搜索意图解析 Prompt

APU 五维度结构:
  - category: 商品类型（用于筛选）
  - product_description: 商品描述（主要索引）
  - attribute_keywords: 物理属性
  - performance_keywords: 性能
  - use_keywords: 使用场景
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from supabase import create_client, Client


class APUPromptBuilder:
    """APU Prompt 构建器 - 商品描述级别"""
    
    def __init__(self, supabase: Client):
        """
        初始化
        
        参数:
            supabase: Supabase 客户端
        """
        self.supabase = supabase
        self._rules_cache: Optional[List[Dict]] = None
    
    def load_product_rules(self, featured_only: bool = False) -> List[Dict]:
        """
        加载商品描述级别的 APU 规则
        
        参数:
            featured_only: 是否只加载精选规则（用于 Prompt）
            
        返回:
            规则列表，每个元素包含 5 个维度
        """
        if self._rules_cache is not None and not featured_only:
            return self._rules_cache
        
        # 从新的规则库表加载
        query = self.supabase.table("gg_apu_product_rules").select("*")
        
        if featured_only:
            query = query.eq("is_featured", True)
        
        result = query.order("category").execute()
        
        if not featured_only:
            self._rules_cache = result.data
        
        return result.data
    
    def build_rules_prompt_section(self, max_per_category: int = 3) -> str:
        """
        构建规则的 Prompt 片段（商品描述级别）
        
        参数:
            max_per_category: 每个品类最多展示几个示例
            
        返回:
            格式化的规则文本，用于注入 Prompt
        """
        rules = self.load_product_rules()
        
        if not rules:
            return "## 暂无规则库数据\n"
        
        # 按品类分组
        category_rules: Dict[str, List[Dict]] = {}
        for rule in rules:
            category = rule["category"]
            if category not in category_rules:
                category_rules[category] = []
            category_rules[category].append(rule)
        
        sections = ["## 商品 APU 规则库（商品描述级别）\n"]
        sections.append("以下是各品类的商品示例及其 APU 三维度解析:\n")
        
        for category, cat_rules in category_rules.items():
            section = f"\n### {category}\n"
            
            # 取精选的或前 N 个
            featured = [r for r in cat_rules if r.get("is_featured")]
            examples = featured[:max_per_category] if featured else cat_rules[:max_per_category]
            
            for rule in examples:
                desc = rule["product_description"]
                attr = ", ".join(rule.get("attribute_keywords", []))
                perf = ", ".join(rule.get("performance_keywords", []))
                use = ", ".join(rule.get("use_keywords", []))
                
                section += f"""
**商品描述**: {desc}
- Attribute (物理属性): {attr}
- Performance (性能): {perf}
- Use (使用场景): {use}
"""
            
            sections.append(section)
        
        return "\n".join(sections)
    
    def build_ingest_prompt(self, item_name: str, price: str) -> str:
        """
        构建入库解析的完整 Prompt
        
        参数:
            item_name: 商品名称
            price: 商品价格
            
        返回:
            完整的 Prompt 文本
        """
        rules_section = self.build_rules_prompt_section()
        
        return f"""你是一个服装电商的商品分析专家。请使用 APU 三维度理论分析商品。

## APU 三维度理论

1. **Attribute (属性)** - 物理特性
   商品的物理属性：外观、材质、颜色、版型、设计细节等
   
2. **Performance (性能)** - 性能表现  
   商品的功能表现：舒适度、保暖性、透气性、耐用性、视觉效果等
   
3. **Use (使用)** - 使用场景
   商品适合的场合：日常、通勤、约会、运动、正式场合等

## 因果关系链
物理属性 → 驱动 → 性能表现 → 使能 → 使用场景

例如：
- 凉感面料 → 凉爽透气 → 夏季日常
- 宽松版型 → 舒适不紧绷 → 休闲逛街
- 羊毛材质 → 保暖柔软 → 秋冬通勤

{rules_section}

## 商品信息
商品名称: {item_name}
商品价格: {price}

## 任务
1. 去除商品名称中的品牌(ZARA)、年份(2025)、系列标识(新款/特惠精选/TRF/ZW)、商品编码(末尾数字)
2. 识别商品品类
3. 参考上面的规则库示例，提取三个维度的具体信息
4. 应用因果关系链推理使用场景
5. 生成融合三维度的增强文本

## 输出格式 (严格 JSON)
{{
  "core_description": "去除品牌编码后的核心描述，保留性别+属性+品类",
  "category": "商品品类",
  "attribute": {{
    "keywords": ["从商品名称提取的具体物理属性关键词"],
    "description": "一句话描述物理特征"
  }},
  "performance": {{
    "keywords": ["根据属性推理出的性能关键词"],
    "description": "一句话描述性能表现"
  }},
  "use": {{
    "keywords": ["根据性能推理出的使用场景"],
    "description": "一句话描述适用场景"
  }},
  "causal_reasoning": "简述因果推理过程",
  "enhanced_text": "融合三维度的搜索文本（用于向量化，包含核心描述+属性+性能+场景）"
}}

## 示例

商品: ZARA2025秋季新品 女装 凉感短袖修身圆领T恤 4174325
输出:
{{
  "core_description": "女装 凉感短袖修身圆领T恤",
  "category": "T恤",
  "attribute": {{
    "keywords": ["凉感面料", "短袖", "修身", "圆领"],
    "description": "凉感面料短袖T恤，修身圆领设计"
  }},
  "performance": {{
    "keywords": ["凉爽", "透气", "贴身显瘦"],
    "description": "凉爽透气，修身贴身显瘦"
  }},
  "use": {{
    "keywords": ["夏季日常", "运动", "通勤打底"],
    "description": "适合夏季日常穿着、运动和通勤打底"
  }},
  "causal_reasoning": "凉感面料→凉爽透气→适合夏季日常和运动；修身版型→贴身显瘦→适合通勤打底",
  "enhanced_text": "女装 凉感短袖修身圆领T恤 凉爽透气贴身显瘦 夏季日常运动通勤打底"
}}

商品: ZARA特惠精选 女装 羊毛混纺针织开衫 9598251 737
输出:
{{
  "core_description": "女装 羊毛混纺针织开衫",
  "category": "针织衫",
  "attribute": {{
    "keywords": ["羊毛混纺", "针织", "开衫"],
    "description": "羊毛混纺针织面料，开衫款式"
  }},
  "performance": {{
    "keywords": ["保暖", "柔软", "穿脱方便", "易搭配"],
    "description": "保暖柔软，开衫穿脱方便易搭配"
  }},
  "use": {{
    "keywords": ["秋冬日常", "通勤", "空调房", "叠穿"],
    "description": "适合秋冬日常、通勤、空调房叠穿"
  }},
  "causal_reasoning": "羊毛混纺→保暖柔软→适合秋冬；开衫款式→穿脱方便→适合空调房和叠穿搭配",
  "enhanced_text": "女装 羊毛混纺针织开衫 保暖柔软穿脱方便 秋冬日常通勤空调房叠穿"
}}"""

    def build_search_prompt(self, user_query: str) -> str:
        """
        构建搜索意图解析的完整 Prompt
        
        参数:
            user_query: 用户输入的搜索文本
            
        返回:
            完整的 Prompt 文本
        """
        rules_section = self.build_rules_prompt_section()
        
        return f"""你是一个服装搜索助手。请使用 APU 三维度理论理解用户的搜索意图。

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

{rules_section}

## 用户输入
{user_query}

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
{{
  "primary_dimension": "attribute/performance/use",
  "intent_analysis": {{
    "attribute": ["用户需要的物理属性"],
    "performance": ["用户需要的性能"],
    "use": ["用户的使用场景"]
  }},
  "causal_reasoning": "反向推理过程说明",
  "extracted_tags": ["映射到标签库的标签"],
  "search_text": "融合三维度的向量搜索文本"
}}

## 示例

用户输入: "我想要去沙滩，给我推荐下好的连衣裙"

分析:
- primary_dimension: "use" (用户从场景出发)
- 场景: 沙滩/度假
- 反向推理: 沙滩 → 需要凉爽透气 → 需要轻薄面料
- 品类: 连衣裙

输出:
{{
  "primary_dimension": "use",
  "intent_analysis": {{
    "attribute": ["轻薄", "连衣裙", "飘逸"],
    "performance": ["凉爽", "透气", "舒适"],
    "use": ["度假", "沙滩", "夏季"]
  }},
  "causal_reasoning": "用户要去沙滩→需要凉爽透气的衣服→需要轻薄飘逸面料的连衣裙",
  "extracted_tags": ["女装", "连衣裙", "夏季"],
  "search_text": "女装 连衣裙 轻薄飘逸凉爽透气 度假沙滩夏季"
}}

用户输入: "保暖的羽绒服"

分析:
- primary_dimension: "performance" (用户从性能出发)
- 性能: 保暖
- 品类: 羽绒服

输出:
{{
  "primary_dimension": "performance",
  "intent_analysis": {{
    "attribute": ["羽绒", "厚实"],
    "performance": ["保暖", "防风", "轻便"],
    "use": ["冬季日常", "户外", "通勤"]
  }},
  "causal_reasoning": "用户要保暖→羽绒服保暖性好→适合冬季日常和户外",
  "extracted_tags": ["女装", "羽绒服", "冬季"],
  "search_text": "女装 羽绒服 保暖防风轻便 冬季日常户外通勤"
}}

用户输入: "宽松的牛仔裤"

分析:
- primary_dimension: "attribute" (用户从属性出发)
- 属性: 宽松、牛仔裤

输出:
{{
  "primary_dimension": "attribute",
  "intent_analysis": {{
    "attribute": ["宽松", "牛仔裤", "阔腿"],
    "performance": ["舒适", "不紧绷", "活动自如"],
    "use": ["日常休闲", "周末", "逛街"]
  }},
  "causal_reasoning": "用户要宽松版型→舒适不紧绷→适合日常休闲和周末逛街",
  "extracted_tags": ["女装", "牛仔裤", "宽松", "休闲"],
  "search_text": "女装 宽松阔腿牛仔裤 舒适不紧绷 日常休闲周末逛街"
}}"""


def load_supabase_client() -> Client:
    """加载 Supabase 客户端"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("未找到 SUPABASE_URL 或 SUPABASE_KEY")
    
    return create_client(url, key)


# 测试
if __name__ == "__main__":
    supabase = load_supabase_client()
    builder = APUPromptBuilder(supabase)
    
    # 打印规则
    print("=" * 70)
    print("APU 规则库 Prompt 片段（商品描述级别）")
    print("=" * 70)
    print(builder.build_rules_prompt_section())
