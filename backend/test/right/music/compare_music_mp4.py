#!/usr/bin/env python3
"""
音频侵权分析脚本 - 使用 Gemini Flash 2.5 模型比对两个音频的相似度和差异
用于生成侵权分析数据基础，不做侵权结论判断
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

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
GEMINI_MODEL = "gemini-2.5-flash"  # 使用最新的 Flash 2.5 模型


def load_api_key_from_env() -> str:
    """从 .env 文件加载 Gemini API Key"""
    # 先尝试从环境变量获取（支持多个变量名）
    for env_var in ["GEMINI_API_KEY_ANALYZE", "GEMINI_API_KEY"]:
        api_key = os.getenv(env_var, "")
        if api_key:
            return api_key
    
    # 尝试从多个位置查找 .env 文件
    # 当前文件在 backend/test/right/music/，需要找到 backend/.env
    env_paths = [
        Path(__file__).resolve().parent / ".env",  # music 目录
        Path(__file__).resolve().parents[1] / ".env",  # right 目录
        Path(__file__).resolve().parents[2] / ".env",  # test 目录
        Path(__file__).resolve().parents[3] / ".env",  # backend 目录 ✓
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            log.info(f"从 {env_path} 加载环境变量")
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    # 支持两种环境变量名
                    if line.startswith("GEMINI_API_KEY_ANALYZE=") or line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if api_key:
                            return api_key
    
    raise RuntimeError("未找到 GEMINI_API_KEY 或 GEMINI_API_KEY_ANALYZE 环境变量")


class AudioComparator:
    """音频比对分析器"""
    
    def __init__(self, api_key: str):
        """初始化比对器
        
        Args:
            api_key: Gemini API密钥
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = GEMINI_MODEL
    
    def extract_audio_from_video(self, video_path: Path, output_audio_path: Path) -> Path:
        """从视频文件中提取音频
        
        Args:
            video_path: 视频文件路径
            output_audio_path: 输出音频文件路径
            
        Returns:
            输出的音频文件路径
        """
        log.info(f"从视频中提取音频: {video_path.name}")
        
        # 使用 ffmpeg 提取音频
        command = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # 不包含视频流
            '-acodec', 'libmp3lame',  # 使用 MP3 编码
            '-q:a', '2',  # 音频质量
            '-y',  # 覆盖已存在的文件
            str(output_audio_path)
        ]
        
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )
            log.info(f"✓ 音频提取成功: {output_audio_path.name}")
            return output_audio_path
        except subprocess.CalledProcessError as e:
            log.error(f"音频提取失败: {e.stderr}")
            raise RuntimeError(f"无法从视频中提取音频: {e.stderr}")
    
    def _wait_file_active(self, name: str, timeout_sec: int = 120) -> None:
        """轮询文件状态，直到 ACTIVE 或超时"""
        start = time.time()
        while True:
            info = self.client.files.get(name=name)
            state = getattr(info, "state", None)
            if str(state).endswith("ACTIVE") or str(state) == "ACTIVE":
                log.info(f"文件 {name} 状态变为 ACTIVE")
                return
            if time.time() - start > timeout_sec:
                raise TimeoutError(f"文件 {name} 在 {timeout_sec}秒 后仍未 ACTIVE (state={state})")
            log.info(f"等待文件 {name} 处理中... (状态: {state})")
            time.sleep(3)
    
    def upload_audio(self, audio_path: Path, display_name: str) -> Dict[str, Any]:
        """上传音频文件到 Gemini Files API
        
        Args:
            audio_path: 音频文件路径
            display_name: 显示名称
            
        Returns:
            包含文件信息的字典
        """
        log.info(f"上传音频: {audio_path.name}")
        
        with open(audio_path, "rb") as f:
            upload_config = types.UploadFileConfig(
                mime_type="audio/mpeg",
                display_name=display_name,
            )
            file_obj = self.client.files.upload(file=f, config=upload_config)
        
        name = getattr(file_obj, "name", None)
        if name:
            self._wait_file_active(name, timeout_sec=180)
        
        file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
        result = {
            "name": name,
            "mime_type": "audio/mpeg",
            "uri": file_uri,
            "display_name": display_name,
        }
        
        log.info(f"✓ 音频上传成功: {display_name}")
        log.info(f"  URI: {file_uri}")
        
        return result
    
    def compare_audios(
        self, 
        audio1_file: Dict[str, Any],
        audio2_file: Dict[str, Any],
        audio1_summary: Dict[str, Any],
        audio2_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用 Gemini 比对两个音频
        
        Args:
            audio1_file: 第一个音频的文件信息
            audio2_file: 第二个音频的文件信息
            audio1_summary: 第一个音频的摘要信息
            audio2_summary: 第二个音频的摘要信息
            
        Returns:
            包含分析结果的字典
        """
        log.info("开始音频比对分析...")
        
        # 构建分析提示词
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(audio1_summary, audio2_summary)
        
        # 构建请求内容，包含两个音频
        contents = [
            types.Part.from_uri(file_uri=audio1_file["uri"], mime_type="audio/mpeg"),
            types.Part.from_uri(file_uri=audio2_file["uri"], mime_type="audio/mpeg"),
            user_prompt
        ]
        
        # 配置生成参数
        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=8000,
            response_mime_type="application/json",
            system_instruction=system_prompt,
        )
        
        # 调用 Gemini API
        log.info(f"调用 Gemini {self.model} 模型进行分析...")
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            
            # 提取 token 使用信息
            usage_metadata = getattr(response, "usage_metadata", None)
            token_info = {}
            if usage_metadata:
                token_info = {
                    "prompt_token_count": getattr(usage_metadata, "prompt_token_count", 0),
                    "candidates_token_count": getattr(usage_metadata, "candidates_token_count", 0),
                    "total_token_count": getattr(usage_metadata, "total_token_count", 0),
                }
                log.info(f"Token 使用情况: 输入={token_info['prompt_token_count']}, "
                        f"输出={token_info['candidates_token_count']}, "
                        f"总计={token_info['total_token_count']}")
            
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
            
            # 解析 JSON 响应
            try:
                result = json.loads(text)
                # 添加 token 使用信息到结果中
                result["_token_usage"] = token_info
                log.info("✓ 分析完成")
                return result
            except json.JSONDecodeError:
                # 尝试提取 JSON 片段
                s = text.strip()
                l = s.find("{")
                r = s.rfind("}")
                if 0 <= l < r:
                    result = json.loads(s[l : r + 1])
                    result["_token_usage"] = token_info
                    log.info("✓ 分析完成（从响应中提取 JSON）")
                    return result
                else:
                    raise RuntimeError(f"无法解析 Gemini 响应为 JSON: {text[:200]}")
        
        except Exception as e:
            log.error(f"分析失败: {e}", exc_info=True)
            raise
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词 - 专注于音频分析"""
        return """你是一个专业的音频内容分析专家，专门从事音频相似度检测和比对分析。

你的任务是：
1. 仔细聆听并分析两段音频的内容
2. 从多个维度比对两段音频的相似性和差异性
3. 提供客观、详细的分析数据和证据
4. **不做侵权结论判断**，只提供数据分析基础

分析维度包括但不限于：
- 音乐元素：旋律、和声、节奏、曲式结构
- 音色特征：乐器编排、音色质感、混音风格
- 人声内容：演唱风格、歌词内容、音域音色
- 节奏律动：节拍、速度、律动感
- 音频制作：音质、后期处理、音效使用
- 情感表达：音乐情绪、氛围营造

请以 JSON 格式输出分析结果，结构如下：
{
  "similarity_analysis": {
    "overall_similarity_score": <0-100的相似度评分>,
    "melody_similarity": {
      "score": <0-100>,
      "description": "旋律相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "rhythm_similarity": {
      "score": <0-100>,
      "description": "节奏相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "timbre_similarity": {
      "score": <0-100>,
      "description": "音色相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "vocal_similarity": {
      "score": <0-100>,
      "description": "人声相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "structure_similarity": {
      "score": <0-100>,
      "description": "结构相似度描述",
      "evidence": ["证据1", "证据2", ...]
    }
  },
  "difference_analysis": {
    "melody_differences": ["差异1", "差异2", ...],
    "rhythm_differences": ["差异1", "差异2", ...],
    "timbre_differences": ["差异1", "差异2", ...],
    "vocal_differences": ["差异1", "差异2", ...],
    "production_differences": ["差异1", "差异2", ...]
  },
  "transformation_analysis": {
    "key_changes": ["调性变化描述"],
    "tempo_changes": ["速度变化描述"],
    "arrangement_changes": ["编曲变化描述"],
    "vocal_modifications": ["人声处理变化描述"]
  },
  "audio_features": {
    "audio1_features": {
      "genre": "音乐风格",
      "tempo_bpm": "估计速度",
      "key": "估计调性",
      "instruments": ["乐器1", "乐器2", ...],
      "vocal_characteristics": "人声特征描述"
    },
    "audio2_features": {
      "genre": "音乐风格",
      "tempo_bpm": "估计速度",
      "key": "估计调性",
      "instruments": ["乐器1", "乐器2", ...],
      "vocal_characteristics": "人声特征描述"
    }
  },
  "content_overlap": {
    "shared_melodic_patterns": ["共同旋律模式1", "共同旋律模式2", ...],
    "shared_lyrics": ["共同歌词片段1", "共同歌词片段2", ...],
    "shared_musical_elements": ["共同音乐元素1", "共同音乐元素2", ...]
  },
  "metadata_comparison": {
    "duration_comparison": "时长对比描述",
    "quality_comparison": "音质对比描述",
    "format_comparison": "格式对比描述"
  },
  "summary": {
    "key_findings": ["关键发现1", "关键发现2", ...],
    "analysis_confidence": "分析置信度说明",
    "data_quality_notes": "数据质量说明"
  }
}

注意：
1. 所有分数使用 0-100 的范围，100 表示完全相同，0 表示完全不同
2. 证据和描述要具体、客观，引用具体的时间点和音频特征
3. 不要使用"侵权"、"抄袭"等结论性词汇
4. 专注于可观测的音频事实和数据
5. 对于音乐特征的描述要专业且准确"""
    
    def _build_user_prompt(
        self, 
        audio1_info: Dict[str, Any],
        audio2_info: Dict[str, Any]
    ) -> str:
        """构建用户提示词 - 专注于音频分析
        
        Args:
            audio1_info: 第一个音频的基本信息
            audio2_info: 第二个音频的基本信息
            
        Returns:
            用户提示词
        """
        return f"""请仔细聆听并分析以下两段音频的相似度和差异。

**音频1基本信息：**
- 文件名: {audio1_info.get('filename', 'N/A')}
- 来源: {audio1_info.get('source', 'N/A')}
- 时长: {audio1_info.get('duration', 'N/A')}

**音频2基本信息：**
- 文件名: {audio2_info.get('filename', 'N/A')}
- 来源: {audio2_info.get('source', 'N/A')}
- 时长: {audio2_info.get('duration', 'N/A')}

请按照系统指令中定义的 JSON 格式，提供完整的分析结果。
请专注于音频内容的分析，包括：
1. 音乐旋律和和声的相似性
2. 节奏和律动的对比
3. 乐器编排和音色特征
4. 人声演唱风格和歌词内容
5. 音频制作质量和后期处理
6. 整体音乐风格和情感表达

请提供详细的时间点标注和具体的音频特征描述。"""


def get_audio_duration(audio_path: Path) -> str:
    """获取音频时长
    
    Args:
        audio_path: 音频文件路径
        
    Returns:
        格式化的时长字符串
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
            capture_output=True,
            text=True,
            check=True
        )
        duration_sec = float(result.stdout.strip())
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        return f"{minutes}分{seconds}秒"
    except Exception:
        return "未知"


def main():
    """主函数"""
    # 输出目录路径
    output_dir = Path(__file__).resolve().parent / "output"
    
    print("\n" + "=" * 80)
    print("音频比对分析工具 - 基于 Gemini Flash 2.5")
    print("=" * 80 + "\n")
    
    # 指定要比对的两个 MP4 文件
    video1_filename = "bilibili_BV1vwGPzDEUr_高端局天赐的声音第五季精选歌单如果可以命运在加纳共和国离婚.mp4"
    video2_filename = "天赐的声音-爱奇艺正版.mp4"
    
    video1_path = output_dir / video1_filename
    video2_path = output_dir / video2_filename
    
    # 验证文件存在
    if not video1_path.exists():
        raise FileNotFoundError(f"文件不存在: {video1_path}")
    if not video2_path.exists():
        raise FileNotFoundError(f"文件不存在: {video2_path}")
    
    # 显示文件大小
    video1_size_mb = video1_path.stat().st_size / (1024 * 1024)
    video2_size_mb = video2_path.stat().st_size / (1024 * 1024)
    log.info(f"视频1大小: {video1_size_mb:.1f} MB")
    log.info(f"视频2大小: {video2_size_mb:.1f} MB")
    
    print(f"✓ 音频来源1: {video1_path.name}")
    print(f"✓ 音频来源2: {video2_path.name}\n")
    
    # 加载 API Key
    api_key = load_api_key_from_env()
    print(f"✓ API Key: {api_key[:20]}...\n")
    
    # 创建比对器
    comparator = AudioComparator(api_key=api_key)
    
    try:
        # 步骤 1: 从 MP4 中提取音频
        print("步骤 1: 从 MP4 文件中提取音频")
        print("-" * 80)
        
        audio1_path = output_dir / f"{video1_path.stem}_audio.mp3"
        audio2_path = output_dir / f"{video2_path.stem}_audio.mp3"
        
        comparator.extract_audio_from_video(video1_path, audio1_path)
        comparator.extract_audio_from_video(video2_path, audio2_path)
        
        # 显示音频文件大小
        audio1_size_mb = audio1_path.stat().st_size / (1024 * 1024)
        audio2_size_mb = audio2_path.stat().st_size / (1024 * 1024)
        log.info(f"提取的音频1大小: {audio1_size_mb:.1f} MB")
        log.info(f"提取的音频2大小: {audio2_size_mb:.1f} MB")
        print()
        
        # 获取音频时长
        audio1_duration = get_audio_duration(audio1_path)
        audio2_duration = get_audio_duration(audio2_path)
        
        # 构建音频信息
        audio1_info = {
            "filename": video1_path.name,
            "source": str(video1_path),
            "duration": audio1_duration
        }
        audio2_info = {
            "filename": video2_path.name,
            "source": str(video2_path),
            "duration": audio2_duration
        }
        
        # 步骤 2: 上传音频到 Gemini Files API
        print("步骤 2: 上传音频到 Gemini Files API")
        print("-" * 80)
        audio1_file = comparator.upload_audio(audio1_path, f"音频1 - {video1_path.stem}")
        print()
        audio2_file = comparator.upload_audio(audio2_path, f"音频2 - {video2_path.stem}")
        print()
        
        # 步骤 3: 使用 Gemini 进行音频比对分析
        print("步骤 3: 使用 Gemini 进行音频比对分析")
        print("-" * 80)
        analysis_result = comparator.compare_audios(
            audio1_file=audio1_file,
            audio2_file=audio2_file,
            audio1_summary=audio1_info,
            audio2_summary=audio2_info
        )
        print()
        
        # 步骤 4: 保存分析结果
        print("步骤 4: 保存分析结果")
        print("-" * 80)
        output_file = output_dir / "audio_comparison_analysis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 分析结果已保存到: {output_file}\n")
        
        # 打印摘要
        print("=" * 80)
        print("分析结果摘要")
        print("=" * 80 + "\n")
        
        # Token 使用情况
        token_usage = analysis_result.get("_token_usage", {})
        if token_usage:
            print("💰 Token 使用情况:")
            print(f"  - 输入 Token: {token_usage.get('prompt_token_count', 0):,}")
            print(f"  - 输出 Token: {token_usage.get('candidates_token_count', 0):,}")
            print(f"  - 总计 Token: {token_usage.get('total_token_count', 0):,}")
            print()
        
        # 总体相似度
        sim_analysis = analysis_result.get("similarity_analysis", {})
        overall_score = sim_analysis.get("overall_similarity_score", 0)
        print(f"📊 总体相似度评分: {overall_score}/100\n")
        
        # 各维度相似度
        print("🎵 各维度相似度:")
        for dimension in ["melody", "rhythm", "timbre", "vocal", "structure"]:
            key = f"{dimension}_similarity"
            if key in sim_analysis:
                score = sim_analysis[key].get("score", 0)
                desc = sim_analysis[key].get("description", "")
                print(f"  - {dimension.capitalize()}: {score}/100")
                if desc:
                    print(f"    {desc}")
        print()
        
        # 主要差异
        diff_analysis = analysis_result.get("difference_analysis", {})
        print("🔄 主要差异:")
        for category, diffs in diff_analysis.items():
            if diffs:
                print(f"  - {category}:")
                for diff in diffs[:3]:  # 只显示前3个
                    print(f"    · {diff}")
        print()
        
        # 关键发现
        summary = analysis_result.get("summary", {})
        key_findings = summary.get("key_findings", [])
        if key_findings:
            print("💡 关键发现:")
            for finding in key_findings:
                print(f"  · {finding}")
        print()
        
        print("=" * 80)
        print("✅ 分析完成！完整结果请查看输出文件。")
        print("=" * 80 + "\n")
        
        # 清理临时音频文件（可选）
        log.info("清理临时音频文件...")
        try:
            audio1_path.unlink()
            audio2_path.unlink()
            log.info("✓ 临时文件已清理")
        except Exception as e:
            log.error(f"清理临时文件失败: {e}")
        
        return analysis_result
        
    except Exception as e:
        log.error(f"分析过程出错: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    result = main()

