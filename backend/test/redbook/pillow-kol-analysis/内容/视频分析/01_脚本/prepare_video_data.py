#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
准备视频分析数据 - 一站式脚本

功能：
1. 从数据库获取31位KOL的TOP5视频（排除纯图文博主）
2. 调用API获取视频详情（含视频URL）
3. 下载视频文件
4. 导出分析所需的元数据JSON
"""

import os
import json
import asyncio
import aiohttp
import aiofiles
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
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
DATA_DIR = PROJECT_DIR / "02_视频数据"

# 加载环境变量
BACKEND_DIR = Path("/Users/rigel/project/hdl-tikhub-goodgame/backend")
load_dotenv(BACKEND_DIR / '.env')


@dataclass
class VideoMetadata:
    """视频元数据（用于AI分析）"""
    note_id: str
    kol_id: str
    kol_name: str
    title: str
    content: str = ""  # 笔记正文
    is_advertise: bool = False
    publish_date: str = ""
    read_num: int = 0
    like_num: int = 0
    collect_num: int = 0
    comment_num: int = 0
    total_interact: int = 0
    rank: int = 0
    fans_count: int = 0
    video_url: Optional[str] = None
    video_duration: int = 0  # 视频时长（秒）
    cover_url: Optional[str] = None
    downloaded: bool = False
    file_path: Optional[str] = None


class VideoDataPreparer:
    """视频数据准备器"""
    
    def __init__(self, concurrency: int = 5, download_concurrency: int = 3):
        self.api_concurrency = concurrency
        self.download_concurrency = download_concurrency
        self.token = os.getenv('JUSTONEAPI_API_KEY', '')
        self.base_url = "https://api.justoneapi.com"
        self.api_semaphore = asyncio.Semaphore(concurrency)
        self.download_semaphore = asyncio.Semaphore(download_concurrency)
        
        # 统计
        self.stats = {
            'total_videos': 0,
            'details_fetched': 0,
            'details_failed': 0,
            'downloaded': 0,
            'download_failed': 0,
            'skipped': 0
        }
    
    def _get_supabase_client(self):
        """获取Supabase客户端"""
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        return create_client(url, key)
    
    def get_video_list(self) -> List[VideoMetadata]:
        """从数据库获取视频列表（TOP5/每位KOL，按互动排序）"""
        client = self._get_supabase_client()
        
        # SQL逻辑：32位入选KOL中有视频的，每人TOP5
        # 先获取入选KOL
        kol_response = client.table('gg_pgy_kol_analysis_result').select(
            'kol_id, kol_name, fans_count_current'
        ).eq('post_frequency_pass', True
        ).eq('comment_gt_20_pass', True
        ).eq('read_fans_ratio_pass', True
        ).execute()
        
        kol_map = {row['kol_id']: row for row in kol_response.data}
        logger.info(f"获取到 {len(kol_map)} 位入选KOL")
        
        all_videos = []
        
        for kol_id, kol_info in kol_map.items():
            # 获取该KOL的视频笔记，按互动排序
            notes_response = client.table('gg_pgy_kol_notes').select(
                'note_id, title, is_video, is_advertise, '
                'read_num, like_num, collect_num, comment_num, publish_date, img_url'
            ).eq('kol_id', kol_id
            ).eq('is_video', True
            ).order('like_num', desc=True
            ).limit(5
            ).execute()
            
            if not notes_response.data:
                logger.warning(f"KOL {kol_info.get('kol_name')} 无视频")
                continue
            
            for i, note in enumerate(notes_response.data):
                total_interact = (
                    (note.get('like_num') or 0) + 
                    (note.get('collect_num') or 0) + 
                    (note.get('comment_num') or 0)
                )
                
                video = VideoMetadata(
                    note_id=note['note_id'],
                    kol_id=kol_id,
                    kol_name=kol_info.get('kol_name') or 'Unknown',
                    title=note.get('title') or '',
                    is_advertise=note.get('is_advertise', False),
                    publish_date=str(note.get('publish_date', '')),
                    read_num=note.get('read_num') or 0,
                    like_num=note.get('like_num') or 0,
                    collect_num=note.get('collect_num') or 0,
                    comment_num=note.get('comment_num') or 0,
                    total_interact=total_interact,
                    rank=i + 1,
                    fans_count=kol_info.get('fans_count_current') or 0,
                    cover_url=note.get('img_url')
                )
                all_videos.append(video)
        
        self.stats['total_videos'] = len(all_videos)
        logger.info(f"共获取 {len(all_videos)} 个视频")
        return all_videos
    
    async def fetch_video_detail(self, session: aiohttp.ClientSession, 
                                  video: VideoMetadata) -> VideoMetadata:
        """获取视频详情"""
        async with self.api_semaphore:
            url = f"{self.base_url}/api/xiaohongshu-pgy/api/solar/note/noteId/detail/v1"
            params = {'token': self.token, 'noteId': video.note_id}
            
            try:
                async with session.get(url, params=params, 
                                       timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get('code') == 0:
                            data = result.get('data', {})
                            
                            # 提取视频URL
                            video_info = data.get('videoInfo', {})
                            video.video_url = video_info.get('videoUrl')
                            video.video_duration = video_info.get('meta', {}).get('duration', 0)
                            
                            # 提取正文内容
                            video.content = data.get('content', '')
                            
                            self.stats['details_fetched'] += 1
                            logger.info(f"✅ {video.kol_name} - {video.title[:20]}...")
                        else:
                            self.stats['details_failed'] += 1
                            logger.warning(f"⚠️ {video.note_id}: API错误 {result.get('code')}")
                    else:
                        self.stats['details_failed'] += 1
                        logger.error(f"❌ {video.note_id}: HTTP {resp.status}")
                        
            except Exception as e:
                self.stats['details_failed'] += 1
                logger.error(f"❌ {video.note_id}: {e}")
            
            await asyncio.sleep(0.5)
            return video
    
    async def download_video(self, session: aiohttp.ClientSession, 
                              video: VideoMetadata) -> VideoMetadata:
        """下载视频"""
        if not video.video_url:
            self.stats['skipped'] += 1
            return video
        
        # 目标文件路径
        kol_dir = DATA_DIR / f"kol_{video.kol_id}" / "videos"
        kol_dir.mkdir(parents=True, exist_ok=True)
        video_file = kol_dir / f"{video.note_id}.mp4"
        
        # 已存在则跳过
        if video_file.exists() and video_file.stat().st_size > 10000:
            video.downloaded = True
            video.file_path = str(video_file)
            self.stats['skipped'] += 1
            logger.info(f"⏭️ 已存在: {video.kol_name} - {video.note_id}")
            return video
        
        async with self.download_semaphore:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Referer': 'https://www.xiaohongshu.com/'
            }
            
            try:
                async with session.get(video.video_url, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=300)) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(video_file, 'wb') as f:
                            async for chunk in resp.content.iter_chunked(1024 * 1024):
                                await f.write(chunk)
                        
                        file_size = video_file.stat().st_size
                        if file_size > 10000:
                            video.downloaded = True
                            video.file_path = str(video_file)
                            self.stats['downloaded'] += 1
                            logger.info(f"📥 下载完成: {video.kol_name} ({file_size/1024/1024:.1f}MB)")
                        else:
                            video_file.unlink()
                            self.stats['download_failed'] += 1
                            logger.warning(f"⚠️ 文件太小: {video.note_id}")
                    else:
                        self.stats['download_failed'] += 1
                        logger.error(f"❌ 下载失败: {video.note_id} HTTP {resp.status}")
                        
            except Exception as e:
                self.stats['download_failed'] += 1
                logger.error(f"❌ 下载异常: {video.note_id} - {e}")
        
        return video
    
    def save_metadata(self, videos: List[VideoMetadata]):
        """保存元数据"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # 按KOL分组保存
        kol_videos = {}
        for v in videos:
            if v.kol_id not in kol_videos:
                kol_videos[v.kol_id] = []
            kol_videos[v.kol_id].append(v)
        
        for kol_id, kol_vids in kol_videos.items():
            kol_dir = DATA_DIR / f"kol_{kol_id}"
            kol_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存该KOL的元数据
            metadata_file = kol_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'kol_id': kol_id,
                    'kol_name': kol_vids[0].kol_name,
                    'fans_count': kol_vids[0].fans_count,
                    'video_count': len(kol_vids),
                    'videos': [asdict(v) for v in kol_vids]
                }, f, ensure_ascii=False, indent=2)
        
        # 保存汇总文件
        summary_file = DATA_DIR / "video_list.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'stats': self.stats,
                'total_kols': len(kol_videos),
                'total_videos': len(videos),
                'videos': [asdict(v) for v in videos]
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📁 元数据已保存到: {DATA_DIR}")
    
    async def run(self, skip_download: bool = False):
        """执行完整流程"""
        logger.info("=" * 60)
        logger.info("开始准备视频分析数据")
        logger.info("=" * 60)
        
        # 1. 获取视频列表
        videos = self.get_video_list()
        
        # 2. 获取视频详情
        logger.info("\n📡 获取视频详情...")
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_video_detail(session, v) for v in videos]
            videos = await asyncio.gather(*tasks)
        
        # 3. 下载视频
        if not skip_download:
            logger.info("\n📥 下载视频文件...")
            async with aiohttp.ClientSession() as session:
                tasks = [self.download_video(session, v) for v in videos]
                videos = await asyncio.gather(*tasks)
        
        # 4. 保存元数据
        self.save_metadata(videos)
        
        # 5. 打印统计
        self._print_stats()
        
        return videos
    
    def _print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 60)
        print("准备完成")
        print("=" * 60)
        print(f"总视频数: {self.stats['total_videos']}")
        print(f"详情获取成功: {self.stats['details_fetched']}")
        print(f"详情获取失败: {self.stats['details_failed']}")
        print(f"下载成功: {self.stats['downloaded']}")
        print(f"下载失败: {self.stats['download_failed']}")
        print(f"跳过（已存在/无URL）: {self.stats['skipped']}")
        print("=" * 60)


async def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='准备视频分析数据')
    parser.add_argument('--skip-download', action='store_true', help='跳过视频下载')
    parser.add_argument('--limit', type=int, default=0, help='限制处理视频数量（0=全部）')
    args = parser.parse_args()
    
    preparer = VideoDataPreparer()
    await preparer.run(skip_download=args.skip_download)


if __name__ == "__main__":
    asyncio.run(main())
