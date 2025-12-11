#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量获取视频详情和下载视频

解决API调用失败率高的问题：
1. 使用多个API端点尝试
2. 增加重试机制
3. 批量处理并保存进度
"""

import os
import json
import asyncio
import aiohttp
import aiofiles
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import random

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


class VideoFetcher:
    """视频获取器 - 支持多API端点和重试"""
    
    def __init__(self):
        self.token = os.getenv('JUSTONEAPI_API_KEY', '')
        self.base_url = "https://api.justoneapi.com"
        self.semaphore = asyncio.Semaphore(3)  # 并发控制
        self.delay = 1.0  # API调用延迟
        
        # API端点列表（按优先级）
        self.api_endpoints = [
            # 蒲公英solar接口（最稳定）
            {
                'name': 'pgy_solar',
                'url': '/api/xiaohongshu-pgy/api/solar/note/noteId/detail/v1',
                'params': lambda note_id: {'token': self.token, 'noteId': note_id},
                'extract': self._extract_from_solar
            },
            # XHS原生接口v5
            {
                'name': 'xhs_v5',
                'url': '/api/xiaohongshu/note/detail/v5',
                'params': lambda note_id: {'token': self.token, 'note_id': note_id},
                'extract': self._extract_from_xhs_v5
            },
        ]
        
        # 统计
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'downloaded': 0,
            'download_failed': 0
        }
    
    def _extract_from_solar(self, data: Dict) -> Optional[str]:
        """从蒲公英solar接口提取视频URL"""
        if data.get('code') != 0:
            return None
        video_info = data.get('data', {}).get('videoInfo', {})
        return video_info.get('videoUrl')
    
    def _extract_from_xhs_v5(self, data: Dict) -> Optional[str]:
        """从XHS v5接口提取视频URL"""
        if data.get('code') != 0:
            return None
        data_content = data.get('data', {})
        video = data_content.get('video', {})
        media = video.get('media', {})
        stream = media.get('stream', {})
        h264 = stream.get('h264', [])
        if h264:
            return h264[0].get('master_url')
        return None
    
    async def fetch_video_url(self, session: aiohttp.ClientSession, 
                               note_id: str) -> Tuple[Optional[str], Optional[Dict]]:
        """获取视频URL（尝试多个API端点）"""
        async with self.semaphore:
            for endpoint in self.api_endpoints:
                try:
                    url = f"{self.base_url}{endpoint['url']}"
                    params = endpoint['params'](note_id)
                    
                    async with session.get(url, params=params,
                                          timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            video_url = endpoint['extract'](result)
                            if video_url:
                                logger.debug(f"✅ {note_id} via {endpoint['name']}")
                                return video_url, result.get('data', {})
                            else:
                                code = result.get('code', 'unknown')
                                logger.debug(f"⚠️ {note_id} via {endpoint['name']}: code={code}")
                except Exception as e:
                    logger.debug(f"❌ {note_id} via {endpoint['name']}: {e}")
                
                # 短暂延迟后尝试下一个端点
                await asyncio.sleep(0.3)
            
            # 所有端点都失败
            return None, None
    
    async def download_video(self, session: aiohttp.ClientSession,
                              video_url: str, save_path: Path) -> bool:
        """下载视频文件"""
        if save_path.exists() and save_path.stat().st_size > 10000:
            logger.info(f"⏭️ 已存在: {save_path.name}")
            return True
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Referer': 'https://www.xiaohongshu.com/'
        }
        
        try:
            async with session.get(video_url, headers=headers,
                                  timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status == 200:
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(save_path, 'wb') as f:
                        total = 0
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            await f.write(chunk)
                            total += len(chunk)
                    
                    if total > 10000:
                        logger.info(f"📥 下载完成: {save_path.name} ({total/1024/1024:.1f}MB)")
                        return True
                    else:
                        save_path.unlink()
                        return False
        except Exception as e:
            logger.error(f"❌ 下载失败 {save_path.name}: {e}")
        
        return False
    
    def get_kol_top5_videos(self) -> List[Dict]:
        """从数据库获取每个KOL的TOP5视频"""
        from supabase import create_client
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        client = create_client(url, key)
        
        # 获取入选KOL
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
            # 获取该KOL的视频笔记，按互动排序取TOP5
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
                
                video = {
                    'note_id': note['note_id'],
                    'kol_id': kol_id,
                    'kol_name': kol_info.get('kol_name') or 'Unknown',
                    'title': note.get('title') or '',
                    'content': note.get('content') or '',
                    'is_advertise': note.get('is_advertise', False),
                    'publish_date': str(note.get('publish_date', '')),
                    'read_num': note.get('read_num') or 0,
                    'like_num': note.get('like_num') or 0,
                    'collect_num': note.get('collect_num') or 0,
                    'comment_num': note.get('comment_num') or 0,
                    'total_interact': total_interact,
                    'rank': i + 1,
                    'fans_count': kol_info.get('fans_count_current') or 0,
                    'cover_url': note.get('img_url'),
                    'video_url': None,
                    'video_duration': 0,
                    'downloaded': False,
                    'file_path': None
                }
                all_videos.append(video)
        
        self.stats['total'] = len(all_videos)
        logger.info(f"共需处理 {len(all_videos)} 个视频")
        return all_videos
    
    async def process_video(self, session: aiohttp.ClientSession, video: Dict) -> Dict:
        """处理单个视频：获取URL并下载"""
        note_id = video['note_id']
        kol_name = video['kol_name']
        
        # 1. 获取视频URL
        video_url, detail_data = await self.fetch_video_url(session, note_id)
        
        if video_url:
            video['video_url'] = video_url
            if detail_data:
                video['video_duration'] = detail_data.get('videoInfo', {}).get('meta', {}).get('duration', 0)
                # 补充content如果为空
                if not video['content']:
                    video['content'] = detail_data.get('content', '')
            
            self.stats['success'] += 1
            
            # 2. 下载视频
            kol_dir = DATA_DIR / f"kol_{video['kol_id']}" / "videos"
            video_file = kol_dir / f"{note_id}.mp4"
            
            downloaded = await self.download_video(session, video_url, video_file)
            if downloaded:
                video['downloaded'] = True
                video['file_path'] = str(video_file)
                self.stats['downloaded'] += 1
            else:
                self.stats['download_failed'] += 1
            
            logger.info(f"✅ {kol_name}: {video['title'][:25]}...")
        else:
            self.stats['failed'] += 1
            logger.warning(f"❌ {kol_name}: {note_id} - 无法获取URL")
        
        await asyncio.sleep(self.delay + random.uniform(0, 0.5))
        return video
    
    def save_results(self, videos: List[Dict]):
        """保存结果"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # 按KOL分组保存
        kol_videos = {}
        for v in videos:
            kol_id = v['kol_id']
            if kol_id not in kol_videos:
                kol_videos[kol_id] = []
            kol_videos[kol_id].append(v)
        
        for kol_id, kol_vids in kol_videos.items():
            kol_dir = DATA_DIR / f"kol_{kol_id}"
            kol_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存该KOL的元数据
            metadata = {
                'kol_id': kol_id,
                'kol_name': kol_vids[0]['kol_name'],
                'fans_count': kol_vids[0]['fans_count'],
                'video_count': len(kol_vids),
                'videos_with_url': sum(1 for v in kol_vids if v['video_url']),
                'videos_downloaded': sum(1 for v in kol_vids if v['downloaded']),
                'videos': kol_vids
            }
            
            metadata_file = kol_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 保存汇总文件
        summary = {
            'generated_at': datetime.now().isoformat(),
            'stats': self.stats,
            'total_kols': len(kol_videos),
            'total_videos': len(videos),
            'videos_with_url': sum(1 for v in videos if v['video_url']),
            'videos_downloaded': sum(1 for v in videos if v['downloaded']),
            'videos': videos
        }
        
        summary_file = DATA_DIR / "video_list.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📁 数据已保存到: {DATA_DIR}")
    
    async def run(self, skip_download: bool = False):
        """执行完整流程"""
        logger.info("=" * 60)
        logger.info("开始批量获取视频")
        logger.info("=" * 60)
        
        # 1. 获取需要处理的视频列表
        videos = self.get_kol_top5_videos()
        
        # 2. 批量处理
        async with aiohttp.ClientSession() as session:
            # 分批处理，每批10个
            batch_size = 10
            for i in range(0, len(videos), batch_size):
                batch = videos[i:i+batch_size]
                logger.info(f"\n处理批次 {i//batch_size + 1}/{(len(videos)-1)//batch_size + 1}")
                
                tasks = [self.process_video(session, v) for v in batch]
                results = await asyncio.gather(*tasks)
                
                # 更新videos列表
                for j, result in enumerate(results):
                    videos[i+j] = result
                
                # 每批次后保存进度
                self.save_results(videos)
        
        # 3. 打印统计
        self._print_stats()
        
        return videos
    
    def _print_stats(self):
        """打印统计"""
        print("\n" + "=" * 60)
        print("处理完成")
        print("=" * 60)
        print(f"总视频数: {self.stats['total']}")
        print(f"URL获取成功: {self.stats['success']}")
        print(f"URL获取失败: {self.stats['failed']}")
        print(f"下载成功: {self.stats['downloaded']}")
        print(f"下载失败: {self.stats['download_failed']}")
        
        # 按KOL统计
        video_list_file = DATA_DIR / "video_list.json"
        if video_list_file.exists():
            with open(video_list_file, 'r') as f:
                data = json.load(f)
            
            print("\n各KOL视频情况:")
            kol_stats = {}
            for v in data['videos']:
                kol_name = v['kol_name']
                if kol_name not in kol_stats:
                    kol_stats[kol_name] = {'total': 0, 'with_url': 0, 'downloaded': 0}
                kol_stats[kol_name]['total'] += 1
                if v.get('video_url'):
                    kol_stats[kol_name]['with_url'] += 1
                if v.get('downloaded'):
                    kol_stats[kol_name]['downloaded'] += 1
            
            for name, stats in sorted(kol_stats.items()):
                print(f"  {name[:15]:<16}: {stats['total']}个, URL {stats['with_url']}个, 下载 {stats['downloaded']}个")
        
        print("=" * 60)


async def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='批量获取视频')
    parser.add_argument('--skip-download', action='store_true', help='跳过视频下载')
    args = parser.parse_args()
    
    fetcher = VideoFetcher()
    await fetcher.run(skip_download=args.skip_download)


if __name__ == "__main__":
    asyncio.run(main())
