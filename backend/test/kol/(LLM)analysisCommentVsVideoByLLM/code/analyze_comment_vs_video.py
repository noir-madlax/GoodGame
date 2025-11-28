#!/usr/bin/env python3
"""
评论 VS 视频内容分析工具
对比视频分析结果与评论数据，评估评论质量和真实性。
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai package not found. Please install: pip install google-genai")
    sys.exit(1)

# 配置
# 用户要求使用 "2.5 flash" 模型，映射为 gemini-2.0-flash-exp (目前最新的 flash 模型)
GEMINI_MODEL = "gemini-2.5-flash"
PROMPT_FILE = Path(__file__).parent.parent / "analysisVideoByLLM/code/comment_analysis_prompt.txt"

def load_env_vars() -> str:
    """加载环境变量并获取 API Key"""
    current_dir = Path(__file__).parent
    # 路径: backend/test/kol/(LLM)analysisCommentVsVideoByLLM/code/ -> backend/.env
    backend_dir = current_dir.parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量: {env_path}")
    else:
        # Fallback search
        env_path_alt = Path("/Users/rigel/project/hdl-tikhub-goodgame/backend/.env")
        if env_path_alt.exists():
            load_dotenv(env_path_alt)
            print(f"✅ 已加载环境变量 (绝对路径): {env_path_alt}")
        else:
            print(f"⚠️ 未找到 .env 文件: {env_path}")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_ANALYZE")
    if not api_key:
        raise RuntimeError("❌ 未找到 GEMINI_API_KEY 环境变量")
    
    return api_key

def load_file_content(file_path: str) -> str:
    """读取文件内容"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def analyze_comments(video_analysis_path: str, comments_path: str, output_path: str = None):
    """主分析函数"""
    try:
        # 1. 初始化
        api_key = load_env_vars()
        client = genai.Client(api_key=api_key)
        
        # 2. 读取输入数据
        print("📖 读取输入文件...")
        video_analysis = load_file_content(video_analysis_path)
        comments_data = load_file_content(comments_path)
        
        # 3. 读取 Prompt
        # Prompt 在当前脚本同级目录下
        prompt_path = Path(__file__).parent / "comment_analysis_prompt.txt"
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt 文件未找到: {prompt_path}")
            
        prompt_template = load_file_content(prompt_path)
        
        # 4. 构建完整 Prompt
        final_prompt = f"""
{prompt_template}

---
**Input 1: 视频内容分析数据**
{video_analysis}

---
**Input 2: 用户评论数据**
{comments_data}
"""

        print(f"🤖 使用模型: {GEMINI_MODEL}")
        print("🧠 正在进行评论深度分析...")
        
        # 5. 调用 AI
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=final_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        
        # 6. 处理结果
        result_text = response.text
        
        try:
            result_json = json.loads(result_text)
            formatted_result = json.dumps(result_json, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            print("⚠️ Warning: AI 返回的不是标准 JSON，保存原始文本")
            formatted_result = result_text

        # 7. 保存结果
        if output_path:
            out_p = Path(output_path)
        else:
            # 默认保存在评论文件同级目录下，文件名加 _quality_analysis_2.5_flash
            comments_p = Path(comments_path)
            out_p = comments_p.parent / f"{comments_p.stem}_quality_analysis_2.5_flash.json"
            
        out_p.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_p, 'w', encoding='utf-8') as f:
            f.write(formatted_result)
            
        print(f"\n✅ 评论分析完成！结果已保存至: {out_p}")
        print("-" * 50)
        print(formatted_result[:500] + "...\n(内容过长已截断)")
        print("-" * 50)

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python analyze_comment_vs_video.py <video_analysis_json> <comments_json> [output_json]")
        sys.exit(1)
        
    video_analysis_file = sys.argv[1]
    comments_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    analyze_comments(video_analysis_file, comments_file, output_file)

