"""
接口 1.6: 获取KOL转化能力分析

功能: 获取KOL的转化能力分析数据，包括转化率、互动数据、GMV能力等

参数:
- kolId: KOL的星图ID
- _range: 时间范围
  - _3: 90天(last 90 days)

状态: 需要测试_range参数的正确值
"""

import requests
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent))

from utils import (
    load_api_key,
    load_cookie,
    load_kol_ids,
    load_completed_kol_ids,
    save_result,
    get_api_base_url
)


def get_kol_conversion_ability(api_key: str, kol_id: str, cookie: str):
    """
    调用转化能力分析接口
    
    Args:
        api_key: API密钥
        kol_id: 星图KOL ID
        cookie: Cookie字符串
        
    Returns:
        API响应数据
    """
    base_url = get_api_base_url(use_china_domain=True)
    endpoint = "/douyin/xingtu/kol_conversion_ability_analysis_v1"
    url = f"{base_url}{endpoint}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'Cookie': cookie
    }
    
    # 正确参数: kolId（驼峰） + _range=_3（90天）
    params = {
        'kolId': kol_id,
        '_range': '_3'  # _3=90天
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                return {'success': True, 'data': result}
            else:
                return {'success': False, 'error': result.get('message', 'Unknown error')}
        else:
            error_detail = response.json().get('detail', {})
            error_msg = error_detail.get('message_zh', error_detail.get('message', 'Unknown'))
            return {'success': False, 'error': f'HTTP {response.status_code}: {error_msg}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


def main():
    """主函数"""
    interface_name = 'conversion_ability'
    
    print('='*70)
    print('接口 1.6: 获取KOL转化能力分析')
    print('='*70)
    
    # 1. 加载配置
    print('\n1️⃣ 加载配置...')
    try:
        api_key = load_api_key()
        print('  ✅ API Key已加载')
    except Exception as e:
        print(f'  ❌ {e}')
        return
    
    cookie = load_cookie()
    if cookie:
        print(f'  ✅ Cookie已加载 (长度: {len(cookie)})')
    else:
        print('  ⚠️ Cookie未加载')
        return
    
    # 2. 加载KOL ID列表
    print('\n2️⃣ 加载KOL列表...')
    try:
        kol_list = load_kol_ids()
        print(f'  ✅ 加载了 {len(kol_list)} 个KOL')
    except Exception as e:
        print(f'  ❌ {e}')
        return
    
    # 3. 加载已完成的KOL
    completed_ids = load_completed_kol_ids(interface_name)
    print(f'\n3️⃣ 已完成: {len(completed_ids)} 个KOL')
    
    # 4. 过滤待处理KOL
    pending_kols = [kol for kol in kol_list if kol['xingtu_kol_id'] not in completed_ids]
    print(f'  待处理: {len(pending_kols)} 个KOL')
    
    if not pending_kols:
        print('\n✅ 所有KOL数据已获取完毕!')
        return
    
    # 5. 逐个处理KOL
    print(f'\n4️⃣ 开始获取转化能力分析数据...')
    print(f'  参数: kolId + _range=_3 (90天)')
    print('='*70)
    
    success_count = 0
    failed_count = 0
    
    for idx, kol in enumerate(pending_kols, 1):
        print(f'\n[{idx}/{len(pending_kols)}] {kol["name"]} (ID: {kol["xingtu_kol_id"]})')
        
        # 调用接口
        result = get_kol_conversion_ability(api_key, kol['xingtu_kol_id'], cookie)
        
        if result['success']:
            print(f'  ✅ 成功获取转化能力分析数据')
            # 保存结果
            filepath = save_result(interface_name, kol, result['data'], True)
            print(f'  💾 已保存: {filepath.name}')
            success_count += 1
        else:
            print(f'  ❌ 失败: {result["error"]}')
            # 也保存失败结果
            save_result(interface_name, kol, result, False)
            failed_count += 1
        
        # 避免请求过快
        if idx < len(pending_kols):
            import time
            time.sleep(1)
    
    # 7. 输出统计
    print('\n' + '='*70)
    print('处理完成!')
    print('='*70)
    print(f'成功: {success_count}')
    print(f'失败: {failed_count}')
    print(f'总计: {len(completed_ids) + success_count}/{len(kol_list)}')


if __name__ == '__main__':
    main()

