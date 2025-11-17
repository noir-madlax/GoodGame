"""
星图接口工具函数
提供共享的配置加载、数据保存等功能
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime


def load_api_key():
    """从环境变量加载TikHub API Key"""
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    api_key = os.getenv('tikhub_API_KEY')
    if not api_key:
        raise ValueError(f"环境变量 tikhub_API_KEY 未设置")
    return api_key


def load_cookie():
    """
    从cookie文件加载Cookie
    
    Returns:
        Cookie字符串
    """
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    cookie_path = backend_dir / 'test' / 'kol' / 'cookie'
    
    if not cookie_path.exists():
        return None
    
    try:
        with open(cookie_path, 'r', encoding='utf-8') as f:
            cookie_list = json.load(f)
            
        cookie_parts = []
        for cookie_item in cookie_list:
            if 'name' in cookie_item and 'value' in cookie_item:
                name = cookie_item['name']
                value = cookie_item['value']
                if name:
                    cookie_parts.append(f"{name}={value}")
        
        return '; '.join(cookie_parts)
    except Exception as e:
        print(f"⚠️ Cookie加载失败: {e}")
        return None


def load_kol_ids():
    """
    从kol_ids_only文件加载KOL ID列表
    
    Returns:
        KOL ID列表
    """
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    kol_ids_path = backend_dir / 'test' / 'kol' / 'output' / 'xingtu_kol_data' / 'kol_ids_only_20251113.json'
    
    if not kol_ids_path.exists():
        raise FileNotFoundError(f"KOL ID文件不存在: {kol_ids_path}")
    
    with open(kol_ids_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get('kol_ids', [])


def get_output_dir(interface_name: str):
    """
    获取接口输出目录
    
    Args:
        interface_name: 接口名称，如 'audience_portrait'
        
    Returns:
        输出目录路径
    """
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    output_dir = backend_dir / 'test' / 'kol' / 'output' / 'xingtu_kol_data' / interface_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def load_completed_kol_ids(interface_name: str):
    """
    加载已完成的KOL ID列表
    
    Args:
        interface_name: 接口名称
        
    Returns:
        已完成的KOL ID集合
    """
    output_dir = get_output_dir(interface_name)
    completed_file = output_dir / 'completed_kol_ids.json'
    
    if not completed_file.exists():
        return set()
    
    try:
        with open(completed_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return set(data.get('completed_kol_ids', []))
    except Exception:
        return set()


def save_completed_kol_id(interface_name: str, kol_id: str):
    """
    保存已完成的KOL ID
    
    Args:
        interface_name: 接口名称
        kol_id: KOL ID
    """
    output_dir = get_output_dir(interface_name)
    completed_file = output_dir / 'completed_kol_ids.json'
    
    # 加载现有数据
    if completed_file.exists():
        with open(completed_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {'completed_kol_ids': []}
    
    # 添加新ID
    if kol_id not in data['completed_kol_ids']:
        data['completed_kol_ids'].append(kol_id)
        data['last_updated'] = datetime.now().isoformat()
    
    # 保存
    with open(completed_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_result(interface_name: str, kol_info: dict, result: dict, success: bool):
    """
    保存接口调用结果
    
    Args:
        interface_name: 接口名称
        kol_info: KOL基本信息
        result: 接口返回结果
        success: 是否成功
    """
    output_dir = get_output_dir(interface_name)
    
    # 文件名：{rank}_{name}_{kol_id}.json
    filename = f"{kol_info['rank']}_{kol_info['name']}_{kol_info['xingtu_kol_id']}.json"
    filepath = output_dir / filename
    
    # 准备保存数据
    save_data = {
        'kol_info': {
            'rank': kol_info['rank'],
            'name': kol_info['name'],
            'xingtu_kol_id': kol_info['xingtu_kol_id'],
            'nick_name': kol_info.get('nick_name', ''),
            'fans_count': kol_info.get('fans_count', 0)
        },
        'interface': interface_name,
        'timestamp': datetime.now().isoformat(),
        'success': success,
        'result': result
    }
    
    # 保存到文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    # 如果成功，标记为已完成
    if success:
        save_completed_kol_id(interface_name, kol_info['xingtu_kol_id'])
    
    return filepath


def get_api_base_url(use_china_domain: bool = True):
    """获取API基础URL"""
    if use_china_domain:
        return "https://api.tikhub.dev/api/v1"
    else:
        return "https://api.tikhub.io/api/v1"

