#!/usr/bin/env python3
"""
阿里云 Qwen3 VL Plus 视频分析脚本
使用阿里云百炼平台的 Qwen3-VL-Plus 模型直接分析视频内容
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime

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

# 尝试导入阿里云SDK
try:
    from dashscope import MultiModalConversation
    import dashscope
except ImportError:
    log.error("需要安装阿里云SDK: pip install dashscope")
    MultiModalConversation = None
    dashscope = None


class ModelMetrics:
    """模型性能指标"""
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.start_time = None
        self.end_time = None
        self.total_time = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.success = False
        self.error_message = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "model_name": self.model_name,
            "timing": {
                "total_time_seconds": round(self.total_time, 2)
            },
            "tokens": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens
            },
            "status": {
                "success": self.success,
                "error_message": self.error_message
            }
        }


def load_api_key() -> str:
    """从 .env 文件加载阿里云 API Key"""
    # 先尝试从环境变量获取
    api_key = os.getenv("ALICLOUD_API_KEY", "")
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
                    if line.startswith("ALICLOUD_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if api_key:
                            return api_key
    
    raise RuntimeError("未找到 ALICLOUD_API_KEY 环境变量")


def prepare_video_url(video_path: Path) -> str:
    """准备视频URL - 使用本地文件路径
    
    注意：DashScope支持本地文件路径，格式为 file:///path/to/video.mp4
    """
    try:
        log.info(f"准备视频路径: {video_path.name}")
        
        # 使用本地文件路径
        video_url = f"file://{video_path.resolve()}"
        log.info(f"✓ 视频路径: {video_url}")
        return video_url
            
    except Exception as e:
        log.error(f"准备视频路径失败: {e}", exc_info=True)
        raise


def analyze_video_with_qwen3_vl_plus(
    video_path: Path,
    api_key: str,
    system_prompt: str,
    user_prompt: str
) -> Tuple[Dict[str, Any], ModelMetrics]:
    """使用 Qwen3-VL-Plus 分析视频
    
    Args:
        video_path: 视频文件路径
        api_key: 阿里云API密钥
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        
    Returns:
        (分析结果, 性能指标)
    """
    if MultiModalConversation is None or dashscope is None:
        raise RuntimeError("需要安装 dashscope: pip install dashscope")
    
    metrics = ModelMetrics("Qwen3-VL-Plus (Aliyun)")
    metrics.start_time = time.time()
    
    try:
        # 设置API Key
        dashscope.api_key = api_key
        
        # 准备视频URL
        log.info("步骤 1: 准备视频文件路径...")
        video_url = prepare_video_url(video_path)
        
        # 构建消息
        log.info("步骤 2: 调用 Qwen-VL-Plus 进行分析...")
        
        messages = [
            {
                'role': 'system',
                'content': [{'text': system_prompt}]
            },
            {
                'role': 'user',
                'content': [
                    {'video': video_url},
                    {'text': user_prompt}
                ]
            }
        ]
        
        # 调用API
        response = MultiModalConversation.call(
            model='qwen-vl-plus',  # 或 qwen-vl-max
            messages=messages,
            result_format='message',
            stream=False
        )
        
        metrics.end_time = time.time()
        metrics.total_time = metrics.end_time - metrics.start_time
        
        # 检查响应
        if response.status_code == 200:
            log.info("✓ 分析完成")
            
            # 提取结果
            output = response.output
            choices = output.get('choices', [])
            if choices:
                message = choices[0].get('message', {})
                content = message.get('content', [])
                
                # 提取文本内容
                text_content = ""
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text_content += item['text']
                
                # 提取token使用情况
                usage = output.get('usage', {})
                metrics.input_tokens = usage.get('input_tokens', 0)
                metrics.output_tokens = usage.get('output_tokens', 0)
                metrics.total_tokens = metrics.input_tokens + metrics.output_tokens
                
                # 解析JSON
                try:
                    result = json.loads(text_content)
                except json.JSONDecodeError:
                    # 尝试提取JSON片段
                    s = text_content.strip()
                    l = s.find("{")
                    r = s.rfind("}")
                    if 0 <= l < r:
                        result = json.loads(s[l : r + 1])
                    else:
                        raise RuntimeError(f"无法解析响应为JSON: {text_content[:200]}")
                
                metrics.success = True
                
                log.info(f"耗时: {metrics.total_time:.1f}秒")
                log.info(f"Tokens: {metrics.input_tokens} 输入, {metrics.output_tokens} 输出")
                
                return result, metrics
            else:
                raise RuntimeError("API返回的choices为空")
        else:
            raise RuntimeError(f"API调用失败: {response.code} - {response.message}")
            
    except Exception as e:
        metrics.end_time = time.time()
        metrics.total_time = metrics.end_time - metrics.start_time
        metrics.success = False
        metrics.error_message = str(e)
        log.error(f"分析失败: {e}", exc_info=True)
        raise


def build_prompts(video1_summary: Dict, video2_summary: Dict) -> Tuple[str, str]:
    """构建分析提示词"""
    system_prompt = """你是一个专业的视频内容分析专家，专门从事视频侵权分析和相似度检测。

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
1. 所有分数使用 0-100 的范围
2. 证据和描述要具体、客观
3. 不要使用"侵权"、"抄袭"等结论性词汇
4. 专注于可观测的事实和数据"""
    
    user_prompt = f"""请分析以下两个视频的相似度和差异。

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

请按照系统指令中定义的 JSON 格式，提供完整的分析结果。"""
    
    return system_prompt, user_prompt


def validate_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """验证分析结果"""
    validation = {
        "is_valid": True,
        "missing_fields": [],
        "completeness_score": 0,
        "notes": []
    }
    
    required_fields = [
        "similarity_analysis",
        "difference_analysis",
        "transformation_analysis",
        "content_overlap",
        "metadata_comparison",
        "summary"
    ]
    
    for field in required_fields:
        if field not in result:
            validation["missing_fields"].append(field)
            validation["is_valid"] = False
    
    total_fields = len(required_fields)
    present_fields = total_fields - len(validation["missing_fields"])
    validation["completeness_score"] = int((present_fields / total_fields) * 100)
    
    if validation["is_valid"]:
        validation["notes"].append("结果结构完整，符合预期")
    else:
        validation["notes"].append(f"缺少字段: {', '.join(validation['missing_fields'])}")
    
    return validation


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("阿里云 Qwen3-VL-Plus 视频比对分析")
    print("=" * 80 + "\n")
    
    # 视频文件路径
    video1_path = Path(__file__).resolve().parent / "output" / "7521959446235548985" / "v1.mp4"
    video2_path = Path(__file__).resolve().parent / "output" / "7523787273016839434" / "7523787273016839434.mp4"
    
    # 摘要文件路径
    summary1_path = video1_path.parent / "summary.json"
    summary2_path = video2_path.parent / "summary.json"
    
    # 输出目录
    output_dir = Path(__file__).resolve().parent / "output"
    
    # 验证文件
    for path in [video1_path, video2_path, summary1_path, summary2_path]:
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
    
    print(f"✓ 视频1: {video1_path.name}")
    print(f"✓ 视频2: {video2_path.name}\n")
    
    # 加载摘要
    with open(summary1_path) as f:
        video1_summary = json.load(f)
    with open(summary2_path) as f:
        video2_summary = json.load(f)
    
    # 加载 API Key
    api_key = load_api_key()
    print(f"✓ API Key: {api_key[:20]}...\n")
    
    # 构建提示词
    system_prompt, user_prompt = build_prompts(video1_summary, video2_summary)
    
    try:
        # 注意：Qwen3-VL-Plus 一次只能处理一个视频
        # 我们需要分别分析两个视频，然后比对结果
        print("⚠️  注意: Qwen3-VL-Plus 需要分别分析每个视频\n")
        
        print("=" * 80)
        print("分析视频1...")
        print("=" * 80)
        result1, metrics1 = analyze_video_with_qwen3_vl_plus(
            video1_path, api_key,
            "你是视频内容分析专家。请详细描述这个视频的内容，包括场景、人物、对话、情节等。",
            f"请详细分析这个视频（{video1_summary.get('title', 'N/A')}）的内容。"
        )
        
        print("\n" + "=" * 80)
        print("分析视频2...")
        print("=" * 80)
        result2, metrics2 = analyze_video_with_qwen3_vl_plus(
            video2_path, api_key,
            "你是视频内容分析专家。请详细描述这个视频的内容，包括场景、人物、对话、情节等。",
            f"请详细分析这个视频（{video2_summary.get('title', 'N/A')}）的内容。"
        )
        
        # 保存单独的分析结果
        output_file1 = output_dir / "qwen3_vl_plus_video1_analysis.json"
        with open(output_file1, "w", encoding="utf-8") as f:
            json.dump(result1, f, ensure_ascii=False, indent=2)
        
        output_file2 = output_dir / "qwen3_vl_plus_video2_analysis.json"
        with open(output_file2, "w", encoding="utf-8") as f:
            json.dump(result2, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 80)
        print("分析完成")
        print("=" * 80)
        print(f"\n✓ 视频1分析结果: {output_file1.name}")
        print(f"✓ 视频2分析结果: {output_file2.name}")
        
        print(f"\n📊 视频1分析耗时: {metrics1.total_time:.1f}秒")
        print(f"📊 视频2分析耗时: {metrics2.total_time:.1f}秒")
        print(f"📊 总耗时: {metrics1.total_time + metrics2.total_time:.1f}秒")
        
        if metrics1.input_tokens > 0:
            print(f"\n🎯 视频1 Tokens: {metrics1.input_tokens} 输入, {metrics1.output_tokens} 输出")
        if metrics2.input_tokens > 0:
            print(f"🎯 视频2 Tokens: {metrics2.input_tokens} 输入, {metrics2.output_tokens} 输出")
        
        print("\n" + "=" * 80)
        print("✅ 任务完成！")
        print("=" * 80 + "\n")
        
    except Exception as e:
        log.error(f"分析失败: {e}", exc_info=True)
        print("\n" + "=" * 80)
        print("❌ 分析失败")
        print("=" * 80 + "\n")
        raise


if __name__ == "__main__":
    main()

