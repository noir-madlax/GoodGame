import json
import os
import statistics

# 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MID_TIER_FILE = os.path.join(OUTPUT_DIR, "mid_tier_skincare_kols.json")
SUPPLEMENTARY_FILE = os.path.join(OUTPUT_DIR, "supplementary_skincare_kols.json")

def main():
    print("📖 读取现有腰部达人名单...")
    with open(MID_TIER_FILE, "r", encoding="utf-8") as f:
        mid_tier_kols = json.load(f)
    print(f"   现有数量: {len(mid_tier_kols)}")

    print("📖 读取补充名单...")
    with open(SUPPLEMENTARY_FILE, "r", encoding="utf-8") as f:
        supplementary_kols = json.load(f)
    print(f"   补充数量: {len(supplementary_kols)}")

    # 合并与去重
    existing_ids = set(k["kol_id"] for k in mid_tier_kols)
    added_count = 0
    
    for k in supplementary_kols:
        # 再次确认是否符合腰部标准 (10w-100w)
        fans = k.get("fans_count", 0)
        if 100000 <= fans <= 1000000:
            if k["kol_id"] not in existing_ids:
                mid_tier_kols.append(k)
                existing_ids.add(k["kol_id"])
                added_count += 1
                print(f"   ➕ 添加: {k['kol_name']} (粉丝: {fans})")
            else:
                print(f"   ⚠️ 已存在: {k['kol_name']}")
        else:
            print(f"   ❌ 不符合粉丝标准: {k['kol_name']} (粉丝: {fans})")

    print(f"✅ 合并完成，新增 {added_count} 位，当前总数: {len(mid_tier_kols)}")

    # 保存合并后的文件
    with open(MID_TIER_FILE, "w", encoding="utf-8") as f:
        json.dump(mid_tier_kols, f, ensure_ascii=False, indent=2)
    print(f"💾 已保存更新后的名单: {MID_TIER_FILE}")

    # --- 数据分析 ---
    print("\n📊 --- 最终腰部达人数据分析 ---")
    
    total_kols = len(mid_tier_kols)
    total_fans = sum(k["fans_count"] for k in mid_tier_kols)
    avg_fans = total_fans / total_kols if total_kols > 0 else 0
    
    # 粉丝分布
    fans_bins = {"10w-30w": 0, "30w-50w": 0, "50w-100w": 0}
    for k in mid_tier_kols:
        f = k["fans_count"]
        if f < 300000: fans_bins["10w-30w"] += 1
        elif f < 500000: fans_bins["30w-50w"] += 1
        else: fans_bins["50w-100w"] += 1

    # 垂直度分析 (skincare_ratio_num)
    vertical_100 = len([k for k in mid_tier_kols if k.get("skincare_ratio_num", 0) == 100])
    vertical_50_plus = len([k for k in mid_tier_kols if k.get("skincare_ratio_num", 0) >= 50])

    # 商业化分析
    ecom_enabled = len([k for k in mid_tier_kols if k.get("is_ecom_enabled")])
    
    prices = [k.get("price_20_60s", 0) for k in mid_tier_kols]
    prices_valid = [p for p in prices if p > 0] # 去除0报价
    
    avg_price = sum(prices_valid) / len(prices_valid) if prices_valid else 0
    median_price = statistics.median(prices_valid) if prices_valid else 0
    price_coverage = len(prices_valid) / total_kols * 100

    print(f"1. 总体规模: {total_kols} 位达人")
    print(f"   覆盖粉丝总量: {total_fans:,}")
    print(f"   平均粉丝数: {int(avg_fans):,}")
    
    print(f"\n2. 粉丝量级分布:")
    for bin_name, count in fans_bins.items():
        print(f"   - {bin_name}: {count} 人 ({count/total_kols*100:.1f}%)")
        
    print(f"\n3. 内容垂直度:")
    print(f"   - 100% 纯护肤: {vertical_100} 人 ({vertical_100/total_kols*100:.1f}%)")
    print(f"   - ≥50% 护肤相关: {vertical_50_plus} 人 ({vertical_50_plus/total_kols*100:.1f}%)")
    
    print(f"\n4. 商业化能力:")
    print(f"   - 开通电商: {ecom_enabled} 人 ({ecom_enabled/total_kols*100:.1f}%)")
    print(f"   - 有公开报价: {len(prices_valid)} 人 ({price_coverage:.1f}%)")
    if prices_valid:
        print(f"   - 20-60s视频报价 (有效样本):")
        print(f"     - 平均值: ¥{int(avg_price)}")
        print(f"     - 中位数: ¥{int(median_price)}")
        print(f"     - 最低: ¥{min(prices_valid)}")
        print(f"     - 最高: ¥{max(prices_valid)}")

if __name__ == "__main__":
    main()

