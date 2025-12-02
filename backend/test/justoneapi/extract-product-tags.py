"""
商品标签提取脚本
从商品名称中提取结构化标签，存入 gg_taobao_product_tags 表

标签类型:
  - gender: 性别 (女装/男装/童装/女士/男士/儿童)
  - season: 季节 (春季/夏季/秋季/冬季/秋冬)
  - year: 年份 (2024/2025)
  - category: 品类 (T恤/连衣裙/牛仔裤/外套/针织衫 等)
  - style: 风格 (修身/宽松/休闲/通勤 等)
  - material: 材质 (棉/羊毛/皮革/针织 等)
  - feature: 特征 (长袖/短袖/圆领/V领 等)
  - series: 系列 (TRF/ZW/特惠精选/新款 等)

使用页面: 独立测试脚本
功能: 解析商品名称，提取标签，存入数据库
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# ==================== 标签规则配置 ====================

# 性别标签
GENDER_PATTERNS = {
    "女装": ["女装", "女士"],
    "男装": ["男装", "男士"],
    "童装女童": ["女童", "童装女童"],
    "童装男童": ["男童", "童装男童", "男婴幼童"],
    "童装": ["童装", "儿童"],
}

# 季节标签
SEASON_PATTERNS = {
    "春季": ["春季", "春装", "春款"],
    "夏季": ["夏季", "夏装", "夏款"],
    "秋季": ["秋季", "秋装", "秋款"],
    "冬季": ["冬季", "冬装", "冬款"],
    "秋冬": ["秋冬"],
}

# 年份标签
YEAR_PATTERNS = {
    "2025": ["2025"],
    "2024": ["2024"],
    "2023": ["2023"],
}

# 品类标签 (服装类型)
CATEGORY_PATTERNS = {
    "T恤": ["T恤", "T 恤"],
    "连衣裙": ["连衣裙"],
    "半身裙": ["半身裙"],
    "牛仔裤": ["牛仔裤"],
    "休闲裤": ["休闲裤", "慢跑裤"],
    "裤装": ["裤装", "长裤", "短裤", "裙裤"],
    "外套": ["外套", "夹克"],
    "大衣": ["大衣"],
    "风衣": ["风衣"],
    "羽绒服": ["羽绒服"],
    "棉服": ["棉服", "棉衣"],
    "针织衫": ["针织衫", "针织"],
    "开衫": ["开衫"],
    "毛衣": ["毛衣"],
    "卫衣": ["卫衣"],
    "衬衫": ["衬衫", "衬衣"],
    "西装": ["西装", "西服"],
    "背心": ["背心", "马甲"],
    "上衣": ["上衣"],
    "连体衣": ["连体衣", "连身衣"],
    "香水": ["香水", "淡香水", "浓香水"],
    "鞋": ["鞋", "穆勒鞋", "高跟鞋", "运动鞋", "皮鞋"],
    "包": ["包", "手提包", "斜挎包", "背包"],
}

# 风格标签
STYLE_PATTERNS = {
    "修身": ["修身"],
    "宽松": ["宽松"],
    "休闲": ["休闲"],
    "通勤": ["通勤"],
    "基础": ["基础", "基本款"],
    "简约": ["简约"],
    "复古": ["复古"],
    "时尚": ["时尚"],
}

# 材质标签
MATERIAL_PATTERNS = {
    "棉": ["棉", "棉质", "纯棉"],
    "羊毛": ["羊毛", "羊绒", "山羊绒"],
    "皮革": ["皮革", "皮质", "仿皮", "人造皮"],
    "针织": ["针织"],
    "牛仔": ["牛仔", "丹宁"],
    "丝绒": ["丝绒", "天鹅绒"],
    "蕾丝": ["蕾丝"],
}

# 特征标签
FEATURE_PATTERNS = {
    "长袖": ["长袖"],
    "短袖": ["短袖"],
    "无袖": ["无袖"],
    "圆领": ["圆领"],
    "V领": ["V领", "V 领"],
    "翻领": ["翻领"],
    "连帽": ["连帽", "帽衫"],
    "高腰": ["高腰"],
    "低腰": ["低腰"],
    "中腰": ["中腰"],
    "直筒": ["直筒"],
    "阔腿": ["阔腿", "宽腿"],
}

# 系列标签
SERIES_PATTERNS = {
    "TRF": ["TRF"],
    "ZW": ["ZW", "Z1975"],
    "新款": ["新款", "新品"],
    "特惠精选": ["特惠精选", "特惠"],
}


def load_supabase_client() -> Client:
    """加载 Supabase 客户端"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError(f"未找到 SUPABASE_URL 或 SUPABASE_KEY")
    
    print(f"✅ 成功连接 Supabase")
    return create_client(url, key)


def extract_tags_from_name(item_name: str) -> list:
    """
    从商品名称中提取标签
    
    参数:
        item_name: 商品名称
    
    返回:
        list: [{"tag_type": ..., "tag_value": ...}, ...]
    """
    tags = []
    
    # 提取性别标签
    for tag_value, patterns in GENDER_PATTERNS.items():
        for pattern in patterns:
            if pattern in item_name:
                tags.append({"tag_type": "gender", "tag_value": tag_value})
                break
    
    # 提取季节标签
    for tag_value, patterns in SEASON_PATTERNS.items():
        for pattern in patterns:
            if pattern in item_name:
                tags.append({"tag_type": "season", "tag_value": tag_value})
                break
    
    # 提取年份标签
    for tag_value, patterns in YEAR_PATTERNS.items():
        for pattern in patterns:
            if pattern in item_name:
                tags.append({"tag_type": "year", "tag_value": tag_value})
                break
    
    # 提取品类标签
    for tag_value, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in item_name:
                tags.append({"tag_type": "category", "tag_value": tag_value})
                break
    
    # 提取风格标签
    for tag_value, patterns in STYLE_PATTERNS.items():
        for pattern in patterns:
            if pattern in item_name:
                tags.append({"tag_type": "style", "tag_value": tag_value})
                break
    
    # 提取材质标签
    for tag_value, patterns in MATERIAL_PATTERNS.items():
        for pattern in patterns:
            if pattern in item_name:
                tags.append({"tag_type": "material", "tag_value": tag_value})
                break
    
    # 提取特征标签
    for tag_value, patterns in FEATURE_PATTERNS.items():
        for pattern in patterns:
            if pattern in item_name:
                tags.append({"tag_type": "feature", "tag_value": tag_value})
                break
    
    # 提取系列标签
    for tag_value, patterns in SERIES_PATTERNS.items():
        for pattern in patterns:
            if pattern in item_name:
                tags.append({"tag_type": "series", "tag_value": tag_value})
                break
    
    return tags


def process_all_products(supabase: Client) -> None:
    """处理所有商品，提取标签"""
    
    # 获取所有商品
    print(f"\n📋 正在获取商品列表...")
    result = supabase.table("gg_taobao_products").select(
        "id, item_id, item_name"
    ).execute()
    
    products = result.data
    print(f"   共 {len(products)} 个商品")
    
    # 提取标签
    all_tags = []
    for product in products:
        product_id = product["id"]
        item_name = product["item_name"] or ""
        
        tags = extract_tags_from_name(item_name)
        
        for tag in tags:
            all_tags.append({
                "product_id": product_id,
                "tag_type": tag["tag_type"],
                "tag_value": tag["tag_value"]
            })
    
    print(f"   共提取 {len(all_tags)} 个标签")
    
    # 批量插入标签
    print(f"\n📝 正在插入标签...")
    batch_size = 100
    inserted_count = 0
    
    for i in range(0, len(all_tags), batch_size):
        batch = all_tags[i:i + batch_size]
        
        try:
            # 使用 upsert 避免重复
            supabase.table("gg_taobao_product_tags").upsert(
                batch,
                on_conflict="product_id,tag_type,tag_value"
            ).execute()
            inserted_count += len(batch)
            print(f"   已插入 {inserted_count}/{len(all_tags)} 条标签")
        except Exception as e:
            print(f"   ⚠️ 批次插入失败: {e}")
    
    print(f"   ✅ 完成标签提取")


def print_tag_statistics(supabase: Client) -> None:
    """打印标签统计信息"""
    print(f"\n📊 标签统计:")
    
    # 按标签类型统计
    result = supabase.table("gg_taobao_product_tags").select(
        "tag_type, tag_value"
    ).execute()
    
    # 统计
    stats = {}
    for row in result.data:
        tag_type = row["tag_type"]
        tag_value = row["tag_value"]
        
        if tag_type not in stats:
            stats[tag_type] = {}
        
        if tag_value not in stats[tag_type]:
            stats[tag_type][tag_value] = 0
        
        stats[tag_type][tag_value] += 1
    
    # 打印
    for tag_type, values in sorted(stats.items()):
        print(f"\n   【{tag_type}】")
        for tag_value, count in sorted(values.items(), key=lambda x: -x[1]):
            print(f"      {tag_value}: {count}")


def main():
    """主函数"""
    print("=" * 70)
    print("🏷️  商品标签提取")
    print("=" * 70)
    
    # 1. 加载 Supabase 客户端
    supabase = load_supabase_client()
    
    # 2. 处理所有商品
    process_all_products(supabase)
    
    # 3. 打印统计
    print_tag_statistics(supabase)
    
    print("\n" + "=" * 70)
    print("✅ 标签提取完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()

