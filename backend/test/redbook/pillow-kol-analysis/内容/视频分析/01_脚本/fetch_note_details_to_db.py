#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量获取笔记详情并存入数据库

功能：
1. 从数据库获取146个目标视频的note_id
2. 调用note_detail_solar接口获取详情
3. 将详情更新到gg_pgy_kol_notes.raw_data字段
4. 标记detail_fetched为true
5. 下载视频文件到本地目录
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


class NoteDetailFetcher:
    """笔记详情获取器"""
    
    # CDN域名列表（用于下载视频）
    CDN_DOMAINS = [
        'v.xiaohongshu.com',
        'sns-video-bd.xhscdn.com',
        'sns-video-hw.xhscdn.com', 
        'sns-video-qc.xhscdn.com',
        'sns-video-al.xhscdn.com',
    ]
    
    def __init__(self, concurrency: int = 5, api_delay: float = 0.5):
        self.concurrency = concurrency
        self.api_delay = api_delay
        self.token = os.getenv('JUSTONEAPI_API_KEY', '')
        self.base_url = "https://api.justoneapi.com"
        self.semaphore = asyncio.Semaphore(concurrency)
        self.download_semaphore = asyncio.Semaphore(3)
        
        # 加载API配置
        config_path = BACKEND_DIR / "test/redbook/pgy/params/config.json"
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.endpoints = self.config['接口列表']
        
        # 统计
        self.stats = {
            'total': 0,
            'fetched': 0,
            'failed': 0,
            'db_updated': 0,
            'downloaded': 0,
            'download_failed': 0
        }
    
    def _get_supabase_client(self):
        """获取Supabase客户端"""
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        return create_client(url, key)
    
    def get_target_notes(self) -> List[Dict]:
        """获取目标笔记列表（32位入选KOL的TOP5视频）"""
        client = self._get_supabase_client()
        
        # 获取入选KOL
        kol_response = client.table('gg_pgy_kol_analysis_result').select(
            'kol_id, kol_name'
        ).eq('post_frequency_pass', True
        ).eq('comment_gt_20_pass', True
        ).eq('read_fans_ratio_pass', True
        ).execute()
        
        kol_map = {row['kol_id']: row['kol_name'] for row in kol_response.data}
        logger.info(f"获取到 {len(kol_map)} 位入选KOL")
        
        all_notes = []
        
        for kol_id, kol_name in kol_map.items():
            # 获取该KOL的视频笔记，按互动排序取TOP5
            # 优先获取detail_fetched=false的
            notes_response = client.table('gg_pgy_kol_notes').select(
                'id, note_id, kol_id, title, is_video, is_advertise, '
                'read_num, like_num, collect_num, comment_num, publish_date, img_url, detail_fetched'
            ).eq('kol_id', kol_id
            ).eq('is_video', True
            ).order('like_num', desc=True
            ).limit(5
            ).execute()
            
            if not notes_response.data:
                logger.warning(f"KOL {kol_name} 无视频")
                continue
            
            for note in notes_response.data:
                note['kol_name'] = kol_name
                all_notes.append(note)
        
        self.stats['total'] = len(all_notes)
        logger.info(f"共需处理 {len(all_notes)} 个视频")
        return all_notes
    
    async def fetch_note_detail(self, session: aiohttp.ClientSession, 
                                 note_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """获取笔记详情，返回(详情数据, 视频URL)"""
        async with self.semaphore:
            endpoint = self.endpoints.get('note_detail_solar')
            url = f"{self.base_url}{endpoint}"
            params = {
                'token': self.token,
                'noteId': note_id,
                'acceptCache': 'true'
            }
            
            try:
                async with session.get(url, params=params,
                                       timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get('code') == 0:
                            data = result.get('data', {})
                            video_url = None
                            video_info = data.get('videoInfo', {})
                            if video_info:
                                video_url = video_info.get('videoUrl')
                            return data, video_url
                        else:
                            code = result.get('code')
                            msg = result.get('message', '')
                            logger.warning(f"⚠️ {note_id}: code={code} {msg}")
                    else:
                        logger.error(f"❌ {note_id}: HTTP {resp.status}")
            except Exception as e:
                logger.error(f"❌ {note_id}: {e}")
            
            await asyncio.sleep(self.api_delay)
            return None, None
    
    def update_note_in_db(self, client, note_id: str, detail_data: Dict) -> bool:
        """更新数据库中的笔记详情"""
        try:
            # 从详情中提取关键字段
            update_data = {
                'raw_data': detail_data,
                'detail_fetched': True,
                'updated_at': datetime.now().isoformat()
            }
            
            # 如果有更多数据，也更新
            if detail_data.get('content'):
                pass  # raw_data中已包含
            if detail_data.get('shareNum'):
                update_data['share_num'] = detail_data['shareNum']
            if detail_data.get('impNum'):
                update_data['imp_num'] = detail_data['impNum']
            if detail_data.get('followCnt'):
                update_data['follow_cnt'] = detail_data['followCnt']
            
            client.table('gg_pgy_kol_notes').update(
                update_data
            ).eq('note_id', note_id).execute()
            
            return True
        except Exception as e:
            logger.error(f"数据库更新失败 {note_id}: {e}")
            return False
    
    async def download_video(self, session: aiohttp.ClientSession,
                              video_url: str, note_id: str, kol_id: str) -> Optional[str]:
        """下载视频文件，尝试多个CDN"""
        kol_dir = DATA_DIR / f"kol_{kol_id}" / "videos"
        kol_dir.mkdir(parents=True, exist_ok=True)
        video_file = kol_dir / f"{note_id}.mp4"
        
        # 已存在则跳过
        if video_file.exists() and video_file.stat().st_size > 10000:
            logger.info(f"⏭️ 已存在: {note_id}")
            return str(video_file)
        
        # 从原URL提取video_key
        video_key = None
        if 'xiaohongshu.com/' in video_url:
            # http://v.xiaohongshu.com/stream/79/110/258/xxx.mp4?sign=...
            path_part = video_url.split('?')[0]
            if '/stream/' in path_part:
                video_key = path_part.split('.com/')[1]
        
        # 构建候选URL列表
        urls_to_try = [video_url]  # 原URL优先
        if video_key:
            for domain in self.CDN_DOMAINS:
                cdn_url = f"http://{domain}/{video_key}"
                if cdn_url != video_url.split('?')[0]:
                    urls_to_try.append(cdn_url)
        
        async with self.download_semaphore:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Referer': 'https://www.xiaohongshu.com/'
            }
            
            for url in urls_to_try:
                try:
                    async with session.get(url, headers=headers,
                                          timeout=aiohttp.ClientTimeout(total=300)) as resp:
                        if resp.status == 200:
                            async with aiofiles.open(video_file, 'wb') as f:
                                total = 0
                                async for chunk in resp.content.iter_chunked(1024 * 1024):
                                    await f.write(chunk)
                                    total += len(chunk)
                            
                            if total > 10000:
                                logger.info(f"📥 下载完成: {note_id} ({total/1024/1024:.1f}MB)")
                                return str(video_file)
                            else:
                                video_file.unlink()
                except Exception as e:
                    logger.debug(f"CDN {url[:50]} 失败: {e}")
                    continue
            
            logger.warning(f"⚠️ 所有CDN都无法下载: {note_id}")
            return None
    
    async def process_note(self, session: aiohttp.ClientSession, 
                            client, note: Dict) -> Dict:
        """处理单个笔记：获取详情、更新数据库、下载视频"""
        note_id = note['note_id']
        kol_id = note['kol_id']
        kol_name = note.get('kol_name', 'Unknown')
        title = (note.get('title') or '')[:25]
        
        # 1. 获取详情
        detail_data, video_url = await self.fetch_note_detail(session, note_id)
        
        if detail_data:
            self.stats['fetched'] += 1
            
            # 2. 更新数据库
            if self.update_note_in_db(client, note_id, detail_data):
                self.stats['db_updated'] += 1
            
            # 3. 下载视频
            if video_url:
                file_path = await self.download_video(session, video_url, note_id, kol_id)
                if file_path:
                    self.stats['downloaded'] += 1
                    note['file_path'] = file_path
                    note['downloaded'] = True
                else:
                    self.stats['download_failed'] += 1
            
            logger.info(f"✅ {kol_name}: {title}...")
            note['video_url'] = video_url
            note['detail_fetched'] = True
        else:
            self.stats['failed'] += 1
            logger.warning(f"❌ {kol_name}: {note_id}")
        
        await asyncio.sleep(self.api_delay)
        return note
    
    def save_local_metadata(self, notes: List[Dict]):
        """保存本地元数据文件"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # 按KOL分组
        kol_notes = {}
        for n in notes:
            kol_id = n['kol_id']
            if kol_id not in kol_notes:
                kol_notes[kol_id] = []
            kol_notes[kol_id].append(n)
        
        for kol_id, notes_list in kol_notes.items():
            kol_dir = DATA_DIR / f"kol_{kol_id}"
            kol_dir.mkdir(parents=True, exist_ok=True)
            
            metadata = {
                'kol_id': kol_id,
                'kol_name': notes_list[0].get('kol_name', 'Unknown'),
                'video_count': len(notes_list),
                'videos': notes_list
            }
            
            with open(kol_dir / 'metadata.json', 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
        
        # 汇总文件
        summary = {
            'generated_at': datetime.now().isoformat(),
            'stats': self.stats,
            'total_kols': len(kol_notes),
            'total_videos': len(notes),
            'videos': notes
        }
        
        with open(DATA_DIR / 'video_list.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"📁 本地元数据已保存到: {DATA_DIR}")
    
    async def run(self):
        """执行完整流程"""
        logger.info("=" * 60)
        logger.info("开始批量获取笔记详情")
        logger.info("=" * 60)
        
        # 1. 获取目标笔记列表
        notes = self.get_target_notes()
        
        # 获取数据库客户端
        client = self._get_supabase_client()
        
        # 2. 创建connector避免session问题
        connector = aiohttp.TCPConnector(limit=10, force_close=True)
        
        # 3. 批量处理
        async with aiohttp.ClientSession(connector=connector) as session:
            batch_size = 5  # 减少批次大小
            for i in range(0, len(notes), batch_size):
                batch = notes[i:i+batch_size]
                logger.info(f"\n处理批次 {i//batch_size + 1}/{(len(notes)-1)//batch_size + 1}")
                
                # 串行处理每个笔记（更稳定）
                for j, note in enumerate(batch):
                    try:
                        result = await self.process_note(session, client, note)
                        notes[i+j] = result
                    except Exception as e:
                        logger.error(f"处理失败 {note.get('note_id')}: {e}")
                        self.stats['failed'] += 1
                
                # 每批次后暂停一下
                await asyncio.sleep(1)
        
        # 4. 保存本地元数据
        self.save_local_metadata(notes)
        
        # 5. 打印统计
        self._print_stats()
        
        return notes
    
    def _print_stats(self):
        """打印统计"""
        print("\n" + "=" * 60)
        print("处理完成")
        print("=" * 60)
        print(f"总笔记数: {self.stats['total']}")
        print(f"详情获取成功: {self.stats['fetched']}")
        print(f"详情获取失败: {self.stats['failed']}")
        print(f"数据库更新成功: {self.stats['db_updated']}")
        print(f"视频下载成功: {self.stats['downloaded']}")
        print(f"视频下载失败: {self.stats['download_failed']}")
        print("=" * 60)


async def main():
    """主函数"""
    fetcher = NoteDetailFetcher(concurrency=5, api_delay=0.5)
    await fetcher.run()


if __name__ == "__main__":
    asyncio.run(main())
