#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取指定 KOL 的全部数据

用于生成 KOL 分析报告
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any
import time


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "params" / "config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_api_token() -> str:
    """从环境变量加载 Just One API Token"""
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    return os.getenv('JUSTONEAPI_API_KEY', '')


def call_api(base_url: str, endpoint: str, token: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    """调用 Just One API"""
    url = f"{base_url}{endpoint}"
    params['token'] = token
    
    print(f"  📡 {endpoint.split('/')[-2]}/{endpoint.split('/')[-1]}")
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code == 200:
            result = response.json()
            code = result.get('code', 'N/A')
            print(f"     ✅ code={code}")
            return result
        else:
            print(f"     ❌ HTTP {response.status_code}")
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"     ❌ {str(e)[:50]}")
        return {"error": str(e)}


def fetch_all_kol_data(kol_id: str, kol_name: str) -> Dict[str, Any]:
    """
    获取 KOL 的全部数据
    """
    config = load_config()
    token = load_api_token()
    base_url = config['api_base_url']
    endpoints = config['接口列表']
    
    print(f"\n{'='*60}")
    print(f"🔍 获取 KOL 数据: {kol_name} ({kol_id})")
    print(f"{'='*60}")
    
    results = {}
    
    # 1. KOL 基础信息
    print("\n[1/10] KOL 基础信息")
    results['kol_info'] = call_api(base_url, endpoints['kol_info'], token, {
        'kolId': kol_id, 'acceptCache': 'true'
    })
    time.sleep(0.5)
    
    # 2. KOL 笔记数据率
    print("\n[2/10] KOL 笔记数据率")
    results['kol_note_rate'] = call_api(base_url, endpoints['kol_note_rate'], token, {
        'kolId': kol_id, 'dateType': '_1', 'noteType': '_3', 
        'adSwitch': '_1', 'business': '_0', 'acceptCache': 'true'
    })
    time.sleep(0.5)
    
    # 3. KOL 粉丝画像
    print("\n[3/10] KOL 粉丝画像")
    results['kol_fans_portrait'] = call_api(base_url, endpoints['kol_fans_portrait'], token, {
        'kolId': kol_id, 'acceptCache': 'true'
    })
    time.sleep(0.5)
    
    # 4. KOL 粉丝分析
    print("\n[4/10] KOL 粉丝分析")
    results['kol_fans_summary'] = call_api(base_url, endpoints['kol_fans_summary'], token, {
        'kolId': kol_id, 'acceptCache': 'true'
    })
    time.sleep(0.5)
    
    # 5. KOL 粉丝趋势
    print("\n[5/10] KOL 粉丝趋势")
    results['kol_fans_trend'] = call_api(base_url, endpoints['kol_fans_trend'], token, {
        'kolId': kol_id, 'dateType': '_1', 'increaseType': '_1', 'acceptCache': 'true'
    })
    time.sleep(0.5)
    
    # 6. KOL 笔记列表 (可能为空)
    print("\n[6/10] KOL 笔记列表")
    results['kol_note_list'] = call_api(base_url, endpoints['kol_note_list'], token, {
        'kolId': kol_id, 'page': 1, 'adSwitch': '_1', 
        'orderType': '_1', 'noteType': '_4', 'acceptCache': 'true'
    })
    time.sleep(0.5)
    
    # 7. KOL 数据概览 V1
    print("\n[7/10] KOL 数据概览 V1")
    results['kol_data_summary_v1'] = call_api(base_url, endpoints['kol_data_summary_v1'], token, {
        'kolId': kol_id, 'business': '_0', 'acceptCache': 'true'
    })
    time.sleep(0.5)
    
    # 8. KOL 数据概览 V2
    print("\n[8/10] KOL 数据概览 V2")
    results['kol_data_summary_v2'] = call_api(base_url, endpoints['kol_data_summary_v2'], token, {
        'kolId': kol_id, 'business': '_0', 'acceptCache': 'true'
    })
    time.sleep(0.5)
    
    # 9. KOL 性价比分析
    print("\n[9/10] KOL 性价比分析")
    results['kol_cost_effective'] = call_api(base_url, endpoints['kol_cost_effective'], token, {
        'kolId': kol_id, 'acceptCache': 'true'
    })
    time.sleep(0.5)
    
    # 10. KOL 核心数据
    print("\n[10/10] KOL 核心数据")
    results['kol_core_data'] = call_api(base_url, endpoints['kol_core_data'], token, {
        'kolId': kol_id, 'dateType': '_1', 'noteType': '_3',
        'adSwitch': '_1', 'business': '_0', 'acceptCache': 'true'
    })
    
    return results


def save_results(results: Dict[str, Any], kol_id: str, kol_name: str) -> Path:
    """保存结果"""
    output_dir = Path(__file__).parent.parent / "output" / f"kol_{kol_name}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存每个接口的结果
    for api_name, data in results.items():
        filepath = output_dir / f"{api_name}_{timestamp}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 保存汇总
    summary_path = output_dir / f"all_data_{timestamp}.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            'kol_id': kol_id,
            'kol_name': kol_name,
            'fetch_time': datetime.now().isoformat(),
            'data': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 数据已保存到: {output_dir}")
    return output_dir


def main():
    # 荔枝吱吱
    kol_id = "5d21ab6b000000001201567d"
    kol_name = "荔枝吱吱"
    
    results = fetch_all_kol_data(kol_id, kol_name)
    output_dir = save_results(results, kol_id, kol_name)
    
    # 打印汇总
    print(f"\n{'='*60}")
    print("📋 数据获取汇总")
    print(f"{'='*60}")
    
    for api_name, data in results.items():
        code = data.get('code', data.get('error', 'N/A'))
        status = "✅" if code == 0 else "❌"
        print(f"  {api_name}: {status} (code={code})")


if __name__ == "__main__":
    main()
