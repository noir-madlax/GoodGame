#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取视频详情脚本

功能：
1. 从数据库获取32位入选KOL的TOP5视频
2. 调用API获取视频详情（包含视频URL）
3. 保存到本地JSON文件
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "02_视频数据"


@dataclass
class VideoInfo:
    """视频信息"""
    note_id: str
    kol_id: str
    kol_name: str
    title: str
    is_video: bool
    is_advertise: bool
    read_num: int
    like_num: int
    collect_num: int
    comment_num: int
    publish_date: str
    img_url: str
    total_interact: int
    rank: int
    video_url: Optional[str] = None
    detail_data: Optional[Dict] = None


class VideoDetailFetcher:
    """视频详情获取器"""
    
    def __init__(self, concurrency: int = 5, api_delay: float = 0.5):
        self.concurrency = concurrency
        self.api_delay = api_delay
        self.token = self._load_api_token()
        self.base_url = "https://api.justoneapi.com"
        self.semaphore = asyncio.Semaphore(concurrency)
        
    def _load_api_token(self) -> str:
        """加载API Token"""
        backend_dir = Path(__file__).parent.parent.parent.parent.parent.parent
        env_path = backend_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
        
        token = os.getenv('JUSTONEAPI_API_KEY', '')
        if not token:
            raise ValueError("请在 .env 文件中配置 JUSTONEAPI_API_KEY")
        return token
    
    def _get_supabase_client(self):
        """获取Supabase客户端"""
        from supabase import create_client
        
        backend_dir = Path(__file__).parent.parent.parent.parent.parent.parent
        env_path = backend_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            raise ValueError("请在 .env 文件中配置 SUPABASE_URL 和 SUPABASE_KEY")
        
        return create_client(url, key)
    
    def get_selected_kol_ids(self) -> List[str]:
        """获取32位入选KOL的ID列表"""
        client = self._get_supabase_client()
        
        response = client.table('gg_pgy_kol_analysis_result').select(
            'kol_id'
        ).eq('post_frequency_pass', True
        ).eq('comment_gt_20_pass', True
        ).eq('read_fans_ratio_pass', True
        ).execute()
        
        return [row['kol_id'] for row in response.data if row.get('kol_id')]
    
    def get_top_videos(self, kol_ids: List[str], top_n: int = 5) -> List[VideoInfo]:
        """获取每位KOL的TOP N视频"""
        client = self._get_supabase_client()
        
        all_videos = []
        
        for kol_id in kol_ids:
            # 获取该KOL的非广告视频，按互动排序
            response = client.table('gg_pgy_kol_notes').select(
                'note_id, kol_id, title, is_video, is_advertise, '
                'read_num, like_num, collect_num, comment_num, publish_date, img_url'
            ).eq('kol_id', kol_id
            ).eq('is_video', True
            ).eq('is_advertise', False
            ).order('like_num', desc=True
            ).limit(top_n
            ).execute()
            
            # 获取KOL名称
            kol_response = client.table('gg_pgy_kol_analysis_result').select(
                'kol_name'
            ).eq('kol_id', kol_id).limit(1).execute()
            
            kol_name = kol_response.data[0].get('kol_name', 'Unknown') if kol_response.data else 'Unknown'
            
            for i, row in enumerate(response.data):
                total_interact = (row.get('like_num', 0) + 
                                 row.get('collect_num', 0) + 
                                 row.get('comment_num', 0))
                
                video = VideoInfo(
                    note_id=row['note_id'],
                    kol_id=kol_id,
                    kol_name=kol_name,
                    title=row.get('title', ''),
                    is_video=row.get('is_video', True),
                    is_advertise=row.get('is_advertise', False),
                    read_num=row.get('read_num', 0),
                    like_num=row.get('like_num', 0),
                    collect_num=row.get('collect_num', 0),
                    comment_num=row.get('comment_num', 0),
                    publish_date=str(row.get('publish_date', '')),
                    img_url=row.get('img_url', ''),
                    total_interact=total_interact,
                    rank=i + 1
                )
                all_videos.append(video)
        
        logger.info(f"共获取 {len(all_videos)} 个视频")
        return all_videos
    
    async def fetch_note_detail(self, session: aiohttp.ClientSession, 
                                 note_id: str) -> Dict[str, Any]:
        """获取笔记详情（包含视频URL）"""
        async with self.semaphore:
            # 使用蒲公英solar接口获取详情（包含视频URL）
            url = f"{self.base_url}/api/xiaohongshu-pgy/api/solar/note/noteId/detail/v1"
            params = {
                'token': self.token,
                'noteId': note_id
            }
            
            try:
                async with session.get(url, params=params, 
                                       timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        result = await response.json()
                        await asyncio.sleep(self.api_delay)
                        return result
                    else:
                        logger.error(f"获取 {note_id} 详情失败: HTTP {response.status}")
                        return {"error": f"HTTP {response.status}"}
            except Exception as e:
                logger.error(f"获取 {note_id} 详情异常: {e}")
                return {"error": str(e)}
    
    def extract_video_url(self, detail_data: Dict) -> Optional[str]:
        """从详情数据中提取视频URL"""
        if detail_data.get('code') != 0:
            return None
        
        data = detail_data.get('data', {})
        if not data:
            return None
        
        # 路径1: videoInfo.videoUrl (蒲公英solar接口)
        video_info = data.get('videoInfo', {})
        if video_info:
            video_url = video_info.get('videoUrl')
            if video_url:
                return video_url
        
        # 路径2: data.video.media.stream.h264[0].master_url
        video_data = data.get('video', {})
        if video_data:
            media = video_data.get('media', {})
            stream = media.get('stream', {})
            h264_list = stream.get('h264', [])
            if h264_list and len(h264_list) > 0:
                return h264_list[0].get('master_url')
        
        # 路径3: data.note_list[0].video.consumer.origin_video_key
        note_list = data.get('note_list', [])
        if note_list:
            video = note_list[0].get('video', {})
            consumer = video.get('consumer', {})
            origin_key = consumer.get('origin_video_key')
            if origin_key:
                return f"https://sns-video-bd.xhscdn.com/{origin_key}"
        
        return None
    
    async def fetch_all_details(self, videos: List[VideoInfo]) -> List[VideoInfo]:
        """批量获取所有视频详情"""
        logger.info(f"开始获取 {len(videos)} 个视频的详情...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for video in videos:
                tasks.append(self.fetch_note_detail(session, video.note_id))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"获取 {videos[i].note_id} 失败: {result}")
                    continue
                
                videos[i].detail_data = result
                videos[i].video_url = self.extract_video_url(result)
                
                if videos[i].video_url:
                    logger.info(f"✅ {videos[i].kol_name} - {videos[i].title[:20]}... 获取视频URL成功")
                else:
                    logger.warning(f"⚠️ {videos[i].kol_name} - {videos[i].title[:20]}... 未找到视频URL")
        
        return videos
    
    def save_results(self, videos: List[VideoInfo]):
        """保存结果到文件"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # 保存视频列表汇总
        video_list = []
        for v in videos:
            video_list.append({
                'note_id': v.note_id,
                'kol_id': v.kol_id,
                'kol_name': v.kol_name,
                'title': v.title,
                'is_advertise': v.is_advertise,
                'read_num': v.read_num,
                'like_num': v.like_num,
                'collect_num': v.collect_num,
                'comment_num': v.comment_num,
                'total_interact': v.total_interact,
                'publish_date': v.publish_date,
                'img_url': v.img_url,
                'video_url': v.video_url,
                'rank': v.rank,
                'has_video_url': v.video_url is not None
            })
        
        # 保存汇总文件
        summary_file = OUTPUT_DIR / "video_list.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'total_videos': len(videos),
                'videos_with_url': sum(1 for v in videos if v.video_url),
                'videos': video_list
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"视频列表已保存到: {summary_file}")
        
        # 按KOL分目录保存详情
        kol_groups = {}
        for v in videos:
            if v.kol_id not in kol_groups:
                kol_groups[v.kol_id] = []
            kol_groups[v.kol_id].append(v)
        
        for kol_id, kol_videos in kol_groups.items():
            kol_dir = OUTPUT_DIR / f"kol_{kol_id}"
            details_dir = kol_dir / "details"
            details_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存KOL信息
            kol_info = {
                'kol_id': kol_id,
                'kol_name': kol_videos[0].kol_name,
                'video_count': len(kol_videos),
                'videos_with_url': sum(1 for v in kol_videos if v.video_url)
            }
            with open(kol_dir / "info.json", 'w', encoding='utf-8') as f:
                json.dump(kol_info, f, ensure_ascii=False, indent=2)
            
            # 保存每个视频的详情
            for v in kol_videos:
                detail_file = details_dir / f"{v.note_id}.json"
                with open(detail_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'note_id': v.note_id,
                        'title': v.title,
                        'video_url': v.video_url,
                        'img_url': v.img_url,
                        'publish_date': v.publish_date,
                        'read_num': v.read_num,
                        'like_num': v.like_num,
                        'collect_num': v.collect_num,
                        'comment_num': v.comment_num,
                        'total_interact': v.total_interact,
                        'rank': v.rank,
                        'detail_data': v.detail_data
                    }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"详情已按KOL保存到: {OUTPUT_DIR}")
    
    def print_summary(self, videos: List[VideoInfo]):
        """打印汇总信息"""
        total = len(videos)
        with_url = sum(1 for v in videos if v.video_url)
        
        print("\n" + "=" * 60)
        print("视频详情获取汇总")
        print("=" * 60)
        print(f"总视频数: {total}")
        print(f"成功获取URL: {with_url} ({with_url/total*100:.1f}%)")
        print(f"未获取URL: {total - with_url}")
        print("=" * 60)
        
        # 按KOL统计
        kol_stats = {}
        for v in videos:
            if v.kol_name not in kol_stats:
                kol_stats[v.kol_name] = {'total': 0, 'with_url': 0}
            kol_stats[v.kol_name]['total'] += 1
            if v.video_url:
                kol_stats[v.kol_name]['with_url'] += 1
        
        print("\n按KOL统计:")
        for kol_name, stats in sorted(kol_stats.items()):
            status = "✅" if stats['with_url'] == stats['total'] else "⚠️"
            print(f"  {status} {kol_name}: {stats['with_url']}/{stats['total']}")


async def main():
    """主函数"""
    fetcher = VideoDetailFetcher(concurrency=5, api_delay=0.5)
    
    # 1. 获取32位入选KOL
    logger.info("获取入选KOL列表...")
    kol_ids = fetcher.get_selected_kol_ids()
    logger.info(f"共 {len(kol_ids)} 位入选KOL")
    
    # 2. 获取每位KOL的TOP5视频
    logger.info("获取TOP5视频...")
    videos = fetcher.get_top_videos(kol_ids, top_n=5)
    
    # 3. 获取视频详情
    videos = await fetcher.fetch_all_details(videos)
    
    # 4. 保存结果
    fetcher.save_results(videos)
    
    # 5. 打印汇总
    fetcher.print_summary(videos)


if __name__ == "__main__":
    asyncio.run(main())
