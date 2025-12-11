#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段4: 获取详细数据

功能：
1. 从筛选结果中读取通过筛选的KOL
2. 调用7个详细API:
   - kol_fans_portrait: 粉丝画像
   - kol_fans_summary: 粉丝质量
   - kol_note_list: 笔记列表
   - kol_data_summary_v1: 数据汇总V1
   - kol_data_summary_v2: 数据汇总V2
   - kol_cost_effective: 性价比
   - kol_core_data: 核心数据
3. 每个API调用后立即保存
4. 支持断点续传

预计API调用: 8 KOL × 7 API = 56次
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List
from dataclasses import dataclass
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
    "concurrency": 7,
    "timeout": 30,
    "retry_count": 3,
    "retry_delay": 2,
    "api_delay": 0.5,
    
    # 详细数据API（7个）
    "detail_apis": {
        "kol_fans_portrait": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-fans-portrait/v1",
            "params": {"acceptCache": "true"}
        },
        "kol_fans_summary": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-fans-summary/v1",
            "params": {"acceptCache": "true"}
        },
        "kol_note_list": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-note-list/v1",
            "params": {
                "page": 1,
                "adSwitch": "_1",
                "orderType": "_1",
                "noteType": "_4",
                "acceptCache": "true"
            }
        },
        "kol_data_summary_v1": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-data-summary/v1",
            "params": {"business": "_0", "acceptCache": "true"}
        },
        "kol_data_summary_v2": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-data-summary/v2",
            "params": {"business": "_0", "acceptCache": "true"}
        },
        "kol_cost_effective": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-cost-effective/v1",
            "params": {"acceptCache": "true"}
        },
        "kol_core_data": {
            "endpoint": "/api/xiaohongshu-pgy/get-kol-core-data/v1",
            "params": {
                "dateType": "_1",
                "noteType": "_3",
                "adSwitch": "_1",
                "business": "_0",
                "acceptCache": "true"
            }
        }
    },
    
    # 排除的KOL ID（近30天无发帖）
    "excluded_kol_ids": [
        "59b8ccb682ec3904bb6f4b57",  # 帝都星光海归
        "60f18e370000000001016085",  # Katrina
        "5d2f4bbb000000001102b119",  # 小生饭饭
        "58d094f482ec396e6c9f634f",  # Alex爱运动
        "6553833c0000000002036a22",  # 美伢（减脂版）
        "6055b9340000000001006c61",  # 二姐美食
        "6653287700000000070050c6",  # 姗姗来迟
    ]
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


class DetailDataFetcher:
    """详细数据获取器"""
    
    def __init__(self):
        self.config = CONFIG
        self.token = self._load_api_token()
        self.base_url = self.config['api_base_url']
        self.output_dir = Path(__file__).parent / "02_详细数据"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载KOL列表
        self.kol_list_file = Path(__file__).parent / "kol_list.json"
        self.kols = self._load_filtered_kols()
        
        # 进度跟踪
        self.progress = FetchProgress()
        
        # 已获取记录
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
    
    def _load_filtered_kols(self) -> List[Dict[str, Any]]:
        """加载筛选后的KOL列表（排除无发帖的）"""
        if not self.kol_list_file.exists():
            raise FileNotFoundError(f"KOL列表文件不存在: {self.kol_list_file}")
        
        with open(self.kol_list_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        kols = data.get('kols', [])
        excluded = set(self.config['excluded_kol_ids'])
        
        # 只返回有kol_id且不在排除列表中的
        filtered = [k for k in kols if k.get('kol_id') and k['kol_id'] not in excluded]
        
        logger.info(f"从 {len(kols)} 个KOL中筛选出 {len(filtered)} 个（排除 {len(excluded)} 个无发帖）")
        return filtered
    
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
    
    async def fetch_kol_detail_data(self, session: aiohttp.ClientSession, 
                                     kol: Dict[str, Any], index: int) -> Dict[str, Any]:
        """获取单个KOL的详细数据"""
        kol_id = kol['kol_id']
        kol_name = kol['name']
        
        logger.info(f"[{index}/{self.progress.total_kols}] 获取详细数据: {kol_name} ({kol_id[:16]}...)")
        
        results = {}
        
        for api_name, api_config in self.config['detail_apis'].items():
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
                    logger.warning(f"  ⚠️ {api_name}: code={code}")
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
        """获取所有KOL的详细数据"""
        kols = self.kols
        if limit:
            kols = kols[:limit]
        
        if not kols:
            logger.warning("没有可获取的KOL")
            return
        
        self.progress.total_kols = len(kols)
        expected_api_calls = len(kols) * len(self.config['detail_apis'])
        
        logger.info("=" * 60)
        logger.info(f"🚀 阶段4: 获取详细数据")
        logger.info("=" * 60)
        logger.info(f"KOL数量: {len(kols)}")
        logger.info(f"每KOL API数: {len(self.config['detail_apis'])}")
        logger.info(f"预计API调用: {expected_api_calls}次")
        logger.info(f"并发数: {self.config['concurrency']}")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info("=" * 60)
        
        # 显示要处理的KOL
        logger.info("待处理KOL:")
        for kol in kols:
            logger.info(f"  - {kol['name']}")
        logger.info("")
        
        async with aiohttp.ClientSession() as session:
            for i, kol in enumerate(kols, 1):
                await self.fetch_kol_detail_data(session, kol, i)
        
        self._print_summary()
        self._merge_all_data()
    
    def _print_summary(self):
        """打印汇总"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("📋 阶段4完成汇总")
        logger.info("=" * 60)
        logger.info(f"KOL总数: {self.progress.total_kols}")
        logger.info(f"完成KOL: {self.progress.completed_kols}")
        logger.info(f"API成功: {self.progress.success_apis}")
        logger.info(f"API失败: {self.progress.failed_apis}")
        logger.info(f"API跳过: {self.progress.skipped_apis}")
        logger.info(f"数据目录: {self.output_dir}")
    
    def _merge_all_data(self):
        """合并所有数据到一个汇总文件"""
        all_data = []
        screening_dir = Path(__file__).parent / "01_基础筛选数据"
        
        for kol in self.kols:
            kol_id = kol['kol_id']
            kol_name = kol['name']
            
            kol_data = {
                "kol_id": kol_id,
                "kol_name": kol_name,
                "screening_data": {},
                "detail_data": {}
            }
            
            # 读取筛选数据
            screening_kol_dir = screening_dir / f"kol_{kol_id}"
            if screening_kol_dir.exists():
                for api_file in screening_kol_dir.glob("*.json"):
                    api_name = api_file.stem
                    with open(api_file, 'r', encoding='utf-8') as f:
                        kol_data['screening_data'][api_name] = json.load(f)
            
            # 读取详细数据
            detail_kol_dir = self.output_dir / f"kol_{kol_id}"
            if detail_kol_dir.exists():
                for api_file in detail_kol_dir.glob("*.json"):
                    api_name = api_file.stem
                    with open(api_file, 'r', encoding='utf-8') as f:
                        kol_data['detail_data'][api_name] = json.load(f)
            
            all_data.append(kol_data)
        
        # 保存汇总
        summary_file = self.output_dir / "_all_kol_data.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_kols": len(all_data),
                "kols": all_data
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📊 汇总数据已保存: {summary_file}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='获取KOL详细数据')
    parser.add_argument('--limit', type=int, default=None, help='限制获取数量（测试用）')
    parser.add_argument('--test', action='store_true', help='测试模式，只获取前2个')
    args = parser.parse_args()
    
    limit = 2 if args.test else args.limit
    
    fetcher = DetailDataFetcher()
    await fetcher.fetch_all(limit=limit)


if __name__ == "__main__":
    asyncio.run(main())
