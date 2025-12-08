#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
汇总分析所有接口测试结果

功能:
1. 读取所有阶段的测试结果
2. 生成接口可用性报告
3. 分析数据结构和业务价值
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "params" / "config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_api_results(output_dir: Path) -> Dict[str, Any]:
    """
    分析所有阶段的测试结果
    """
    results = {
        "phase1": {},
        "phase2": {},
        "phase3": {},
        "api_summary": {}
    }
    
    # 分析 Phase 1
    phase1_dir = output_dir / "phase1"
    if phase1_dir.exists():
        for json_file in phase1_dir.glob("*.json"):
            if "summary" not in json_file.name:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    api_name = json_file.stem.split('_')[0]
                    results["phase1"][api_name] = {
                        "code": data.get('code'),
                        "has_data": 'data' in data and data['data'] is not None,
                        "file": json_file.name
                    }
    
    # 分析 Phase 2
    phase2_dir = output_dir / "phase2"
    if phase2_dir.exists():
        for json_file in phase2_dir.glob("*.json"):
            if "summary" not in json_file.name:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    api_name = '_'.join(json_file.stem.split('_')[:-2])  # 去掉 ID 和时间戳
                    results["phase2"][api_name] = {
                        "code": data.get('code'),
                        "has_data": 'data' in data and data['data'] is not None,
                        "data_keys": list(data.get('data', {}).keys()) if isinstance(data.get('data'), dict) else [],
                        "file": json_file.name
                    }
    
    # 分析 Phase 3
    phase3_dir = output_dir / "phase3"
    if phase3_dir.exists():
        for json_file in phase3_dir.glob("*.json"):
            if "summary" not in json_file.name:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    api_name = '_'.join(json_file.stem.split('_')[:-2])
                    results["phase3"][api_name] = {
                        "code": data.get('code'),
                        "has_data": 'data' in data and data['data'] is not None,
                        "file": json_file.name
                    }
    
    return results


def generate_report(config: Dict, results: Dict) -> str:
    """
    生成汇总报告
    """
    report = []
    report.append("=" * 70)
    report.append("小红书蒲公英 (PGY) API 接口测试报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    
    # 接口列表
    endpoints = config.get('接口列表', {})
    
    report.append("\n## 一、接口列表概览")
    report.append("-" * 70)
    report.append(f"{'序号':<4} {'接口名称':<30} {'路径':<50}")
    report.append("-" * 70)
    
    for i, (name, path) in enumerate(endpoints.items(), 1):
        report.append(f"{i:<4} {name:<30} {path:<50}")
    
    report.append(f"\n总计: {len(endpoints)} 个接口")
    
    # 测试结果汇总
    report.append("\n## 二、测试结果汇总")
    report.append("-" * 70)
    
    # 统计
    all_apis = {}
    
    # 合并所有阶段的结果
    for phase, phase_results in results.items():
        if phase.startswith("phase"):
            for api_name, api_result in phase_results.items():
                if api_name not in all_apis:
                    all_apis[api_name] = api_result
    
    success_count = sum(1 for r in all_apis.values() if r.get('code') == 0)
    fail_count = len(all_apis) - success_count
    
    report.append(f"\n测试接口数: {len(all_apis)}")
    report.append(f"成功: {success_count}")
    report.append(f"失败: {fail_count}")
    report.append(f"成功率: {success_count/len(all_apis)*100:.1f}%" if all_apis else "N/A")
    
    # 详细结果
    report.append("\n### 接口测试详情")
    report.append("-" * 70)
    report.append(f"{'接口名称':<35} {'状态':<10} {'数据字段数':<10}")
    report.append("-" * 70)
    
    for api_name, api_result in sorted(all_apis.items()):
        code = api_result.get('code')
        status = "✅ 成功" if code == 0 else f"❌ 失败({code})"
        data_keys = api_result.get('data_keys', [])
        field_count = len(data_keys) if data_keys else "-"
        report.append(f"{api_name:<35} {status:<10} {str(field_count):<10}")
    
    # 接口分类说明
    report.append("\n## 三、接口分类说明")
    report.append("-" * 70)
    
    report.append("""
### KOL 相关接口 (需要 kolId 参数)
1. get-kol-info/v1 - KOL 基础信息 (头像、昵称、粉丝数等)
2. get-kol-note-rate/v1 - KOL 笔记数据率 (阅读率、互动率等)
3. get-kol-fans-portrait/v1 - KOL 粉丝画像 (年龄、性别、地域、兴趣等)
4. get-kol-fans-summary/v1 - KOL 粉丝分析 (粉丝质量、活跃度等)
5. get-kol-fans-trend/v1 - KOL 粉丝趋势 (粉丝增长曲线)
6. get-kol-track/v1 - 相似 KOL 推荐 (404，可能已下线)
7. get-kol-note-list/v1 - KOL 笔记列表 (该 KOL 发布的笔记)
8. get-kol-data-summary/v1 - KOL 数据概览 V1
9. get-kol-data-summary/v2 - KOL 数据概览 V2 (更详细)
10. get-kol-cost-effective/v1 - KOL 性价比分析 (301，可能需要特殊权限)
11. get-kol-core-data/v1 - KOL 核心数据

### 笔记相关接口 (需要 noteId 参数)
1. get-note-detail/v1 - 笔记详情 (已废弃，返回 301)
2. api/solar/note/noteId/detail/v1 - 笔记详情 Solar 版本 ✅ 推荐使用

### KOL 笔记列表接口 (需要 userId 参数)
1. api/solar/kol/dataV2/notesDetail/v1 - KOL 笔记详情 V2
""")
    
    # ID 获取说明
    report.append("\n## 四、ID 获取说明")
    report.append("-" * 70)
    report.append("""
### kolId / userId 获取方式
1. 从搜索结果的 widgets_context 字段中提取 author_id
2. 从笔记详情的 userId 字段获取
3. kolId 和 userId 在大多数情况下是相同的

### noteId 获取方式
1. 从搜索结果的 note.id 字段获取
2. 从 KOL 笔记列表接口获取
""")
    
    # 业务价值分析
    report.append("\n## 五、业务价值分析")
    report.append("-" * 70)
    report.append("""
### 高价值接口
1. **get-kol-fans-portrait/v1** - 粉丝画像数据非常详细
   - 年龄分布、性别比例
   - 地域分布 (省份、城市)
   - 兴趣标签
   - 设备品牌分布

2. **api/solar/note/noteId/detail/v1** - 笔记详情数据丰富
   - 曝光数、阅读数、点赞数、收藏数、评论数、分享数
   - 作者信息 (粉丝数、报价等)
   - 图片/视频信息

3. **get-kol-data-summary/v2** - KOL 数据概览最全面
   - 48 个数据字段
   - 包含各种维度的数据统计

### 注意事项
1. 部分接口返回 301，可能需要特殊权限或已下线
2. 建议使用 acceptCache=true 减少 API 调用成本
3. 某些 KOL 可能没有笔记数据 (list 为空)
""")
    
    return "\n".join(report)


def main():
    print("=" * 60)
    print("生成接口测试汇总报告")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    
    # 输出目录
    output_dir = Path(__file__).parent.parent / "output"
    
    # 分析结果
    results = analyze_api_results(output_dir)
    
    # 生成报告
    report = generate_report(config, results)
    
    # 打印报告
    print(report)
    
    # 保存报告
    report_path = output_dir / f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n💾 报告已保存: {report_path}")
    
    # 保存 JSON 格式的汇总
    summary = {
        "test_time": datetime.now().isoformat(),
        "config": config,
        "results": results,
        "statistics": {
            "total_apis": len(config.get('接口列表', {})),
            "tested_apis": sum(len(r) for r in results.values() if isinstance(r, dict)),
        }
    }
    
    summary_path = output_dir / f"api_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"💾 JSON 汇总已保存: {summary_path}")


if __name__ == "__main__":
    main()
