#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量处理所有视频详情数据

功能：
1. 依次处理 batch_1_response.json 到 batch_13_response.json
2. 解析并导入每批数据到 gg_xingtu_kol_videos_details 表
3. 跳过已存在的视频ID，避免重复插入

使用方法：
python process_all_batches.py
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

def parse_video_data(aweme, request_id):
    """
    解析单个视频数据，提取需要插入数据库的字段

    Args:
        aweme: API 返回的单个视频数据
        request_id: API 请求ID

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
        'request_id': request_id
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
            return None
    except Exception as e:
        print(f"❌ 查询 kol_id 失败 for {aweme_id}: {e}")
        return None

def insert_video_details_batch(supabase, video_data_list):
    """
    批量插入视频详情数据（使用 upsert，避免重复）

    Args:
        supabase: Supabase 客户端
        video_data_list: 视频数据列表

    Returns:
        tuple: (成功数量, 失败数量, 跳过数量)
    """
    success_count = 0
    fail_count = 0
    skip_count = 0

    # 批量处理，每次处理50条
    batch_size = 50

    for i in range(0, len(video_data_list), batch_size):
        batch = video_data_list[i:i + batch_size]

        try:
            # 使用 upsert 批量插入
            response = supabase.table('gg_xingtu_kol_videos_details').upsert(batch).execute()

            if response.data:
                success_count += len(batch)
                print(f"✅ 批量插入成功: {len(batch)} 条")
            else:
                fail_count += len(batch)
                print(f"❌ 批量插入失败: {len(batch)} 条")

        except Exception as e:
            fail_count += len(batch)
            print(f"❌ 批量插入异常: {e}")

    return success_count, fail_count, skip_count

def get_existing_aweme_ids(supabase):
    """
    获取数据库中已存在的 aweme_id 集合

    Args:
        supabase: Supabase 客户端

    Returns:
        set: 已存在的 aweme_id 集合
    """
    try:
        response = supabase.table('gg_xingtu_kol_videos_details')\
            .select('aweme_id')\
            .execute()

        existing_ids = {row['aweme_id'] for row in response.data} if response.data else set()
        print(f"📊 数据库中已有 {len(existing_ids)} 条视频数据")
        return existing_ids
    except Exception as e:
        print(f"❌ 获取已存在ID失败: {e}")
        return set()

def process_batch_file(batch_file_path, supabase, existing_ids):
    """
    处理单个批次文件

    Args:
        batch_file_path: 批次文件路径
        supabase: Supabase 客户端
        existing_ids: 已存在的 aweme_id 集合

    Returns:
        tuple: (总数量, 新增数量, 跳过数量, 失败数量)
    """
    batch_name = batch_file_path.stem
    print(f"\n📂 处理批次: {batch_name}")

    try:
        # 读取文件
        with open(batch_file_path, 'r', encoding='utf-8') as f:
            response_data = json.load(f)

        code = response_data.get('code')
        if code != 200:
            print(f"❌ API 响应错误: code={code}")
            return 0, 0, 0, 0

        aweme_details = response_data.get('data', {}).get('aweme_details', [])
        request_id = response_data.get('request_id', '')

        print(f"📊 读取到 {len(aweme_details)} 条视频数据")

        if not aweme_details:
            print("⚠️ 无视频数据，跳过")
            return 0, 0, 0, 0

        # 解析数据并过滤已存在的
        video_data_list = []
        skipped_existing = 0

        for aweme in aweme_details:
            try:
                aweme_id = aweme.get('aweme_id')
                if aweme_id in existing_ids:
                    skipped_existing += 1
                    continue

                parsed_data = parse_video_data(aweme, request_id)
                if parsed_data['aweme_id'] and parsed_data['kol_id']:  # 确保必要字段存在
                    video_data_list.append(parsed_data)
                else:
                    print(f"⚠️ 跳过无效数据: aweme_id={parsed_data.get('aweme_id')}, kol_id={parsed_data.get('kol_id')}")
            except Exception as e:
                print(f"❌ 解析数据失败: {e}")

        print(f"✅ 成功解析 {len(video_data_list)} 条新数据 (跳过 {skipped_existing} 条已存在数据)")

        total_processed = len(aweme_details)
        skipped_total = skipped_existing

        if not video_data_list:
            return total_processed, 0, skipped_total, 0

        # 插入数据库
        success_count, fail_count, _ = insert_video_details_batch(supabase, video_data_list)

        return total_processed, success_count, skipped_total, fail_count

    except Exception as e:
        print(f"❌ 处理批次失败: {e}")
        return 0, 0, 0, 1  # 失败算1

def main():
    """主函数"""
    print("=" * 60)
    print("批量处理所有视频详情数据")
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

    # 3. 获取批次文件列表
    print("\n3️⃣ 获取批次文件...")
    current_dir = Path(__file__).parent.parent
    output_dir = current_dir / "output"


    if not output_dir.exists():
        print(f"❌ 输出目录不存在: {output_dir}")
        return

    # 查找所有 batch_*.json 文件
    batch_files = []
    for i in range(1, 14):  # batch_1 到 batch_13
        batch_file = output_dir / f"batch_{i}_response.json"
        if batch_file.exists():
            batch_files.append(batch_file)
        else:
            print(f"⚠️ 批次文件不存在: {batch_file}")

    print(f"📋 找到 {len(batch_files)} 个批次文件: {[f.stem for f in batch_files]}")

    if not batch_files:
        print("❌ 没有找到批次文件")
        return

    # 4. 获取已存在的数据ID
    print("\n4️⃣ 获取已存在数据...")
    existing_ids = get_existing_aweme_ids(supabase)

    # 5. 处理所有批次
    print("\n5️⃣ 开始处理批次...")
    total_processed = 0
    total_success = 0
    total_fail = 0
    total_skip = 0

    start_time = time.time()

    for batch_file in batch_files:
        processed, success, skip, fail = process_batch_file(batch_file, supabase, existing_ids)
        total_processed += processed
        total_success += success
        total_fail += fail
        total_skip += skip

        # 更新已存在ID集合（用于后续批次）
        # 注意：这里不更新existing_ids，因为我们要在所有批次开始前就确定跳过哪些

        # 批次间稍作休息
        if batch_file != batch_files[-1]:  # 不是最后一个
            print("⏳ 批次间休息 2 秒...")
            time.sleep(2)

    end_time = time.time()
    duration = end_time - start_time

    # 6. 输出最终统计
    print("\n" + "=" * 60)
    print("最终处理统计")
    print("=" * 60)
    print(f"处理批次数: {len(batch_files)}")
    print(f"总视频数: {total_processed}")
    print(f"新增插入数: {total_success}")
    print(f"跳过已存在数: {total_skip}")
    print(f"失败插入数: {total_fail}")
    new_data_rate = (total_success / total_processed * 100) if total_processed > 0 else 0
    print(f"新增数据占比: {new_data_rate:.1f}%")
    print(f"处理用时: {duration:.1f} 秒")
    if duration > 0:
        speed = total_processed / duration
        print(f"处理速度: {speed:.2f} 条/秒")
    else:
        print("处理速度: N/A")
    print("=" * 60)

    if total_success > 0:
        print("✅ 批量处理完成！")
    else:
        print("❌ 批量处理失败，请检查数据和配置。")

if __name__ == "__main__":
    main()
