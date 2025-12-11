#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量下载视频脚本

功能：
1. 读取视频列表JSON
2. 并发下载视频
3. 保存到对应KOL目录
"""

import os
import json
import asyncio
import aiohttp
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
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


class VideoDownloader:
    """视频下载器"""
    
    def __init__(self, concurrency: int = 3, chunk_size: int = 1024 * 1024):
        self.concurrency = concurrency
        self.chunk_size = chunk_size
        self.semaphore = asyncio.Semaphore(concurrency)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/'
        }
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.skip_count = 0
    
    def load_video_list(self) -> List[Dict]:
        """加载视频列表"""
        video_list_file = DATA_DIR / "video_list.json"
        
        if not video_list_file.exists():
            raise FileNotFoundError(f"视频列表文件不存在: {video_list_file}")
        
        with open(video_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('videos', [])
    
    async def download_video(self, session: aiohttp.ClientSession, 
                             video: Dict) -> bool:
        """下载单个视频"""
        note_id = video.get('note_id')
        kol_id = video.get('kol_id')
        kol_name = video.get('kol_name', 'Unknown')
        video_url = video.get('video_url')
        
        if not video_url:
            logger.warning(f"跳过 {kol_name} - {note_id}: 无视频URL")
            self.skip_count += 1
            return False
        
        # 创建KOL视频目录
        kol_video_dir = DATA_DIR / f"kol_{kol_id}" / "videos"
        kol_video_dir.mkdir(parents=True, exist_ok=True)
        
        # 视频文件路径
        video_file = kol_video_dir / f"{note_id}.mp4"
        
        # 检查是否已下载
        if video_file.exists():
            logger.info(f"跳过 {kol_name} - {note_id}: 已存在")
            self.skip_count += 1
            return True
        
        async with self.semaphore:
            try:
                logger.info(f"下载 {kol_name} - {note_id}...")
                
                async with session.get(video_url, headers=self.headers, 
                                       timeout=aiohttp.ClientTimeout(total=300)) as resp:
                    if resp.status != 200:
                        logger.error(f"下载失败 {note_id}: HTTP {resp.status}")
                        self.fail_count += 1
                        return False
                    
                    # 流式写入文件
                    async with aiofiles.open(video_file, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(self.chunk_size):
                            await f.write(chunk)
                
                # 验证文件大小
                file_size = video_file.stat().st_size
                if file_size < 10000:  # 小于10KB可能是错误
                    logger.warning(f"文件太小 {note_id}: {file_size} bytes")
                    video_file.unlink()
                    self.fail_count += 1
                    return False
                
                logger.info(f"✅ 完成 {kol_name} - {note_id} ({file_size / 1024 / 1024:.1f} MB)")
                self.success_count += 1
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"超时 {note_id}")
                self.fail_count += 1
                return False
            except Exception as e:
                logger.error(f"异常 {note_id}: {e}")
                self.fail_count += 1
                return False
    
    async def download_all(self, videos: List[Dict]):
        """批量下载所有视频"""
        logger.info(f"开始下载 {len(videos)} 个视频...")
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.download_video(session, v) for v in videos]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 打印统计
        print("\n" + "=" * 60)
        print("下载完成")
        print("=" * 60)
        print(f"成功: {self.success_count}")
        print(f"失败: {self.fail_count}")
        print(f"跳过: {self.skip_count}")
        print("=" * 60)
    
    def update_download_status(self, videos: List[Dict]):
        """更新下载状态"""
        for video in videos:
            kol_id = video.get('kol_id')
            note_id = video.get('note_id')
            video_file = DATA_DIR / f"kol_{kol_id}" / "videos" / f"{note_id}.mp4"
            video['downloaded'] = video_file.exists()
            if video['downloaded']:
                video['file_size'] = video_file.stat().st_size
        
        # 保存更新后的列表
        video_list_file = DATA_DIR / "video_list.json"
        with open(video_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data['videos'] = videos
        data['download_time'] = datetime.now().isoformat()
        data['download_stats'] = {
            'success': self.success_count,
            'fail': self.fail_count,
            'skip': self.skip_count
        }
        
        with open(video_list_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


async def main():
    """主函数"""
    downloader = VideoDownloader(concurrency=3)
    
    try:
        # 加载视频列表
        videos = downloader.load_video_list()
        
        # 筛选有URL的视频
        videos_to_download = [v for v in videos if v.get('video_url')]
        logger.info(f"共 {len(videos_to_download)} 个视频有URL")
        
        # 下载
        await downloader.download_all(videos_to_download)
        
        # 更新状态
        downloader.update_download_status(videos)
        
    except FileNotFoundError as e:
        logger.error(f"错误: {e}")
        logger.info("请先运行 fetch_video_details.py 获取视频列表")


if __name__ == "__main__":
    asyncio.run(main())
