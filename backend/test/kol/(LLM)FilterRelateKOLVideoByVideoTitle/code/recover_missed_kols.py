import json
import os

# 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SOURCE_FILE = os.path.join(OUTPUT_DIR, "non_skincare_kols_with_titles.json")
TARGET_FILE = os.path.join(OUTPUT_DIR, "supplementary_skincare_kols.json")

# 需要补充的 KOL ID 列表 (人工复核确认)
IDS_TO_RECOVER = [
    "6791985736481505287", # 琳欧尼在韩国
    "7052614366088134687", # 护肤配方工程师老潘
    "7106421268575944737", # 馨忆帮护肤-沃肤娜
    "6870164682775199751", # 欧莱雅男士
    "7295958615330914314", # 啵啵文
    "6870171442021924871"  # 大美姐护肤
]

def main():
    print(f"📖 读取源文件: {SOURCE_FILE}")
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        source_data = json.load(f)
        
    recovered_kols = []
    for k in source_data:
        if k["kol_id"] in IDS_TO_RECOVER:
            # 修正数据：把 sample_titles_non_skincare 移回 sample_titles
            k["sample_titles"] = k.get("sample_titles_non_skincare", [])
            # 修正标记
            k["skincare_videos_count"] = len(k["sample_titles"]) # 假设这些全是护肤
            k["skincare_ratio"] = "100.0%" # 人工确认
            k["skincare_ratio_num"] = 100.0
            # 清理字段
            if "sample_titles_non_skincare" in k:
                del k["sample_titles_non_skincare"]
            
            recovered_kols.append(k)
            
    print(f"✅ 成功提取 {len(recovered_kols)} 位漏判护肤达人")
    
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        json.dump(recovered_kols, f, ensure_ascii=False, indent=2)
    print(f"💾 已保存至: {TARGET_FILE}")

if __name__ == "__main__":
    main()

