#!/usr/bin/env python3
"""
视频侵权分析脚本 - 使用 Gemini Flash 2.5 模型比对两个视频的相似度和差异
用于生成侵权分析数据基础，不做侵权结论判断
"""
import os
import sys
import json
import time
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
    env_paths = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
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


class VideoComparator:
    """视频比对分析器"""
    
    def __init__(self, api_key: str):
        """初始化比对器
        
        Args:
            api_key: Gemini API密钥
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = GEMINI_MODEL
    
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
    
    def upload_video(self, video_path: Path, display_name: str) -> Dict[str, Any]:
        """上传视频文件到 Gemini Files API
        
        Args:
            video_path: 视频文件路径
            display_name: 显示名称
            
        Returns:
            包含文件信息的字典
        """
        log.info(f"上传视频: {video_path.name}")
        
        with open(video_path, "rb") as f:
            upload_config = types.UploadFileConfig(
                mime_type="video/mp4",
                display_name=display_name,
            )
            file_obj = self.client.files.upload(file=f, config=upload_config)
        
        name = getattr(file_obj, "name", None)
        if name:
            self._wait_file_active(name, timeout_sec=180)
        
        file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
        result = {
            "name": name,
            "mime_type": "video/mp4",
            "uri": file_uri,
            "display_name": display_name,
        }
        
        log.info(f"✓ 视频上传成功: {display_name}")
        log.info(f"  URI: {file_uri}")
        
        return result
    
    def compare_videos(
        self, 
        video1_file: Dict[str, Any],
        video2_file: Dict[str, Any],
        video1_summary: Dict[str, Any],
        video2_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用 Gemini 比对两个视频
        
        Args:
            video1_file: 第一个视频的文件信息
            video2_file: 第二个视频的文件信息
            video1_summary: 第一个视频的摘要信息
            video2_summary: 第二个视频的摘要信息
            
        Returns:
            包含分析结果的字典
        """
        log.info("开始视频比对分析...")
        
        # 构建分析提示词
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(video1_summary, video2_summary)
        
        # 构建请求内容，包含两个视频
        contents = [
            types.Part.from_uri(file_uri=video1_file["uri"], mime_type="video/mp4"),
            types.Part.from_uri(file_uri=video2_file["uri"], mime_type="video/mp4"),
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
                log.info("✓ 分析完成")
                return result
            except json.JSONDecodeError:
                # 尝试提取 JSON 片段
                s = text.strip()
                l = s.find("{")
                r = s.rfind("}")
                if 0 <= l < r:
                    result = json.loads(s[l : r + 1])
                    log.info("✓ 分析完成（从响应中提取 JSON）")
                    return result
                else:
                    raise RuntimeError(f"无法解析 Gemini 响应为 JSON: {text[:200]}")
        
        except Exception as e:
            log.error(f"分析失败: {e}", exc_info=True)
            raise
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个专业的视频内容分析专家，专门从事视频侵权分析和相似度检测。

你的任务是：
1. 仔细观看并分析两个视频的内容
2. 从多个维度比对两个视频的相似性和差异性
3. 提供客观、详细的分析数据和证据
4. **不做侵权结论判断**，只提供数据分析基础

分析维度包括但不限于：
- 视觉内容：场景、画面构图、色彩风格、镜头语言
- 音频内容：背景音乐、配音、音效
- 文字内容：字幕、标题、文案
- 叙事结构：故事线、情节发展、节奏
- 创作元素：特效、转场、剪辑手法
- 技术参数：分辨率、时长、格式

请以 JSON 格式输出分析结果，结构如下：
{
  "similarity_analysis": {
    "overall_similarity_score": <0-100的相似度评分>,
    "visual_similarity": {
      "score": <0-100>,
      "description": "视觉相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "audio_similarity": {
      "score": <0-100>,
      "description": "音频相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "text_similarity": {
      "score": <0-100>,
      "description": "文字相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "narrative_similarity": {
      "score": <0-100>,
      "description": "叙事结构相似度描述",
      "evidence": ["证据1", "证据2", ...]
    }
  },
  "difference_analysis": {
    "visual_differences": ["差异1", "差异2", ...],
    "audio_differences": ["差异1", "差异2", ...],
    "text_differences": ["差异1", "差异2", ...],
    "narrative_differences": ["差异1", "差异2", ...],
    "technical_differences": ["差异1", "差异2", ...]
  },
  "transformation_analysis": {
    "modifications": ["修改1", "修改2", ...],
    "additions": ["新增内容1", "新增内容2", ...],
    "deletions": ["删除内容1", "删除内容2", ...],
    "rearrangements": ["重新排列1", "重新排列2", ...]
  },
  "content_overlap": {
    "shared_scenes": ["共同场景描述1", "共同场景描述2", ...],
    "shared_dialogues": ["共同对话1", "共同对话2", ...],
    "shared_visual_elements": ["共同视觉元素1", "共同视觉元素2", ...]
  },
  "metadata_comparison": {
    "duration_comparison": "时长对比描述",
    "quality_comparison": "画质对比描述",
    "format_comparison": "格式对比描述"
  },
  "summary": {
    "key_findings": ["关键发现1", "关键发现2", ...],
    "data_quality_notes": "数据质量说明"
  }
}

注意：
1. 所有分数使用 0-100 的范围，100 表示完全相同，0 表示完全不同
2. 证据和描述要具体、客观，引用具体的时间点和内容
3. 不要使用"侵权"、"抄袭"等结论性词汇
4. 专注于可观测的事实和数据"""
    
    def _build_user_prompt(
        self, 
        video1_summary: Dict[str, Any],
        video2_summary: Dict[str, Any]
    ) -> str:
        """构建用户提示词
        
        Args:
            video1_summary: 第一个视频的摘要
            video2_summary: 第二个视频的摘要
            
        Returns:
            用户提示词
        """
        return f"""请分析以下两个视频的相似度和差异。

**视频1基本信息：**
- ID: {video1_summary.get('video_id', 'N/A')}
- 标题: {video1_summary.get('title', 'N/A')}
- 作者: {video1_summary.get('author', 'N/A')}
- 时长: {video1_summary.get('duration', 0) / 1000:.1f}秒

**视频2基本信息：**
- ID: {video2_summary.get('video_id', 'N/A')}
- 标题: {video2_summary.get('title', 'N/A')}
- 作者: {video2_summary.get('author', 'N/A')}
- 时长: {video2_summary.get('duration', 0) / 1000:.1f}秒

请按照系统指令中定义的 JSON 格式，提供完整的分析结果。注意观察视频的每一个细节，包括画面、声音、文字、剪辑等各个方面。"""


def main():
    """主函数"""
    # 视频文件路径
    video1_path = Path(__file__).resolve().parent / "output" / "7521959446235548985" / "v1.mp4"
    video2_path = Path(__file__).resolve().parent / "output" / "7523787273016839434" / "7523787273016839434.mp4"
    
    # 摘要文件路径
    summary1_path = video1_path.parent / "summary.json"
    summary2_path = video2_path.parent / "summary.json"
    
    # 输出文件路径
    output_dir = Path(__file__).resolve().parent / "output"
    output_file = output_dir / "video_comparison_analysis.json"
    
    print("\n" + "=" * 80)
    print("视频侵权分析工具 - 基于 Gemini Flash 2.5")
    print("=" * 80 + "\n")
    
    # 验证文件存在
    if not video1_path.exists():
        raise FileNotFoundError(f"视频1不存在: {video1_path}")
    if not video2_path.exists():
        raise FileNotFoundError(f"视频2不存在: {video2_path}")
    if not summary1_path.exists():
        raise FileNotFoundError(f"摘要1不存在: {summary1_path}")
    if not summary2_path.exists():
        raise FileNotFoundError(f"摘要2不存在: {summary2_path}")
    
    print(f"✓ 视频1: {video1_path.name}")
    print(f"✓ 视频2: {video2_path.name}\n")
    
    # 加载摘要信息
    with open(summary1_path) as f:
        video1_summary = json.load(f)
    with open(summary2_path) as f:
        video2_summary = json.load(f)
    
    # 加载 API Key
    api_key = load_api_key_from_env()
    print(f"✓ API Key: {api_key[:20]}...\n")
    
    # 创建比对器
    comparator = VideoComparator(api_key=api_key)
    
    try:
        # 上传视频
        print("步骤 1: 上传视频到 Gemini Files API")
        print("-" * 80)
        video1_file = comparator.upload_video(video1_path, f"视频1 - {video1_summary['title'][:30]}")
        print()
        video2_file = comparator.upload_video(video2_path, f"视频2 - {video2_summary['title'][:30]}")
        print()
        
        # 比对分析
        print("步骤 2: 使用 Gemini 进行视频比对分析")
        print("-" * 80)
        analysis_result = comparator.compare_videos(
            video1_file=video1_file,
            video2_file=video2_file,
            video1_summary=video1_summary,
            video2_summary=video2_summary
        )
        print()
        
        # 保存结果
        print("步骤 3: 保存分析结果")
        print("-" * 80)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 分析结果已保存到: {output_file}\n")
        
        # 打印摘要
        print("=" * 80)
        print("分析结果摘要")
        print("=" * 80 + "\n")
        
        # 总体相似度
        sim_analysis = analysis_result.get("similarity_analysis", {})
        overall_score = sim_analysis.get("overall_similarity_score", 0)
        print(f"📊 总体相似度评分: {overall_score}/100\n")
        
        # 各维度相似度
        print("🔍 各维度相似度:")
        for dimension in ["visual", "audio", "text", "narrative"]:
            key = f"{dimension}_similarity"
            if key in sim_analysis:
                score = sim_analysis[key].get("score", 0)
                desc = sim_analysis[key].get("description", "")
                print(f"  - {dimension.capitalize()}: {score}/100")
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
        
        return analysis_result
        
    except Exception as e:
        log.error(f"分析过程出错: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    result = main()

