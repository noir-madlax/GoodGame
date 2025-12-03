"""
全量商品 APU 分析脚本
使用 LLM 分析所有商品的 Attribute-Performance-Use 三维度

使用页面: 独立分析脚本
功能:
  1. 从数据库读取所有商品
  2. 使用 LLM (Gemini) 分析每个商品的 APU
  3. 输出 JSON 结果供用户确认
  4. 确认后同时入库到:
     - gg_taobao_product_apu: 商品 APU 解析结果
     - gg_apu_product_rules: 新的规则库（5 维度）

运行方式:
  # 分析并输出 JSON（不入库）
  python analyze_products_apu.py --output output/apu_analysis.json
  
  # 分析指定数量的商品（测试用）
  python analyze_products_apu.py --limit 10 --output output/apu_analysis_test.json
  
  # 将确认后的 JSON 入库（同时导入 product_apu 和 product_rules）
  python analyze_products_apu.py --import output/apu_analysis.json
"""

import os
import json
import re
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI

from apu_prompt_builder import APUPromptBuilder, load_supabase_client


# ==================== 配置 ====================
# LLM 配置
LLM_MODEL = "google/gemini-2.5-flash"  # 通过 OpenRouter 调用
REQUEST_DELAY = 0.5  # 请求间隔（秒）
MAX_RETRIES = 3      # 最大重试次数

# 输出目录
OUTPUT_DIR = Path(__file__).parent / "output" / "apu_analysis"


class ProductAPUAnalyzer:
    """商品 APU 分析器"""
    
    def __init__(self, supabase: Client, llm_client: OpenAI):
        """
        初始化
        
        参数:
            supabase: Supabase 客户端
            llm_client: OpenAI/OpenRouter 客户端
        """
        self.supabase = supabase
        self.llm = llm_client
        self.prompt_builder = APUPromptBuilder(supabase)
    
    def get_all_products(self, limit: Optional[int] = None, skip_analyzed: bool = False) -> List[Dict]:
        """
        获取所有商品
        
        参数:
            limit: 限制数量（用于测试）
            skip_analyzed: 是否跳过已分析的商品（增量模式）
        """
        if skip_analyzed:
            # 获取已分析的商品 ID
            analyzed_result = self.supabase.table("gg_taobao_product_apu").select("product_id").execute()
            analyzed_ids = [r["product_id"] for r in analyzed_result.data]
            
            # 获取未分析的商品
            query = self.supabase.table("gg_taobao_products").select(
                "id, item_id, item_name, price_yuan"
            )
            
            if analyzed_ids:
                # 使用 not.in_ 过滤已分析的商品
                query = query.not_.in_("id", analyzed_ids)
            
            query = query.order("id")
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            return result.data
        else:
            query = self.supabase.table("gg_taobao_products").select(
                "id, item_id, item_name, price_yuan"
            ).order("id")
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            return result.data
    
    def analyze_single_product(self, product: Dict) -> Dict:
        """
        分析单个商品的 APU
        
        参数:
            product: 商品数据
            
        返回:
            APU 分析结果
        """
        item_name = product["item_name"]
        price = str(product["price_yuan"])
        
        # 构建 Prompt
        prompt = self.prompt_builder.build_ingest_prompt(item_name, price)
        
        # 调用 LLM
        for retry in range(MAX_RETRIES):
            try:
                response = self.llm.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000,
                )
                
                content = response.choices[0].message.content
                
                # 解析 JSON
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    result = json.loads(json_match.group())
                    result["_source"] = {
                        "product_id": product["id"],
                        "item_id": product["item_id"],
                        "original_name": item_name,
                        "price": price,
                    }
                    return result
                else:
                    raise ValueError("LLM 返回格式错误，无法解析 JSON")
                    
            except Exception as e:
                print(f"   ⚠️ 重试 {retry + 1}/{MAX_RETRIES}: {e}")
                if retry < MAX_RETRIES - 1:
                    time.sleep(2)
                else:
                    return {
                        "_error": str(e),
                        "_source": {
                            "product_id": product["id"],
                            "item_id": product["item_id"],
                            "original_name": item_name,
                            "price": price,
                        }
                    }
        
        return None
    
    def analyze_all_products(
        self, 
        limit: Optional[int] = None,
        output_path: Optional[Path] = None,
        skip_analyzed: bool = False
    ) -> List[Dict]:
        """
        分析所有商品
        
        参数:
            limit: 限制数量
            output_path: 输出文件路径
            skip_analyzed: 是否跳过已分析的商品（增量模式）
            
        返回:
            所有分析结果
        """
        # 获取商品
        products = self.get_all_products(limit, skip_analyzed)
        print(f"📋 共 {len(products)} 个商品待分析")
        
        results = []
        success_count = 0
        error_count = 0
        
        start_time = time.time()
        
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{len(products)}] 分析: {product['item_name'][:50]}...")
            
            result = self.analyze_single_product(product)
            
            if result and "_error" not in result:
                results.append(result)
                success_count += 1
                print(f"   ✅ 品类: {result.get('category', '未知')}")
                print(f"   📝 核心描述: {result.get('core_description', '')[:40]}...")
            else:
                results.append(result)
                error_count += 1
                print(f"   ❌ 分析失败")
            
            # 请求间隔
            if i < len(products):
                time.sleep(REQUEST_DELAY)
            
            # 每 50 个保存一次（防止中断丢失）
            if output_path and i % 50 == 0:
                self._save_results(results, output_path)
                print(f"   💾 已保存 {i} 条结果")
        
        elapsed = time.time() - start_time
        
        # 最终保存
        if output_path:
            self._save_results(results, output_path)
        
        # 统计
        print(f"\n" + "=" * 70)
        print(f"📊 分析完成:")
        print(f"   总数: {len(products)}")
        print(f"   成功: {success_count}")
        print(f"   失败: {error_count}")
        print(f"   耗时: {elapsed:.1f} 秒")
        if output_path:
            print(f"   输出: {output_path}")
        print("=" * 70)
        
        return results
    
    def _save_results(self, results: List[Dict], output_path: Path):
        """保存结果到 JSON 文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 格式化输出，方便查看
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "total_count": len(results),
            "success_count": len([r for r in results if "_error" not in r]),
            "error_count": len([r for r in results if "_error" in r]),
            "results": results
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    def import_results(self, json_path: Path) -> Dict[str, int]:
        """
        将 JSON 结果导入数据库
        同时导入到:
          - gg_taobao_product_apu: 商品 APU 解析结果
          - gg_apu_product_rules: 新的规则库（5 维度）
        
        参数:
            json_path: JSON 文件路径
            
        返回:
            {"apu": 导入数量, "rules": 导入数量}
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        results = data.get("results", [])
        print(f"📋 准备导入 {len(results)} 条结果")
        
        apu_imported = 0
        rules_imported = 0
        
        for result in results:
            if "_error" in result:
                continue
            
            source = result.get("_source", {})
            product_id = source.get("product_id")
            core_description = result.get("core_description", "")
            category = result.get("category")
            
            if not product_id or not core_description:
                continue
            
            # ====== 1. 导入 gg_taobao_product_apu ======
            apu_record = {
                "product_id": product_id,
                "core_description": core_description,
                "category": category,
                "attribute_keywords": result.get("attribute", {}).get("keywords", []),
                "attribute_description": result.get("attribute", {}).get("description"),
                "performance_keywords": result.get("performance", {}).get("keywords", []),
                "performance_description": result.get("performance", {}).get("description"),
                "use_keywords": result.get("use", {}).get("keywords", []),
                "use_description": result.get("use", {}).get("description"),
                "causal_reasoning": result.get("causal_reasoning"),
                "enhanced_text": result.get("enhanced_text", ""),
            }
            
            try:
                self.supabase.table("gg_taobao_product_apu").upsert(
                    apu_record,
                    on_conflict="product_id"
                ).execute()
                apu_imported += 1
            except Exception as e:
                print(f"   ⚠️ APU 导入失败 (product_id={product_id}): {e}")
            
            # ====== 2. 导入 gg_apu_product_rules ======
            # 新的规则库：5 维度结构
            rules_record = {
                "category": category or "未分类",
                "product_description": core_description,  # 商品描述作为主要索引
                "attribute_keywords": result.get("attribute", {}).get("keywords", []),
                "performance_keywords": result.get("performance", {}).get("keywords", []),
                "use_keywords": result.get("use", {}).get("keywords", []),
                "is_featured": False,  # 默认非精选，后续可手动标记
                "source": "llm_analysis",
            }
            
            try:
                self.supabase.table("gg_apu_product_rules").upsert(
                    rules_record,
                    on_conflict="product_description"
                ).execute()
                rules_imported += 1
            except Exception as e:
                print(f"   ⚠️ Rules 导入失败 (desc={core_description[:30]}): {e}")
        
        print(f"\n✅ 导入完成:")
        print(f"   gg_taobao_product_apu: {apu_imported} 条")
        print(f"   gg_apu_product_rules: {rules_imported} 条")
        
        return {"apu": apu_imported, "rules": rules_imported}


def load_llm_client() -> OpenAI:
    """加载 LLM 客户端（通过 OpenRouter）"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("未找到 OPENROUTER_API_KEY")
    
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="商品 APU 分析工具")
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出 JSON 文件路径"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="限制分析数量（用于测试）"
    )
    parser.add_argument(
        "--import", "-i",
        dest="import_path",
        type=str,
        help="导入已确认的 JSON 文件到数据库"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="增量模式：跳过已分析的商品"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔍 商品 APU 分析工具 (v2 - 5 维度规则库)")
    print("=" * 70)
    
    # 加载客户端
    supabase = load_supabase_client()
    print("✅ 成功连接 Supabase")
    
    llm = load_llm_client()
    print(f"✅ 成功连接 LLM ({LLM_MODEL})")
    
    # 创建分析器
    analyzer = ProductAPUAnalyzer(supabase, llm)
    
    # 执行操作
    if args.import_path:
        # 导入模式
        print(f"\n📥 导入模式: {args.import_path}")
        print("   将同时导入到:")
        print("   - gg_taobao_product_apu (商品 APU 结果)")
        print("   - gg_apu_product_rules (规则库)")
        analyzer.import_results(Path(args.import_path))
    else:
        # 分析模式
        output_path = None
        if args.output:
            output_path = Path(args.output)
        else:
            # 默认输出路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = OUTPUT_DIR / f"apu_analysis_{timestamp}.json"
        
        print(f"\n🔬 分析模式")
        if args.limit:
            print(f"   限制: {args.limit} 条")
        if args.incremental:
            print(f"   增量模式: 跳过已分析的商品")
        print(f"   输出: {output_path}")
        
        analyzer.analyze_all_products(
            limit=args.limit,
            output_path=output_path,
            skip_analyzed=args.incremental
        )
        
        print(f"\n📄 请查看输出文件确认结果:")
        print(f"   {output_path}")
        print(f"\n确认无误后，运行以下命令导入数据库:")
        print(f"   python analyze_products_apu.py --import {output_path}")


if __name__ == "__main__":
    main()
