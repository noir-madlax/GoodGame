#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段1: 获取KOL ID

功能：
1. 通过小红书搜索API根据KOL昵称搜索用户
2. 返回匹配的用户ID
3. 每个搜索结果立即保存
4. 显示进度和结果

API: /api/xiaohongshu/search-user/v2
参数: keyword, page
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


# ==================== 配置 ====================
CONFIG = {
    "api_base_url": "https://api.justoneapi.com",
    "search_endpoint": "/api/xiaohongshu/search-user/v2",
    "concurrency": 5,  # 搜索并发数
    "timeout": 30,
    "retry_count": 3,
    "retry_delay": 2,
    "api_delay": 0.5,  # 每次API调用间隔
}


class KolIdFetcher:
    """KOL ID获取器"""
    
    def __init__(self):
        self.config = CONFIG
        self.token = self._load_api_token()
        self.base_url = self.config['api_base_url']
        self.output_dir = Path(__file__).parent / "search_results"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载KOL列表
        self.kol_list_file = Path(__file__).parent / "kol_list.json"
        self.kols = self._load_kol_list()
        
        # 统计
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "api_calls": 0
        }
        
        # 信号量控制并发
        self.semaphore = asyncio.Semaphore(self.config['concurrency'])
    
    def _load_api_token(self) -> str:
        """从环境变量加载 Just One API Token"""
        backend_dir = Path(__file__).parent.parent.parent.parent.parent
        env_path = backend_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
        
        token = os.getenv('JUSTONEAPI_API_KEY', '')
        if not token:
            raise ValueError("请在 .env 文件中配置 JUSTONEAPI_API_KEY")
        return token
    
    def _load_kol_list(self) -> List[Dict[str, Any]]:
        """加载KOL列表"""
        if not self.kol_list_file.exists():
            raise FileNotFoundError(f"KOL列表文件不存在: {self.kol_list_file}")
        
        with open(self.kol_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('kols', [])
    
    def _save_kol_list(self, kols: List[Dict[str, Any]]):
        """保存KOL列表"""
        with open(self.kol_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data['kols'] = kols
        data['updated_at'] = datetime.now().isoformat()
        
        with open(self.kol_list_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def _search_user(self, session: aiohttp.ClientSession, keyword: str) -> Dict[str, Any]:
        """搜索用户"""
        async with self.semaphore:
            url = f"{self.base_url}{self.config['search_endpoint']}"
            params = {
                'token': self.token,
                'keyword': keyword,
                'page': 1
            }
            
            self.stats['api_calls'] += 1
            
            for attempt in range(self.config['retry_count']):
                try:
                    async with session.get(url, params=params, 
                                          timeout=aiohttp.ClientTimeout(total=self.config['timeout'])) as response:
                        if response.status == 200:
                            result = await response.json()
                            await asyncio.sleep(self.config['api_delay'])
                            return result
                        else:
                            logger.warning(f"搜索 '{keyword}' HTTP {response.status}")
                except asyncio.TimeoutError:
                    logger.warning(f"搜索 '{keyword}' 超时，重试 {attempt + 1}/{self.config['retry_count']}")
                except Exception as e:
                    logger.warning(f"搜索 '{keyword}' 错误: {e}，重试 {attempt + 1}/{self.config['retry_count']}")
                
                if attempt < self.config['retry_count'] - 1:
                    await asyncio.sleep(self.config['retry_delay'])
            
            return {"error": f"搜索失败: {keyword}"}
    
    def _find_best_match(self, keyword: str, search_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从搜索结果中找到最匹配的用户"""
        if search_result.get('code') != 0:
            return None
        
        users = search_result.get('data', {}).get('user_list', [])
        if not users:
            # 尝试其他数据结构
            users = search_result.get('data', {}).get('users', [])
        if not users:
            users = search_result.get('data', [])
        
        if not users:
            return None
        
        # 精确匹配优先
        for user in users:
            nickname = user.get('nickname') or user.get('name') or ''
            if nickname == keyword:
                return user
        
        # 包含匹配
        for user in users:
            nickname = user.get('nickname') or user.get('name') or ''
            if keyword in nickname or nickname in keyword:
                return user
        
        # 返回第一个结果
        return users[0] if users else None
    
    async def search_single_kol(self, session: aiohttp.ClientSession, kol: Dict[str, Any], index: int) -> Dict[str, Any]:
        """搜索单个KOL"""
        name = kol['name']
        
        logger.info(f"[{index}/{self.stats['total']}] 搜索: {name}")
        
        result = await self._search_user(session, name)
        
        # 保存原始搜索结果
        result_file = self.output_dir / f"search_{index:02d}_{name}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "keyword": name,
                "search_time": datetime.now().isoformat(),
                "result": result
            }, f, ensure_ascii=False, indent=2)
        
        # 解析结果
        if 'error' in result:
            logger.error(f"  ❌ 搜索失败: {result['error']}")
            kol['status'] = '搜索失败'
            self.stats['failed'] += 1
            return kol
        
        matched_user = self._find_best_match(name, result)
        
        if matched_user:
            user_id = matched_user.get('user_id') or matched_user.get('id') or matched_user.get('userId')
            nickname = matched_user.get('nickname') or matched_user.get('name')
            fans_count = matched_user.get('fans') or matched_user.get('fansCount') or matched_user.get('fans_count')
            
            kol['kol_id'] = user_id
            kol['matched_nickname'] = nickname
            kol['fans_count_search'] = fans_count
            kol['status'] = '已获取ID'
            self.stats['success'] += 1
            
            logger.info(f"  ✅ 找到: {nickname} (ID: {user_id}, 粉丝: {fans_count})")
        else:
            kol['status'] = '未找到匹配'
            self.stats['failed'] += 1
            logger.warning(f"  ⚠️ 未找到匹配用户")
        
        return kol
    
    async def search_all(self, limit: int = None):
        """搜索所有KOL"""
        kols = self.kols
        if limit:
            kols = kols[:limit]
        
        self.stats['total'] = len(kols)
        
        logger.info("=" * 60)
        logger.info(f"🔍 开始搜索 {len(kols)} 个KOL的ID")
        logger.info(f"   并发数: {self.config['concurrency']}")
        logger.info("=" * 60)
        
        async with aiohttp.ClientSession() as session:
            for i, kol in enumerate(kols, 1):
                # 跳过已有ID的
                if kol.get('kol_id'):
                    logger.info(f"[{i}/{self.stats['total']}] 跳过已有ID: {kol['name']}")
                    continue
                
                await self.search_single_kol(session, kol, i)
                
                # 每个搜索后保存列表
                self._save_kol_list(self.kols)
        
        self._print_summary()
    
    def _print_summary(self):
        """打印汇总"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("📋 搜索完成汇总")
        logger.info("=" * 60)
        logger.info(f"总数: {self.stats['total']}")
        logger.info(f"成功: {self.stats['success']}")
        logger.info(f"失败: {self.stats['failed']}")
        logger.info(f"API调用: {self.stats['api_calls']}")
        logger.info(f"结果保存: {self.output_dir}")
        
        # 显示结果详情
        logger.info("")
        logger.info("📊 KOL ID获取结果:")
        for kol in self.kols:
            status = "✅" if kol.get('kol_id') else "❌"
            kol_id = kol.get('kol_id', '-')[:16] + '...' if kol.get('kol_id') and len(kol.get('kol_id', '')) > 16 else kol.get('kol_id', '-')
            logger.info(f"  {status} {kol['name']}: {kol_id}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='搜索获取KOL ID')
    parser.add_argument('--limit', type=int, default=None, help='限制搜索数量（测试用）')
    parser.add_argument('--test', action='store_true', help='测试模式，只搜索前3个')
    args = parser.parse_args()
    
    limit = 3 if args.test else args.limit
    
    fetcher = KolIdFetcher()
    await fetcher.search_all(limit=limit)


if __name__ == "__main__":
    asyncio.run(main())
