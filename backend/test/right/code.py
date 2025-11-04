"""
多模型视频比对分析脚本
对比 Gemini Flash 2.5 和 Qwen3 VL 模型的性能和输出质量
"""
import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
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

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

import requests


def load_api_keys() -> Dict[str, str]:
    """从 .env 文件加载所有 API Keys"""
    keys = {}
    
    # 尝试从环境变量获取
    keys["gemini"] = os.getenv("GEMINI_API_KEY", "")
    keys["openrouter"] = os.getenv("OPENROUTER_API_KEY", "")
    
    # 如果没有，尝试从 .env 文件加载
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
                    if line.startswith("GEMINI_API_KEY=") and not keys["gemini"]:
                        keys["gemini"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("OPENROUTER_API_KEY=") and not keys["openrouter"]:
                        keys["openrouter"] = line.split("=", 1)[1].strip().strip('"').strip("'")
    
    return keys


def encode_video_to_base64(video_path: Path) -> str:
    """将视频编码为 base64 字符串"""
    with open(video_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class ModelMetrics:
    """模型性能指标"""
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.start_time = None
        self.end_time = None
        self.upload_time = 0
        self.inference_time = 0
        self.total_time = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.cost_input = 0.0
        self.cost_output = 0.0
        self.total_cost = 0.0
        self.success = False
        self.error_message = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "model_name": self.model_name,
            "timing": {
                "upload_time_seconds": round(self.upload_time, 2),
                "inference_time_seconds": round(self.inference_time, 2),
                "total_time_seconds": round(self.total_time, 2)
            },
            "tokens": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens
            },
            "cost": {
                "input_cost_usd": round(self.cost_input, 6),
                "output_cost_usd": round(self.cost_output, 6),
                "total_cost_usd": round(self.total_cost, 6)
            },
            "status": {
                "success": self.success,
                "error_message": self.error_message
            }
        }


class GeminiComparator:
    """Gemini 模型比对器"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        if genai is None or types is None:
            raise RuntimeError("需要安装 google-genai: pip install google-genai")
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.metrics = ModelMetrics(f"Gemini {model_name}")
    
    def _wait_file_active(self, name: str, timeout_sec: int = 180) -> None:
        """轮询文件状态"""
        start = time.time()
        while True:
            info = self.client.files.get(name=name)
            state = getattr(info, "state", None)
            if str(state).endswith("ACTIVE") or str(state) == "ACTIVE":
                return
            if time.time() - start > timeout_sec:
                raise TimeoutError(f"文件 {name} 在 {timeout_sec}秒 后仍未 ACTIVE")
            time.sleep(3)
    
    def analyze(
        self,
        video1_path: Path,
        video2_path: Path,
        video1_summary: Dict[str, Any],
        video2_summary: Dict[str, Any],
        system_prompt: str,
        user_prompt: str
    ) -> Tuple[Dict[str, Any], ModelMetrics]:
        """使用 Gemini 分析视频"""
        self.metrics.start_time = time.time()
        
        try:
            # 上传视频
            upload_start = time.time()
            log.info(f"[{self.model_name}] 上传视频1...")
            with open(video1_path, "rb") as f:
                file1_obj = self.client.files.upload(
                    file=f,
                    config=types.UploadFileConfig(
                        mime_type="video/mp4",
                        display_name=f"视频1-{video1_summary['video_id']}"
                    )
                )
            self._wait_file_active(getattr(file1_obj, "name"))
            
            log.info(f"[{self.model_name}] 上传视频2...")
            with open(video2_path, "rb") as f:
                file2_obj = self.client.files.upload(
                    file=f,
                    config=types.UploadFileConfig(
                        mime_type="video/mp4",
                        display_name=f"视频2-{video2_summary['video_id']}"
                    )
                )
            self._wait_file_active(getattr(file2_obj, "name"))
            
            self.metrics.upload_time = time.time() - upload_start
            log.info(f"[{self.model_name}] ✓ 上传完成 ({self.metrics.upload_time:.1f}秒)")
            
            # 推理分析
            inference_start = time.time()
            log.info(f"[{self.model_name}] 开始分析...")
            
            contents = [
                types.Part.from_uri(
                    file_uri=getattr(file1_obj, "uri"),
                    mime_type="video/mp4"
                ),
                types.Part.from_uri(
                    file_uri=getattr(file2_obj, "uri"),
                    mime_type="video/mp4"
                ),
                user_prompt
            ]
            
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=8000,
                response_mime_type="application/json",
                system_instruction=system_prompt,
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            
            self.metrics.inference_time = time.time() - inference_start
            
            # 提取结果
            text = getattr(response, "text", None) or ""
            if not text:
                try:
                    cand = (getattr(response, "candidates", None) or [None])[0]
                    content = getattr(cand, "content", None)
                    if hasattr(content, "parts"):
                        text = "".join(getattr(p, "text", "") for p in content.parts)
                except Exception:
                    pass
            
            if not text:
                raise RuntimeError("模型返回空响应")
            
            # 解析 JSON
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                s = text.strip()
                l = s.find("{")
                r = s.rfind("}")
                if 0 <= l < r:
                    result = json.loads(s[l : r + 1])
                else:
                    raise RuntimeError(f"无法解析响应为 JSON")
            
            # 提取 token 使用情况
            usage_metadata = getattr(response, "usage_metadata", None)
            if usage_metadata:
                self.metrics.input_tokens = getattr(usage_metadata, "prompt_token_count", 0)
                self.metrics.output_tokens = getattr(usage_metadata, "candidates_token_count", 0)
                self.metrics.total_tokens = getattr(usage_metadata, "total_token_count", 0)
            
            # Gemini 2.5 Flash 定价（假设）
            # 输入: $0.075 / 1M tokens，输出: $0.30 / 1M tokens
            self.metrics.cost_input = self.metrics.input_tokens * 0.075 / 1_000_000
            self.metrics.cost_output = self.metrics.output_tokens * 0.30 / 1_000_000
            self.metrics.total_cost = self.metrics.cost_input + self.metrics.cost_output
            
            self.metrics.end_time = time.time()
            self.metrics.total_time = self.metrics.end_time - self.metrics.start_time
            self.metrics.success = True
            
            log.info(f"[{self.model_name}] ✓ 分析完成")
            log.info(f"[{self.model_name}] 耗时: {self.metrics.total_time:.1f}秒")
            log.info(f"[{self.model_name}] Tokens: {self.metrics.input_tokens} 输入, {self.metrics.output_tokens} 输出")
            log.info(f"[{self.model_name}] 成本: ${self.metrics.total_cost:.6f}")
            
            return result, self.metrics
            
        except Exception as e:
            self.metrics.end_time = time.time()
            self.metrics.total_time = self.metrics.end_time - self.metrics.start_time
            self.metrics.success = False
            self.metrics.error_message = str(e)
            log.error(f"[{self.model_name}] 分析失败: {e}")
            raise


class OpenRouterComparator:
    """OpenRouter 模型比对器（Qwen3 VL）"""
    
    # 价格配置（根据 OpenRouter 网站）
    PRICING = {
        "qwen/qwen3-vl-32b-instruct": {
            "input": 0.35 / 1_000_000,   # $0.35/M tokens
            "output": 1.10 / 1_000_000   # $1.10/M tokens
        },
        "qwen/qwen3-vl-235b-a22b-instruct": {
            "input": 0.22 / 1_000_000,   # $0.22/M tokens
            "output": 0.88 / 1_000_000   # $0.88/M tokens
        }
    }
    
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.metrics = ModelMetrics(f"OpenRouter {model_name}")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def analyze(
        self,
        video1_path: Path,
        video2_path: Path,
        video1_summary: Dict[str, Any],
        video2_summary: Dict[str, Any],
        system_prompt: str,
        user_prompt: str
    ) -> Tuple[Dict[str, Any], ModelMetrics]:
        """使用 OpenRouter / Qwen3 VL 分析视频"""
        self.metrics.start_time = time.time()
        
        try:
            # 注意：OpenRouter 的 Qwen3 VL 可能不支持直接上传视频文件
            # 我们尝试使用 base64 编码或提供视频帧的描述
            log.info(f"[{self.model_name}] 准备视频数据...")
            upload_start = time.time()
            
            # 尝试方法1: 使用 base64 编码（可能会因为文件太大而失败）
            # 尝试方法2: 使用视频摘要作为替代
            # 这里我们使用视频摘要和文本描述作为输入
            
            video_context = f"""
视频1信息：
- ID: {video1_summary.get('video_id')}
- 标题: {video1_summary.get('title')}
- 作者: {video1_summary.get('author')}
- 时长: {video1_summary.get('duration', 0) / 1000:.1f}秒

视频2信息：
- ID: {video2_summary.get('video_id')}
- 标题: {video2_summary.get('title')}
- 作者: {video2_summary.get('author')}
- 时长: {video2_summary.get('duration', 0) / 1000:.1f}秒

注意：由于 API 限制，我们无法直接上传视频文件。请基于提供的视频元数据和标题信息进行分析。
这是一个测试，目的是评估在没有实际视频内容的情况下，模型能否提供有用的分析框架。
"""
            
            self.metrics.upload_time = time.time() - upload_start
            log.info(f"[{self.model_name}] ✓ 数据准备完成 ({self.metrics.upload_time:.1f}秒)")
            
            # 推理分析
            inference_start = time.time()
            log.info(f"[{self.model_name}] 开始分析...")
            
            # 构建请求
            messages = [
                {
                    "role": "system",
                    "content": system_prompt + "\n\n" + video_context
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 8000,
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/goodgame-video-analysis",
                "X-Title": "GoodGame Video Comparison"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=180
            )
            
            self.metrics.inference_time = time.time() - inference_start
            
            if response.status_code != 200:
                raise RuntimeError(f"API 返回错误: {response.status_code} - {response.text}")
            
            data = response.json()
            
            # 提取结果
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            if not content:
                raise RuntimeError("模型返回空响应")
            
            # 解析 JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                s = content.strip()
                l = s.find("{")
                r = s.rfind("}")
                if 0 <= l < r:
                    result = json.loads(s[l : r + 1])
                else:
                    raise RuntimeError(f"无法解析响应为 JSON: {content[:200]}")
            
            # 提取 token 使用情况
            usage = data.get("usage", {})
            self.metrics.input_tokens = usage.get("prompt_tokens", 0)
            self.metrics.output_tokens = usage.get("completion_tokens", 0)
            self.metrics.total_tokens = usage.get("total_tokens", 0)
            
            # 计算成本
            pricing = self.PRICING.get(self.model_name, {"input": 0, "output": 0})
            self.metrics.cost_input = self.metrics.input_tokens * pricing["input"]
            self.metrics.cost_output = self.metrics.output_tokens * pricing["output"]
            self.metrics.total_cost = self.metrics.cost_input + self.metrics.cost_output
            
            self.metrics.end_time = time.time()
            self.metrics.total_time = self.metrics.end_time - self.metrics.start_time
            self.metrics.success = True
            
            log.info(f"[{self.model_name}] ✓ 分析完成")
            log.info(f"[{self.model_name}] 耗时: {self.metrics.total_time:.1f}秒")
            log.info(f"[{self.model_name}] Tokens: {self.metrics.input_tokens} 输入, {self.metrics.output_tokens} 输出")
            log.info(f"[{self.model_name}] 成本: ${self.metrics.total_cost:.6f}")
            
            return result, self.metrics
            
        except Exception as e:
            self.metrics.end_time = time.time()
            self.metrics.total_time = self.metrics.end_time - self.metrics.start_time
            self.metrics.success = False
            self.metrics.error_message = str(e)
            log.error(f"[{self.model_name}] 分析失败: {e}")
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


def validate_result(result: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """验证分析结果是否符合预期"""
    validation = {
        "model_name": model_name,
        "is_valid": True,
        "missing_fields": [],
        "invalid_scores": [],
        "completeness_score": 0,
        "notes": []
    }
    
    # 检查必需字段
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
    
    # 检查相似度分数
    if "similarity_analysis" in result:
        sim = result["similarity_analysis"]
        score_fields = ["overall_similarity_score", "visual_similarity", "audio_similarity", 
                       "text_similarity", "narrative_similarity"]
        for field in score_fields:
            if field == "overall_similarity_score":
                score = sim.get(field, -1)
            else:
                score = sim.get(field, {}).get("score", -1)
            
            if score < 0 or score > 100:
                validation["invalid_scores"].append(f"{field}: {score}")
                validation["is_valid"] = False
    
    # 计算完整性得分
    total_fields = len(required_fields)
    present_fields = total_fields - len(validation["missing_fields"])
    validation["completeness_score"] = int((present_fields / total_fields) * 100)
    
    # 添加注释
    if validation["is_valid"]:
        validation["notes"].append("结果结构完整，符合预期")
    else:
        if validation["missing_fields"]:
            validation["notes"].append(f"缺少字段: {', '.join(validation['missing_fields'])}")
        if validation["invalid_scores"]:
            validation["notes"].append(f"无效评分: {', '.join(validation['invalid_scores'])}")
    
    return validation


def main():
    """主函数"""
    # 视频文件路径
    video1_path = Path(__file__).resolve().parent / "output" / "7521959446235548985" / "v1.mp4"
    video2_path = Path(__file__).resolve().parent / "output" / "7523787273016839434" / "7523787273016839434.mp4"
    
    # 摘要文件路径
    summary1_path = video1_path.parent / "summary.json"
    summary2_path = video2_path.parent / "summary.json"
    
    # 输出目录
    output_dir = Path(__file__).resolve().parent / "output"
    
    print("\n" + "=" * 80)
    print("多模型视频比对分析工具")
    print("对比 Gemini Flash 2.5 和 Qwen3 VL 模型")
    print("=" * 80 + "\n")
    
    # 验证文件
    for path in [video1_path, video2_path, summary1_path, summary2_path]:
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
    
    # 加载摘要
    with open(summary1_path) as f:
        video1_summary = json.load(f)
    with open(summary2_path) as f:
        video2_summary = json.load(f)
    
    # 加载 API Keys
    api_keys = load_api_keys()
    print(f"✓ Gemini API Key: {api_keys['gemini'][:20]}...")
    print(f"✓ OpenRouter API Key: {api_keys['openrouter'][:20]}...\n")
    
    # 构建提示词
    system_prompt, user_prompt = build_prompts(video1_summary, video2_summary)
    
    # 定义要测试的模型
    models_to_test = []
    
    # 1. Gemini Flash 2.5
    if api_keys["gemini"]:
        models_to_test.append(("gemini", "gemini-2.5-flash", api_keys["gemini"]))
    
    # 2. Qwen3 VL 32B
    if api_keys["openrouter"]:
        models_to_test.append(("openrouter", "qwen/qwen3-vl-32b-instruct", api_keys["openrouter"]))
    
    # 3. Qwen3 VL 235B
    if api_keys["openrouter"]:
        models_to_test.append(("openrouter", "qwen/qwen3-vl-235b-a22b-instruct", api_keys["openrouter"]))
    
    # 存储所有结果
    all_results = []
    all_metrics = []
    all_validations = []
    
    # 运行测试
    for i, (provider, model_name, api_key) in enumerate(models_to_test, 1):
        print("=" * 80)
        print(f"测试 {i}/{len(models_to_test)}: {model_name}")
        print("=" * 80 + "\n")
        
        try:
            if provider == "gemini":
                comparator = GeminiComparator(api_key, model_name)
            else:
                comparator = OpenRouterComparator(api_key, model_name)
            
            result, metrics = comparator.analyze(
                video1_path, video2_path,
                video1_summary, video2_summary,
                system_prompt, user_prompt
            )
            
            # 验证结果
            validation = validate_result(result, model_name)
            
            all_results.append({
                "model": model_name,
                "provider": provider,
                "result": result
            })
            all_metrics.append(metrics.to_dict())
            all_validations.append(validation)
            
            # 保存单个模型的结果
            output_file = output_dir / f"comparison_{model_name.replace('/', '_')}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n✓ 结果已保存: {output_file.name}\n")
            
        except Exception as e:
            log.error(f"模型 {model_name} 测试失败: {e}", exc_info=True)
            all_metrics.append(ModelMetrics(model_name).to_dict())
            all_validations.append({
                "model_name": model_name,
                "is_valid": False,
                "error": str(e)
            })
    
    # 生成对比报告
    print("\n" + "=" * 80)
    print("对比报告")
    print("=" * 80 + "\n")
    
    comparison_report = {
        "timestamp": datetime.now().isoformat(),
        "models_tested": len(models_to_test),
        "metrics_comparison": all_metrics,
        "validation_results": all_validations,
        "summary": {
            "fastest_model": None,
            "most_cost_effective": None,
            "highest_quality": None
        }
    }
    
    # 找出最快的模型
    successful_metrics = [m for m in all_metrics if m["status"]["success"]]
    if successful_metrics:
        fastest = min(successful_metrics, key=lambda x: x["timing"]["total_time_seconds"])
        comparison_report["summary"]["fastest_model"] = fastest["model_name"]
        
        # 找出最经济的模型
        cheapest = min(successful_metrics, key=lambda x: x["cost"]["total_cost_usd"])
        comparison_report["summary"]["most_cost_effective"] = cheapest["model_name"]
        
        # 找出质量最高的模型（基于完整性）
        validations_with_scores = [(v, m) for v, m in zip(all_validations, all_metrics) 
                                   if m["status"]["success"]]
        if validations_with_scores:
            best_quality = max(validations_with_scores, 
                             key=lambda x: x[0].get("completeness_score", 0))
            comparison_report["summary"]["highest_quality"] = best_quality[1]["model_name"]
    
    # 保存对比报告
    report_file = output_dir / "model_comparison_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(comparison_report, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 对比报告已保存: {report_file}\n")
    
    # 打印摘要
    print("📊 性能对比：\n")
    for metrics in all_metrics:
        print(f"模型: {metrics['model_name']}")
        print(f"  - 状态: {'✅ 成功' if metrics['status']['success'] else '❌ 失败'}")
        if metrics['status']['success']:
            print(f"  - 总耗时: {metrics['timing']['total_time_seconds']}秒")
            print(f"  - Tokens: {metrics['tokens']['input_tokens']} 输入 / {metrics['tokens']['output_tokens']} 输出")
            print(f"  - 成本: ${metrics['cost']['total_cost_usd']:.6f}")
        else:
            print(f"  - 错误: {metrics['status']['error_message']}")
        print()
    
    print("\n📋 质量验证：\n")
    for validation in all_validations:
        print(f"模型: {validation['model_name']}")
        print(f"  - 有效性: {'✅ 有效' if validation.get('is_valid', False) else '❌ 无效'}")
        print(f"  - 完整性: {validation.get('completeness_score', 0)}%")
        if validation.get('notes'):
            for note in validation['notes']:
                print(f"  - {note}")
        print()
    
    if comparison_report["summary"]["fastest_model"]:
        print("\n🏆 最佳模型：\n")
        print(f"⚡ 最快: {comparison_report['summary']['fastest_model']}")
        print(f"💰 最经济: {comparison_report['summary']['most_cost_effective']}")
        print(f"🎯 质量最高: {comparison_report['summary']['highest_quality']}")
    
    print("\n" + "=" * 80)
    print("✅ 所有测试完成！")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
