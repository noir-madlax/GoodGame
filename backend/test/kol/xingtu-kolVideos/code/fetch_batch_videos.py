"""
批量获取护肤保养达人的视频信息
使用 TikHub API 的 fetch_multi_video_v2 接口一次获取50个视频
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Set
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量 (从backend目录加载.env)
# 当前文件: backend/test/kol/xingtu-searchkol-权限开通了/code/fetch_batch_videos.py
# 目标文件: backend/.env
env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# ===== 配置 =====
API_BASE_URL = "https://api.tikhub.dev"  # 大陆用户使用此域名
API_KEY = os.getenv("tikhub_API_KEY")  # 从环境变量读取API密钥

# 输入输出路径
INPUT_DIR = Path(__file__).parent.parent / "output" / "keyword_护肤保养" / "detail"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "keyword_护肤保养" / "batch_videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 视频类型映射 (video_tag)
VIDEO_TAG_MAP = {
    3: "高播放作品(百万级)",
    4: "带货作品",
    5: "热门作品(十万级)",
    6: "近期作品"
}


class VideoInfo:
    """视频信息类，用于记录视频的关联信息"""
    def __init__(self, item_id: str, author_id: str, author_name: str, video_tag: int, source: str):
        self.item_id = item_id  # 视频ID
        self.author_id = author_id  # 达人ID
        self.author_name = author_name  # 达人昵称
        self.video_tag = video_tag  # 视频类型标签
        self.video_type = VIDEO_TAG_MAP.get(video_tag, "未知类型")  # 视频类型描述
        self.source = source  # 来源：items 或 last_10_items
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "item_id": self.item_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "video_tag": self.video_tag,
            "video_type": self.video_type,
            "source": self.source
        }


def collect_video_ids_from_files() -> Dict[str, VideoInfo]:
    """
    从所有raw_page JSON文件中收集视频ID
    返回：{item_id: VideoInfo} 字典，自动去重
    """
    video_dict: Dict[str, VideoInfo] = {}  # 使用字典自动去重
    processed_files = 0
    
    # 遍历所有raw_page JSON文件
    for json_file in sorted(INPUT_DIR.glob("raw_page_*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否有authors数据
            if 'data' not in data or 'authors' not in data['data']:
                continue
            
            authors = data['data']['authors']
            processed_files += 1
            
            # 遍历每个达人
            for author in authors:
                # 获取达人基础信息
                attr = author.get('attribute_datas', {})
                author_id = attr.get('id') or attr.get('star_id', '')
                author_name = attr.get('nick_name', '未知达人')
                
                if not author_id:
                    continue
                
                # 1. 从 items (代表作品) 提取视频ID
                items = author.get('items', [])
                for item in items:
                    item_id = item.get('item_id')
                    video_tag = item.get('video_tag', 0)
                    
                    if item_id and item_id not in video_dict:  # 去重
                        video_dict[item_id] = VideoInfo(
                            item_id=item_id,
                            author_id=author_id,
                            author_name=author_name,
                            video_tag=video_tag,
                            source="代表作品(items)"
                        )
                
                # 2. 从 last_10_items (最近作品) 提取视频ID
                last_10_items_str = attr.get('last_10_items', '[]')
                try:
                    last_10_items = json.loads(last_10_items_str)
                    for item in last_10_items:
                        item_id = item.get('item_id')
                        
                        if item_id and item_id not in video_dict:  # 去重
                            video_dict[item_id] = VideoInfo(
                                item_id=item_id,
                                author_id=author_id,
                                author_name=author_name,
                                video_tag=6,  # last_10_items 归类为"近期作品"
                                source="最近10个作品(last_10_items)"
                            )
                except json.JSONDecodeError:
                    pass  # 忽略解析错误
        
        except Exception as e:
            print(f"❌ 处理文件 {json_file.name} 时出错: {e}")
            continue
    
    print(f"✅ 已处理 {processed_files} 个JSON文件")
    print(f"✅ 共收集到 {len(video_dict)} 个不重复的视频ID")
    
    return video_dict


def select_50_videos(video_dict: Dict[str, VideoInfo]) -> List[VideoInfo]:
    """
    从收集的视频中选择50个
    优先选择不同达人的代表作品，确保多样性
    """
    # 按优先级排序：代表作品 > 最近作品
    items_videos = [v for v in video_dict.values() if v.source == "代表作品(items)"]
    last10_videos = [v for v in video_dict.values() if v.source == "最近10个作品(last_10_items)"]
    
    selected = []
    seen_authors = set()  # 记录已选择的达人，保证多样性
    
    # 第一轮：每个达人选1个代表作品
    for video in items_videos:
        if len(selected) >= 50:
            break
        if video.author_id not in seen_authors:
            selected.append(video)
            seen_authors.add(video.author_id)
    
    # 第二轮：如果不足50个，继续添加代表作品
    for video in items_videos:
        if len(selected) >= 50:
            break
        if video not in selected:
            selected.append(video)
    
    # 第三轮：如果还不足50个，添加最近作品
    for video in last10_videos:
        if len(selected) >= 50:
            break
        if video not in selected:
            selected.append(video)
    
    print(f"\n✅ 已选择 {len(selected)} 个视频")
    print(f"   - 涉及 {len(seen_authors)} 个不同的达人")
    
    # 统计视频类型分布
    type_count = {}
    for video in selected:
        type_count[video.video_type] = type_count.get(video.video_type, 0) + 1
    
    print(f"   - 视频类型分布：")
    for vtype, count in sorted(type_count.items()):
        print(f"     * {vtype}: {count}个")
    
    return selected


def call_tikhub_api(video_list: List[VideoInfo]):
    """
    调用 TikHub API 的 fetch_multi_video_v2 接口
    批量获取50个视频的详细信息
    """
    # API端点
    endpoint = f"{API_BASE_URL}/api/v1/douyin/app/v3/fetch_multi_video_v2"
    
    # 准备请求参数
    aweme_ids = [video.item_id for video in video_list]  # 视频ID列表
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 根据API文档，直接发送列表作为请求体
    payload = aweme_ids
    
    print(f"\n🔄 正在调用 TikHub API...")
    print(f"   - 请求URL: {endpoint}")
    print(f"   - 视频数量: {len(aweme_ids)}")
    print(f"   - 前5个ID: {aweme_ids[:5]}")
    
    try:
        # 发送POST请求，直接发送列表作为JSON
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # 保存原始API响应
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_output_file = OUTPUT_DIR / f"api_response_raw_{timestamp}.json"
        with open(raw_output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ API原始响应已保存: {raw_output_file}")
        
        # 保存视频关联信息（哪个视频属于哪个达人）
        mapping_file = OUTPUT_DIR / f"video_author_mapping_{timestamp}.json"
        mapping_data = {
            "total_count": len(video_list),
            "videos": [v.to_dict() for v in video_list]
        }
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 视频-达人关联信息已保存: {mapping_file}")
        
        # 生成汇总报告
        generate_summary_report(result, video_list, timestamp)
        
        return result
    
    except requests.exceptions.RequestException as e:
        print(f"❌ API请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   响应内容: {e.response.text}")
        return None


def generate_summary_report(api_result: dict, video_list: List[VideoInfo], timestamp: str):
    """
    生成可读的汇总报告
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("护肤保养达人视频批量获取报告")
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # 1. API请求概况
    report_lines.append("## 1. API请求概况")
    report_lines.append(f"   - 请求视频数量: {len(video_list)}")
    report_lines.append(f"   - API响应状态: {api_result.get('code', 'N/A')}")
    report_lines.append(f"   - API消息: {api_result.get('message_zh', 'N/A')}")
    report_lines.append("")
    
    # 2. 视频-达人关联信息
    report_lines.append("## 2. 视频-达人关联信息")
    report_lines.append("")
    
    # 按达人分组
    author_groups = {}
    for video in video_list:
        if video.author_id not in author_groups:
            author_groups[video.author_id] = {
                "name": video.author_name,
                "videos": []
            }
        author_groups[video.author_id]["videos"].append(video)
    
    report_lines.append(f"   涉及达人数量: {len(author_groups)}")
    report_lines.append("")
    
    for idx, (author_id, info) in enumerate(author_groups.items(), 1):
        report_lines.append(f"   【达人 {idx}】{info['name']} (ID: {author_id})")
        for video in info['videos']:
            report_lines.append(f"      - {video.item_id} | {video.video_type} | {video.source}")
        report_lines.append("")
    
    # 3. 视频类型统计
    report_lines.append("## 3. 视频类型分布")
    type_stats = {}
    for video in video_list:
        type_stats[video.video_type] = type_stats.get(video.video_type, 0) + 1
    
    for vtype, count in sorted(type_stats.items()):
        percentage = (count / len(video_list)) * 100
        report_lines.append(f"   - {vtype}: {count}个 ({percentage:.1f}%)")
    report_lines.append("")
    
    # 4. API返回的视频数据（如果有）
    if 'data' in api_result:
        data = api_result['data']
        if isinstance(data, dict) and 'aweme_list' in data:
            aweme_list = data['aweme_list']
            report_lines.append(f"## 4. API返回的视频数据")
            report_lines.append(f"   - 成功返回视频数: {len(aweme_list)}")
            report_lines.append("")
        elif isinstance(data, list):
            report_lines.append(f"## 4. API返回的视频数据")
            report_lines.append(f"   - 成功返回视频数: {len(data)}")
            report_lines.append("")
    
    report_lines.append("=" * 80)
    report_lines.append("报告结束")
    report_lines.append("=" * 80)
    
    # 保存报告
    report_file = OUTPUT_DIR / f"summary_report_{timestamp}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    
    print(f"✅ 汇总报告已生成: {report_file}")
    
    # 同时打印到控制台
    print("\n" + "\n".join(report_lines[:30]))  # 打印前30行


def main():
    """主函数"""
    print("=" * 80)
    print("护肤保养达人视频批量获取工具")
    print("=" * 80)
    print("")
    
    # 检查API密钥
    if not API_KEY:
        print(f"❌ 错误: 未设置 tikhub_API_KEY 环境变量")
        print(f"   尝试加载的.env路径: {env_path}")
        print(f"   .env文件是否存在: {env_path.exists()}")
        return
    
    print(f"✅ API密钥已加载 (长度: {len(API_KEY)} 字符)")
    
    # 步骤1: 收集所有视频ID
    print("\n【步骤1】收集视频ID...")
    video_dict = collect_video_ids_from_files()
    
    if not video_dict:
        print("❌ 未找到任何视频ID，请检查输入文件")
        return
    
    # 步骤2: 选择50个视频
    print("\n【步骤2】选择50个视频...")
    selected_videos = select_50_videos(video_dict)
    
    if len(selected_videos) < 50:
        print(f"⚠️  警告: 只找到 {len(selected_videos)} 个视频，少于50个")
    
    # 步骤3: 调用API获取视频信息
    print("\n【步骤3】调用API获取视频信息...")
    api_result = call_tikhub_api(selected_videos)
    
    if api_result:
        print("\n✅ 所有步骤完成！")
    else:
        print("\n❌ API调用失败")


if __name__ == "__main__":
    main()

