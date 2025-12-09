#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将爬取的API数据导入数据库

功能：
1. 读取 output/api_data/kol_xxx/all_data.json 文件
2. 将10个API的数据导入到对应的8个数据库表
3. 支持并发导入（默认10并发）
4. 使用upsert避免重复
5. 失败自动重试（最多3次）
6. 实时进度显示
7. 数据验证和完整性检查
8. 最终数据报告（字段空值比例统计）
"""

import os
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import threading

# 配置日志 - 实时输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 确保实时输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)


@dataclass
class ImportStats:
    """导入统计"""
    total_kols: int = 0
    imported_kols: int = 0
    failed_kols: int = 0
    skipped_kols: int = 0
    retried_kols: int = 0
    base_info_updated: int = 0
    audience_inserted: int = 0
    fans_summary_inserted: int = 0
    fans_trend_inserted: int = 0
    note_rate_inserted: int = 0
    notes_inserted: int = 0
    cost_effective_inserted: int = 0
    core_data_inserted: int = 0
    errors: List[str] = field(default_factory=list)
    failed_kol_ids: List[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def increment(self, field_name: str, value: int = 1):
        """线程安全的增量操作"""
        with self._lock:
            current = getattr(self, field_name)
            setattr(self, field_name, current + value)
    
    def add_error(self, error: str):
        """线程安全地添加错误"""
        with self._lock:
            self.errors.append(error)
    
    def add_failed_kol(self, kol_id: str):
        """线程安全地添加失败的KOL ID"""
        with self._lock:
            self.failed_kol_ids.append(kol_id)


class ApiDataImporter:
    """API数据导入器"""
    
    def __init__(self, concurrency: int = 10, max_retries: int = 3):
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.data_dir = Path(__file__).parent / "output" / "api_data"
        self.stats = ImportStats()
        self.start_time = None
        self.processed_count = 0
        self._count_lock = threading.Lock()
        
        # 每个线程使用独立的客户端
        self._client_local = threading.local()
    
    def _get_client(self):
        """获取线程本地的Supabase客户端"""
        if not hasattr(self._client_local, 'client'):
            from supabase import create_client
            
            backend_dir = Path(__file__).parent.parent.parent.parent
            env_path = backend_dir / '.env'
            
            if env_path.exists():
                load_dotenv(env_path)
            
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_KEY')
            
            if not url or not key:
                raise ValueError("请在 .env 文件中配置 SUPABASE_URL 和 SUPABASE_KEY")
            
            self._client_local.client = create_client(url, key)
        
        return self._client_local.client
    
    def _safe_float(self, value: Any, default: float = None) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_int(self, value: Any, default: int = None) -> Optional[int]:
        """安全转换为整数"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """解析日期字符串"""
        if not date_str:
            return None
        try:
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(date_str[:19], fmt).strftime('%Y-%m-%d')
                except ValueError:
                    continue
            return date_str[:10] if len(date_str) >= 10 else None
        except Exception:
            return None
    
    def _extract_base_info(self, kol_id: str, apis: Dict[str, Any]) -> Dict[str, Any]:
        """从kol_info提取基础信息更新"""
        kol_info = apis.get('kol_info', {})
        if kol_info.get('code') != 0:
            return None
        
        data = kol_info.get('data', {})
        if not data:
            return None
        
        summary_v1 = apis.get('kol_data_summary_v1', {}).get('data', {}) or {}
        summary_v2 = apis.get('kol_data_summary_v2', {}).get('data', {}) or {}
        
        raw_data = {
            'kol_info': kol_info,
            'kol_data_summary_v1': apis.get('kol_data_summary_v1', {}),
            'kol_data_summary_v2': apis.get('kol_data_summary_v2', {})
        }
        
        return {
            'kol_id': kol_id,
            'kol_name': data.get('name'),
            'red_id': data.get('redId'),
            'gender': data.get('gender'),
            'location': data.get('location'),
            'travel_area_list': data.get('travelAreaList'),
            'head_photo': data.get('headPhoto'),
            'fans_count': self._safe_int(data.get('fansCount')),
            'like_collect_count': self._safe_int(data.get('likeCollectCountInfo')),
            'business_note_count': self._safe_int(data.get('businessNoteCount')),
            'total_note_count': self._safe_int(data.get('totalNoteCount')),
            'picture_price': self._safe_float(data.get('picturePrice')),
            'video_price': self._safe_float(data.get('videoPrice')),
            'picture_state': self._safe_int(data.get('pictureState')),
            'video_state': self._safe_int(data.get('videoState')),
            'lower_price': self._safe_float(data.get('lowerPrice')),
            'content_tags': data.get('contentTags'),
            'feature_tags': data.get('featureTags'),
            'personal_tags': data.get('personalTags'),
            'trade_type': data.get('tradeType'),
            'click_mid_num': self._safe_int(data.get('clickMidNum')),
            'inter_mid_num': self._safe_int(data.get('interMidNum')),
            'fans_30_growth_num': self._safe_int(data.get('fans30GrowthNum')),
            'fans_30_growth_rate': self._safe_float(data.get('fans30GrowthRate')),
            'current_level': self._safe_int(data.get('currentLevel')),
            'cooper_type': self._safe_int(data.get('cooperType')),
            'user_type': self._safe_int(data.get('userType')),
            'low_active': data.get('lowActive'),
            'kol_advantage': summary_v2.get('kolAdvantage'),
            'cooperate_state': self._safe_int(data.get('cooperateState')),
            'estimate_picture_cpm': self._safe_float(data.get('estimatePictureCpm')),
            'estimate_video_cpm': self._safe_float(data.get('estimateVideoCpm')),
            'estimate_picture_engage_cost': self._safe_float(data.get('estimatePictureEngageCost')),
            'estimate_video_engage_cost': self._safe_float(data.get('estimateVideoEngageCost')),
            'response_rate': self._safe_float(summary_v1.get('responseRate')),
            'invite_num': self._safe_int(summary_v1.get('inviteNum')),
            'active_day_in_last_7': self._safe_int(summary_v1.get('activeDayInLast7')),
            'is_active': summary_v1.get('isActive'),
            'easy_connect': summary_v1.get('easyConnect'),
            'raw_data': raw_data,
            'api_fetch_status': 'fetched',
            'fetch_date': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def _extract_audience(self, kol_id: str, apis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从kol_fans_portrait提取粉丝画像"""
        portrait = apis.get('kol_fans_portrait', {})
        if portrait.get('code') != 0:
            return None
        
        data = portrait.get('data', {})
        if not data:
            return None
        
        return {
            'kol_id': kol_id,
            'gender_distribution': data.get('gender'),
            'age_distribution': data.get('ages'),
            'province_distribution': data.get('provinces'),
            'city_distribution': data.get('cities'),
            'device_distribution': data.get('devices'),
            'interest_distribution': data.get('interests'),
            'date_key': self._parse_date(data.get('dateKey')),
            'raw_data': portrait,
            'fetch_date': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def _extract_fans_summary(self, kol_id: str, apis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从kol_fans_summary提取粉丝质量"""
        summary = apis.get('kol_fans_summary', {})
        if summary.get('code') != 0:
            return None
        
        data = summary.get('data', {})
        if not data:
            return None
        
        return {
            'kol_id': kol_id,
            'fans_num': self._safe_int(data.get('fansNum')),
            'fans_increase_num': self._safe_int(data.get('fansIncreaseNum')),
            'fans_growth_rate': self._safe_float(data.get('fansGrowthRate')),
            'fans_growth_beyond_rate': self._safe_float(data.get('fansGrowthBeyondRate')),
            'active_fans_l28': self._safe_int(data.get('activeFansL28')),
            'active_fans_rate': self._safe_float(data.get('activeFansRate')),
            'active_fans_beyond_rate': self._safe_float(data.get('activeFansBeyondRate')),
            'engage_fans_l30': self._safe_int(data.get('engageFansL30')),
            'engage_fans_rate': self._safe_float(data.get('engageFansRate')),
            'engage_fans_beyond_rate': self._safe_float(data.get('engageFansBeyondRate')),
            'read_fans_in_30': self._safe_int(data.get('readFansIn30')),
            'read_fans_rate': self._safe_float(data.get('readFansRate')),
            'read_fans_beyond_rate': self._safe_float(data.get('readFansBeyondRate')),
            'pay_fans_user_rate_30d': self._safe_float(data.get('payFansUserRate30d')),
            'pay_fans_user_num_30d': self._safe_int(data.get('payFansUserNum30d')),
            'raw_data': summary,
            'fetch_date': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def _extract_fans_trend(self, kol_id: str, apis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从kol_fans_trend提取粉丝趋势"""
        trend = apis.get('kol_fans_trend', {})
        if trend.get('code') != 0:
            return []
        
        data = trend.get('data', {}) or {}
        trend_list = data.get('list', []) or []
        
        records = []
        for item in trend_list:
            date_key = self._parse_date(item.get('dateKey'))
            if date_key:
                records.append({
                    'kol_id': kol_id,
                    'date_key': date_key,
                    'fans_num': self._safe_int(item.get('num'))
                })
        
        return records
    
    def _extract_note_rate(self, kol_id: str, apis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从kol_note_rate提取笔记数据率"""
        note_rate = apis.get('kol_note_rate', {})
        if note_rate.get('code') != 0:
            return None
        
        data = note_rate.get('data', {})
        if not data:
            return None
        
        return {
            'kol_id': kol_id,
            'note_number': self._safe_int(data.get('noteNumber')),
            'video_note_number': self._safe_int(data.get('videoNoteNumber')),
            'imp_median': self._safe_int(data.get('impMedian')),
            'imp_median_beyond_rate': self._safe_float(data.get('impMedianBeyondRate')),
            'read_median': self._safe_int(data.get('readMedian')),
            'read_median_beyond_rate': self._safe_float(data.get('readMedianBeyondRate')),
            'interaction_median': self._safe_int(data.get('interactionMedian')),
            'interaction_rate': self._safe_float(data.get('interactionRate')),
            'interaction_beyond_rate': self._safe_float(data.get('interactionBeyondRate')),
            'like_median': self._safe_int(data.get('likeMedian')),
            'collect_median': self._safe_int(data.get('collectMedian')),
            'comment_median': self._safe_int(data.get('commentMedian')),
            'share_median': self._safe_int(data.get('shareMedian')),
            'hundred_like_percent': self._safe_float(data.get('hundredLikePercent')),
            'thousand_like_percent': self._safe_float(data.get('thousandLikePercent')),
            'page_percent_vo': data.get('pagePercentVo'),
            'long_term_common_note_vo': data.get('longTermCommonNoteVo'),
            'long_term_cooperate_note_vo': data.get('longTermCooperateNoteVo'),
            'note_type': data.get('noteType'),
            'raw_data': note_rate,
            'fetch_date': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def _extract_notes(self, kol_id: str, apis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从kol_note_list提取笔记列表"""
        note_list = apis.get('kol_note_list', {})
        if note_list.get('code') != 0:
            return []
        
        data = note_list.get('data', {}) or {}
        notes = data.get('list', []) or []
        
        records = []
        for note in notes:
            note_id = note.get('noteId')
            if note_id:
                records.append({
                    'kol_id': kol_id,
                    'note_id': note_id,
                    'title': note.get('title'),
                    'img_url': note.get('imgUrl'),
                    'is_video': note.get('isVideo'),
                    'is_advertise': note.get('isAdvertise'),
                    'brand_name': note.get('brandName'),
                    'read_num': self._safe_int(note.get('readNum')),
                    'like_num': self._safe_int(note.get('likeNum')),
                    'collect_num': self._safe_int(note.get('collectNum')),
                    'third_read_user_num': self._safe_int(note.get('thirdReadUserNum')),
                    'publish_date': self._parse_date(note.get('date')),
                    'raw_data': note,
                    'detail_fetched': False,
                    'updated_at': datetime.now().isoformat()
                })
        
        return records
    
    def _extract_cost_effective(self, kol_id: str, apis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从kol_cost_effective提取性价比"""
        cost = apis.get('kol_cost_effective', {})
        if cost.get('code') != 0:
            return None
        
        data = cost.get('data', {})
        if not data:
            return None
        
        return {
            'kol_id': kol_id,
            'picture_read_cost': self._safe_float(data.get('pictureReadCost')),
            'picture_surpass_rate': self._safe_float(data.get('pictureSurpassRate')),
            'picture_case': self._safe_int(data.get('pictureCase')),
            'estimate_picture_cpm': self._safe_float(data.get('estimatePictureCpm')),
            'estimate_picture_cpm_compare': self._safe_float(data.get('estimatePictureCpmCompare')),
            'estimate_picture_engage_cost': self._safe_float(data.get('estimatePictureEngageCost')),
            'estimate_picture_engage_cost_compare': self._safe_float(data.get('estimatePictureEngageCostCompare')),
            'video_read_cost': self._safe_float(data.get('videoReadCost')),
            'video_surpass_rate': self._safe_float(data.get('videoSurpassRate')),
            'video_case': self._safe_int(data.get('videoCase')),
            'estimate_video_cpm': self._safe_float(data.get('estimateVideoCpm')),
            'estimate_video_cpm_compare': self._safe_float(data.get('estimateVideoCpmCompare')),
            'estimate_video_engage_cost': self._safe_float(data.get('estimateVideoEngageCost')),
            'estimate_video_engage_cost_compare': self._safe_float(data.get('estimateVideoEngageCostCompare')),
            'raw_data': cost,
            'fetch_date': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def _extract_core_data(self, kol_id: str, apis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从kol_core_data提取核心数据"""
        core = apis.get('kol_core_data', {})
        if core.get('code') != 0:
            return []
        
        data = core.get('data', {}) or {}
        daily_data = data.get('dailyData', []) or []
        
        records = []
        for item in daily_data:
            date_key = self._parse_date(item.get('dateKey'))
            if date_key:
                records.append({
                    'kol_id': kol_id,
                    'date_key': date_key,
                    'imp': self._safe_int(item.get('imp')),
                    'read': self._safe_int(item.get('read')),
                    'engage': self._safe_int(item.get('engage')),
                    'third_user_num': self._safe_int(item.get('thirdUserNum')),
                    'cpm': self._safe_float(item.get('cpm')),
                    'cpe': self._safe_float(item.get('cpe')),
                    'cpuv': self._safe_float(item.get('cpuv')),
                    'cpv': self._safe_float(item.get('cpv'))
                })
        
        return records
    
    def _import_single_kol_internal(self, kol_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, int]]:
        """导入单个KOL的数据（内部方法）"""
        kol_id = kol_data.get('kol_id')
        kol_name = kol_data.get('kol_name', 'Unknown')
        apis = kol_data.get('apis', {})
        
        client = self._get_client()
        local_stats = {
            'base_info': 0, 'audience': 0, 'fans_summary': 0,
            'fans_trend': 0, 'note_rate': 0, 'notes': 0,
            'cost_effective': 0, 'core_data': 0
        }
        
        # 1. 更新基础信息
        base_info = self._extract_base_info(kol_id, apis)
        if base_info:
            client.table('gg_pgy_kol_base_info').upsert(base_info, on_conflict='kol_id').execute()
            local_stats['base_info'] = 1
        
        # 2. 插入粉丝画像
        audience = self._extract_audience(kol_id, apis)
        if audience:
            client.table('gg_pgy_kol_audience').delete().eq('kol_id', kol_id).execute()
            client.table('gg_pgy_kol_audience').insert(audience).execute()
            local_stats['audience'] = 1
        
        # 3. 插入粉丝质量
        fans_summary = self._extract_fans_summary(kol_id, apis)
        if fans_summary:
            client.table('gg_pgy_kol_fans_summary').delete().eq('kol_id', kol_id).execute()
            client.table('gg_pgy_kol_fans_summary').insert(fans_summary).execute()
            local_stats['fans_summary'] = 1
        
        # 4. 插入粉丝趋势
        fans_trend = self._extract_fans_trend(kol_id, apis)
        if fans_trend:
            client.table('gg_pgy_kol_fans_trend').delete().eq('kol_id', kol_id).execute()
            batch_size = 50
            for i in range(0, len(fans_trend), batch_size):
                batch = fans_trend[i:i+batch_size]
                client.table('gg_pgy_kol_fans_trend').insert(batch).execute()
            local_stats['fans_trend'] = len(fans_trend)
        
        # 5. 插入笔记数据率
        note_rate = self._extract_note_rate(kol_id, apis)
        if note_rate:
            client.table('gg_pgy_kol_note_rate').delete().eq('kol_id', kol_id).execute()
            client.table('gg_pgy_kol_note_rate').insert(note_rate).execute()
            local_stats['note_rate'] = 1
        
        # 6. 插入笔记列表
        notes = self._extract_notes(kol_id, apis)
        if notes:
            client.table('gg_pgy_kol_notes').delete().eq('kol_id', kol_id).execute()
            batch_size = 50
            for i in range(0, len(notes), batch_size):
                batch = notes[i:i+batch_size]
                client.table('gg_pgy_kol_notes').insert(batch).execute()
            local_stats['notes'] = len(notes)
        
        # 7. 插入性价比
        cost_effective = self._extract_cost_effective(kol_id, apis)
        if cost_effective:
            client.table('gg_pgy_kol_cost_effective').delete().eq('kol_id', kol_id).execute()
            client.table('gg_pgy_kol_cost_effective').insert(cost_effective).execute()
            local_stats['cost_effective'] = 1
        
        # 8. 插入核心数据
        core_data = self._extract_core_data(kol_id, apis)
        if core_data:
            client.table('gg_pgy_kol_core_data').delete().eq('kol_id', kol_id).execute()
            batch_size = 50
            for i in range(0, len(core_data), batch_size):
                batch = core_data[i:i+batch_size]
                client.table('gg_pgy_kol_core_data').insert(batch).execute()
            local_stats['core_data'] = len(core_data)
        
        return True, f"成功导入 {kol_name} ({kol_id})", local_stats
    
    def import_single_kol_with_retry(self, kol_dir: Path, index: int, total: int) -> Tuple[bool, str]:
        """导入单个KOL（带重试机制）"""
        kol_data = self.load_kol_data(kol_dir)
        if not kol_data:
            with self._count_lock:
                self.processed_count += 1
            self.stats.increment('skipped_kols')
            logger.warning(f"[{index}/{total}] ⚠️ 跳过无效目录: {kol_dir.name}")
            return True, "跳过"
        
        kol_id = kol_data.get('kol_id')
        kol_name = kol_data.get('kol_name', 'Unknown')
        
        # 检查是否所有API都是skipped
        apis = kol_data.get('apis', {})
        all_skipped = all(
            api_data.get('skipped', False) or api_data.get('code') != 0
            for api_data in apis.values()
        )
        if all_skipped:
            with self._count_lock:
                self.processed_count += 1
            self.stats.increment('skipped_kols')
            logger.info(f"[{index}/{total}] ⏭️ 跳过(无有效数据): {kol_name} ({kol_id})")
            return True, "跳过"
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                success, msg, local_stats = self._import_single_kol_internal(kol_data)
                
                if success:
                    # 更新全局统计
                    self.stats.increment('base_info_updated', local_stats['base_info'])
                    self.stats.increment('audience_inserted', local_stats['audience'])
                    self.stats.increment('fans_summary_inserted', local_stats['fans_summary'])
                    self.stats.increment('fans_trend_inserted', local_stats['fans_trend'])
                    self.stats.increment('note_rate_inserted', local_stats['note_rate'])
                    self.stats.increment('notes_inserted', local_stats['notes'])
                    self.stats.increment('cost_effective_inserted', local_stats['cost_effective'])
                    self.stats.increment('core_data_inserted', local_stats['core_data'])
                    self.stats.increment('imported_kols')
                    
                    if attempt > 0:
                        self.stats.increment('retried_kols')
                        logger.info(f"[{index}/{total}] ✅ 重试成功(第{attempt+1}次): {msg}")
                    else:
                        logger.info(f"[{index}/{total}] ✅ {msg}")
                    
                    with self._count_lock:
                        self.processed_count += 1
                        elapsed = time.time() - self.start_time
                        avg_time = elapsed / self.processed_count
                        remaining = (total - self.processed_count) * avg_time
                        logger.info(f"    📊 进度: {self.processed_count}/{total} ({100*self.processed_count/total:.1f}%) | 预计剩余: {remaining/60:.1f}分钟")
                    
                    return True, msg
                
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"[{index}/{total}] ⚠️ 第{attempt+1}次尝试失败: {kol_name} ({kol_id}), 错误: {last_error}, {wait_time}秒后重试...")
                    time.sleep(wait_time)
        
        # 所有重试都失败
        error_msg = f"导入 {kol_name} ({kol_id}) 失败(重试{self.max_retries}次): {last_error}"
        self.stats.add_error(error_msg)
        self.stats.add_failed_kol(kol_id)
        self.stats.increment('failed_kols')
        logger.error(f"[{index}/{total}] ❌ {error_msg}")
        
        with self._count_lock:
            self.processed_count += 1
        
        return False, error_msg
    
    def load_kol_data(self, kol_dir: Path) -> Optional[Dict[str, Any]]:
        """加载单个KOL的数据文件"""
        data_file = kol_dir / "all_data.json"
        if not data_file.exists():
            return None
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载文件失败 {data_file}: {e}")
            return None
    
    def get_all_kol_dirs(self) -> List[Path]:
        """获取所有KOL数据目录"""
        if not self.data_dir.exists():
            return []
        
        kol_dirs = []
        for item in self.data_dir.iterdir():
            if item.is_dir() and item.name.startswith('kol_'):
                kol_dirs.append(item)
        
        return sorted(kol_dirs, key=lambda x: x.name)
    
    def import_kols_concurrent(self, kol_dirs: List[Path], limit: int = None):
        """并发导入KOL数据"""
        if limit:
            kol_dirs = kol_dirs[:limit]
        
        total = len(kol_dirs)
        self.stats.total_kols = total
        self.start_time = time.time()
        self.processed_count = 0
        
        logger.info("=" * 70)
        logger.info(f"🚀 开始并发导入 {total} 个KOL的数据")
        logger.info(f"   并发数: {self.concurrency}, 最大重试次数: {self.max_retries}")
        logger.info("=" * 70)
        
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {
                executor.submit(self.import_single_kol_with_retry, kol_dir, i+1, total): kol_dir
                for i, kol_dir in enumerate(kol_dirs)
            }
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    kol_dir = futures[future]
                    logger.error(f"❌ 未预期的错误 {kol_dir.name}: {e}")
        
        elapsed = time.time() - self.start_time
        self._print_summary(elapsed)
        
        return self.stats
    
    def _print_summary(self, elapsed: float):
        """打印导入汇总"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("📋 导入完成汇总")
        logger.info("=" * 70)
        logger.info(f"⏱️  总耗时: {elapsed/60:.2f} 分钟")
        logger.info(f"📊 总KOL数: {self.stats.total_kols}")
        logger.info(f"✅ 成功导入: {self.stats.imported_kols}")
        logger.info(f"⏭️  跳过(无数据): {self.stats.skipped_kols}")
        logger.info(f"🔄 重试成功: {self.stats.retried_kols}")
        logger.info(f"❌ 失败: {self.stats.failed_kols}")
        logger.info("-" * 50)
        logger.info(f"📝 基础信息更新: {self.stats.base_info_updated}")
        logger.info(f"👥 粉丝画像插入: {self.stats.audience_inserted}")
        logger.info(f"📈 粉丝质量插入: {self.stats.fans_summary_inserted}")
        logger.info(f"📉 粉丝趋势插入: {self.stats.fans_trend_inserted} 条")
        logger.info(f"📰 笔记数据率插入: {self.stats.note_rate_inserted}")
        logger.info(f"📄 笔记列表插入: {self.stats.notes_inserted} 条")
        logger.info(f"💰 性价比插入: {self.stats.cost_effective_inserted}")
        logger.info(f"📊 核心数据插入: {self.stats.core_data_inserted} 条")
        
        if self.stats.errors:
            logger.info("-" * 50)
            logger.info(f"❌ 错误列表 ({len(self.stats.errors)}):")
            for err in self.stats.errors[:20]:
                logger.info(f"  - {err}")
            if len(self.stats.errors) > 20:
                logger.info(f"  ... 还有 {len(self.stats.errors) - 20} 个错误")


class DataValidator:
    """数据验证器"""
    
    def __init__(self):
        self.client = self._load_supabase_client()
        self.data_dir = Path(__file__).parent / "output" / "api_data"
    
    def _load_supabase_client(self):
        """加载Supabase客户端"""
        from supabase import create_client
        
        backend_dir = Path(__file__).parent.parent.parent.parent
        env_path = backend_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        return create_client(url, key)
    
    def validate_kol(self, kol_id: str) -> Dict[str, Any]:
        """验证单个KOL的数据完整性"""
        results = {
            'kol_id': kol_id,
            'valid': True,
            'checks': {}
        }
        
        kol_dir = self.data_dir / f"kol_{kol_id}"
        json_file = kol_dir / "all_data.json"
        
        if not json_file.exists():
            results['valid'] = False
            results['error'] = f"JSON文件不存在: {json_file}"
            return results
        
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        apis = json_data.get('apis', {})
        
        checks = {
            'base_info': self._check_base_info(kol_id, apis),
            'audience': self._check_audience(kol_id, apis),
            'fans_summary': self._check_fans_summary(kol_id, apis),
            'fans_trend': self._check_fans_trend(kol_id, apis),
            'note_rate': self._check_note_rate(kol_id, apis),
            'notes': self._check_notes(kol_id, apis),
            'cost_effective': self._check_cost_effective(kol_id, apis),
            'core_data': self._check_core_data(kol_id, apis)
        }
        
        results['checks'] = checks
        results['valid'] = all(c['valid'] for c in checks.values())
        
        return results
    
    def _check_base_info(self, kol_id: str, apis: Dict) -> Dict:
        db_data = self.client.table('gg_pgy_kol_base_info').select('*').eq('kol_id', kol_id).execute()
        
        if not db_data.data:
            api_code = apis.get('kol_info', {}).get('code')
            if api_code != 0:
                return {'valid': True, 'note': 'API无有效数据'}
            return {'valid': False, 'error': '数据库中无记录'}
        
        db_row = db_data.data[0]
        api_data = apis.get('kol_info', {}).get('data', {})
        
        if not api_data:
            return {'valid': True, 'note': 'API无数据，跳过'}
        
        mismatches = []
        field_mappings = {
            'kol_name': 'name',
            'fans_count': 'fansCount',
            'video_price': 'videoPrice'
        }
        
        for db_field, api_field in field_mappings.items():
            db_val = db_row.get(db_field)
            api_val = api_data.get(api_field)
            
            if db_val is not None and api_val is not None:
                if isinstance(api_val, (int, float)):
                    if abs(float(db_val or 0) - float(api_val or 0)) > 0.01:
                        mismatches.append(f"{db_field}: DB={db_val}, API={api_val}")
                elif str(db_val) != str(api_val):
                    mismatches.append(f"{db_field}: DB={db_val}, API={api_val}")
        
        return {
            'valid': len(mismatches) == 0,
            'mismatches': mismatches if mismatches else None
        }
    
    def _check_audience(self, kol_id: str, apis: Dict) -> Dict:
        db_data = self.client.table('gg_pgy_kol_audience').select('*').eq('kol_id', kol_id).execute()
        api_code = apis.get('kol_fans_portrait', {}).get('code')
        
        if api_code != 0:
            return {'valid': True, 'note': 'API返回非0，跳过'}
        
        if not db_data.data:
            return {'valid': False, 'error': '数据库中无记录'}
        
        return {'valid': True, 'count': len(db_data.data)}
    
    def _check_fans_summary(self, kol_id: str, apis: Dict) -> Dict:
        db_data = self.client.table('gg_pgy_kol_fans_summary').select('*').eq('kol_id', kol_id).execute()
        api_code = apis.get('kol_fans_summary', {}).get('code')
        
        if api_code != 0:
            return {'valid': True, 'note': 'API返回非0，跳过'}
        
        if not db_data.data:
            return {'valid': False, 'error': '数据库中无记录'}
        
        return {'valid': True, 'count': len(db_data.data)}
    
    def _check_fans_trend(self, kol_id: str, apis: Dict) -> Dict:
        db_data = self.client.table('gg_pgy_kol_fans_trend').select('*').eq('kol_id', kol_id).execute()
        api_data = apis.get('kol_fans_trend', {}) or {}
        data = api_data.get('data', {}) or {}
        api_list = data.get('list', []) or []
        
        db_count = len(db_data.data)
        api_count = len(api_list)
        
        return {
            'valid': db_count == api_count,
            'db_count': db_count,
            'api_count': api_count
        }
    
    def _check_note_rate(self, kol_id: str, apis: Dict) -> Dict:
        db_data = self.client.table('gg_pgy_kol_note_rate').select('*').eq('kol_id', kol_id).execute()
        api_code = apis.get('kol_note_rate', {}).get('code')
        
        if api_code != 0:
            return {'valid': True, 'note': 'API返回非0，跳过'}
        
        if not db_data.data:
            return {'valid': False, 'error': '数据库中无记录'}
        
        return {'valid': True, 'count': len(db_data.data)}
    
    def _check_notes(self, kol_id: str, apis: Dict) -> Dict:
        db_data = self.client.table('gg_pgy_kol_notes').select('*').eq('kol_id', kol_id).execute()
        api_data = apis.get('kol_note_list', {}) or {}
        data = api_data.get('data', {}) or {}
        api_list = data.get('list', []) or []
        
        db_count = len(db_data.data)
        api_count = len(api_list)
        
        return {
            'valid': db_count == api_count,
            'db_count': db_count,
            'api_count': api_count
        }
    
    def _check_cost_effective(self, kol_id: str, apis: Dict) -> Dict:
        db_data = self.client.table('gg_pgy_kol_cost_effective').select('*').eq('kol_id', kol_id).execute()
        api_code = apis.get('kol_cost_effective', {}).get('code')
        
        if api_code != 0:
            return {'valid': True, 'note': 'API返回非0，跳过'}
        
        if not db_data.data:
            return {'valid': False, 'error': '数据库中无记录'}
        
        return {'valid': True, 'count': len(db_data.data)}
    
    def _check_core_data(self, kol_id: str, apis: Dict) -> Dict:
        db_data = self.client.table('gg_pgy_kol_core_data').select('*').eq('kol_id', kol_id).execute()
        core_data = apis.get('kol_core_data', {}) or {}
        data = core_data.get('data', {}) or {}
        api_list = data.get('dailyData', []) or []
        
        db_count = len(db_data.data)
        api_count = len(api_list)
        
        return {
            'valid': db_count == api_count,
            'db_count': db_count,
            'api_count': api_count
        }
    
    def validate_all(self, kol_ids: List[str] = None, limit: int = None) -> Dict[str, Any]:
        """验证所有或指定的KOL"""
        if kol_ids is None:
            kol_ids = []
            for item in sorted(self.data_dir.iterdir()):
                if item.is_dir() and item.name.startswith('kol_'):
                    kol_ids.append(item.name.replace('kol_', ''))
        
        if limit:
            kol_ids = kol_ids[:limit]
        
        results = {
            'total': len(kol_ids),
            'valid': 0,
            'invalid': 0,
            'details': []
        }
        
        for i, kol_id in enumerate(kol_ids):
            if (i + 1) % 50 == 0:
                logger.info(f"验证进度: {i+1}/{len(kol_ids)}")
            
            result = self.validate_kol(kol_id)
            results['details'].append(result)
            
            if result['valid']:
                results['valid'] += 1
            else:
                results['invalid'] += 1
        
        return results


class DataReporter:
    """数据报告生成器"""
    
    def __init__(self):
        self.client = self._load_supabase_client()
    
    def _load_supabase_client(self):
        from supabase import create_client
        
        backend_dir = Path(__file__).parent.parent.parent.parent
        env_path = backend_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        return create_client(url, key)
    
    def generate_report(self) -> Dict[str, Any]:
        """生成完整的数据报告"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'tables': {}
        }
        
        tables_config = {
            'gg_pgy_kol_base_info': [
                'kol_id', 'kol_name', 'red_id', 'gender', 'location', 'head_photo',
                'fans_count', 'like_collect_count', 'business_note_count', 'total_note_count',
                'picture_price', 'video_price', 'lower_price', 'content_tags', 'feature_tags',
                'personal_tags', 'trade_type', 'click_mid_num', 'inter_mid_num',
                'fans_30_growth_num', 'fans_30_growth_rate', 'current_level', 'cooper_type',
                'user_type', 'low_active', 'kol_advantage', 'cooperate_state',
                'response_rate', 'invite_num', 'active_day_in_last_7', 'is_active', 'easy_connect'
            ],
            'gg_pgy_kol_audience': [
                'kol_id', 'gender_distribution', 'age_distribution', 'province_distribution',
                'city_distribution', 'device_distribution', 'interest_distribution', 'date_key'
            ],
            'gg_pgy_kol_fans_summary': [
                'kol_id', 'fans_num', 'fans_increase_num', 'fans_growth_rate',
                'fans_growth_beyond_rate', 'active_fans_l28', 'active_fans_rate',
                'active_fans_beyond_rate', 'engage_fans_l30', 'engage_fans_rate',
                'engage_fans_beyond_rate', 'read_fans_in_30', 'read_fans_rate',
                'read_fans_beyond_rate', 'pay_fans_user_rate_30d', 'pay_fans_user_num_30d'
            ],
            'gg_pgy_kol_note_rate': [
                'kol_id', 'note_number', 'video_note_number', 'imp_median',
                'imp_median_beyond_rate', 'read_median', 'read_median_beyond_rate',
                'interaction_median', 'interaction_rate', 'interaction_beyond_rate',
                'like_median', 'collect_median', 'comment_median', 'share_median',
                'hundred_like_percent', 'thousand_like_percent'
            ],
            'gg_pgy_kol_cost_effective': [
                'kol_id', 'picture_read_cost', 'picture_surpass_rate', 'picture_case',
                'estimate_picture_cpm', 'estimate_picture_cpm_compare', 'estimate_picture_engage_cost',
                'estimate_picture_engage_cost_compare', 'video_read_cost', 'video_surpass_rate',
                'video_case', 'estimate_video_cpm', 'estimate_video_cpm_compare',
                'estimate_video_engage_cost', 'estimate_video_engage_cost_compare'
            ]
        }
        
        for table_name, fields in tables_config.items():
            logger.info(f"分析表: {table_name}")
            table_report = self._analyze_table(table_name, fields)
            report['tables'][table_name] = table_report
        
        # 统计多条记录的表
        multi_record_tables = {
            'gg_pgy_kol_fans_trend': 'fans_num',
            'gg_pgy_kol_notes': 'read_num',
            'gg_pgy_kol_core_data': 'imp'
        }
        
        for table_name, sample_field in multi_record_tables.items():
            logger.info(f"分析表(多记录): {table_name}")
            count_result = self.client.table(table_name).select('kol_id', count='exact').execute()
            report['tables'][table_name] = {
                'total_records': count_result.count if hasattr(count_result, 'count') else len(count_result.data),
                'note': '多记录表，每个KOL有多条记录'
            }
        
        return report
    
    def _analyze_table(self, table_name: str, fields: List[str]) -> Dict[str, Any]:
        """分析单个表的字段空值情况"""
        # 获取所有记录
        result = self.client.table(table_name).select(','.join(fields)).execute()
        
        if not result.data:
            return {'total_records': 0, 'fields': {}}
        
        total = len(result.data)
        field_stats = {}
        
        for field in fields:
            null_count = sum(1 for row in result.data if row.get(field) is None)
            empty_count = sum(1 for row in result.data if row.get(field) == '' or row.get(field) == [] or row.get(field) == {})
            valid_count = total - null_count - empty_count
            
            field_stats[field] = {
                'total': total,
                'valid': valid_count,
                'null': null_count,
                'empty': empty_count,
                'valid_rate': f"{100 * valid_count / total:.1f}%",
                'null_rate': f"{100 * null_count / total:.1f}%"
            }
        
        return {
            'total_records': total,
            'fields': field_stats
        }
    
    def print_report(self, report: Dict[str, Any]):
        """打印报告"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 数据质量报告")
        logger.info(f"   生成时间: {report['generated_at']}")
        logger.info("=" * 80)
        
        for table_name, table_data in report['tables'].items():
            logger.info("")
            logger.info(f"📋 表: {table_name}")
            logger.info(f"   记录数: {table_data['total_records']}")
            
            if 'fields' in table_data:
                logger.info("   字段空值统计:")
                logger.info(f"   {'字段名':<35} {'有效数':<10} {'空值数':<10} {'有效率':<10} {'空值率':<10}")
                logger.info("   " + "-" * 75)
                
                for field_name, stats in table_data['fields'].items():
                    logger.info(f"   {field_name:<35} {stats['valid']:<10} {stats['null']:<10} {stats['valid_rate']:<10} {stats['null_rate']:<10}")
            
            if 'note' in table_data:
                logger.info(f"   备注: {table_data['note']}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='导入API数据到数据库')
    parser.add_argument('--limit', type=int, default=None, help='限制导入数量（用于测试）')
    parser.add_argument('--concurrency', type=int, default=10, help='并发数（默认10）')
    parser.add_argument('--validate', action='store_true', help='仅验证数据，不导入')
    parser.add_argument('--validate-all', action='store_true', help='验证所有数据')
    parser.add_argument('--report', action='store_true', help='生成数据质量报告')
    parser.add_argument('--kol-id', type=str, help='指定单个KOL ID进行验证')
    parser.add_argument('--full', action='store_true', help='执行完整流程：导入+验证+报告')
    args = parser.parse_args()
    
    if args.report:
        reporter = DataReporter()
        report = reporter.generate_report()
        reporter.print_report(report)
        
        # 保存报告到文件
        report_file = Path(__file__).parent / "output" / "data_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"\n报告已保存到: {report_file}")
        
    elif args.validate or args.validate_all:
        validator = DataValidator()
        
        if args.kol_id:
            result = validator.validate_kol(args.kol_id)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            limit = None if args.validate_all else 10
            results = validator.validate_all(limit=args.limit or limit)
            print(f"\n✅ 验证结果: {results['valid']}/{results['total']} 通过")
            
            invalid_details = [d for d in results['details'] if not d['valid']]
            if invalid_details:
                print(f"\n❌ 失败详情 ({len(invalid_details)}):")
                for detail in invalid_details[:10]:
                    print(f"\n  {detail['kol_id']}:")
                    for check_name, check_result in detail.get('checks', {}).items():
                        if not check_result.get('valid'):
                            print(f"    {check_name}: {check_result}")
    
    elif args.full:
        # 完整流程：导入 + 验证 + 报告
        logger.info("🚀 开始完整流程：导入 → 验证 → 报告")
        
        # 1. 导入
        importer = ApiDataImporter(concurrency=args.concurrency)
        kol_dirs = importer.get_all_kol_dirs()
        importer.import_kols_concurrent(kol_dirs, limit=args.limit)
        
        # 2. 验证
        logger.info("\n" + "=" * 70)
        logger.info("🔍 开始验证导入的数据...")
        validator = DataValidator()
        results = validator.validate_all(limit=args.limit)
        logger.info(f"\n✅ 验证结果: {results['valid']}/{results['total']} 通过")
        
        invalid_count = results['invalid']
        if invalid_count > 0:
            logger.warning(f"⚠️ 有 {invalid_count} 个KOL数据验证失败")
        
        # 3. 报告
        logger.info("\n" + "=" * 70)
        logger.info("📊 生成数据质量报告...")
        reporter = DataReporter()
        report = reporter.generate_report()
        reporter.print_report(report)
        
        # 保存报告
        report_file = Path(__file__).parent / "output" / "data_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"\n📁 报告已保存到: {report_file}")
        
    else:
        # 仅导入
        importer = ApiDataImporter(concurrency=args.concurrency)
        kol_dirs = importer.get_all_kol_dirs()
        
        if args.limit:
            logger.info(f"测试模式：仅导入前 {args.limit} 个KOL")
        
        importer.import_kols_concurrent(kol_dirs, limit=args.limit)


if __name__ == "__main__":
    main()
