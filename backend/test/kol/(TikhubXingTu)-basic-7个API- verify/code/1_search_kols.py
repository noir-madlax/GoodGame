#!/usr/bin/env python3
"""
脚本名称: 1_search_kols.py
功能描述: 搜索抖音内容，获取关于"护肤达人排行榜"的搜索结果
输入: ../input 文件中的搜索关键词
输出: ../output/1_search_result_{timestamp}.json
参考: backend/tikhub_api/fetchers/douyin_video_fetcher.py 的实现
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

import requests


def load_env_vars():
    """加载环境变量（API Key）- 注意变量名大小写"""
    project_root = Path(__file__).resolve().parents[4]
    backend_env = project_root / "backend/.env"
    
    if load_dotenv and backend_env.exists():
        load_dotenv(backend_env)
    
    # 注意：环境变量名是 tikhub_API_KEY（不是全大写）
    api_key = os.getenv("tikhub_API_KEY")
    if not api_key:
        raise RuntimeError("tikhub_API_KEY not found in environment")
    
    return api_key


def load_search_keyword():
    """从input文件加载搜索关键词"""
    input_file = Path(__file__).resolve().parent.parent / "input"
    
    if not input_file.exists():
        raise RuntimeError("input文件不存在")
    
    content = input_file.read_text(encoding="utf-8").strip()
    
    # 解析格式: "搜索关键词=抖音 护肤达人 排行榜"
    if "=" in content:
        keyword = content.split("=", 1)[1].strip()
    else:
        keyword = content
    
    return keyword


def search_douyin_v3(api_key: str, keyword: str, count: int = 20) -> dict:
    """
    调用抖音搜索接口 fetch_general_search_v3
    参考: backend/tikhub_api/fetchers/douyin_video_fetcher.py
    
    接口路径: /douyin/search/fetch_general_search_v3
    方法: POST
    """
    # 设置请求头（参考 BaseFetcher）
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 准备请求体（参考 DOUYIN_SEARCH_DEFAULT_PAYLOAD）
    payload = {
        "keyword": keyword,  # 搜索关键词
        "cursor": 0,  # 翻页游标（首次请求传 0）
        "sort_type": "0",  # 排序方式：0: 综合排序
        "publish_time": "0",  # 0: 不限时间
        "filter_duration": "0",  # 0: 不限时长
        "content_type": "0",  # 0: 不限类型（包含视频、图片、文章）
        "search_id": ""  # 搜索ID（首次请求为空）
    }
    
    # API基础URL（参考 BaseFetcher.base_url）
    base_url = "https://api.tikhub.io/api/v1"
    url = f"{base_url}/douyin/search/fetch_general_search_v3"
    
    print(f"正在请求抖音搜索API...")
    print(f"URL: {url}")
    print(f"搜索关键词: {keyword}")
    print(f"请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
        # 使用POST方法（参考 BaseFetcher._make_request）
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"响应状态码: {response.status_code}")
        
        # 尝试解析JSON
        try:
            data = response.json()
        except:
            print(f"响应不是有效的JSON")
            print(f"响应内容: {response.text[:500]}")
            raise RuntimeError("响应不是有效的JSON格式")
        
        # 检查业务状态码（参考 BaseFetcher._check_api_response）
        if data.get('code') == 200:
            print(f"✓ 请求成功！code=200")
            
            # 构造返回结果（包含请求信息）
            result = {
                "request_info": {
                    "url": url,
                    "method": "POST",
                    "payload": payload,
                    "timestamp": datetime.now().isoformat(),
                },
                "response_info": {
                    "status_code": response.status_code,
                    "code": data.get('code')
                },
                "data": data
            }
            
            return result
        else:
            # 业务逻辑失败
            error_msg = data.get('message', '未知错误')
            print(f"✗ 业务逻辑失败: code={data.get('code')}, message={error_msg}")
            raise RuntimeError(f"API返回业务错误: {error_msg}")
    
    except requests.RequestException as e:
        print(f"✗ 请求异常: {e}")
        raise RuntimeError(f"请求失败: {e}")


def save_output(data: dict):
    """保存搜索结果到output目录"""
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    
    # 保存完整搜索结果
    result_file = output_dir / f"1_search_result_{timestamp}.json"
    with result_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 搜索结果已保存: {result_file}")
    
    # 打印统计信息
    try:
        # 结构: data.data.data (参考 douyin_video_fetcher.py 的解析逻辑)
        response_data = data.get("data", {}).get("data", {})
        items = response_data.get("data", [])
        
        if isinstance(items, list):
            print(f"\n搜索结果统计:")
            print(f"  - 总结果数: {len(items)}")
            
            # 统计类型
            type_counts = {}
            for item in items:
                item_type = item.get("type", "unknown")
                type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            print(f"  - 结果类型分布:")
            for t, count in type_counts.items():
                type_name = {
                    1: "视频",
                    2: "用户",
                    3: "音乐",
                    4: "话题",
                    5: "直播",
                    6: "商品"
                }.get(t, f"未知类型({t})")
                print(f"    * type={t} ({type_name}): {count}条")
            
            # 统计视频结果
            video_count = type_counts.get(1, 0)
            if video_count > 0:
                print(f"\n  - 视频结果: {video_count}个")
                print(f"    (这些视频内容可能包含护肤达人排行榜信息)")
    except Exception as e:
        print(f"统计信息提取失败: {e}")
    
    return str(result_file)


def main():
    """主函数"""
    print("="*80)
    print("抖音内容搜索脚本")
    print("参考: backend/tikhub_api/fetchers/douyin_video_fetcher.py")
    print("="*80)
    
    try:
        # 1. 加载环境变量
        print("\n[1/3] 加载环境变量...")
        api_key = load_env_vars()
        print("✓ API Key已加载")
        
        # 2. 加载搜索关键词
        print("\n[2/3] 加载搜索关键词...")
        keyword = load_search_keyword()
        print(f"✓ 搜索关键词: {keyword}")
        
        # 3. 执行搜索
        print("\n[3/3] 执行搜索...")
        search_result = search_douyin_v3(
            api_key=api_key,
            keyword=keyword,
            count=20
        )
        
        # 4. 保存输出
        print("\n保存输出文件...")
        output_file = save_output(search_result)
        
        print("\n" + "="*80)
        print("✓ 搜索完成！")
        print("="*80)
        print(f"\n输出文件: {output_file}")
        print("\n后续步骤:")
        print("  - 查看输出文件，分析其中提到的护肤达人排行榜信息")
        print("  - 从视频内容中提取达人名称列表")
        print("  - 根据达人信息运行后续脚本获取详细数据")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
