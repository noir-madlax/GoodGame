#!/usr/bin/env python3
"""
视频内容分析工具
使用 Gemini 2.0 Flash 模型对 KOL 带货视频进行深度分析。
输入：视频文件
输出：JSON 格式的分析报告
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
# 注意：用户提到的 "gemini 2.5 flash" 
GEMINI_MODEL = "gemini-2.5-flash" 
PROMPT_FILE = Path(__file__).parent / "video_analysis_prompt.txt"

def load_env_vars() -> str:
    """加载环境变量并获取 API Key"""
    current_dir = Path(__file__).parent
    # 尝试向上查找 .env 文件
    # 路径: backend/test/kol/(Tikhub)GetKOLVideosBatchByVVID/code/ -> backend/.env
    backend_dir = current_dir.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量: {env_path}")
    else:
        print(f"⚠️ 未找到 .env 文件或 python-dotenv 未安装: {env_path}")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_ANALYZE")
    if not api_key:
        raise RuntimeError("❌ 未找到 GEMINI_API_KEY 环境变量")
    
    return api_key

def load_prompt() -> str:
    """读取 Prompt 文件"""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {PROMPT_FILE}")
    
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def upload_video(client: genai.Client, video_path: Path) -> Any:
    """上传视频到 Gemini"""
    print(f"📤 正在上传视频: {video_path.name} ...")
    
    try:
        file_obj = client.files.upload(file=str(video_path))
        print(f"   - Upload URI: {file_obj.uri}")
        print(f"   - Initial State: {file_obj.state.name}")

        # 等待处理
        while file_obj.state.name == "PROCESSING":
            print("   - 等待视频处理中...", end="\r", flush=True)
            time.sleep(2)
            file_obj = client.files.get(name=file_obj.name)
        
        print(f"\n✅ 视频处理完成，状态: {file_obj.state.name}")
        
        if file_obj.state.name == "FAILED":
            raise RuntimeError(f"视频处理失败: {file_obj.error.message}")
            
        return file_obj
        
    except Exception as e:
        print(f"\n❌ 上传失败: {e}")
        raise

def analyze_video(video_path: str, output_path: str = None):
    """主分析函数"""
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ 视频文件不存在: {video_path}")
        return

    try:
        # 1. 初始化
        api_key = load_env_vars()
        client = genai.Client(api_key=api_key)
        prompt_text = load_prompt()
        
        print(f"🤖 使用模型: {GEMINI_MODEL}")
        
        # 2. 上传视频
        video_file = upload_video(client, video_path)
        
        # 3. 调用分析
        print("🧠 正在进行 AI 分析...")
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_uri(
                    file_uri=video_file.uri,
                    mime_type=video_file.mime_type
                ),
                prompt_text
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        
        # 4. 处理结果
        result_text = response.text
        
        # 尝试解析 JSON
        try:
            result_json = json.loads(result_text)
            formatted_result = json.dumps(result_json, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            print("⚠️ Warning: AI 返回的不是标准 JSON，保存原始文本")
            formatted_result = result_text
            result_json = {"raw_text": result_text}

        # 5. 保存结果
        if output_path:
            out_p = Path(output_path)
        else:
            # 默认保存在视频同级目录，文件名加 _analysis_2.5_flash
            out_p = video_path.parent / f"{video_path.stem}_analysis_2.5_flash.json"
            
        out_p.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_p, 'w', encoding='utf-8') as f:
            f.write(formatted_result)
            
        print(f"\n✅ 分析完成！结果已保存至: {out_p}")
        print("-" * 50)
        print(formatted_result[:500] + "...\n(内容过长已截断)")
        print("-" * 50)

        # 清理文件 (可选，Gemini 文件会自动过期，但主动清理是好习惯)
        try:
            client.files.delete(name=video_file.name)
            print("🧹 已清理云端临时文件")
        except Exception as e:
            print(f"🧹 清理文件失败 (不影响结果): {e}")

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 默认测试视频路径
    DEFAULT_VIDEO = Path(__file__).parent / "(LLM)analysisVideoByLLM" / "7509416656843902271_540p_latest.mp4"
    
    if len(sys.argv) > 1:
        target_video = sys.argv[1]
    elif DEFAULT_VIDEO.exists():
        target_video = str(DEFAULT_VIDEO)
    else:
        print("Usage: python analyze_video_content.py <video_path>")
        sys.exit(1)
        
    analyze_video(target_video)

