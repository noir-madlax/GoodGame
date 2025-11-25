#!/usr/bin/env python3
"""
脚本名称: 6_analyze_content_simple.py
功能描述: 使用Gemini Flash API分析帖子描述文本，提取其中提到的护肤达人信息
输入: ../output/file/{aweme_id}/metadata.json
输出: ../output/file/{aweme_id}/analysis.json
说明: 简化版本，仅分析文本描述，不处理视频和图片内容
"""

import os
import json
import time
import requests
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def load_env_vars():
    """加载环境变量"""
    project_root = Path(__file__).resolve().parents[4]
    backend_env = project_root / "backend/.env"
    
    if load_dotenv and backend_env.exists():
        load_dotenv(backend_env)


def get_gemini_api_key() -> str:
    """获取Gemini API Key"""
    api_key = os.getenv("GEMINI_API_KEY_ANALYZE") or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY_ANALYZE 或 GEMINI_API_KEY 未找到。"
            "请在 backend/.env 文件中设置"
        )
    
    return api_key.strip()


def call_gemini_api(
    api_key: str,
    system_prompt: str,
    user_text: str,
    model: str = "gemini-2.5-flash"
) -> dict:
    """调用Gemini API进行文本分析
    
    参数:
        api_key: API密钥
        system_prompt: 系统提示词
        user_text: 用户输入文本
        model: 模型名称
        
    返回:
        分析结果字典
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": user_text}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": system_prompt}
            ]
        },
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8000,
            "responseMimeType": "application/json"
        }
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            params={"key": api_key},
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                "error": f"API返回错误: HTTP {response.status_code}",
                "details": response.text[:500]
            }
        
        result = response.json()
        
        # 提取文本内容
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            analysis = json.loads(text)
            return analysis
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return {
                "error": f"解析响应失败: {e}",
                "raw_response": result
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "error": f"API请求失败: {e}"
        }


def process_single_item(
    api_key: str,
    system_prompt: str,
    aweme_id: str,
    file_dir: Path
) -> dict:
    """处理单个帖子
    
    参数:
        api_key: API密钥
        system_prompt: 系统提示词
        aweme_id: 帖子ID
        file_dir: 文件目录
        
    返回:
        分析结果字典
    """
    print(f"\n处理帖子: {aweme_id}")
    
    # 读取元数据
    metadata_path = file_dir / "metadata.json"
    if not metadata_path.exists():
        return {
            "aweme_id": aweme_id,
            "error": "元数据文件不存在",
            "success": False
        }
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    content_type = metadata.get("content_type")
    desc = metadata.get("desc", "")
    author = metadata.get("author", {})
    
    print(f"  类型: {content_type}")
    print(f"  描述: {desc[:100]}...")
    
    # 构建用户输入
    user_text = f"""以下是抖音{content_type}帖子的内容：

【标题/描述】: {desc}

【作者】: {author.get('nickname', '未知')}

请分析这个帖子的标题描述，识别其中提到的护肤/美妆达人信息。"""
    
    print("  调用Gemini API分析...")
    
    analysis = call_gemini_api(api_key, system_prompt, user_text)
    
    if "error" in analysis:
        print(f"  ✗ 分析失败: {analysis['error']}")
        return {
            "aweme_id": aweme_id,
            "error": analysis["error"],
            "success": False
        }
    
    # 保存分析结果
    analysis_path = file_dir / "analysis.json"
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump({
            "aweme_id": aweme_id,
            "content_type": content_type,
            "desc": desc,
            "analysis": analysis,
            "analyzed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "note": "仅分析了标题描述文本"
        }, f, ensure_ascii=False, indent=2)
    
    # 提取KOL信息
    kols_found = analysis.get("total_kols_found", 0)
    is_relevant = analysis.get("content_analysis", {}).get("is_relevant", False)
    
    print(f"  ✓ 分析完成: 发现 {kols_found} 位达人")
    if not is_relevant:
        print(f"  ℹ 内容不相关")
    
    return {
        "aweme_id": aweme_id,
        "success": True,
        "is_relevant": is_relevant,
        "kols_found": kols_found,
        "analysis_path": str(analysis_path)
    }


def main() -> None:
    print("=" * 80)
    print("Gemini API内容分析脚本 - 识别护肤达人（简化版）")
    print("=" * 80)
    
    # 加载环境变量
    print("\n[1/6] 加载环境变量...")
    load_env_vars()
    api_key = get_gemini_api_key()
    print("✓ API Key已加载")
    
    # 读取系统提示词
    print("\n[2/6] 读取分析提示词...")
    prompt_path = Path(__file__).resolve().parent / "kol_analysis_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")
    
    system_prompt = prompt_path.read_text(encoding='utf-8')
    print(f"✓ 提示词已加载 ({len(system_prompt)} 字符)")
    
    # 查找所有需要分析的目录
    print("\n[3/6] 扫描媒体文件目录...")
    output_dir = Path(__file__).resolve().parent.parent / "output" / "file"
    
    if not output_dir.exists():
        raise RuntimeError("媒体文件目录不存在，请先运行 5_download_media.py")
    
    # 获取所有aweme_id目录
    aweme_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    print(f"✓ 找到 {len(aweme_dirs)} 个帖子目录")
    
    # 处理每个帖子
    print("\n[4/6] 分析帖子内容...")
    results = []
    success_count = 0
    relevant_count = 0
    total_kols = 0
    
    for idx, aweme_dir in enumerate(aweme_dirs, 1):
        aweme_id = aweme_dir.name
        print(f"\n进度: {idx}/{len(aweme_dirs)}")
        
        result = process_single_item(api_key, system_prompt, aweme_id, aweme_dir)
        results.append(result)
        
        if result.get("success"):
            success_count += 1
            if result.get("is_relevant"):
                relevant_count += 1
                total_kols += result.get("kols_found", 0)
        
        # 避免API限流，稍作延迟
        time.sleep(0.5)
    
    # 保存汇总结果
    print("\n[5/6] 保存汇总结果...")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    summary_file = output_dir.parent / f"6_analysis_summary_{stamp}.json"
    
    summary = {
        "analysis_time": stamp,
        "total_items": len(aweme_dirs),
        "success_count": success_count,
        "failed_count": len(aweme_dirs) - success_count,
        "relevant_count": relevant_count,
        "irrelevant_count": success_count - relevant_count,
        "total_kols_found": total_kols,
        "results": results
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 汇总结果已保存: {summary_file}")
    
    # 打印统计信息
    print("\n" + "=" * 80)
    print("分析统计")
    print("=" * 80)
    print(f"总帖子数: {len(aweme_dirs)}")
    print(f"分析成功: {success_count}")
    print(f"分析失败: {len(aweme_dirs) - success_count}")
    print(f"相关内容: {relevant_count}")
    print(f"不相关内容: {success_count - relevant_count}")
    print(f"发现达人总数: {total_kols}")
    if relevant_count > 0:
        print(f"平均每个相关内容: {total_kols/relevant_count:.1f} 位达人")
    
    print("\n[6/6] 完成！")
    print("\n说明: 本次分析仅基于帖子的标题描述文本")
    print("      完整的图片和视频内容分析需要使用multimodal API")


if __name__ == "__main__":
    main()

