#!/usr/bin/env python3
"""
视频抄袭对比分析工具 - 使用 Gemini 2.5 Flash 进行视频相似度分析
支持长视频分析，自动调整采样率以控制 token 使用量
"""
import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import subprocess
import shutil

# 简化的日志类
class SimpleLogger:
    """简化的日志类"""
    def info(self, msg):
        print(f"[INFO] {msg}")
    
    def error(self, msg, exc_info=False):
        print(f"[ERROR] {msg}")
        if exc_info:
            import traceback
            traceback.print_exc()

log = SimpleLogger()

try:
    from google import genai
    from google.genai import types
except ImportError:
    log.error("需要安装 google-genai: pip install google-genai")
    sys.exit(1)


# Gemini 配置
GEMINI_MODEL_FLASH = "gemini-2.0-flash-exp"  # 用于视频分析
GEMINI_MODEL_PRO = "gemini-2.0-flash-thinking-exp"  # 用于生成报告

# Token 限制配置
MAX_VIDEO_TOKENS_PER_VIDEO = 800000  # 每个视频最大 token 数（保守估计）
ESTIMATED_TOKENS_PER_FRAME = 258  # 每帧估计 token 数


def load_api_key_from_env() -> str:
    """从 .env 文件加载 Gemini API Key"""
    # 先尝试从环境变量获取
    for env_var in ["GEMINI_API_KEY_ANALYZE", "GEMINI_API_KEY"]:
        api_key = os.getenv(env_var, "")
        if api_key:
            return api_key
    
    # 尝试从多个位置查找 .env 文件
    env_paths = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            log.info(f"从 {env_path} 加载环境变量")
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY_ANALYZE=") or line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if api_key:
                            return api_key
    
    raise RuntimeError("未找到 GEMINI_API_KEY 或 GEMINI_API_KEY_ANALYZE 环境变量")


def get_video_duration(video_path: Path) -> float:
    """获取视频时长（秒）
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        视频时长（秒）
    """
    try:
        # 使用 ffprobe 获取视频时长
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        log.error(f"获取视频时长失败: {e}")
        # 默认返回 20 分钟
        return 20 * 60


def calculate_optimal_fps(duration: float, max_tokens: int) -> float:
    """根据视频时长计算最优采样率
    
    Args:
        duration: 视频时长（秒）
        max_tokens: 最大允许 token 数
        
    Returns:
        最优采样率（fps）
    """
    # 计算最大允许帧数
    max_frames = max_tokens // ESTIMATED_TOKENS_PER_FRAME
    
    # 计算最优 fps
    optimal_fps = max_frames / duration
    
    # 限制在合理范围内
    if optimal_fps > 1.0:
        return 1.0
    elif optimal_fps > 0.5:
        return 0.5
    elif optimal_fps > 0.25:
        return 0.25
    else:
        return 0.1  # 最低 0.1fps


def extract_frames_from_video(
    video_path: Path,
    output_dir: Path,
    fps: float = 1.0,
    max_frames: Optional[int] = None
) -> List[Path]:
    """从视频中提取帧
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        fps: 采样率（每秒提取多少帧）
        max_frames: 最大帧数限制
        
    Returns:
        提取的帧文件路径列表
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 清空输出目录
    for f in output_dir.glob("frame_*.jpg"):
        f.unlink()
    
    log.info(f"从视频提取帧: {video_path.name}")
    log.info(f"采样率: {fps} fps")
    
    try:
        # 使用 ffmpeg 提取帧
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vf", f"fps={fps}",
            "-q:v", "2",  # 高质量
            str(output_dir / "frame_%06d.jpg")
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        # 获取提取的帧列表
        frames = sorted(output_dir.glob("frame_*.jpg"))
        
        # 限制帧数
        if max_frames and len(frames) > max_frames:
            log.info(f"限制帧数: {len(frames)} -> {max_frames}")
            # 均匀采样
            step = len(frames) / max_frames
            selected_frames = [frames[int(i * step)] for i in range(max_frames)]
            # 删除未选中的帧
            for f in frames:
                if f not in selected_frames:
                    f.unlink()
            frames = selected_frames
        
        log.info(f"✓ 成功提取 {len(frames)} 帧")
        return frames
    
    except Exception as e:
        log.error(f"提取帧失败: {e}", exc_info=True)
        raise


def upload_video_to_gemini(
    client: genai.Client,
    video_path: Path,
    display_name: Optional[str] = None
) -> Any:
    """上传视频到 Gemini File API
    
    Args:
        client: Gemini 客户端
        video_path: 视频文件路径
        display_name: 显示名称
        
    Returns:
        上传的文件对象
    """
    log.info(f"上传视频到 Gemini: {video_path.name}")
    
    if display_name is None:
        display_name = video_path.name
    
    try:
        # 上传文件 - 使用正确的 API
        file = client.files.upload(
            file=str(video_path)
        )
        
        log.info(f"✓ 视频上传成功: {file.name}")
        log.info(f"  - URI: {file.uri}")
        log.info(f"  - 状态: {file.state.name}")
        
        # 等待处理完成
        while file.state.name == "PROCESSING":
            log.info("  等待视频处理...")
            time.sleep(5)
            file = client.files.get(name=file.name)
        
        if file.state.name == "FAILED":
            raise RuntimeError(f"视频处理失败")
        
        log.info("✓ 视频处理完成")
        return file
    
    except Exception as e:
        log.error(f"上传视频失败: {e}", exc_info=True)
        raise


class VideoComparer:
    """视频对比分析器"""
    
    def __init__(self, api_key: str):
        """初始化视频对比分析器
        
        Args:
            api_key: Gemini API 密钥
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = GEMINI_MODEL_FLASH
    
    def compare_videos(
        self,
        video1_path: Path,
        video2_path: Path,
        fps: float = 1.0
    ) -> Dict[str, Any]:
        """对比两个视频
        
        Args:
            video1_path: 原始视频路径
            video2_path: 疑似抄袭视频路径
            fps: 采样率
            
        Returns:
            对比分析结果
        """
        log.info("=" * 80)
        log.info("开始视频对比分析")
        log.info("=" * 80)
        
        # 上传视频到 Gemini
        log.info("\n步骤 1: 上传视频到 Gemini File API")
        log.info("-" * 80)
        
        video1_file = upload_video_to_gemini(
            self.client,
            video1_path,
            display_name=f"原始视频: {video1_path.name}"
        )
        
        video2_file = upload_video_to_gemini(
            self.client,
            video2_path,
            display_name=f"疑似抄袭视频: {video2_path.name}"
        )
        
        # 构建分析提示词
        log.info("\n步骤 2: 调用 Gemini 进行视频对比分析")
        log.info("-" * 80)
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(video1_path.name, video2_path.name)
        
        # 配置生成参数
        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=8000,
            system_instruction=system_prompt,
            response_mime_type="application/json",  # 要求返回 JSON
        )
        
        # 调用 Gemini API
        log.info(f"使用模型: {self.model}")
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_uri(
                        file_uri=video1_file.uri,
                        mime_type=video1_file.mime_type
                    ),
                    types.Part.from_uri(
                        file_uri=video2_file.uri,
                        mime_type=video2_file.mime_type
                    ),
                    user_prompt
                ],
                config=config,
            )
            
            # 提取响应文本
            text = getattr(response, "text", None) or ""
            if not text:
                # 尝试从 candidates 提取
                try:
                    cand = (getattr(response, "candidates", None) or [None])[0]
                    content = getattr(cand, "content", None)
                    if hasattr(content, "parts"):
                        text = "".join(getattr(p, "text", "") for p in content.parts)
                except Exception:
                    pass
            
            if not text:
                raise RuntimeError("Gemini 返回空响应")
            
            # 记录 token 使用量
            usage_metadata = getattr(response, "usage_metadata", None)
            if usage_metadata:
                prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0)
                response_tokens = getattr(usage_metadata, "candidates_token_count", 0)
                total_tokens = getattr(usage_metadata, "total_token_count", 0)
                
                log.info(f"Token 使用统计:")
                log.info(f"  - 输入 Token: {prompt_tokens:,}")
                log.info(f"  - 输出 Token: {response_tokens:,}")
                log.info(f"  - 总计 Token: {total_tokens:,}")
            
            # 解析 JSON 响应
            analysis = json.loads(text)
            
            # 添加 token 使用信息到分析结果
            if usage_metadata:
                analysis["token_usage"] = {
                    "prompt_tokens": prompt_tokens,
                    "response_tokens": response_tokens,
                    "total_tokens": total_tokens,
                    "model": self.model
                }
            
            log.info("✓ 视频对比分析完成")
            
            # 清理上传的文件
            try:
                self.client.files.delete(name=video1_file.name)
                self.client.files.delete(name=video2_file.name)
                log.info("✓ 已清理临时文件")
            except Exception:
                pass
            
            return analysis
        
        except Exception as e:
            log.error(f"视频对比分析失败: {e}", exc_info=True)
            raise
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一位说中文的专业的视频内容分析专家和版权保护顾问，擅长识别视频抄袭、搬运和二次创作行为。

你的任务是：
1. 深入分析两个视频的相似性和差异性
2. 识别视频搬运、抄袭、二次创作的特征
3. 评估侵权风险等级
4. 提供详细、结构化的分析结果

分析维度：
1. **内容相似度**：场景、人物、对话、情节、主题等
2. **视觉相似度**：画面构图、色彩、运镜、剪辑风格等
3. **音频相似度**：背景音乐、配音、音效等
4. **时间结构相似度**：时长、节奏、情节顺序等
5. **修改检测**：裁剪、镜像、变速、加水印、调色等
6. **创作性评估**：是否有实质性的二次创作

输出要求：
- 必须返回有效的 JSON 格式
- 提供详细的证据和推理过程
- 使用中文进行分析回答
- 评分使用 0-100 的标准
- 风险等级：LOW（低风险）、MEDIUM（中风险）、HIGH（高风险）、CRITICAL（严重）

请保持客观、专业、详细，基于视频内容进行分析。"""
    
    def _build_user_prompt(self, video1_name: str, video2_name: str) -> str:
        """构建用户提示词
        
        Args:
            video1_name: 原始视频名称
            video2_name: 疑似抄袭视频名称
            
        Returns:
            用户提示词
        """
        return f"""请对比分析以下两个视频，判断第二个视频是否涉嫌抄袭或搬运第一个视频的内容。

**视频信息：**
- 原始视频：{video1_name}
- 疑似抄袭/搬运视频：{video2_name}

**分析要求：**

请从以下维度进行深入分析，并返回 JSON 格式的结果：

```json
{{
  "video_info": {{
    "original_video": "{video1_name}",
    "suspected_video": "{video2_name}",
    "analysis_date": "YYYY-MM-DD HH:MM:SS"
  }},
  
  "content_similarity": {{
    "score": 0-100,
    "description": "内容相似度的详细描述",
    "evidence": [
      "证据1：具体的相似场景、情节或对话",
      "证据2：...",
      "..."
    ]
  }},
  
  "visual_similarity": {{
    "score": 0-100,
    "description": "视觉相似度的详细描述",
    "evidence": [
      "证据1：具体的画面、构图或视觉元素",
      "证据2：...",
      "..."
    ]
  }},
  
  "audio_similarity": {{
    "score": 0-100,
    "description": "音频相似度的详细描述",
    "evidence": [
      "证据1：背景音乐、配音或音效",
      "证据2：...",
      "..."
    ]
  }},
  
  "temporal_similarity": {{
    "score": 0-100,
    "description": "时间结构相似度的详细描述",
    "evidence": [
      "证据1：时长、节奏或顺序",
      "证据2：...",
      "..."
    ]
  }},
  
  "modification_analysis": {{
    "detected_modifications": [
      "检测到的修改1：如裁剪、镜像、变速等",
      "检测到的修改2：...",
      "..."
    ],
    "cropping": "裁剪分析描述",
    "mirroring": "镜像分析描述",
    "speed_change": "变速分析描述",
    "watermark_changes": "水印变化描述",
    "color_grading": "调色分析描述",
    "other_modifications": "其他修改描述"
  }},
  
  "difference_analysis": {{
    "content_differences": [
      "内容差异1",
      "内容差异2",
      "..."
    ],
    "visual_differences": [
      "视觉差异1",
      "视觉差异2",
      "..."
    ],
    "audio_differences": [
      "音频差异1",
      "音频差异2",
      "..."
    ]
  }},
  
  "creativity_assessment": {{
    "has_substantial_creativity": true/false,
    "creativity_score": 0-100,
    "description": "创作性评估的详细描述",
    "evidence": [
      "证据1：展现创作性的具体元素",
      "证据2：...",
      "..."
    ]
  }},
  
  "infringement_assessment": {{
    "overall_similarity_score": 0-100,
    "risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
    "risk_score": 0-100,
    "reasoning": "综合评估的推理过程（详细说明为何给出该风险等级）",
    "key_indicators": [
      "关键指标1：支持侵权判断的核心证据",
      "关键指标2：...",
      "..."
    ],
    "mitigating_factors": [
      "减轻因素1：降低侵权风险的因素",
      "减轻因素2：...",
      "..."
    ],
    "aggravating_factors": [
      "加重因素1：增加侵权风险的因素",
      "加重因素2：...",
      "..."
    ]
  }},
  
  "conclusion": {{
    "is_plagiarism": true/false,
    "confidence_level": "LOW/MEDIUM/HIGH",
    "summary": "综合结论的简要总结",
    "key_findings": [
      "核心发现1",
      "核心发现2",
      "..."
    ],
    "recommendations": [
      "建议1：针对该案例的具体建议",
      "建议2：...",
      "..."
    ]
  }}
}}
```

**重要提示：**
1. 请逐帧、逐段分析视频内容
2. 关注细节：场景、人物、对话、音乐、特效等
3. 识别任何修改手法：裁剪、镜像、变速、调色、加字幕、加水印等
4. 评估是否为简单搬运，还是有实质性的二次创作
5. 提供充分的证据和推理过程
6. 保持客观、专业、详细

请开始分析并返回 JSON 格式的结果。"""


def save_analysis_result(
    analysis: Dict[str, Any],
    output_path: Path
):
    """保存分析结果到 JSON 文件
    
    Args:
        analysis: 分析结果
        output_path: 输出文件路径
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    log.info(f"✓ 分析结果已保存: {output_path}")


def print_analysis_summary(analysis: Dict[str, Any]):
    """打印分析结果摘要
    
    Args:
        analysis: 分析结果
    """
    print("\n" + "=" * 80)
    print("视频对比分析结果摘要")
    print("=" * 80 + "\n")
    
    # 视频信息
    video_info = analysis.get("video_info", {})
    print(f"原始视频: {video_info.get('original_video', 'N/A')}")
    print(f"疑似抄袭视频: {video_info.get('suspected_video', 'N/A')}")
    print(f"分析时间: {video_info.get('analysis_date', 'N/A')}\n")
    
    # 相似度评分
    print("相似度评分:")
    print(f"  - 内容相似度: {analysis.get('content_similarity', {}).get('score', 0)}/100")
    print(f"  - 视觉相似度: {analysis.get('visual_similarity', {}).get('score', 0)}/100")
    print(f"  - 音频相似度: {analysis.get('audio_similarity', {}).get('score', 0)}/100")
    print(f"  - 时间结构相似度: {analysis.get('temporal_similarity', {}).get('score', 0)}/100\n")
    
    # 侵权评估
    infringement = analysis.get("infringement_assessment", {})
    print("侵权评估:")
    print(f"  - 综合相似度: {infringement.get('overall_similarity_score', 0)}/100")
    print(f"  - 风险等级: {infringement.get('risk_level', 'N/A')}")
    print(f"  - 风险评分: {infringement.get('risk_score', 0)}/100\n")
    
    # 结论
    conclusion = analysis.get("conclusion", {})
    print("结论:")
    print(f"  - 是否涉嫌抄袭: {'是' if conclusion.get('is_plagiarism') else '否'}")
    print(f"  - 置信度: {conclusion.get('confidence_level', 'N/A')}")
    print(f"  - 摘要: {conclusion.get('summary', 'N/A')}\n")
    
    print("=" * 80 + "\n")


def main():
    """主函数"""
    # 脚本目录
    script_dir = Path(__file__).resolve().parent
    
    # 视频文件
    video1_path = script_dir / "video1_comedy_king.mp4"
    video2_path = script_dir / "video2_xhs_chenmingfei.mp4"
    
    # 输出目录
    output_dir = script_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 输出文件
    analysis_json = output_dir / "video_comparison_analysis.json"
    
    print("\n" + "=" * 80)
    print("视频抄袭对比分析工具")
    print("=" * 80 + "\n")
    
    # 验证视频文件存在
    if not video1_path.exists():
        raise FileNotFoundError(f"原始视频不存在: {video1_path}")
    if not video2_path.exists():
        raise FileNotFoundError(f"疑似抄袭视频不存在: {video2_path}")
    
    print(f"✓ 原始视频: {video1_path.name}")
    print(f"✓ 疑似抄袭视频: {video2_path.name}\n")
    
    # 检查视频时长
    print("检查视频时长...")
    duration1 = get_video_duration(video1_path)
    duration2 = get_video_duration(video2_path)
    
    print(f"  - 视频1 时长: {duration1/60:.1f} 分钟 ({duration1:.0f} 秒)")
    print(f"  - 视频2 时长: {duration2/60:.1f} 分钟 ({duration2:.0f} 秒)\n")
    
    # 计算最优采样率
    max_duration = max(duration1, duration2)
    optimal_fps = calculate_optimal_fps(max_duration, MAX_VIDEO_TOKENS_PER_VIDEO)
    
    print(f"推荐采样率: {optimal_fps} fps")
    print(f"预计每个视频提取帧数: ~{int(max_duration * optimal_fps)} 帧")
    print(f"预计总 token 数: ~{int(max_duration * optimal_fps * ESTIMATED_TOKENS_PER_FRAME * 2):,}\n")
    
    # 使用推荐的采样率（或用户指定的）
    fps = optimal_fps
    
    # 加载 API Key
    api_key = load_api_key_from_env()
    print(f"✓ API Key: {api_key[:20]}...\n")
    
    # 创建视频对比分析器
    comparer = VideoComparer(api_key=api_key)
    
    try:
        # 执行视频对比分析
        analysis = comparer.compare_videos(
            video1_path=video1_path,
            video2_path=video2_path,
            fps=fps
        )
        
        # 添加时间戳
        if "video_info" not in analysis:
            analysis["video_info"] = {}
        analysis["video_info"]["analysis_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 保存分析结果
        save_analysis_result(analysis, analysis_json)
        
        # 打印摘要
        print_analysis_summary(analysis)
        
        print("=" * 80)
        print("✅ 视频对比分析完成！")
        print("=" * 80 + "\n")
        print(f"📊 分析结果: {analysis_json}\n")
        
        return analysis
    
    except Exception as e:
        log.error(f"视频对比分析失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    result = main()

