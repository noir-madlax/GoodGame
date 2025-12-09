#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量获取 KOL 笔记列表（包含评论数）

使用接口: /api/xiaohongshu/get-user-note-list/v4
- 只获取近 3 个月的数据
- 并发 20 个请求
- 跳过已获取的 KOL
- 每次请求打印日志
- 每个 KOL 获取后立即保存
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Set
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 加载环境变量 - 使用绝对路径确保正确加载
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

# API 配置 - 使用国内服务器
API_BASE_URL = os.getenv('JUSTONEAPI_BASE_URL', 'http://47.117.133.51:30015')
TOKEN = os.getenv('JUSTONEAPI_API_KEY', '')

# 目录配置
CURRENT_DIR = Path(__file__).parent
API_DATA_DIR = CURRENT_DIR / "output" / "api_data"
OUTPUT_DIR = CURRENT_DIR / "output" / "note_comments"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 记录已请求过的 KOL（包括失败的），避免重复请求
FETCHED_RECORD_FILE = OUTPUT_DIR / "fetched_record.json"

# 时间限制：只获取近 3 个月的数据，超过3个月停止翻页
THREE_MONTHS_AGO = datetime.now() - timedelta(days=90)


class BatchNoteFetcher:
    """批量笔记获取器"""
    
    def __init__(self, concurrency: int = 20, delay: float = 0.3):
        self.concurrency = concurrency
        self.delay = delay
        self.token = TOKEN
        self.base_url = API_BASE_URL
        self.semaphore = asyncio.Semaphore(concurrency)
        
        # 统计
        self.success_count = 0
        self.skip_count = 0
        self.fail_count = 0
        self.total_notes = 0
        
    def get_all_kol_ids(self) -> List[str]:
        """从 fetched_kols.json 获取所有 KOL ID"""
        fetched_file = API_DATA_DIR / "fetched_kols.json"
        if not fetched_file.exists():
            logger.error(f"找不到 fetched_kols.json")
            return []
        
        with open(fetched_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return list(data.keys())
    
    def get_fetched_kol_ids(self) -> Set[str]:
        """获取已经获取过笔记评论数据的 KOL ID"""
        fetched = set()
        
        # 检查 note_comments 目录
        for file in OUTPUT_DIR.glob("kol_*_notes.json"):
            # 文件名格式: kol_{kol_id}_notes.json
            kol_id = file.stem.replace("kol_", "").replace("_notes", "")
            fetched.add(kol_id)
        
        # 也检查之前测试目录的数据
        test_dir = Path(__file__).parent.parent / "pgy" / "output" / "user_note_list_with_comments"
        if test_dir.exists():
            for file in test_dir.glob("kol_*_note_stats.json"):
                kol_id = file.stem.replace("kol_", "").replace("_note_stats", "")
                fetched.add(kol_id)
        
        return fetched
    
    async def fetch_kol_notes(
        self, 
        session: aiohttp.ClientSession, 
        kol_id: str,
        kol_index: int,
        total_kols: int
    ) -> Dict[str, Any]:
        """
        获取单个 KOL 的笔记列表
        
        只获取近 3 个月的数据，超过 6 个月的停止获取
        """
        all_notes = []
        last_cursor = None
        page = 0
        max_pages = 10  # 最多获取 10 页
        should_stop = False
        
        async with self.semaphore:
            while page < max_pages and not should_stop:
                url = f"{self.base_url}/api/xiaohongshu/get-user-note-list/v4"
                params = {
                    'token': self.token,
                    'userId': kol_id,
                }
                if last_cursor:
                    params['lastCursor'] = last_cursor
                
                try:
                    async with session.get(
                        url, 
                        params=params, 
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if result.get('code') == 0:
                                data = result.get('data', {})
                                notes = data.get('notes', [])
                                has_more = data.get('has_more', False)
                                
                                if notes:
                                    # 过滤近 3 个月的笔记
                                    # 注意：置顶帖可能时间较老，不能以第一条帖子来判断停止
                                    filtered_notes = []
                                    oldest_non_sticky_date = None
                                    
                                    for note in notes:
                                        create_time = note.get('create_time')
                                        is_sticky = note.get('sticky', False)
                                        
                                        if create_time:
                                            note_date = datetime.fromtimestamp(create_time)
                                            
                                            # 只保留近 3 个月的
                                            if note_date >= THREE_MONTHS_AGO:
                                                filtered_notes.append({
                                                    'id': note.get('id'),
                                                    'title': note.get('title', note.get('display_title', ''))[:100],
                                                    'type': note.get('type'),
                                                    'likes': note.get('likes', 0),
                                                    'collected_count': note.get('collected_count', 0),
                                                    'comments_count': note.get('comments_count', 0),
                                                    'share_count': note.get('share_count', 0),
                                                    'time_desc': note.get('time_desc', ''),
                                                    'create_time': create_time,
                                                    'create_date': note_date.strftime('%Y-%m-%d'),
                                                    'sticky': is_sticky
                                                })
                                            
                                            # 用非置顶帖的最老时间来判断是否停止翻页
                                            if not is_sticky:
                                                if oldest_non_sticky_date is None or note_date < oldest_non_sticky_date:
                                                    oldest_non_sticky_date = note_date
                                    
                                    # 如果非置顶帖的最老时间超过3个月，停止翻页
                                    if oldest_non_sticky_date and oldest_non_sticky_date < THREE_MONTHS_AGO:
                                        should_stop = True
                                    
                                    all_notes.extend(filtered_notes)
                                    
                                    # 获取下一页游标
                                    last_cursor = notes[-1].get('cursor') or notes[-1].get('id')
                                    
                                    logger.debug(f"  [{kol_index}/{total_kols}] {kol_id} 第{page+1}页: 获取{len(notes)}篇, 保留{len(filtered_notes)}篇")
                                
                                if not has_more or not notes or should_stop:
                                    break
                            else:
                                logger.warning(f"  [{kol_index}/{total_kols}] {kol_id} API错误: {result.get('message')}")
                                break
                        else:
                            logger.error(f"  [{kol_index}/{total_kols}] {kol_id} HTTP错误: {response.status}")
                            break
                            
                except asyncio.TimeoutError:
                    logger.error(f"  [{kol_index}/{total_kols}] {kol_id} 请求超时")
                    break
                except Exception as e:
                    logger.error(f"  [{kol_index}/{total_kols}] {kol_id} 异常: {e}")
                    break
                
                await asyncio.sleep(self.delay)
                page += 1
        
        return {
            'kol_id': kol_id,
            'fetch_time': datetime.now().isoformat(),
            'total_notes': len(all_notes),
            'notes': all_notes
        }
    
    def calculate_stats(self, notes: List[Dict]) -> Dict[str, Any]:
        """计算统计数据"""
        if not notes:
            return {}
        
        likes = [n.get('likes', 0) for n in notes]
        collects = [n.get('collected_count', 0) for n in notes]
        comments = [n.get('comments_count', 0) for n in notes]
        shares = [n.get('share_count', 0) for n in notes]
        
        def calc(data):
            if not data:
                return {'avg': 0, 'median': 0, 'sum': 0, 'count': 0}
            sorted_data = sorted(data)
            n = len(sorted_data)
            median = sorted_data[n // 2] if n % 2 == 1 else (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
            return {
                'avg': round(sum(data) / len(data), 2),
                'median': median,
                'sum': sum(data),
                'count': len(data)
            }
        
        high_comment_notes = [n for n in notes if n.get('comments_count', 0) > 20]
        
        return {
            'stats': {
                'likes': calc(likes),
                'collects': calc(collects),
                'comments': calc(comments),
                'shares': calc(shares)
            },
            'high_comment_count': len(high_comment_notes),
            'high_comment_notes': [
                {'id': n['id'], 'title': n['title'][:30], 'comments': n['comments_count']}
                for n in high_comment_notes[:5]
            ]
        }
    
    def save_result(self, kol_id: str, data: Dict[str, Any]):
        """保存结果"""
        output_file = OUTPUT_DIR / f"kol_{kol_id}_notes.json"
        
        # 添加统计数据
        if data.get('notes'):
            data['statistics'] = self.calculate_stats(data['notes'])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def process_kol(
        self, 
        session: aiohttp.ClientSession, 
        kol_id: str, 
        kol_index: int, 
        total_kols: int
    ):
        """处理单个 KOL"""
        start_time = time.time()
        
        result = await self.fetch_kol_notes(session, kol_id, kol_index, total_kols)
        
        elapsed = time.time() - start_time
        
        if result['total_notes'] > 0:
            self.save_result(kol_id, result)
            self.success_count += 1
            self.total_notes += result['total_notes']
            
            stats = result.get('statistics', {})
            high_comments = stats.get('high_comment_count', 0)
            
            logger.info(
                f"✅ [{kol_index}/{total_kols}] {kol_id}: "
                f"{result['total_notes']}篇笔记, "
                f"评论>20: {high_comments}篇, "
                f"耗时: {elapsed:.1f}s"
            )
        else:
            self.fail_count += 1
            logger.warning(f"⚠️ [{kol_index}/{total_kols}] {kol_id}: 无数据, 耗时: {elapsed:.1f}s")
    
    async def run(self):
        """运行批量获取"""
        logger.info("=" * 60)
        logger.info("开始批量获取 KOL 笔记数据（包含评论数）")
        logger.info(f"接口: /api/xiaohongshu/get-user-note-list/v4")
        logger.info(f"并发数: {self.concurrency}")
        logger.info(f"数据范围: 近3个月")
        logger.info("=" * 60)
        
        # 获取所有 KOL ID
        all_kol_ids = self.get_all_kol_ids()
        logger.info(f"总 KOL 数量: {len(all_kol_ids)}")
        
        # 获取已获取的 KOL ID
        fetched_kol_ids = self.get_fetched_kol_ids()
        logger.info(f"已获取数量: {len(fetched_kol_ids)}")
        
        # 筛选待获取的 KOL
        pending_kol_ids = [kid for kid in all_kol_ids if kid not in fetched_kol_ids]
        logger.info(f"待获取数量: {len(pending_kol_ids)}")
        
        if not pending_kol_ids:
            logger.info("所有 KOL 数据已获取完成！")
            return
        
        self.skip_count = len(fetched_kol_ids)
        total_kols = len(pending_kol_ids)
        
        logger.info("-" * 60)
        logger.info(f"开始获取 {total_kols} 个 KOL 的数据...")
        logger.info("-" * 60)
        
        start_time = time.time()
        
        # 创建任务
        connector = aiohttp.TCPConnector(limit=self.concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i, kol_id in enumerate(pending_kol_ids, 1):
                task = self.process_kol(session, kol_id, i, total_kols)
                tasks.append(task)
            
            # 执行所有任务
            await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # 打印汇总
        logger.info("=" * 60)
        logger.info("获取完成！")
        logger.info(f"  成功: {self.success_count}")
        logger.info(f"  失败: {self.fail_count}")
        logger.info(f"  跳过: {self.skip_count}")
        logger.info(f"  总笔记数: {self.total_notes}")
        logger.info(f"  总耗时: {total_time:.1f}s")
        logger.info(f"  输出目录: {OUTPUT_DIR}")
        logger.info("=" * 60)


def main():
    """主函数"""
    if not TOKEN:
        print("❌ 未配置 JUSTONEAPI_API_KEY")
        return
    
    fetcher = BatchNoteFetcher(concurrency=3, delay=0.5)
    asyncio.run(fetcher.run())


if __name__ == "__main__":
    main()
