#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段6-1: 获取视频详情

功能：
1. 从详细数据中读取笔记列表
2. 筛选非广告视频，每人TOP 5
3. 调用API获取视频详情（包含视频URL）
4. 保存到本地

目标KOL (4人):
- 加绒卷子: 6080c7ca0000000001004c6b
- 汤圆小玩子: 6297c9030000000021022723
- vikk啦啦啦: 59476bb282ec39663ed76f6a
- 出逃的哈哈ya🎈: 58ef740f6a6a696f5c5fa25f

预计API调用: 4 × 5 = 20次
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = SCRIPT_DIR.parent.parent / "01_KOL数据获取" / "02_详细数据"
OUTPUT_DIR = PROJECT_DIR / "02_视频数据"

# 目标KOL
TARGET_KOLS = [
    {"kol_id": "6080c7ca0000000001004c6b", "name": "加绒卷子"},
    {"kol_id": "6297c9030000000021022723", "name": "汤圆小玩子"},
    {"kol_id": "59476bb282ec39663ed76f6a", "name": "vikk啦啦啦"},
    {"kol_id": "58ef740f6a6a696f5c5fa25f", "name": "出逃的哈哈ya🎈"},
]

CONFIG = {
    "api_base_url": "https://api.justoneapi.com",
    "concurrency": 5,
    "timeout": 30,
    "api_delay": 0.5,
    "top_n": 5,  # 每人取TOP 5视频
}


class VideoDetailFetcher:
    """视频详情获取器"""
    
    def __init__(self):
        self.config = CONFIG
        self.token = self._load_api_token()
        self.base_url = self.config['api_base_url']
        self.semaphore = asyncio.Semaphore(self.config['concurrency'])
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_api_token(self) -> str:
        """加载API Token"""
        # backend目录路径
        backend_dir = Path(__file__).parent.parent.parent.parent.parent.parent
        env_path = backend_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
        
        token = os.getenv('JUSTONEAPI_API_KEY', '')
        if not token:
            raise ValueError("请在 .env 文件中配置 JUSTONEAPI_API_KEY")
        return token
    
    def get_kol_videos(self, kol_id: str, kol_name: str) -> List[Dict]:
        """从本地数据获取KOL的视频列表"""
        note_list_file = DATA_DIR / f"kol_{kol_id}" / "kol_note_list.json"
        
        if not note_list_file.exists():
            logger.warning(f"找不到 {kol_name} 的笔记列表文件")
            return []
        
        with open(note_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result = data.get('result', {})
        if result.get('code') != 0:
            logger.warning(f"{kol_name} 笔记列表API返回错误")
            return []
        
        notes = result.get('data', {}).get('list', []) or []
        
        # 筛选：视频 + 非广告
        videos = []
        for note in notes:
            if note.get('isVideo') and not note.get('isAdvertise'):
                videos.append({
                    'note_id': note.get('noteId'),
                    'kol_id': kol_id,
                    'kol_name': kol_name,
                    'title': note.get('title', ''),
                    'is_video': True,
                    'is_advertise': False,
                    'read_num': note.get('readNum', 0) or 0,
                    'like_num': note.get('likeNum', 0) or 0,
                    'collect_num': note.get('collectNum', 0) or 0,
                    'publish_date': note.get('date', ''),
                    'img_url': note.get('imgUrl', ''),
                    'total_interact': (note.get('likeNum', 0) or 0) + (note.get('collectNum', 0) or 0)
                })
        
        # 按互动排序，取TOP N
        videos.sort(key=lambda x: x['total_interact'], reverse=True)
        videos = videos[:self.config['top_n']]
        
        # 添加排名
        for i, v in enumerate(videos):
            v['rank'] = i + 1
        
        logger.info(f"  {kol_name}: 筛选出 {len(videos)} 个视频")
        return videos
    
    async def fetch_note_detail(self, session: aiohttp.ClientSession, 
                                 note_id: str, kol_name: str) -> Dict[str, Any]:
        """获取笔记详情（包含视频URL）"""
        async with self.semaphore:
            url = f"{self.base_url}/api/xiaohongshu-pgy/api/solar/note/noteId/detail/v1"
            params = {
                'token': self.token,
                'noteId': note_id
            }
            
            try:
                async with session.get(url, params=params,
                                       timeout=aiohttp.ClientTimeout(total=self.config['timeout'])) as response:
                    if response.status == 200:
                        result = await response.json()
                        await asyncio.sleep(self.config['api_delay'])
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
        
        # 路径1: videoInfo.videoUrl
        video_info = data.get('videoInfo', {})
        if video_info:
            video_url = video_info.get('videoUrl')
            if video_url:
                return video_url
        
        return None
    
    def extract_video_content(self, detail_data: Dict) -> str:
        """提取视频正文内容"""
        if detail_data.get('code') != 0:
            return ""
        
        data = detail_data.get('data', {})
        return data.get('content', '') or ''
    
    async def fetch_all(self):
        """获取所有视频详情"""
        logger.info("=" * 60)
        logger.info("🚀 阶段6-1: 获取视频详情")
        logger.info("=" * 60)
        
        # 收集所有视频
        all_videos = []
        for kol in TARGET_KOLS:
            videos = self.get_kol_videos(kol['kol_id'], kol['name'])
            all_videos.extend(videos)
        
        logger.info(f"\n总计 {len(all_videos)} 个视频待获取详情")
        logger.info(f"预计API调用: {len(all_videos)} 次\n")
        
        # 获取详情
        async with aiohttp.ClientSession() as session:
            for i, video in enumerate(all_videos, 1):
                note_id = video['note_id']
                kol_name = video['kol_name']
                title = video['title'][:20] if video['title'] else '无标题'
                
                logger.info(f"[{i}/{len(all_videos)}] {kol_name} - {title}...")
                
                detail = await self.fetch_note_detail(session, note_id, kol_name)
                video['detail_data'] = detail
                video['video_url'] = self.extract_video_url(detail)
                video['content'] = self.extract_video_content(detail)
                
                if video['video_url']:
                    logger.info(f"  ✅ 获取视频URL成功")
                else:
                    logger.warning(f"  ⚠️ 未找到视频URL")
        
        # 保存结果
        self._save_results(all_videos)
        self._print_summary(all_videos)
    
    def _save_results(self, videos: List[Dict]):
        """保存结果"""
        # 保存汇总
        video_list = []
        for v in videos:
            video_list.append({
                'note_id': v['note_id'],
                'kol_id': v['kol_id'],
                'kol_name': v['kol_name'],
                'title': v['title'],
                'read_num': v['read_num'],
                'like_num': v['like_num'],
                'collect_num': v['collect_num'],
                'total_interact': v['total_interact'],
                'publish_date': v['publish_date'],
                'img_url': v['img_url'],
                'video_url': v['video_url'],
                'content': v.get('content', '')[:500],  # 截取前500字
                'rank': v['rank'],
                'has_video_url': v['video_url'] is not None,
                'downloaded': False,
                'file_path': None
            })
        
        summary_file = OUTPUT_DIR / "video_list.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'total_videos': len(videos),
                'videos_with_url': sum(1 for v in videos if v['video_url']),
                'videos': video_list
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📄 视频列表已保存: {summary_file}")
        
        # 按KOL分目录保存详情
        for kol in TARGET_KOLS:
            kol_id = kol['kol_id']
            kol_videos = [v for v in videos if v['kol_id'] == kol_id]
            
            if not kol_videos:
                continue
            
            kol_dir = OUTPUT_DIR / f"kol_{kol_id}"
            details_dir = kol_dir / "details"
            details_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存KOL信息
            kol_info = {
                'kol_id': kol_id,
                'kol_name': kol['name'],
                'video_count': len(kol_videos),
                'videos_with_url': sum(1 for v in kol_videos if v['video_url'])
            }
            with open(kol_dir / "info.json", 'w', encoding='utf-8') as f:
                json.dump(kol_info, f, ensure_ascii=False, indent=2)
            
            # 保存每个视频详情
            for v in kol_videos:
                detail_file = details_dir / f"{v['note_id']}.json"
                with open(detail_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'note_id': v['note_id'],
                        'title': v['title'],
                        'video_url': v['video_url'],
                        'content': v.get('content', ''),
                        'img_url': v['img_url'],
                        'publish_date': v['publish_date'],
                        'read_num': v['read_num'],
                        'like_num': v['like_num'],
                        'collect_num': v['collect_num'],
                        'total_interact': v['total_interact'],
                        'rank': v['rank'],
                        'detail_data': v['detail_data']
                    }, f, ensure_ascii=False, indent=2)
    
    def _print_summary(self, videos: List[Dict]):
        """打印汇总"""
        total = len(videos)
        with_url = sum(1 for v in videos if v['video_url'])
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("📋 视频详情获取汇总")
        logger.info("=" * 60)
        logger.info(f"总视频数: {total}")
        logger.info(f"成功获取URL: {with_url} ({with_url/total*100:.1f}%)")
        logger.info(f"未获取URL: {total - with_url}")
        logger.info("")
        
        # 按KOL统计
        logger.info("按KOL统计:")
        for kol in TARGET_KOLS:
            kol_videos = [v for v in videos if v['kol_id'] == kol['kol_id']]
            kol_with_url = sum(1 for v in kol_videos if v['video_url'])
            status = "✅" if kol_with_url == len(kol_videos) else "⚠️"
            logger.info(f"  {status} {kol['name']}: {kol_with_url}/{len(kol_videos)}")


async def main():
    """主函数"""
    fetcher = VideoDetailFetcher()
    await fetcher.fetch_all()


if __name__ == "__main__":
    asyncio.run(main())
