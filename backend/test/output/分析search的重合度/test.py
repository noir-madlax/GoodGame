"""
内容ID提取与重复度分析工具
功能：
1. 从 response_data 提取内容ID（支持抖音、小红书）
2. 分析同一天内与其他API查询的内容重复度
3. 更新数据库字段 content_ids 和 content_overlap_rate
"""
import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# 加载 .env 文件
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)

# 从环境变量读取 Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("请设置 SUPABASE_URL 和 SUPABASE_KEY 环境变量")

# 创建 Supabase 客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================================
# 第一部分：内容ID提取功能
# ============================================================================

def extract_douyin_content_ids(response_data: Dict[str, Any]) -> List[str]:
    """
    从抖音平台的 response_data 中提取内容ID
    路径: response_data.data.data[].aweme_info.aweme_id
    """
    content_ids = []
    try:
        if not response_data or 'data' not in response_data:
            return content_ids
        
        data_wrapper = response_data.get('data', {})
        if not data_wrapper or 'data' not in data_wrapper:
            return content_ids
        
        data_items = data_wrapper.get('data', [])
        if not isinstance(data_items, list):
            return content_ids
        
        for item in data_items:
            if not isinstance(item, dict):
                continue
            
            aweme_info = item.get('aweme_info', {})
            if not isinstance(aweme_info, dict):
                continue
            
            aweme_id = aweme_info.get('aweme_id')
            if aweme_id:
                content_ids.append(str(aweme_id))
    
    except Exception as e:
        print(f"  ⚠️  提取抖音内容ID时出错: {e}")
    
    return content_ids


def extract_xiaohongshu_content_ids(response_data: Dict[str, Any]) -> List[str]:
    """
    从小红书平台的 response_data 中提取内容ID
    路径: response_data.data.data.items[].note.id
    """
    content_ids = []
    try:
        if not response_data or 'data' not in response_data:
            return content_ids
        
        data_wrapper = response_data.get('data', {})
        if not data_wrapper or 'data' not in data_wrapper:
            return content_ids
        
        data_obj = data_wrapper.get('data', {})
        if not isinstance(data_obj, dict):
            return content_ids
        
        items = data_obj.get('items', [])
        if not isinstance(items, list):
            return content_ids
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            note = item.get('note', {})
            if not isinstance(note, dict):
                continue
            
            note_id = note.get('id')
            if note_id:
                content_ids.append(str(note_id))
    
    except Exception as e:
        print(f"  ⚠️  提取小红书内容ID时出错: {e}")
    
    return content_ids


def extract_content_ids(platform: str, response_data: Optional[Dict[str, Any]]) -> List[str]:
    """根据平台类型提取内容ID"""
    if not response_data:
        return []
    
    if platform == "抖音":
        return extract_douyin_content_ids(response_data)
    elif platform == "小红书":
        return extract_xiaohongshu_content_ids(response_data)
    else:
        print(f"  ⚠️  未知平台: {platform}")
        return []


def extract_guide_search_words(response_data: Optional[Dict[str, Any]]) -> List[str]:
    """
    从 response_data 中提取推荐搜索词
    路径: response_data.data.guide_search_words[].word
    
    注意：目前只有抖音平台有此字段
    """
    guide_words = []
    try:
        if not response_data or 'data' not in response_data:
            return guide_words
        
        data = response_data.get('data', {})
        if not isinstance(data, dict):
            return guide_words
        
        guide_search_words = data.get('guide_search_words', [])
        if not isinstance(guide_search_words, list):
            return guide_words
        
        # 提取每个元素中的 word 字段
        for item in guide_search_words:
            if isinstance(item, dict) and 'word' in item:
                word = item.get('word')
                if word:
                    guide_words.append(str(word))
    
    except Exception as e:
        print(f"  ⚠️  提取推荐搜索词时出错: {e}")
    
    return guide_words


# ============================================================================
# 第二部分：重复度分析功能
# ============================================================================

def parse_content_ids_from_db(content_ids_json: Optional[str]) -> List[str]:
    """从数据库中解析content_ids字段"""
    if not content_ids_json:
        return []
    
    try:
        # content_ids是JSONB类型，可能是字符串或已经解析的对象
        if isinstance(content_ids_json, str):
            # 可能是双重JSON编码的字符串
            parsed = json.loads(content_ids_json)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            return parsed if isinstance(parsed, list) else []
        elif isinstance(content_ids_json, list):
            return content_ids_json
        else:
            return []
    except Exception as e:
        print(f"  ⚠️  解析content_ids时出错: {e}")
        return []


def calculate_overlap_rate(record_id: int, current_content_ids: List[str], 
                          same_day_records: List[Dict]) -> float:
    """
    计算内容重复度
    
    Args:
        record_id: 当前记录ID
        current_content_ids: 当前记录的内容ID列表
        same_day_records: 同一天的所有记录
        
    Returns:
        重复度比例（0-1之间）
    """
    if not current_content_ids:
        return 0.0
    
    current_ids_set = set(current_content_ids)
    overlap_count = 0
    
    # 遍历同一天的其他记录
    for other_record in same_day_records:
        # 跳过当前记录本身
        if other_record['id'] == record_id:
            continue
        
        other_content_ids = parse_content_ids_from_db(other_record.get('content_ids'))
        if not other_content_ids:
            continue
        
        # 计算交集
        other_ids_set = set(other_content_ids)
        overlap = current_ids_set.intersection(other_ids_set)
        overlap_count += len(overlap)
    
    # 计算重复度：重复的ID总数 / 当前记录的ID数量
    # 注意：一个ID可能在多条记录中出现，所以overlap_count可能大于len(current_content_ids)
    overlap_rate = min(overlap_count / len(current_content_ids), 1.0)
    
    return round(overlap_rate, 4)


# ============================================================================
# 第三部分：批量处理功能
# ============================================================================

def process_content_extraction(platform: str, limit: int = None, dry_run: bool = True):
    """
    步骤1：提取内容ID
    
    Args:
        platform: 平台名称（"抖音" 或 "小红书"）
        limit: 处理记录数量限制，None表示处理所有
        dry_run: 是否为预览模式
    """
    print("=" * 80)
    print(f"步骤1：提取 {platform} 平台的内容ID")
    print(f"处理数量: {'全部' if limit is None else limit} 条")
    print(f"模式: {'预览模式（不更新数据库）' if dry_run else '更新模式'}")
    print("=" * 80)
    
    try:
        # 查询记录
        query = supabase.table("gg_search_response_logs") \
            .select("id, platform, keyword, response_data, content_ids, guide_search_words") \
            .eq("platform", platform) \
            .not_.is_("response_data", "null")
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        
        if not response.data:
            print(f"未找到 {platform} 平台的记录\n")
            return
        
        print(f"\n找到 {len(response.data)} 条记录\n")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for idx, record in enumerate(response.data, 1):
            record_id = record['id']
            keyword = record['keyword']
            response_data = record.get('response_data')
            existing_content_ids = record.get('content_ids')
            
            # 检查是否需要更新
            existing_guide_words = record.get('guide_search_words')
            update_guide_words_only = False
            
            if existing_content_ids and not dry_run:
                # 如果已经有content_ids，只需要更新guide_search_words
                update_guide_words_only = True
                if idx <= 5:
                    print(f"记录 {idx} (ID: {record_id}): 已有content_ids，只更新guide_search_words")
            
            # 提取内容ID
            content_ids = extract_content_ids(platform, response_data)
            
            # 提取推荐搜索词（guide_search_words）
            guide_words = extract_guide_search_words(response_data)
            
            if idx <= 10 or not content_ids:  # 显示前10条或提取失败的
                if not update_guide_words_only:  # 只在非仅更新guide_words模式下显示
                    print(f"记录 {idx} (ID: {record_id}):")
                    print(f"  关键词: {keyword}")
                    print(f"  提取到的内容ID数量: {len(content_ids)}")
                    if content_ids:
                        print(f"  示例ID: {content_ids[:3]}{'...' if len(content_ids) > 3 else ''}")
                    print(f"  推荐搜索词数量: {len(guide_words)}")
                    if guide_words:
                        print(f"  推荐词: {guide_words[:5]}{'...' if len(guide_words) > 5 else ''}")
            
            if not content_ids and not update_guide_words_only:
                error_count += 1
                if idx <= 5:
                    print(f"  ⚠️  未提取到内容ID")
                continue
            
            if not dry_run:
                try:
                    if update_guide_words_only:
                        # 只更新 guide_search_words
                        if guide_words:
                            supabase.table("gg_search_response_logs") \
                                .update({"guide_search_words": guide_words}) \
                                .eq("id", record_id) \
                                .execute()
                            success_count += 1
                            if idx <= 10:
                                print(f"  ✓ 更新guide_search_words成功 ({len(guide_words)}个词)")
                        else:
                            # 没有推荐词，不更新
                            success_count += 1  # 仍然计为成功，因为这是正常情况
                            if idx <= 10:
                                print(f"  - 无推荐搜索词，跳过")
                    else:
                        # 更新 content_ids 和 guide_search_words
                        update_data = {
                            "content_ids": content_ids
                        }
                        # 只有当有推荐搜索词时才更新该字段
                        if guide_words:
                            update_data["guide_search_words"] = guide_words
                        
                        supabase.table("gg_search_response_logs") \
                            .update(update_data) \
                            .eq("id", record_id) \
                            .execute()
                        success_count += 1
                except Exception as e:
                    error_count += 1
                    if idx <= 5:
                        print(f"  ✗ 更新失败: {e}")
        
        print(f"\n处理完成：")
        print(f"  成功: {success_count} 条")
        print(f"  跳过: {skip_count} 条")
        print(f"  失败: {error_count} 条")
        print()
    
    except Exception as e:
        print(f"处理记录时出错: {e}")
        import traceback
        traceback.print_exc()


def process_overlap_analysis(limit: int = None, dry_run: bool = True):
    """
    步骤2：分析内容重复度
    
    Args:
        limit: 处理记录数量限制，None表示处理所有
        dry_run: 是否为预览模式
    """
    print("=" * 80)
    print(f"步骤2：分析内容重复度")
    print(f"处理数量: {'全部' if limit is None else limit} 条")
    print(f"模式: {'预览模式（不更新数据库）' if dry_run else '更新模式'}")
    print("=" * 80)
    
    try:
        # 查询所有有content_ids的记录
        query = supabase.table("gg_search_response_logs") \
            .select("id, platform, keyword, content_ids, created_at") \
            .not_.is_("content_ids", "null")
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        
        if not response.data:
            print("未找到有content_ids的记录\n")
            return
        
        all_records = response.data
        print(f"\n找到 {len(all_records)} 条有content_ids的记录\n")
        
        # 按日期分组
        records_by_date = {}
        for record in all_records:
            if not record.get('created_at'):
                continue
            
            # 提取日期部分（YYYY-MM-DD）
            created_at = record['created_at']
            if isinstance(created_at, str):
                date_str = created_at.split('T')[0]
            else:
                date_str = str(created_at).split(' ')[0]
            
            if date_str not in records_by_date:
                records_by_date[date_str] = []
            records_by_date[date_str].append(record)
        
        print(f"日期分组：{len(records_by_date)} 个不同的日期\n")
        
        success_count = 0
        error_count = 0
        
        # 处理每条记录
        for idx, record in enumerate(all_records, 1):
            record_id = record['id']
            platform = record['platform']
            keyword = record['keyword']
            content_ids_json = record.get('content_ids')
            created_at = record.get('created_at')
            
            if not created_at:
                error_count += 1
                if idx <= 5:
                    print(f"记录 {idx} (ID: {record_id}): 缺少created_at字段，跳过")
                continue
            
            # 解析content_ids
            current_content_ids = parse_content_ids_from_db(content_ids_json)
            if not current_content_ids:
                error_count += 1
                if idx <= 5:
                    print(f"记录 {idx} (ID: {record_id}): content_ids为空，跳过")
                continue
            
            # 获取日期
            if isinstance(created_at, str):
                date_str = created_at.split('T')[0]
            else:
                date_str = str(created_at).split(' ')[0]
            
            # 获取同一天的所有记录
            same_day_records = records_by_date.get(date_str, [])
            
            # 计算重复度
            overlap_rate = calculate_overlap_rate(
                record_id, 
                current_content_ids, 
                same_day_records
            )
            
            if idx <= 5:  # 显示前5条
                print(f"记录 {idx} (ID: {record_id}):")
                print(f"  平台: {platform}")
                print(f"  关键词: {keyword}")
                print(f"  日期: {date_str}")
                print(f"  内容ID数量: {len(current_content_ids)}")
                print(f"  同一天记录数: {len(same_day_records)}")
                print(f"  重复度: {overlap_rate:.2%}")
            
            if not dry_run:
                try:
                    supabase.table("gg_search_response_logs") \
                        .update({"content_overlap_rate": overlap_rate}) \
                        .eq("id", record_id) \
                        .execute()
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    if idx <= 5:
                        print(f"  ✗ 更新失败: {e}")
        
        print(f"\n处理完成：")
        print(f"  成功: {success_count} 条")
        print(f"  失败: {error_count} 条")
        print()
    
    except Exception as e:
        print(f"处理记录时出错: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# 第四部分：主程序与测试
# ============================================================================

def test_extraction():
    """测试内容ID提取（预览模式）"""
    print("\n" + "=" * 80)
    print("测试模式：内容ID提取")
    print("=" * 80 + "\n")
    
    # 测试抖音平台（2条记录）
    process_content_extraction("抖音", limit=2, dry_run=True)
    
    # 测试小红书平台（2条记录）
    process_content_extraction("小红书", limit=2, dry_run=True)


def test_overlap_analysis():
    """测试重复度分析（预览模式）"""
    print("\n" + "=" * 80)
    print("测试模式：重复度分析")
    print("=" * 80 + "\n")
    
    # 分析前5条记录
    process_overlap_analysis(limit=5, dry_run=True)


def run_extraction_update(platform: str = None):
    """执行内容ID提取更新"""
    print("\n" + "=" * 80)
    print("执行模式：内容ID提取")
    print("=" * 80 + "\n")
    
    if platform:
        process_content_extraction(platform, limit=None, dry_run=False)
    else:
        # 处理所有平台
        process_content_extraction("抖音", limit=None, dry_run=False)
        process_content_extraction("小红书", limit=None, dry_run=False)


def run_overlap_update():
    """执行重复度分析更新"""
    print("\n" + "=" * 80)
    print("执行模式：重复度分析")
    print("=" * 80 + "\n")
    
    process_overlap_analysis(limit=None, dry_run=False)


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("\n" + "=" * 80)
        print("内容ID提取与重复度分析工具")
        print("=" * 80 + "\n")
        print("使用方法:")
        print("  python test.py test              # 测试模式（预览）")
        print("  python test.py extract           # 提取内容ID（实际更新）")
        print("  python test.py analyze           # 分析重复度（实际更新）")
        print("  python test.py all               # 执行完整流程（提取+分析）")
        print("\n示例:")
        print("  python test.py test              # 先测试查看效果")
        print("  python test.py extract           # 确认无误后提取ID")
        print("  python test.py analyze           # 最后分析重复度")
        print()
        return
    
    command = sys.argv[1]
    
    if command == "test":
        # 测试模式
        test_extraction()
        test_overlap_analysis()
        print("\n" + "=" * 80)
        print("测试完成！如果结果正确，请运行实际更新：")
        print("  python test.py extract    # 提取内容ID")
        print("  python test.py analyze    # 分析重复度")
        print("=" * 80 + "\n")
    
    elif command == "extract":
        # 执行内容ID提取
        run_extraction_update()
        print("\n" + "=" * 80)
        print("内容ID提取完成！接下来可以分析重复度：")
        print("  python test.py analyze")
        print("=" * 80 + "\n")
    
    elif command == "analyze":
        # 执行重复度分析
        run_overlap_update()
        print("\n" + "=" * 80)
        print("重复度分析完成！")
        print("=" * 80 + "\n")
    
    elif command == "all":
        # 执行完整流程
        print("\n" + "=" * 80)
        print("执行完整流程：提取内容ID + 分析重复度")
        print("=" * 80 + "\n")
        
        run_extraction_update()
        print("\n" + "-" * 80 + "\n")
        run_overlap_update()
        
        print("\n" + "=" * 80)
        print("所有任务完成！")
        print("=" * 80 + "\n")
    
    else:
        print(f"未知命令: {command}")
        print("可用命令: test, extract, analyze, all")


if __name__ == "__main__":
    main()

