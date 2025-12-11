#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段6-2: 下载视频

功能：
1. 读取video_list.json
2. 下载所有视频到本地
3. 支持断点续传
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "02_视频数据"

CONFIG = {
    "concurrency": 3,
    "timeout": 300,  # 5分钟超时
    "headers": {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://www.xiaohongshu.com/"
    }
}


class VideoDownloader:
    """视频下载器"""
    
    def __init__(self):
        self.config = CONFIG
        self.semaphore = asyncio.Semaphore(self.config['concurrency'])
        self.video_list_file = DATA_DIR / "video_list.json"
    
    def load_video_list(self) -> List[Dict]:
        """加载视频列表"""
        with open(self.video_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('videos', [])
    
    def save_video_list(self, videos: List[Dict]):
        """保存视频列表（更新下载状态）"""
        with open(self.video_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data['videos'] = videos
        
        with open(self.video_list_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def download_video(self, session: aiohttp.ClientSession, video: Dict, index: int, total: int) -> bool:
        """下载单个视频"""
        async with self.semaphore:
            note_id = video['note_id']
            kol_id = video['kol_id']
            kol_name = video['kol_name']
            video_url = video.get('video_url')
            title = video.get('title', '')[:20]
            
            if not video_url:
                logger.warning(f"[{index}/{total}] ⚠️ {kol_name} - {title}: 无视频URL")
                return False
            
            # 创建目录
            kol_dir = DATA_DIR / f"kol_{kol_id}" / "videos"
            kol_dir.mkdir(parents=True, exist_ok=True)
            
            video_path = kol_dir / f"{note_id}.mp4"
            
            # 检查是否已下载
            if video_path.exists() and video_path.stat().st_size > 10000:
                logger.info(f"[{index}/{total}] ⏭️ {kol_name} - {title}: 已存在")
                video['downloaded'] = True
                video['file_path'] = str(video_path)
                return True
            
            logger.info(f"[{index}/{total}] 📥 {kol_name} - {title}...")
            
            try:
                async with session.get(video_url, headers=self.config['headers'],
                                       timeout=aiohttp.ClientTimeout(total=self.config['timeout'])) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        with open(video_path, 'wb') as f:
                            f.write(content)
                        
                        size_mb = len(content) / 1024 / 1024
                        logger.info(f"  ✅ 完成 ({size_mb:.1f}MB)")
                        
                        video['downloaded'] = True
                        video['file_path'] = str(video_path)
                        return True
                    else:
                        logger.error(f"  ❌ HTTP {response.status}")
                        return False
            except asyncio.TimeoutError:
                logger.error(f"  ❌ 下载超时")
                return False
            except Exception as e:
                logger.error(f"  ❌ 错误: {e}")
                return False
    
    async def download_all(self):
        """下载所有视频"""
        logger.info("=" * 60)
        logger.info("🚀 阶段6-2: 下载视频")
        logger.info("=" * 60)
        
        videos = self.load_video_list()
        
        # 筛选有URL且未下载的
        to_download = [v for v in videos if v.get('video_url') and not v.get('downloaded')]
        already_done = len(videos) - len(to_download)
        
        logger.info(f"总视频数: {len(videos)}")
        logger.info(f"待下载: {len(to_download)}")
        logger.info(f"已完成: {already_done}")
        logger.info(f"并发数: {self.config['concurrency']}")
        logger.info("")
        
        if not to_download:
            logger.info("✅ 所有视频已下载完成")
            return
        
        async with aiohttp.ClientSession() as session:
            for i, video in enumerate(videos, 1):
                if video.get('video_url') and not video.get('downloaded'):
                    await self.download_video(session, video, i, len(videos))
                    # 每次下载后保存状态
                    self.save_video_list(videos)
        
        # 统计
        success = sum(1 for v in videos if v.get('downloaded'))
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"📋 下载完成: {success}/{len(videos)}")
        logger.info("=" * 60)


async def main():
    downloader = VideoDownloader()
    await downloader.download_all()


if __name__ == "__main__":
    asyncio.run(main())
