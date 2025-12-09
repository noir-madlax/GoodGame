#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量获取KOL的蒲公英API数据

功能：
1. 从数据库读取所有待获取的KOL
2. 并发调用10个KOL级别PGY API
3. 获取笔记列表后，再调用笔记详情API
4. 将原始数据保存到JSON文件（后续再落库）
5. 跳过已获取的数据避免重复调用
6. 支持10并发，每个API调用延迟500ms
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


@dataclass
class FetchProgress:
    """获取进度跟踪"""
    total_kols: int = 0
    completed_kols: int = 0
    failed_kols: int = 0
    api_calls: int = 0
    api_errors: int = 0
    skipped_calls: int = 0


@dataclass
class KolApiResult:
    """单个KOL的API结果"""
    kol_id: str
    kol_name: str
    fetch_time: str = ""
    apis: Dict[str, Any] = field(default_factory=dict)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    is_pgy_kol: bool = False  # 是否是蒲公英博主


class BatchKolFetcher:
    """批量KOL数据获取器"""
    
    # 10个可用的KOL级别API（排除已下线的kol_track和已废弃的note_detail_v1）
    KOL_APIS = [
        'kol_info',
        'kol_note_rate', 
        'kol_fans_portrait',
        'kol_fans_summary',
        'kol_fans_trend',
        'kol_note_list',
        'kol_data_summary_v1',
        'kol_data_summary_v2',
        'kol_cost_effective',
        'kol_core_data',
    ]
    
    # API参数配置
    API_PARAMS = {
        'kol_info': {'acceptCache': 'true'},
        'kol_note_rate': {'dateType': '_1', 'noteType': '_3', 'adSwitch': '_1', 'business': '_0', 'acceptCache': 'true'},
        'kol_fans_portrait': {'acceptCache': 'true'},
        'kol_fans_summary': {'acceptCache': 'true'},
        'kol_fans_trend': {'dateType': '_1', 'increaseType': '_1', 'acceptCache': 'true'},
        'kol_note_list': {'page': 1, 'adSwitch': '_1', 'orderType': '_1', 'noteType': '_4', 'acceptCache': 'true'},
        'kol_data_summary_v1': {'business': '_0', 'acceptCache': 'true'},
        'kol_data_summary_v2': {'business': '_0', 'acceptCache': 'true'},
        'kol_cost_effective': {'acceptCache': 'true'},
        'kol_core_data': {'dateType': '_1', 'noteType': '_3', 'adSwitch': '_1', 'business': '_0', 'acceptCache': 'true'},
    }
    
    def __init__(self, concurrency: int = 10, api_delay: float = 0.5):
        self.concurrency = concurrency
        self.api_delay = api_delay
        self.config = self._load_config()
        self.token = self._load_api_token()
        self.base_url = self.config['api_base_url']
        self.endpoints = self.config['接口列表']
        self.progress = FetchProgress()
        self.output_dir = Path(__file__).parent / "output" / "api_data"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 已获取的KOL记录文件
        self.fetched_record_file = self.output_dir / "fetched_kols.json"
        self.fetched_kols = self._load_fetched_record()
        
        # 信号量控制并发
        self.semaphore = asyncio.Semaphore(concurrency)
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path(__file__).parent.parent / "pgy" / "params" / "config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_api_token(self) -> str:
        """从环境变量加载 Just One API Token"""
        backend_dir = Path(__file__).parent.parent.parent.parent
        env_path = backend_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
        
        token = os.getenv('JUSTONEAPI_API_KEY', '')
        if not token:
            raise ValueError("请在 .env 文件中配置 JUSTONEAPI_API_KEY")
        return token
    
    def _load_fetched_record(self) -> Dict[str, Dict[str, bool]]:
        """加载已获取记录"""
        if self.fetched_record_file.exists():
            with open(self.fetched_record_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_fetched_record(self):
        """保存已获取记录"""
        with open(self.fetched_record_file, 'w', encoding='utf-8') as f:
            json.dump(self.fetched_kols, f, ensure_ascii=False, indent=2)
    
    def _is_api_fetched(self, kol_id: str, api_name: str) -> bool:
        """检查某个KOL的某个API是否已获取"""
        if kol_id not in self.fetched_kols:
            return False
        return self.fetched_kols[kol_id].get(api_name, False)
    
    def _mark_api_fetched(self, kol_id: str, api_name: str, success: bool = True):
        """标记某个API已获取"""
        if kol_id not in self.fetched_kols:
            self.fetched_kols[kol_id] = {}
        self.fetched_kols[kol_id][api_name] = success
    
    async def _call_api(self, session: aiohttp.ClientSession, endpoint: str, 
                        params: Dict[str, Any], api_name: str) -> Dict[str, Any]:
        """调用单个API"""
        url = f"{self.base_url}{endpoint}"
        params['token'] = self.token
        
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    code = result.get('code', 'N/A')
                    self.progress.api_calls += 1
                    return result
                else:
                    self.progress.api_errors += 1
                    return {"error": f"HTTP {response.status}", "api_name": api_name}
        except asyncio.TimeoutError:
            self.progress.api_errors += 1
            return {"error": "Timeout", "api_name": api_name}
        except Exception as e:
            self.progress.api_errors += 1
            return {"error": str(e), "api_name": api_name}
    
    async def _fetch_single_api(self, session: aiohttp.ClientSession, 
                                 kol_id: str, api_name: str) -> tuple[str, Dict[str, Any]]:
        """获取单个KOL的单个API数据"""
        async with self.semaphore:
            # 检查是否已获取
            if self._is_api_fetched(kol_id, api_name):
                self.progress.skipped_calls += 1
                return api_name, {"skipped": True, "reason": "already_fetched"}
            
            endpoint = self.endpoints.get(api_name)
            if not endpoint:
                return api_name, {"error": f"Unknown API: {api_name}"}
            
            params = {'kolId': kol_id}
            params.update(self.API_PARAMS.get(api_name, {}))
            
            result = await self._call_api(session, endpoint, params, api_name)
            
            # 延迟500ms
            await asyncio.sleep(self.api_delay)
            
            # 标记已获取
            success = 'error' not in result
            self._mark_api_fetched(kol_id, api_name, success)
            
            return api_name, result
    
    async def _fetch_note_detail(self, session: aiohttp.ClientSession, 
                                  note_id: str) -> Dict[str, Any]:
        """获取笔记详情"""
        async with self.semaphore:
            endpoint = self.endpoints.get('note_detail_solar')
            if not endpoint:
                return {"error": "note_detail_solar endpoint not found"}
            
            params = {'noteId': note_id, 'acceptCache': 'true', 'token': self.token}
            
            result = await self._call_api(session, endpoint, params, 'note_detail_solar')
            
            # 延迟500ms
            await asyncio.sleep(self.api_delay)
            
            return result
    
    async def fetch_kol_data(self, session: aiohttp.ClientSession, 
                              kol_id: str, kol_name: str) -> KolApiResult:
        """获取单个KOL的所有API数据"""
        result = KolApiResult(
            kol_id=kol_id,
            kol_name=kol_name,
            fetch_time=datetime.now().isoformat()
        )
        
        logger.info(f"开始获取 KOL: {kol_name} ({kol_id})")
        
        # 并发获取所有KOL级别API
        tasks = [
            self._fetch_single_api(session, kol_id, api_name)
            for api_name in self.KOL_APIS
        ]
        
        api_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for item in api_results:
            if isinstance(item, Exception):
                result.errors.append(str(item))
                continue
            api_name, data = item
            result.apis[api_name] = data
            
            # 检查是否是蒲公英博主（通过kol_info判断）
            if api_name == 'kol_info' and data.get('code') == 0:
                kol_data = data.get('data', {})
                # 如果能获取到数据，说明是蒲公英博主
                if kol_data:
                    result.is_pgy_kol = True
        
        # 笔记详情API暂时禁用（成本较高）
        # 如果需要获取笔记详情，可以后续单独处理
        # note_list_data = result.apis.get('kol_note_list', {})
        # if note_list_data.get('code') == 0:
        #     notes = note_list_data.get('data', {}).get('list', [])
        #     if notes:
        #         logger.info(f"  获取 {len(notes)} 篇笔记详情...")
        #         # 获取前5篇笔记的详情（避免调用过多）
        #         note_tasks = []
        #         for note in notes[:5]:
        #             note_id = note.get('noteId') or note.get('id')
        #             if note_id:
        #                 # 检查是否已获取
        #                 note_api_key = f"note_detail_{note_id}"
        #                 if not self._is_api_fetched(kol_id, note_api_key):
        #                     note_tasks.append(self._fetch_note_detail(session, note_id))
        #                 else:
        #                     self.progress.skipped_calls += 1
        #         
        #         if note_tasks:
        #             note_results = await asyncio.gather(*note_tasks, return_exceptions=True)
        #             for i, note_result in enumerate(note_results):
        #                 if isinstance(note_result, Exception):
        #                     result.errors.append(f"Note detail error: {str(note_result)}")
        #                 else:
        #                     result.notes.append(note_result)
        #                     # 标记已获取
        #                     if notes[i]:
        #                         note_id = notes[i].get('noteId') or notes[i].get('id')
        #                         if note_id:
        #                             self._mark_api_fetched(kol_id, f"note_detail_{note_id}", True)
        
        return result
    
    def _save_kol_result(self, result: KolApiResult):
        """保存单个KOL的结果"""
        # 按KOL保存
        kol_dir = self.output_dir / f"kol_{result.kol_id}"
        kol_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存完整结果
        result_file = kol_dir / "all_data.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'kol_id': result.kol_id,
                'kol_name': result.kol_name,
                'fetch_time': result.fetch_time,
                'is_pgy_kol': result.is_pgy_kol,
                'apis': result.apis,
                'notes': result.notes,
                'errors': result.errors
            }, f, ensure_ascii=False, indent=2)
        
        # 保存获取记录
        self._save_fetched_record()
    
    async def fetch_all_kols(self, kols: List[Dict[str, str]]):
        """批量获取所有KOL数据"""
        self.progress.total_kols = len(kols)
        
        logger.info(f"开始批量获取 {len(kols)} 个KOL的数据")
        logger.info(f"并发数: {self.concurrency}, API延迟: {self.api_delay}s")
        
        async with aiohttp.ClientSession() as session:
            for i, kol in enumerate(kols):
                kol_id = kol.get('kol_id')
                kol_name = kol.get('kol_name', 'Unknown')
                
                if not kol_id:
                    logger.warning(f"跳过无效KOL: {kol}")
                    continue
                
                try:
                    result = await self.fetch_kol_data(session, kol_id, kol_name)
                    self._save_kol_result(result)
                    self.progress.completed_kols += 1
                    
                    # 打印进度
                    logger.info(f"进度: {self.progress.completed_kols}/{self.progress.total_kols} "
                               f"| API调用: {self.progress.api_calls} | 跳过: {self.progress.skipped_calls} "
                               f"| 错误: {self.progress.api_errors}")
                    
                except Exception as e:
                    logger.error(f"获取KOL {kol_name} ({kol_id}) 失败: {e}")
                    self.progress.failed_kols += 1
        
        # 打印最终统计
        self._print_summary()
    
    def _print_summary(self):
        """打印获取汇总"""
        logger.info("=" * 60)
        logger.info("批量获取完成")
        logger.info("=" * 60)
        logger.info(f"总KOL数: {self.progress.total_kols}")
        logger.info(f"成功: {self.progress.completed_kols}")
        logger.info(f"失败: {self.progress.failed_kols}")
        logger.info(f"API调用次数: {self.progress.api_calls}")
        logger.info(f"跳过（已获取）: {self.progress.skipped_calls}")
        logger.info(f"API错误: {self.progress.api_errors}")
        logger.info(f"数据保存目录: {self.output_dir}")


def load_kols_from_db() -> List[Dict[str, str]]:
    """从数据库加载KOL列表"""
    from supabase import create_client, Client
    
    backend_dir = Path(__file__).parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        raise ValueError("请在 .env 文件中配置 SUPABASE_URL 和 SUPABASE_KEY")
    
    client = create_client(url, key)
    
    # 获取所有待获取的KOL
    response = client.table('gg_pgy_kol_base_info').select(
        'kol_id, kol_name, api_fetch_status'
    ).eq('api_fetch_status', 'not_fetched').execute()
    
    kols = []
    for row in response.data:
        if row.get('kol_id'):
            kols.append({
                'kol_id': row['kol_id'],
                'kol_name': row.get('kol_name', 'Unknown')
            })
    
    logger.info(f"从数据库加载了 {len(kols)} 个待获取的KOL")
    return kols


async def main():
    """主函数"""
    # 从数据库加载KOL列表
    kols = load_kols_from_db()
    
    if not kols:
        logger.warning("没有待获取的KOL")
        return
    
    # 创建获取器并执行
    fetcher = BatchKolFetcher(concurrency=10, api_delay=0.5)
    await fetcher.fetch_all_kols(kols)


if __name__ == "__main__":
    asyncio.run(main())
