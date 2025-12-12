#!/usr/bin/env python3
"""
MCN公司广告费调研脚本 - 使用 Gemini Deep Research API

调研主题：
中国MCN公司在服务品牌客户时的广告费收取模式，包括：
1. 广告费收取比例（10%-40%的波动原因）
2. 不同收费比例对应的服务内容
3. MCN公司与广告公司在网红工作方面的区别

使用方法:
    cd backend
    source .venv/bin/activate
    python -m test.deep_research.mcn_research
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from google import genai
except ImportError:
    print("❌ 请安装 google-genai: pip install google-genai")
    sys.exit(1)


def get_gemini_api_key() -> str:
    """获取 Gemini API Key"""
    api_key = os.getenv("GEMINI_API_KEY_ANALYZE") or os.getenv("GEMINI_API_KEY")
    
    if api_key:
        return api_key
    
    # 尝试从 .env 文件读取
    env_paths = [
        Path(__file__).parent.parent.parent / ".env",
        Path(__file__).parent / ".env",
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY_ANALYZE="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
                    if line.startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    
    raise RuntimeError(
        "未找到 GEMINI_API_KEY_ANALYZE 或 GEMINI_API_KEY 环境变量。\n"
        "请在 backend/.env 中配置或设置环境变量。"
    )


def run_deep_research(prompt: str, output_dir: Path) -> dict:
    """
    运行 Gemini Deep Research Agent
    
    Args:
        prompt: 研究主题和问题
        output_dir: 输出目录
        
    Returns:
        研究结果字典
    """
    api_key = get_gemini_api_key()
    client = genai.Client(api_key=api_key)
    
    print("=" * 60)
    print("🔬 Gemini Deep Research Agent - MCN广告费调研")
    print("=" * 60)
    print(f"\n📝 研究主题:\n{prompt[:500]}...")
    print("\n" + "-" * 60)
    
    # 启动 Deep Research Agent
    print("\n🚀 启动 Deep Research Agent...")
    print("   Agent: deep-research-pro-preview-12-2025")
    print("   模式: 后台异步执行 (background=True)")
    
    try:
        interaction = client.interactions.create(
            input=prompt,
            agent="deep-research-pro-preview-12-2025",
            background=True
        )
        
        interaction_id = interaction.id
        print(f"\n✅ 研究任务已启动")
        print(f"   Interaction ID: {interaction_id}")
        print(f"   状态: {interaction.status}")
        
    except Exception as e:
        print(f"\n❌ 启动研究任务失败: {e}")
        raise
    
    # 轮询等待结果
    print("\n⏳ 等待研究完成...")
    print("   (Deep Research 通常需要 5-20 分钟，最长 60 分钟)")
    print()
    
    poll_interval = 15  # 每15秒检查一次
    max_wait_time = 60 * 60  # 最长等待60分钟
    start_time = time.time()
    last_status = None
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > max_wait_time:
            print(f"\n⚠️ 超时: 已等待超过 {max_wait_time // 60} 分钟")
            break
        
        try:
            interaction = client.interactions.get(interaction_id)
            current_status = interaction.status
            
            # 状态变化时打印
            if current_status != last_status:
                print(f"   [{datetime.now().strftime('%H:%M:%S')}] 状态: {current_status}")
                last_status = current_status
            else:
                # 每分钟打印一次进度
                if int(elapsed) % 60 == 0 and int(elapsed) > 0:
                    print(f"   [{datetime.now().strftime('%H:%M:%S')}] 已等待 {int(elapsed // 60)} 分钟...")
            
            if current_status == "completed":
                print(f"\n✅ 研究完成! (耗时: {int(elapsed // 60)} 分钟 {int(elapsed % 60)} 秒)")
                break
            elif current_status == "failed":
                error_msg = getattr(interaction, 'error', '未知错误')
                print(f"\n❌ 研究失败: {error_msg}")
                break
            elif current_status == "cancelled":
                print(f"\n⚠️ 研究被取消")
                break
                
        except Exception as e:
            print(f"   [{datetime.now().strftime('%H:%M:%S')}] 轮询出错: {e}")
        
        time.sleep(poll_interval)
    
    # 提取结果
    result = {
        "interaction_id": interaction_id,
        "status": interaction.status,
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": time.time() - start_time,
        "report": None,
        "outputs": []
    }
    
    if interaction.status == "completed" and interaction.outputs:
        # 获取最终报告文本
        for output in interaction.outputs:
            output_data = {
                "type": getattr(output, 'type', 'unknown'),
            }
            if hasattr(output, 'text') and output.text:
                output_data["text"] = output.text
                # 最后一个文本输出通常是最终报告
                result["report"] = output.text
            result["outputs"].append(output_data)
    
    # 保存结果
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存 JSON 结果
    json_path = output_dir / f"mcn_research_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n📄 JSON 结果已保存: {json_path}")
    
    # 保存 Markdown 报告
    if result["report"]:
        md_path = output_dir / f"mcn_research_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# MCN公司广告费调研报告\n\n")
            f.write(f"**生成时间**: {result['timestamp']}\n\n")
            f.write(f"**耗时**: {int(result['elapsed_seconds'] // 60)} 分钟 {int(result['elapsed_seconds'] % 60)} 秒\n\n")
            f.write(f"---\n\n")
            f.write(result["report"])
        print(f"📝 Markdown 报告已保存: {md_path}")
    
    return result


def main():
    """主函数"""
    # 定义研究问题
    research_prompt = """
请深入调研以下主题：

# 中国MCN公司在KOL/KOC合作中的广告费收取模式研究

## 研究背景
中国的MCN公司在服务品牌客户时，负责寻找和对接社交媒体网红（如小红书、抖音上的KOL和KOC）。据了解，他们的广告费收取比例通常在10%-40%之间波动。

## 需要调研的问题

### 1. 广告费收取比例
- MCN公司收取的广告费比例一般是多少？
- 这个10%-40%的波动范围是否准确？
- 不同规模的MCN公司收费标准有何差异？

### 2. 服务内容与收费关系
- 不同收费比例对应哪些具体服务内容？
- 服务可能包括：
  - 达人搜索与筛选
  - 建联与对接
  - 内容创作优化
  - 投放效果监测
  - 数据分析报告
- 收费高低是否与服务内容多少直接相关？
- 是否也与整体广告费金额有关？

### 3. 责任与收费比例的关系
- 承担更多责任（如效果承诺）是否收费更高？
- 有哪些常见的合作模式和定价方式？
- 品牌方如何选择合适的合作模式？

### 4. MCN公司 vs 广告公司
- MCN公司和广告公司在网红营销方面有什么本质区别？
- 各自的优势和劣势是什么？
- 在什么情况下品牌应该选择MCN公司，什么情况下选择广告公司？
- 两者的收费模式有何不同？

## 输出要求
请提供：
1. 详细的市场调研数据
2. 具体的收费案例和行业标准
3. 清晰的服务内容分类和对应收费
4. MCN与广告公司的对比分析
5. 对品牌方的建议

请确保信息来源可靠，尽量引用行业报告、权威媒体报道或公开数据。
"""
    
    # 输出目录
    output_dir = Path(__file__).parent / "output"
    
    print("\n" + "=" * 60)
    print("🔬 MCN公司广告费调研 - Gemini Deep Research")
    print("=" * 60)
    
    try:
        result = run_deep_research(research_prompt, output_dir)
        
        print("\n" + "=" * 60)
        print("📊 调研结果摘要")
        print("=" * 60)
        
        if result["report"]:
            # 打印报告前2000字符作为预览
            preview = result["report"][:2000]
            print(f"\n{preview}")
            if len(result["report"]) > 2000:
                print(f"\n... (完整报告共 {len(result['report'])} 字符，请查看保存的文件)")
        else:
            print("\n⚠️ 未能获取到研究报告")
            
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
