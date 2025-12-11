#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段2: 获取基础筛选数据

功能：
1. 从kol_list.json读取已获取ID的KOL
2. 调用3个必要的筛选API:
   - kol_info: 基本信息、粉丝数、是否蒲公英博主
   - kol_note_rate: 笔记数据率（阅读/互动中位数）
   - kol_fans_trend: 粉丝趋势
3. 每个API调用后立即保存结果
4. 支持失败重试和断点续传
5. 实时显示进度

API调用估算: 15 KOL × 3 API = 45次
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


# ==================== 配置 ====================
CONFIG = {
    "api_base_url": "https://api.justoneapi.com",
    "concurrency": 7,  # 并发数
    "timeout": 30,
    "retry_count": 3,
    "retry_delay": 2,
    "api_delay": 0.5,  # 每次API调用间隔
    
    # 筛选阶段需要的3个API
    "screening_apis": {
        "kol_info": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-info/v1",
            "params": {"acceptCache": "true"}
        },
        "kol_note_rate": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-note-rate/v1",
            "params": {
                "dateType": "_1",      # 30天
                "noteType": "_3",       # 图文和视频
                "adSwitch": "_1",       # 全流量
                "business": "_0",       # 日常笔记
                "acceptCache": "true"
            }
        },
        "kol_fans_trend": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-fans-trend/v1",
            "params": {
                "dateType": "_1",       # 30天
                "increaseType": "_1",   # 粉丝总量
                "acceptCache": "true"
            }
        }
    }
}


@dataclass
class FetchProgress:
    """获取进度"""
    total_kols: int = 0
    completed_kols: int = 0
    total_apis: int = 0
    success_apis: int = 0
    failed_apis: int = 0
    skipped_apis: int = 0


class ScreeningDataFetcher:
    """筛选数据获取器"""
    
    def __init__(self):
        self.config = CONFIG
        self.token = self._load_api_token()
        self.base_url = self.config['api_base_url']
        self.output_dir = Path(__file__).parent / "01_基础筛选数据"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载KOL列表
        self.kol_list_file = Path(__file__).parent / "kol_list.json"
        self.kols = self._load_kol_list()
        
        # 进度跟踪
        self.progress = FetchProgress()
        
        # 已获取记录（用于断点续传）
        self.fetched_record_file = self.output_dir / "_fetched_record.json"
        self.fetched_record = self._load_fetched_record()
        
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
        
        # 只返回有kol_id的
        kols = data.get('kols', [])
        return [k for k in kols if k.get('kol_id')]
    
    def _load_fetched_record(self) -> Dict[str, Dict[str, bool]]:
        """加载已获取记录"""
        if self.fetched_record_file.exists():
            with open(self.fetched_record_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_fetched_record(self):
        """保存已获取记录"""
        with open(self.fetched_record_file, 'w', encoding='utf-8') as f:
            json.dump(self.fetched_record, f, ensure_ascii=False, indent=2)
    
    def _is_api_fetched(self, kol_id: str, api_name: str) -> bool:
        """检查某个API是否已获取"""
        return self.fetched_record.get(kol_id, {}).get(api_name, False)
    
    def _mark_api_fetched(self, kol_id: str, api_name: str, success: bool = True):
        """标记API已获取"""
        if kol_id not in self.fetched_record:
            self.fetched_record[kol_id] = {}
        self.fetched_record[kol_id][api_name] = success
        self._save_fetched_record()
    
    async def _call_api(self, session: aiohttp.ClientSession, endpoint: str, 
                        params: Dict[str, Any]) -> Dict[str, Any]:
        """调用单个API"""
        async with self.semaphore:
            url = f"{self.base_url}{endpoint}"
            params['token'] = self.token
            
            for attempt in range(self.config['retry_count']):
                try:
                    async with session.get(url, params=params,
                                          timeout=aiohttp.ClientTimeout(total=self.config['timeout'])) as response:
                        if response.status == 200:
                            result = await response.json()
                            await asyncio.sleep(self.config['api_delay'])
                            return result
                        else:
                            logger.warning(f"HTTP {response.status}")
                except asyncio.TimeoutError:
                    logger.warning(f"超时，重试 {attempt + 1}/{self.config['retry_count']}")
                except Exception as e:
                    logger.warning(f"错误: {e}，重试 {attempt + 1}/{self.config['retry_count']}")
                
                if attempt < self.config['retry_count'] - 1:
                    await asyncio.sleep(self.config['retry_delay'])
            
            return {"error": "API调用失败"}
    
    def _save_api_result(self, kol_id: str, kol_name: str, api_name: str, result: Dict[str, Any]):
        """保存单个API结果"""
        kol_dir = self.output_dir / f"kol_{kol_id}"
        kol_dir.mkdir(parents=True, exist_ok=True)
        
        result_file = kol_dir / f"{api_name}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "kol_id": kol_id,
                "kol_name": kol_name,
                "api_name": api_name,
                "fetch_time": datetime.now().isoformat(),
                "result": result
            }, f, ensure_ascii=False, indent=2)
    
    async def fetch_kol_screening_data(self, session: aiohttp.ClientSession, 
                                        kol: Dict[str, Any], index: int) -> Dict[str, Any]:
        """获取单个KOL的筛选数据"""
        kol_id = kol['kol_id']
        kol_name = kol['name']
        
        logger.info(f"[{index}/{self.progress.total_kols}] 获取: {kol_name} ({kol_id[:16]}...)")
        
        results = {}
        
        for api_name, api_config in self.config['screening_apis'].items():
            # 检查是否已获取
            if self._is_api_fetched(kol_id, api_name):
                logger.info(f"  ⏭️ {api_name}: 已获取，跳过")
                self.progress.skipped_apis += 1
                continue
            
            # 调用API
            params = {"kolId": kol_id}
            params.update(api_config['params'])
            
            result = await self._call_api(session, api_config['endpoint'], params)
            self.progress.total_apis += 1
            
            # 判断成功/失败
            if 'error' in result:
                logger.error(f"  ❌ {api_name}: {result['error']}")
                self.progress.failed_apis += 1
                self._mark_api_fetched(kol_id, api_name, False)
            else:
                code = result.get('code', -1)
                if code == 0:
                    logger.info(f"  ✅ {api_name}: 成功")
                    self.progress.success_apis += 1
                    self._mark_api_fetched(kol_id, api_name, True)
                else:
                    logger.warning(f"  ⚠️ {api_name}: code={code}, msg={result.get('message', '')}")
                    self.progress.failed_apis += 1
                    self._mark_api_fetched(kol_id, api_name, False)
            
            # 立即保存结果
            self._save_api_result(kol_id, kol_name, api_name, result)
            results[api_name] = result
        
        self.progress.completed_kols += 1
        
        # 显示进度
        total_api_calls = self.progress.success_apis + self.progress.failed_apis + self.progress.skipped_apis
        logger.info(f"  📊 进度: {self.progress.completed_kols}/{self.progress.total_kols} KOL | "
                   f"API调用: {total_api_calls} (成功:{self.progress.success_apis} 失败:{self.progress.failed_apis} 跳过:{self.progress.skipped_apis})")
        
        return results
    
    async def fetch_all(self, limit: int = None):
        """获取所有KOL的筛选数据"""
        kols = self.kols
        if limit:
            kols = kols[:limit]
        
        if not kols:
            logger.warning("没有可获取的KOL（请先运行阶段1获取KOL ID）")
            return
        
        self.progress.total_kols = len(kols)
        expected_api_calls = len(kols) * len(self.config['screening_apis'])
        
        logger.info("=" * 60)
        logger.info(f"🚀 阶段2: 获取基础筛选数据")
        logger.info("=" * 60)
        logger.info(f"KOL数量: {len(kols)}")
        logger.info(f"每KOL API数: {len(self.config['screening_apis'])}")
        logger.info(f"预计API调用: {expected_api_calls}次")
        logger.info(f"并发数: {self.config['concurrency']}")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info("=" * 60)
        
        async with aiohttp.ClientSession() as session:
            for i, kol in enumerate(kols, 1):
                await self.fetch_kol_screening_data(session, kol, i)
        
        self._print_summary()
        self._generate_summary_report()
    
    def _print_summary(self):
        """打印汇总"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("📋 阶段2完成汇总")
        logger.info("=" * 60)
        logger.info(f"KOL总数: {self.progress.total_kols}")
        logger.info(f"完成KOL: {self.progress.completed_kols}")
        logger.info(f"API成功: {self.progress.success_apis}")
        logger.info(f"API失败: {self.progress.failed_apis}")
        logger.info(f"API跳过: {self.progress.skipped_apis}")
        logger.info(f"数据目录: {self.output_dir}")
    
    def _generate_summary_report(self):
        """生成汇总报告"""
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_kols": self.progress.total_kols,
            "api_stats": {
                "success": self.progress.success_apis,
                "failed": self.progress.failed_apis,
                "skipped": self.progress.skipped_apis
            },
            "kols": []
        }
        
        # 遍历每个KOL的数据
        for kol in self.kols[:self.progress.total_kols]:
            kol_id = kol['kol_id']
            kol_name = kol['name']
            kol_dir = self.output_dir / f"kol_{kol_id}"
            
            kol_summary = {
                "kol_id": kol_id,
                "kol_name": kol_name,
                "apis": {}
            }
            
            # 读取每个API的结果
            for api_name in self.config['screening_apis'].keys():
                result_file = kol_dir / f"{api_name}.json"
                if result_file.exists():
                    with open(result_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    result = data.get('result', {})
                    code = result.get('code', -1)
                    kol_summary['apis'][api_name] = {
                        "success": code == 0,
                        "code": code
                    }
                    
                    # 提取关键数据
                    if api_name == 'kol_info' and code == 0:
                        info = result.get('data', {})
                        kol_summary['fans_count'] = info.get('fansCount')
                        kol_summary['total_note_count'] = info.get('totalNoteCount')
                        kol_summary['kol_name_api'] = info.get('name')
                        kol_summary['is_pgy_kol'] = True
                    elif api_name == 'kol_info' and code != 0:
                        kol_summary['is_pgy_kol'] = False
                    
                    if api_name == 'kol_note_rate' and code == 0:
                        rate = result.get('data', {})
                        kol_summary['read_median'] = rate.get('readMedian')
                        kol_summary['interaction_median'] = rate.get('interactionMedian')
                        kol_summary['note_number'] = rate.get('noteNumber')
            
            summary['kols'].append(kol_summary)
        
        # 保存汇总
        summary_file = self.output_dir / "_screening_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📊 汇总报告已保存: {summary_file}")
        
        # 打印简要汇总
        logger.info("\n📊 KOL基础数据概览:")
        logger.info("-" * 80)
        logger.info(f"{'名称':<20} {'蒲公英':<8} {'粉丝数':<12} {'阅读中位数':<12} {'互动中位数':<12}")
        logger.info("-" * 80)
        
        for kol in summary['kols']:
            name = kol['kol_name'][:18]
            is_pgy = "✅" if kol.get('is_pgy_kol') else "❌"
            fans = kol.get('fans_count', '-')
            read = kol.get('read_median', '-')
            interact = kol.get('interaction_median', '-')
            
            if isinstance(fans, int):
                fans = f"{fans:,}"
            if isinstance(read, int):
                read = f"{read:,}"
            if isinstance(interact, int):
                interact = f"{interact:,}"
            
            logger.info(f"{name:<20} {is_pgy:<8} {str(fans):<12} {str(read):<12} {str(interact):<12}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='获取KOL基础筛选数据')
    parser.add_argument('--limit', type=int, default=None, help='限制获取数量（测试用）')
    parser.add_argument('--test', action='store_true', help='测试模式，只获取前3个')
    args = parser.parse_args()
    
    limit = 3 if args.test else args.limit
    
    fetcher = ScreeningDataFetcher()
    await fetcher.fetch_all(limit=limit)


if __name__ == "__main__":
    asyncio.run(main())
