#!/usr/bin/env python3
"""
图片侵权分析脚本 - 使用 Gemini Flash 2.5 模型比对两张图片的相似度和差异
用于生成侵权分析数据基础，判断是否构成侵权
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[3]
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
        Path(__file__).resolve().parents[3] / ".env",
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


class ImageComparator:
    """图片比对分析器"""
    
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
            time.sleep(2)
    
    def upload_image(self, image_path: Path, display_name: str) -> Dict[str, Any]:
        """上传图片文件到 Gemini Files API
        
        Args:
            image_path: 图片文件路径
            display_name: 显示名称
            
        Returns:
            包含文件信息的字典
        """
        log.info(f"上传图片: {image_path.name}")
        
        # 根据文件扩展名确定 MIME 类型
        suffix = image_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")
        
        with open(image_path, "rb") as f:
            upload_config = types.UploadFileConfig(
                mime_type=mime_type,
                display_name=display_name,
            )
            file_obj = self.client.files.upload(file=f, config=upload_config)
        
        name = getattr(file_obj, "name", None)
        if name:
            self._wait_file_active(name, timeout_sec=60)
        
        file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
        result = {
            "name": name,
            "mime_type": mime_type,
            "uri": file_uri,
            "display_name": display_name,
        }
        
        log.info(f"✓ 图片上传成功: {display_name}")
        log.info(f"  URI: {file_uri}")
        
        return result
    
    def compare_images(
        self, 
        image1_file: Dict[str, Any],
        image2_file: Dict[str, Any],
        image1_name: str,
        image2_name: str
    ) -> Dict[str, Any]:
        """使用 Gemini 比对两张图片
        
        Args:
            image1_file: 第一张图片的文件信息（原图）
            image2_file: 第二张图片的文件信息（疑似侵权图）
            image1_name: 第一张图片的名称
            image2_name: 第二张图片的名称
            
        Returns:
            包含分析结果的字典
        """
        log.info("开始图片比对分析...")
        
        # 构建分析提示词
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(image1_name, image2_name)
        
        # 构建请求内容，包含两张图片
        contents = [
            types.Part.from_uri(file_uri=image1_file["uri"], mime_type=image1_file["mime_type"]),
            types.Part.from_uri(file_uri=image2_file["uri"], mime_type=image2_file["mime_type"]),
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
        return """你是一个专业的图片内容分析专家，专门从事图片侵权分析和相似度检测。

你的任务是：
1. 仔细观察并分析两张图片的内容
2. 从多个维度比对两张图片的相似性和差异性
3. 提供客观、详细的分析数据和证据
4. **基于分析结果判断是否可能构成侵权**

分析维度包括但不限于：
- 视觉内容：画面主体、构图、色彩、光影、细节元素
- 设计元素：字体、图标、logo、排版、配色方案
- 创意表达：创意概念、表现手法、艺术风格
- 技术特征：分辨率、尺寸、格式、质量
- 修改痕迹：裁剪、滤镜、水印、拼接等

请以 JSON 格式输出分析结果，结构如下：
{
  "similarity_analysis": {
    "overall_similarity_score": <0-100的相似度评分>,
    "visual_similarity": {
      "score": <0-100>,
      "description": "视觉相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "composition_similarity": {
      "score": <0-100>,
      "description": "构图相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "color_similarity": {
      "score": <0-100>,
      "description": "色彩相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "style_similarity": {
      "score": <0-100>,
      "description": "风格相似度描述",
      "evidence": ["证据1", "证据2", ...]
    },
    "detail_similarity": {
      "score": <0-100>,
      "description": "细节元素相似度描述",
      "evidence": ["证据1", "证据2", ...]
    }
  },
  "difference_analysis": {
    "visual_differences": ["差异1", "差异2", ...],
    "composition_differences": ["差异1", "差异2", ...],
    "color_differences": ["差异1", "差异2", ...],
    "style_differences": ["差异1", "差异2", ...],
    "technical_differences": ["差异1", "差异2", ...]
  },
  "modification_analysis": {
    "detected_modifications": ["检测到的修改1", "检测到的修改2", ...],
    "cropping": "裁剪情况描述",
    "filters_effects": "滤镜/特效使用描述",
    "watermark_changes": "水印变化描述",
    "quality_changes": "质量变化描述"
  },
  "content_overlap": {
    "shared_elements": ["共同元素1", "共同元素2", ...],
    "shared_subjects": ["共同主体1", "共同主体2", ...],
    "shared_design_elements": ["共同设计元素1", "共同设计元素2", ...]
  },
  "infringement_assessment": {
    "risk_level": "<low/medium/high - 侵权风险等级>",
    "risk_score": <0-100的侵权风险评分，100表示极高风险>,
    "reasoning": "判断理由的详细说明",
    "key_indicators": ["指标1", "指标2", ...],
    "mitigating_factors": ["减轻因素1", "减轻因素2", ...],
    "aggravating_factors": ["加重因素1", "加重因素2", ...]
  },
  "summary": {
    "key_findings": ["关键发现1", "关键发现2", ...],
    "conclusion": "总体结论",
    "confidence_level": "<low/medium/high - 分析置信度>"
  }
}

注意：
1. 所有分数使用 0-100 的范围，100 表示完全相同，0 表示完全不同
2. 证据和描述要具体、客观，指出具体的视觉特征
3. 侵权风险评估要综合考虑相似度、创意性、修改程度等因素
4. 专注于可观测的事实和数据
5. 风险等级判断标准：
   - low (低): 整体相似度低于30%，或有显著的独创性差异
   - medium (中): 整体相似度在30-70%之间，部分元素相似但有明显差异
   - high (高): 整体相似度超过70%，核心创意和表现高度相似"""
    
    def _build_user_prompt(
        self, 
        image1_name: str,
        image2_name: str
    ) -> str:
        """构建用户提示词
        
        Args:
            image1_name: 第一张图片的名称（原图）
            image2_name: 第二张图片的名称（疑似侵权图）
            
        Returns:
            用户提示词
        """
        return f"""请分析以下两张图片是否存在侵权风险。

**图片1（原图）：**
- 文件名: {image1_name}

**图片2（疑似侵权图）：**
- 文件名: {image2_name}

请按照系统指令中定义的 JSON 格式，提供完整的分析结果。请仔细观察图片的每一个细节，包括：
1. 主体内容和构图
2. 色彩搭配和光影效果
3. 设计元素和排版
4. 细节特征和纹理
5. 任何可能的修改痕迹

请基于这些观察，判断图片2是否可能侵犯图片1的版权。"""


def find_image_pairs(source_dir: Path) -> List[Tuple[str, Path, Path]]:
    """查找所有需要比对的图片对
    
    Args:
        source_dir: 源图片目录
        
    Returns:
        列表，每个元素为 (team_name, org_image_path, copy_image_path)
    """
    pairs = []
    
    # 遍历所有 team 目录
    for team_dir in sorted(source_dir.iterdir()):
        if not team_dir.is_dir() or not team_dir.name.startswith("team"):
            continue
        
        # 查找 org 和 copy 图片
        org_images = list(team_dir.glob("*-org.*"))
        copy_images = list(team_dir.glob("*-copy.*"))
        
        if not org_images:
            log.error(f"团队 {team_dir.name} 没有找到原图 (*-org.*)")
            continue
        if not copy_images:
            log.error(f"团队 {team_dir.name} 没有找到疑似侵权图 (*-copy.*)")
            continue
        
        pairs.append((team_dir.name, org_images[0], copy_images[0]))
    
    return pairs


def analyze_team(
    comparator: ImageComparator,
    team_name: str,
    org_image: Path,
    copy_image: Path,
    output_dir: Path
) -> Dict[str, Any]:
    """分析一个团队的图片对
    
    Args:
        comparator: 图片比对器
        team_name: 团队名称
        org_image: 原图路径
        copy_image: 疑似侵权图路径
        output_dir: 输出目录
        
    Returns:
        分析结果字典
    """
    print("\n" + "=" * 80)
    print(f"分析团队: {team_name}")
    print("=" * 80 + "\n")
    
    print(f"✓ 原图: {org_image.name}")
    print(f"✓ 疑似侵权图: {copy_image.name}\n")
    
    try:
        # 步骤 1: 上传图片
        print("步骤 1: 上传图片到 Gemini Files API")
        print("-" * 80)
        image1_file = comparator.upload_image(org_image, f"{team_name} - 原图")
        print()
        image2_file = comparator.upload_image(copy_image, f"{team_name} - 疑似侵权图")
        print()
        
        # 步骤 2: 比对分析
        print("步骤 2: 使用 Gemini 进行图片比对分析")
        print("-" * 80)
        analysis_result = comparator.compare_images(
            image1_file=image1_file,
            image2_file=image2_file,
            image1_name=org_image.name,
            image2_name=copy_image.name
        )
        print()
        
        # 步骤 3: 保存结果
        print("步骤 3: 保存分析结果")
        print("-" * 80)
        output_file = output_dir / f"{team_name}_analysis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 分析结果已保存到: {output_file}\n")
        
        # 打印摘要
        print_analysis_summary(team_name, analysis_result)
        
        return analysis_result
        
    except Exception as e:
        log.error(f"分析团队 {team_name} 时出错: {e}", exc_info=True)
        raise


def print_analysis_summary(team_name: str, analysis_result: Dict[str, Any]):
    """打印分析结果摘要
    
    Args:
        team_name: 团队名称
        analysis_result: 分析结果
    """
    print("=" * 80)
    print(f"{team_name} 分析结果摘要")
    print("=" * 80 + "\n")
    
    # 总体相似度
    sim_analysis = analysis_result.get("similarity_analysis", {})
    overall_score = sim_analysis.get("overall_similarity_score", 0)
    print(f"📊 总体相似度评分: {overall_score}/100\n")
    
    # 各维度相似度
    print("🔍 各维度相似度:")
    for dimension in ["visual", "composition", "color", "style", "detail"]:
        key = f"{dimension}_similarity"
        if key in sim_analysis:
            score = sim_analysis[key].get("score", 0)
            desc = sim_analysis[key].get("description", "")
            print(f"  - {dimension.capitalize()}: {score}/100")
            if desc:
                print(f"    {desc}")
    print()
    
    # 侵权风险评估
    infringement = analysis_result.get("infringement_assessment", {})
    risk_level = infringement.get("risk_level", "unknown")
    risk_score = infringement.get("risk_score", 0)
    reasoning = infringement.get("reasoning", "")
    
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk_level, "⚪")
    print(f"{risk_emoji} 侵权风险评估:")
    print(f"  - 风险等级: {risk_level.upper()}")
    print(f"  - 风险评分: {risk_score}/100")
    if reasoning:
        print(f"  - 判断理由: {reasoning}")
    print()
    
    # 关键发现
    summary = analysis_result.get("summary", {})
    key_findings = summary.get("key_findings", [])
    if key_findings:
        print("💡 关键发现:")
        for finding in key_findings:
            print(f"  · {finding}")
    
    conclusion = summary.get("conclusion", "")
    if conclusion:
        print(f"\n📝 总体结论: {conclusion}")
    
    confidence = summary.get("confidence_level", "")
    if confidence:
        print(f"📈 置信度: {confidence.upper()}")
    
    print()


def main():
    """主函数"""
    # 目录路径
    script_dir = Path(__file__).resolve().parent
    source_dir = script_dir / "source-pic"
    output_dir = script_dir / "output"
    
    # 创建输出目录
    output_dir.mkdir(exist_ok=True)
    
    print("\n" + "=" * 80)
    print("图片侵权分析工具 - 基于 Gemini Flash 2.5")
    print("=" * 80 + "\n")
    
    # 验证源目录存在
    if not source_dir.exists():
        raise FileNotFoundError(f"源图片目录不存在: {source_dir}")
    
    # 查找所有图片对
    image_pairs = find_image_pairs(source_dir)
    
    if not image_pairs:
        log.error("未找到任何需要比对的图片对")
        return
    
    print(f"✓ 找到 {len(image_pairs)} 个团队需要分析\n")
    
    # 加载 API Key
    api_key = load_api_key_from_env()
    print(f"✓ API Key: {api_key[:20]}...\n")
    
    # 创建比对器
    comparator = ImageComparator(api_key=api_key)
    
    # 分析每个团队
    results = {}
    for team_name, org_image, copy_image in image_pairs:
        try:
            result = analyze_team(
                comparator=comparator,
                team_name=team_name,
                org_image=org_image,
                copy_image=copy_image,
                output_dir=output_dir
            )
            results[team_name] = result
        except Exception as e:
            log.error(f"跳过团队 {team_name}: {e}")
            continue
    
    # 打印总体摘要
    print("\n" + "=" * 80)
    print("所有团队分析完成")
    print("=" * 80 + "\n")
    
    for team_name, result in results.items():
        risk = result.get("infringement_assessment", {}).get("risk_level", "unknown")
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
        score = result.get("similarity_analysis", {}).get("overall_similarity_score", 0)
        print(f"{risk_emoji} {team_name}: 相似度 {score}/100, 风险等级 {risk.upper()}")
    
    print("\n" + "=" * 80)
    print("✅ 所有分析完成！详细结果请查看 output 目录。")
    print("=" * 80 + "\n")
    
    return results


if __name__ == "__main__":
    result = main()

