"""
小红书评论获取脚本 - Web 版本
使用 TikHub Web API 获取笔记评论

API 接口说明：
- 一级评论: /api/v1/xiaohongshu/web/get_note_comments
  文档: https://docs.tikhub.io/268383322e0
  
- 子评论: /api/v1/xiaohongshu/web/get_note_sub_comments
  文档: https://docs.tikhub.io/268383323e0
  注意: 经测试此接口返回 404，可能暂不可用

与 App 版本的区别：
- App 版本使用 /xiaohongshu/app/get_note_comments (返回 400 错误，服务端问题)
- Web 版本使用 /xiaohongshu/web/get_note_comments (可获取数据)

已知问题 (2025-12-08):
- Web API 分页 cursor 不工作，每次请求返回相同的第一页数据
- 只能获取第一页约 15 条评论
- 但可以获取准确的统计信息: comment_count (总评论数), comment_count_l1 (一级评论数)
"""

import os
import json
import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "params", "config.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_note_comments_web(
    api_key: str,
    note_id: str,
    last_cursor: str = "",
    xsec_token: str = ""
) -> Dict[str, Any]:
    """
    获取笔记评论 - Web 版本
    
    API: /api/v1/xiaohongshu/web/get_note_comments
    文档: https://docs.tikhub.io/268383322e0
    
    参数:
    - note_id: 笔记ID (必填)
    - last_cursor: 分页游标，首次请求为空，后续传上一页最后一条评论的ID
    - xsec_token: 可选的安全令牌
    
    重要：分页参数名是 lastCursor (驼峰命名)，值是评论ID字符串
    
    返回字段说明:
    - comment_count: 总评论数（包含子评论）
    - comment_count_l1: 一级评论数
    - has_more: 是否有更多评论
    - cursor: 下一页游标（评论ID）
    - comments: 评论列表
    """
    url = "https://api.tikhub.io/api/v1/xiaohongshu/web/get_note_comments"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    params = {
        "note_id": note_id
    }
    
    # 重要：参数名是 lastCursor (驼峰命名)
    if last_cursor:
        params["lastCursor"] = last_cursor
    
    if xsec_token:
        params["xsec_token"] = xsec_token
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                print(f"  [Web API] 状态码: 200")
                return response.json()
            elif response.status_code == 400 and attempt < max_retries - 1:
                print(f"  [Web API] 状态码: 400，第 {attempt + 1} 次重试...")
                time.sleep(retry_delay)
                continue
            else:
                print(f"  [Web API] 状态码: {response.status_code}")
                print(f"  [Web API] 错误响应: {response.text[:500]}")
                return {"error": True, "status_code": response.status_code, "message": response.text}
                
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                print(f"  [Web API] 请求异常，第 {attempt + 1} 次重试: {e}")
                time.sleep(retry_delay)
                continue
            print(f"  [Web API] 请求异常: {e}")
            return {"error": True, "message": str(e)}
    
    return {"error": True, "message": "Max retries exceeded"}


def get_sub_comments_web(
    api_key: str,
    note_id: str,
    root_comment_id: str,
    cursor: str = "",
    xsec_token: str = ""
) -> Dict[str, Any]:
    """
    获取子评论 - Web 版本
    
    API: /api/v1/xiaohongshu/web/get_note_sub_comments
    文档: https://docs.tikhub.io/268383323e0
    
    注意: 经测试此接口返回 404，可能暂不可用
    
    参数:
    - note_id: 笔记ID (必填)
    - root_comment_id: 父评论ID (必填)
    - cursor: 分页游标
    - xsec_token: 可选的安全令牌
    """
    url = "https://api.tikhub.io/api/v1/xiaohongshu/web/get_note_sub_comments"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    params = {
        "note_id": note_id,
        "root_comment_id": root_comment_id
    }
    
    if cursor:
        params["cursor"] = cursor
    
    if xsec_token:
        params["xsec_token"] = xsec_token
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"  [Web API] 子评论请求 URL: {response.url}")
        print(f"  [Web API] 状态码: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  [Web API] 错误响应: {response.text[:500]}")
            return {"error": True, "status_code": response.status_code, "message": response.text}
            
    except requests.RequestException as e:
        print(f"  [Web API] 请求异常: {e}")
        return {"error": True, "message": str(e)}


def extract_comment_info(comment: Dict[str, Any]) -> Dict[str, Any]:
    """从评论数据中提取关键信息"""
    # Web 版本的评论结构 - user 字段而非 user_info
    user_info = comment.get("user", {})
    
    # 计算子评论数量 - Web 版本使用 sub_comments 数组或 sub_comment_count
    sub_comments = comment.get("sub_comments", [])
    sub_comment_count = comment.get("sub_comment_count", len(sub_comments))
    
    return {
        "comment_id": comment.get("id", ""),
        "content": comment.get("content", ""),
        "create_time": comment.get("create_time", 0),
        "like_count": comment.get("like_count", 0),
        "sub_comment_count": sub_comment_count,
        "sub_comment_has_more": comment.get("sub_comment_has_more", False),
        "sub_comment_cursor": comment.get("sub_comment_cursor", ""),
        "user_id": user_info.get("userid", ""),
        "nickname": user_info.get("nickname", ""),
        "ip_location": comment.get("ip_location", ""),
        "note_id": comment.get("note_id", ""),
        # 保留原始数据以便后续分析
        "raw": comment
    }


def fetch_all_primary_comments(
    api_key: str,
    note_id: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    获取笔记的所有一级评论（不获取子评论）
    
    支持断点续传：
    - 保存进度到 progress_{note_id}.json
    - 每页获取后立即保存
    """
    # 配置参数
    request_delay = config.get("请求间隔", {}).get("request_delay", 0.3)
    max_pages = config.get("一级评论获取", {}).get("max_pages", 100)
    
    # 进度文件路径
    progress_file = os.path.join(OUTPUT_DIR, f"web_progress_{note_id}.json")
    comments_file = os.path.join(OUTPUT_DIR, f"web_comments_{note_id}.json")
    
    # 加载已有进度
    progress = {
        "note_id": note_id,
        "last_cursor": "",
        "fetched_comment_ids": [],
        "total_fetched": 0,
        "comment_count": 0,
        "comment_count_l1": 0,
        "fetch_completed": False,
        "last_update": ""
    }
    
    all_comments = []
    
    if os.path.exists(progress_file):
        with open(progress_file, "r", encoding="utf-8") as f:
            progress = json.load(f)
        print(f"  [断点续传] 加载进度: 已获取 {progress['total_fetched']} 条评论")
        
        if progress.get("fetch_completed"):
            print(f"  [断点续传] 该笔记的一级评论已全部获取完成")
            # 加载已有评论
            if os.path.exists(comments_file):
                with open(comments_file, "r", encoding="utf-8") as f:
                    all_comments = json.load(f)
            return {
                "comments": all_comments,
                "progress": progress
            }
    
    # 加载已有评论
    if os.path.exists(comments_file):
        with open(comments_file, "r", encoding="utf-8") as f:
            all_comments = json.load(f)
    
    fetched_ids = set(progress.get("fetched_comment_ids", []))
    last_cursor = progress.get("last_cursor", "")
    page = progress.get("current_page", 1)
    
    print(f"\n{'='*60}")
    print(f"开始获取笔记 {note_id} 的一级评论 (Web API)")
    print(f"{'='*60}")
    
    if last_cursor:
        print(f"  [断点续传] 从第 {page} 页继续，cursor: {last_cursor[:20]}...")
    
    while page <= max_pages:
        print(f"\n--- 第 {page} 页 ---")
        
        result = get_note_comments_web(api_key, note_id, last_cursor)
        
        if result.get("error"):
            print(f"  [错误] 获取失败: {result.get('message', '未知错误')}")
            # 保存当前进度，下次可以继续
            progress["last_update"] = datetime.now().isoformat()
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
            break
        
        # Web API 返回结构是嵌套的 data.data
        outer_data = result.get("data", {})
        data = outer_data.get("data", outer_data)  # 兼容两种结构
        
        # 首次获取时记录总数
        if page == 1 and not progress.get("comment_count"):
            progress["comment_count"] = data.get("comment_count", 0)
            progress["comment_count_l1"] = data.get("comment_count_l1", 0)
            print(f"  [统计] 总评论数: {progress['comment_count']}")
            print(f"  [统计] 一级评论数: {progress['comment_count_l1']}")
        
        comments = data.get("comments", [])
        
        if not comments:
            print("  [完成] 没有更多评论")
            progress["fetch_completed"] = True
            break
        
        # 处理评论
        new_count = 0
        for comment in comments:
            comment_info = extract_comment_info(comment)
            comment_id = comment_info["comment_id"]
            
            if comment_id not in fetched_ids:
                all_comments.append(comment_info)
                fetched_ids.add(comment_id)
                new_count += 1
        
        print(f"  [获取] 本页 {len(comments)} 条，新增 {new_count} 条")
        print(f"  [累计] 已获取 {len(all_comments)} 条一级评论")
        
        # 显示本页评论的子评论数量统计
        sub_counts = [c.get("sub_comment_count", 0) for c in comments]
        if sub_counts:
            total_sub = sum(sub_counts)
            if total_sub > 0:
                print(f"  [子评论统计] 本页: 最小={min(sub_counts)}, 最大={max(sub_counts)}, 总计={total_sub}")
        
        # 获取下一页的 cursor
        cursor_str = data.get("cursor", "")
        if cursor_str:
            # cursor 可能是 JSON 字符串或简单字符串
            if cursor_str.startswith("{"):
                cursor_obj = json.loads(cursor_str)
                next_cursor = cursor_obj.get("cursor", "")
            else:
                next_cursor = cursor_str
        else:
            next_cursor = ""
        
        # 更新进度
        progress["last_cursor"] = next_cursor
        progress["current_page"] = page + 1
        progress["fetched_comment_ids"] = list(fetched_ids)
        progress["total_fetched"] = len(all_comments)
        progress["last_update"] = datetime.now().isoformat()
        
        # 立即保存进度和评论
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        
        with open(comments_file, "w", encoding="utf-8") as f:
            json.dump(all_comments, f, ensure_ascii=False, indent=2)
        
        print(f"  [保存] 进度已保存")
        
        # 检查是否还有更多
        has_more = data.get("has_more", False)
        if not has_more:
            print("  [完成] 已获取全部一级评论")
            progress["fetch_completed"] = True
            break
        
        if not next_cursor:
            print("  [完成] 没有下一页游标")
            progress["fetch_completed"] = True
            break
        
        last_cursor = next_cursor
        page += 1
        time.sleep(request_delay)
    
    # 最终保存
    progress["last_update"] = datetime.now().isoformat()
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    
    with open(comments_file, "w", encoding="utf-8") as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=2)
    
    return {
        "comments": all_comments,
        "progress": progress
    }


def generate_summary(note_id: str, comments: List[Dict], progress: Dict) -> str:
    """生成评论摘要报告"""
    summary_lines = []
    summary_lines.append(f"{'='*60}")
    summary_lines.append(f"小红书笔记评论摘要 (Web API)")
    summary_lines.append(f"{'='*60}")
    summary_lines.append(f"")
    summary_lines.append(f"笔记 ID: {note_id}")
    summary_lines.append(f"API 版本: Web (/xiaohongshu/web/get_note_comments)")
    summary_lines.append(f"")
    summary_lines.append(f"--- 统计信息 ---")
    summary_lines.append(f"总评论数（含子评论）: {progress.get('comment_count', 'N/A')}")
    summary_lines.append(f"一级评论数: {progress.get('comment_count_l1', 'N/A')}")
    summary_lines.append(f"已获取一级评论: {len(comments)}")
    summary_lines.append(f"获取完成: {'是' if progress.get('fetch_completed') else '否'}")
    summary_lines.append(f"")
    
    # 子评论统计
    sub_counts = [c.get("sub_comment_count", 0) for c in comments]
    total_sub = sum(sub_counts)
    comments_with_sub = len([c for c in sub_counts if c > 0])
    comments_with_sub_gt5 = len([c for c in sub_counts if c > 5])
    
    summary_lines.append(f"--- 子评论分析 ---")
    summary_lines.append(f"子评论总数: {total_sub}")
    summary_lines.append(f"有子评论的一级评论数: {comments_with_sub}")
    summary_lines.append(f"子评论数 > 5 的一级评论数: {comments_with_sub_gt5}")
    summary_lines.append(f"")
    
    # 验证总数
    estimated_total = len(comments) + total_sub
    summary_lines.append(f"--- 数量验证 ---")
    summary_lines.append(f"一级评论 + 子评论 = {len(comments)} + {total_sub} = {estimated_total}")
    summary_lines.append(f"API 返回的总评论数: {progress.get('comment_count', 'N/A')}")
    summary_lines.append(f"")
    
    # 子评论数量分布
    summary_lines.append(f"--- 子评论数量分布 ---")
    distribution = {}
    for count in sub_counts:
        if count == 0:
            key = "0"
        elif count <= 5:
            key = "1-5"
        elif count <= 10:
            key = "6-10"
        elif count <= 20:
            key = "11-20"
        else:
            key = ">20"
        distribution[key] = distribution.get(key, 0) + 1
    
    for key in ["0", "1-5", "6-10", "11-20", ">20"]:
        if key in distribution:
            summary_lines.append(f"  {key}: {distribution[key]} 条评论")
    summary_lines.append(f"")
    
    # 热门评论（按子评论数排序）
    summary_lines.append(f"--- 热门评论 TOP 10（按子评论数）---")
    sorted_comments = sorted(comments, key=lambda x: x.get("sub_comment_count", 0), reverse=True)[:10]
    for i, c in enumerate(sorted_comments, 1):
        content = c.get("content", "")[:50]
        if len(c.get("content", "")) > 50:
            content += "..."
        summary_lines.append(f"{i}. [{c.get('sub_comment_count', 0)}条子评论] {c.get('nickname', '匿名')}: {content}")
    summary_lines.append(f"")
    
    # 最新评论
    summary_lines.append(f"--- 最新评论 10 条 ---")
    for i, c in enumerate(comments[:10], 1):
        content = c.get("content", "")[:50]
        if len(c.get("content", "")) > 50:
            content += "..."
        timestamp = c.get("create_time", 0)
        time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M") if timestamp else "未知"
        summary_lines.append(f"{i}. [{time_str}] {c.get('nickname', '匿名')}: {content}")
    
    return "\n".join(summary_lines)


def main():
    """主函数"""
    # 加载 API Key
    api_key = os.getenv("tikhub_API_KEY")
    if not api_key:
        print("错误: 未找到 tikhub_API_KEY 环境变量")
        return
    
    # 加载配置
    config = load_config()
    print("配置加载成功")
    print(f"  请求间隔: {config.get('请求间隔', {}).get('request_delay', 0.3)} 秒")
    print(f"  最大页数: {config.get('一级评论获取', {}).get('max_pages', 100)}")
    
    # 获取目标笔记 ID
    note_ids = config.get("目标帖子", {}).get("note_ids", [])
    
    if not note_ids:
        # 从 top3_notes.json 读取
        top3_file = os.path.join(OUTPUT_DIR, "top3_notes.json")
        if os.path.exists(top3_file):
            with open(top3_file, "r", encoding="utf-8") as f:
                top3_data = json.load(f)
                note_ids = [note["note_id"] for note in top3_data]
    
    if not note_ids:
        print("错误: 未找到目标笔记 ID")
        return
    
    print(f"\n目标笔记: {note_ids}")
    
    # 处理每个笔记
    for note_id in note_ids:
        print(f"\n{'#'*60}")
        print(f"处理笔记: {note_id}")
        print(f"{'#'*60}")
        
        result = fetch_all_primary_comments(api_key, note_id, config)
        
        comments = result["comments"]
        progress = result["progress"]
        
        # 生成摘要
        summary = generate_summary(note_id, comments, progress)
        
        # 保存摘要
        summary_file = os.path.join(OUTPUT_DIR, f"web_summary_{note_id}.txt")
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)
        
        print(f"\n{summary}")
        print(f"\n摘要已保存到: {summary_file}")


if __name__ == "__main__":
    main()
