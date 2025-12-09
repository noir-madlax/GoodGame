#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取用户笔记列表（包含评论数）

使用小红书原生接口: /api/xiaohongshu/get-user-note-list/v4
获取的数据包含:
- likes: 点赞数
- collected_count: 收藏数  
- comments_count: 评论数 ✅ (蒲公英接口缺少的关键字段)
- share_count: 分享数

用途: 补充蒲公英 kol_note_list API 缺少的评论数字段
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
backend_dir = Path(__file__).parent.parent.parent.parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

# API 配置 - 使用国内服务器提高稳定性
API_BASE_URL = os.getenv('JUSTONEAPI_BASE_URL', 'http://47.117.133.51:30015')
TOKEN = os.getenv('JUSTONEAPI_API_KEY', '')

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "user_note_list_with_comments"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class UserNoteListFetcher:
    """用户笔记列表获取器（包含评论数）"""
    
    def __init__(self, concurrency: int = 5, delay: float = 0.5):
        self.concurrency = concurrency
        self.delay = delay
        self.token = TOKEN
        self.base_url = API_BASE_URL
        self.semaphore = asyncio.Semaphore(concurrency)
        
    async def fetch_user_notes(
        self, 
        session: aiohttp.ClientSession, 
        user_id: str,
        max_pages: int = 5
    ) -> Dict[str, Any]:
        """
        获取单个用户的所有笔记（分页获取）
        
        Args:
            session: aiohttp 会话
            user_id: 用户ID (与 kolId 相同)
            max_pages: 最大获取页数
            
        Returns:
            包含所有笔记的字典
        """
        all_notes = []
        last_cursor = None
        page = 0
        
        while page < max_pages:
            async with self.semaphore:
                url = f"{self.base_url}/api/xiaohongshu/get-user-note-list/v4"
                params = {
                    'token': self.token,
                    'userId': user_id,
                }
                if last_cursor:
                    params['lastCursor'] = last_cursor
                
                try:
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=60)) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if result.get('code') == 0:
                                data = result.get('data', {})
                                notes = data.get('notes', [])
                                has_more = data.get('has_more', False)
                                
                                if notes:
                                    all_notes.extend(notes)
                                    # 获取最后一条笔记的 cursor 用于翻页
                                    last_cursor = notes[-1].get('cursor') or notes[-1].get('id')
                                    logger.info(f"  第 {page + 1} 页: 获取 {len(notes)} 篇笔记")
                                
                                if not has_more or not notes:
                                    break
                            else:
                                logger.warning(f"  API 返回错误: {result.get('message')}")
                                break
                        else:
                            logger.error(f"  HTTP 错误: {response.status}")
                            break
                            
                except asyncio.TimeoutError:
                    logger.error(f"  请求超时")
                    break
                except Exception as e:
                    logger.error(f"  请求异常: {e}")
                    break
                
                # 延迟
                await asyncio.sleep(self.delay)
                page += 1
        
        return {
            'user_id': user_id,
            'total_notes': len(all_notes),
            'notes': all_notes
        }
    
    def extract_note_stats(self, notes: List[Dict]) -> Dict[str, Any]:
        """
        从笔记列表提取统计数据
        
        Args:
            notes: 笔记列表
            
        Returns:
            统计数据
        """
        if not notes:
            return {}
        
        # 提取各项数据
        likes_list = [n.get('likes', 0) for n in notes]
        collect_list = [n.get('collected_count', 0) for n in notes]
        comment_list = [n.get('comments_count', 0) for n in notes]
        share_list = [n.get('share_count', 0) for n in notes]
        
        def calc_stats(data_list):
            if not data_list:
                return {'avg': 0, 'median': 0, 'sum': 0, 'count': 0}
            sorted_list = sorted(data_list)
            n = len(sorted_list)
            median = sorted_list[n // 2] if n % 2 == 1 else (sorted_list[n // 2 - 1] + sorted_list[n // 2]) / 2
            return {
                'avg': round(sum(data_list) / len(data_list), 2),
                'median': median,
                'sum': sum(data_list),
                'count': len(data_list)
            }
        
        # 按日期筛选最近一个月的笔记
        recent_notes = []
        now = datetime.now()
        for note in notes:
            # 尝试从 time_desc 或 create_time 解析时间
            create_time = note.get('create_time')
            if create_time:
                note_date = datetime.fromtimestamp(create_time)
                days_ago = (now - note_date).days
                if days_ago <= 30:
                    recent_notes.append(note)
        
        recent_comment_list = [n.get('comments_count', 0) for n in recent_notes]
        recent_likes_list = [n.get('likes', 0) for n in recent_notes]
        recent_collect_list = [n.get('collected_count', 0) for n in recent_notes]
        
        # 统计评论 > 20 的笔记
        notes_with_high_comments = [n for n in notes if n.get('comments_count', 0) > 20]
        
        return {
            'all_time': {
                'likes': calc_stats(likes_list),
                'collects': calc_stats(collect_list),
                'comments': calc_stats(comment_list),
                'shares': calc_stats(share_list),
                'total_notes': len(notes)
            },
            'recent_30_days': {
                'likes': calc_stats(recent_likes_list),
                'collects': calc_stats(recent_collect_list),
                'comments': calc_stats(recent_comment_list),
                'total_notes': len(recent_notes)
            },
            'high_comment_notes': {
                'count': len(notes_with_high_comments),
                'notes': [
                    {
                        'id': n.get('id'),
                        'title': n.get('title', n.get('display_title', ''))[:50],
                        'comments_count': n.get('comments_count', 0),
                        'likes': n.get('likes', 0)
                    }
                    for n in notes_with_high_comments[:10]  # 最多显示10篇
                ]
            },
            'note_details': [
                {
                    'id': n.get('id'),
                    'title': n.get('title', n.get('display_title', ''))[:50],
                    'type': n.get('type'),
                    'likes': n.get('likes', 0),
                    'collected_count': n.get('collected_count', 0),
                    'comments_count': n.get('comments_count', 0),
                    'share_count': n.get('share_count', 0),
                    'time_desc': n.get('time_desc', ''),
                    'create_time': n.get('create_time')
                }
                for n in notes
            ]
        }


async def fetch_kol_note_stats(user_id: str, user_name: str = "unknown") -> Dict[str, Any]:
    """
    获取单个 KOL 的笔记统计数据
    
    Args:
        user_id: 用户ID (与 kolId 相同)
        user_name: 用户名
        
    Returns:
        统计数据
    """
    logger.info(f"开始获取 KOL: {user_name} ({user_id})")
    
    fetcher = UserNoteListFetcher()
    
    async with aiohttp.ClientSession() as session:
        result = await fetcher.fetch_user_notes(session, user_id)
        
        if result['total_notes'] > 0:
            stats = fetcher.extract_note_stats(result['notes'])
            stats['user_id'] = user_id
            stats['user_name'] = user_name
            stats['fetch_time'] = datetime.now().isoformat()
            
            # 保存结果
            output_file = OUTPUT_DIR / f"kol_{user_id}_note_stats.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 保存到: {output_file}")
            
            return stats
        else:
            logger.warning(f"❌ 未获取到笔记数据")
            return {}


async def batch_fetch_kol_stats(kol_list: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    批量获取 KOL 笔记统计数据
    
    Args:
        kol_list: KOL 列表 [{'user_id': 'xxx', 'user_name': 'xxx'}, ...]
        
    Returns:
        所有 KOL 的统计数据列表
    """
    results = []
    
    for kol in kol_list:
        user_id = kol.get('user_id') or kol.get('kol_id')
        user_name = kol.get('user_name') or kol.get('kol_name', 'unknown')
        
        if user_id:
            stats = await fetch_kol_note_stats(user_id, user_name)
            if stats:
                results.append(stats)
            
            # 每个 KOL 之间稍微延迟
            await asyncio.sleep(1)
    
    return results


def main():
    """主函数 - 示例用法"""
    if not TOKEN:
        print("❌ 未配置 JUSTONEAPI_API_KEY")
        return
    
    print("=" * 60)
    print("获取用户笔记列表（包含评论数）")
    print("使用接口: /api/xiaohongshu/get-user-note-list/v4")
    print("=" * 60)
    
    # 测试用户列表
    test_kols = [
        {"user_id": "6635f4b000000000030333dc", "user_name": "夏意意"},
        {"user_id": "5b46eef84eacab53c36cbb73", "user_name": "大力小鱼"},
        {"user_id": "599534e26a6a694603f84a90", "user_name": "七七芋泥包"},
    ]
    
    results = asyncio.run(batch_fetch_kol_stats(test_kols))
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("📊 统计汇总")
    print("=" * 60)
    
    for stats in results:
        print(f"\n【{stats.get('user_name')}】")
        all_time = stats.get('all_time', {})
        recent = stats.get('recent_30_days', {})
        high_comment = stats.get('high_comment_notes', {})
        
        print(f"  全部笔记: {all_time.get('total_notes', 0)} 篇")
        print(f"  近30天笔记: {recent.get('total_notes', 0)} 篇")
        print(f"  评论中位数: {all_time.get('comments', {}).get('median', 0)}")
        print(f"  评论平均值: {all_time.get('comments', {}).get('avg', 0)}")
        print(f"  点赞中位数: {all_time.get('likes', {}).get('median', 0)}")
        print(f"  评论>20条的笔记: {high_comment.get('count', 0)} 篇")
        
        if high_comment.get('notes'):
            print(f"  高评论笔记:")
            for note in high_comment['notes'][:3]:
                print(f"    - {note['title']}: {note['comments_count']}条评论")


if __name__ == "__main__":
    main()
