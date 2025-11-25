#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导入视频详情数据到数据库

功能：
1. 从 batch_1_response.json 读取视频详情数据
2. 解析并格式化数据
3. 插入到 gg_xingtu_kol_videos_details 表
4. 先导入50条测试数据

使用方法：
python import_video_details.py
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

def load_env():
    # 从 backend/test/kol/kol-video-fetcher/database/ 到 backend/
    current_dir = Path(__file__).parent
    backend_dir = current_dir.parent.parent.parent.parent
    env_path = backend_dir / '.env'

    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 从 {env_path} 加载环境变量")
    else:
        print(f"⚠️ 未找到 .env 文件: {env_path}")

def get_supabase_client():
    """获取 Supabase 客户端"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL 或 SUPABASE_KEY 未设置")

    return create_client(url, key)

def parse_video_data(aweme):
    """
    解析单个视频数据，提取需要插入数据库的字段

    Args:
        aweme: API 返回的单个视频数据

    Returns:
        dict: 格式化后的数据
    """
    # 基本信息
    aweme_id = aweme.get('aweme_id')
    video_desc = aweme.get('desc') or aweme.get('video_desc', '')
    duration = aweme.get('duration')

    # 时间戳
    create_time = aweme.get('create_time')
    publish_time = aweme.get('publish_time') or create_time

    # 统计数据
    statistics = aweme.get('statistics', {})
    play_count = statistics.get('play_count', 0)
    comment_count = statistics.get('comment_count', 0)
    share_count = statistics.get('share_count', 0)
    digg_count = statistics.get('digg_count', 0)
    collect_count = statistics.get('collect_count', 0)
    download_count = statistics.get('download_count', 0)
    forward_count = statistics.get('forward_count', 0)
    admire_count = statistics.get('admire_count', 0)

    # 作者信息
    author = aweme.get('author', {})
    author_uid = author.get('uid')
    author_nickname = author.get('nickname')
    author_unique_id = author.get('unique_id')
    author_follower_count = author.get('follower_count')

    # 视频资源
    video = aweme.get('video', {})
    video_url = None
    cover_url = None

    # 获取视频播放地址
    play_addr = video.get('play_addr') or video.get('play_addr_h264')
    if play_addr and play_addr.get('url_list'):
        video_url = play_addr['url_list'][0]

    # 获取封面地址
    cover = video.get('cover') or video.get('origin_cover')
    if cover and cover.get('url_list'):
        cover_url = cover['url_list'][0]

    # 视频规格
    video_width = video.get('width')
    video_height = video.get('height')
    video_ratio = video.get('ratio')
    video_format = video.get('format')

    # 控制权限
    aweme_control = aweme.get('aweme_control', {})
    video_control = aweme.get('video_control', {})

    can_comment = aweme_control.get('can_comment', True)
    can_share = aweme_control.get('can_share', True)
    can_forward = aweme_control.get('can_forward', True)
    allow_download = video_control.get('allow_download', True)

    # 业务标识
    is_ads = aweme.get('is_ads', False)
    commerce_info = aweme.get('commerce_info', {})
    is_commerce = commerce_info.get('is_ad', False)
    geofencing_regions = aweme.get('geofencing_regions')

    # 获取 KOL ID（需要从现有的视频表关联获取）
    kol_id = get_kol_id_by_aweme_id(aweme_id)

    return {
        'aweme_id': aweme_id,
        'kol_id': kol_id,
        'video_desc': video_desc,
        'duration': duration,
        'create_time': create_time,
        'publish_time': publish_time,
        'play_count': play_count,
        'comment_count': comment_count,
        'share_count': share_count,
        'digg_count': digg_count,
        'collect_count': collect_count,
        'download_count': download_count,
        'forward_count': forward_count,
        'admire_count': admire_count,
        'author_uid': author_uid,
        'author_nickname': author_nickname,
        'author_unique_id': author_unique_id,
        'author_follower_count': author_follower_count,
        'video_url': video_url,
        'cover_url': cover_url,
        'video_width': video_width,
        'video_height': video_height,
        'video_ratio': video_ratio,
        'video_format': video_format,
        'can_comment': can_comment,
        'can_share': can_share,
        'can_forward': can_forward,
        'allow_download': allow_download,
        'is_ads': is_ads,
        'is_commerce': is_commerce,
        'geofencing_regions': geofencing_regions,
        'video_data': video,
        'author_data': author,
        'text_extra_data': aweme.get('text_extra'),
        'challenge_data': aweme.get('cha_list'),
        'statistics_data': statistics,
        'control_data': {
            'aweme_control': aweme_control,
            'video_control': video_control
        },
        'raw_video_data': aweme,
        'request_id': 'b23dd215-7d12-48a1-93af-19b746175a6c'  # 从响应中获取
    }

def get_kol_id_by_aweme_id(aweme_id):
    """
    根据 aweme_id 从 gg_xingtu_kol_videos 表获取 kol_id

    Args:
        aweme_id: 视频ID

    Returns:
        str: KOL ID，如果找不到返回 None
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table('gg_xingtu_kol_videos')\
            .select('kol_id')\
            .eq('item_id', aweme_id)\
            .execute()

        if response.data:
            return response.data[0]['kol_id']
        else:
            print(f"⚠️ 找不到 aweme_id={aweme_id} 对应的 kol_id")
            return None
    except Exception as e:
        print(f"❌ 查询 kol_id 失败: {e}")
        return None

def insert_video_details(supabase, video_data_list):
    """
    批量插入视频详情数据

    Args:
        supabase: Supabase 客户端
        video_data_list: 视频数据列表

    Returns:
        tuple: (成功数量, 失败数量)
    """
    success_count = 0
    fail_count = 0

    for i, video_data in enumerate(video_data_list, 1):
        try:
            # 过滤掉没有 kol_id 的数据
            if not video_data.get('kol_id'):
                print(f"⚠️ 跳过第 {i} 条数据：缺少 kol_id")
                fail_count += 1
                continue

            response = supabase.table('gg_xingtu_kol_videos_details').upsert(video_data).execute()

            if response.data:
                success_count += 1
                print(f"✅ 插入第 {i} 条数据成功: aweme_id={video_data['aweme_id']}")
            else:
                fail_count += 1
                print(f"❌ 插入第 {i} 条数据失败: aweme_id={video_data['aweme_id']}")

        except Exception as e:
            fail_count += 1
            print(f"❌ 插入第 {i} 条数据异常: {e}")

        # 每10条打印一次进度
        if i % 10 == 0:
            print(f"📊 进度: {i}/{len(video_data_list)} (成功:{success_count}, 失败:{fail_count})")

    return success_count, fail_count

def main():
    """主函数"""
    print("=" * 60)
    print("批量导入视频详情数据到数据库")
    print("=" * 60)

    # 1. 加载环境变量
    print("\n1️⃣ 加载环境配置...")
    load_env()

    # 2. 初始化 Supabase 客户端
    print("\n2️⃣ 初始化数据库连接...")
    try:
        supabase = get_supabase_client()
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return

    # 3. 读取数据文件
    print("\n3️⃣ 读取数据文件...")
    current_dir = Path(__file__).parent.parent
    data_file = current_dir / "output" / "batch_1_response.json"

    if not data_file.exists():
        print(f"❌ 数据文件不存在: {data_file}")
        return

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            response_data = json.load(f)

        code = response_data.get('code')
        if code != 200:
            print(f"❌ API 响应错误: code={code}")
            return

        aweme_details = response_data.get('data', {}).get('aweme_details', [])
        total_videos = len(aweme_details)
        print(f"✅ 读取到 {total_videos} 条视频数据")

    except Exception as e:
        print(f"❌ 读取数据文件失败: {e}")
        return

    # 4. 解析数据（只处理前50条）
    print("\n4️⃣ 解析视频数据...")
    video_data_list = []
    test_limit = 50  # 先处理50条测试

    for i, aweme in enumerate(aweme_details[:test_limit], 1):
        try:
            parsed_data = parse_video_data(aweme)
            if parsed_data['aweme_id']:  # 确保有有效的 aweme_id
                video_data_list.append(parsed_data)
                print(f"✅ 解析第 {i} 条: aweme_id={parsed_data['aweme_id']}")
            else:
                print(f"⚠️ 跳过第 {i} 条：无效的 aweme_id")
        except Exception as e:
            print(f"❌ 解析第 {i} 条失败: {e}")

    print(f"📊 成功解析 {len(video_data_list)}/{test_limit} 条数据")

    # 5. 插入数据库
    print("\n5️⃣ 插入数据库...")
    success_count, fail_count = insert_video_details(supabase, video_data_list)

    # 6. 输出结果
    print("\n" + "=" * 60)
    print("导入结果统计")
    print("=" * 60)
    print(f"总视频数: {total_videos}")
    print(f"测试处理数: {test_limit}")
    print(f"成功解析数: {len(video_data_list)}")
    print(f"成功插入数: {success_count}")
    print(f"失败插入数: {fail_count}")
    success_rate = (success_count / len(video_data_list) * 100) if video_data_list else 0.0
    print(f"成功率: {success_rate:.1f}%")
    print("=" * 60)

    if success_count > 0:
        print("✅ 数据导入测试成功！可以继续处理其他批次数据。")
    else:
        print("❌ 数据导入测试失败，请检查数据格式和数据库连接。")

if __name__ == "__main__":
    main()
