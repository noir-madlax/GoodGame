#!/usr/bin/env python3
"""
脚本名称: 8_retry_failed_analyses.py
功能描述: 重新分析之前失败的帖子，采用优化策略：
         1. 增加max_output_tokens到8000
         2. 对于图片过多的帖子，只上传前5张最重要的图片
         3. 简化prompt，只提取达人名称和基本信息
输入: ../output/file/{aweme_id}/analysis.json (检查error字段)
输出: ../output/file/{aweme_id}/analysis_retry.json (重试结果)
      ../output/8_retry_summary_{timestamp}.json (重试汇总)
"""

import os
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("错误: 需要安装 google-genai: pip install google-genai")
    sys.exit(1)


def load_env_vars():
    """加载环境变量"""
    backend_env = project_root / "backend/.env"
    
    if load_dotenv and backend_env.exists():
        load_dotenv(backend_env)
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_ANALYZE")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 未找到")
    
    return api_key.strip()


class FailedAnalysisRetrier:
    """失败分析重试器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        
        # 简化的提示词，专注于提取达人名称
        self.system_prompt = """你是一个专业的社交媒体内容分析专家。
请分析提供的图片内容，提取所有提到的护肤/美妆达人的名称。

要求：
1. 仔细查看图片中的排行榜、列表、名字等信息
2. 提取每位达人的完整名称
3. 如果有排名信息，也一并记录

输出格式（JSON）：
{
  "is_relevant": true/false,
  "kols_mentioned": [
    {
      "name": "达人名称",
      "ranking_position": "排名（如有）",
      "context": "简要上下文"
    }
  ],
  "total_kols_found": 数量
}

请确保返回完整的JSON，不要截断。"""
    
    def _wait_file_active(self, name: str, timeout_sec: int = 120) -> None:
        """等待文件状态变为ACTIVE"""
        start = time.time()
        while True:
            info = self.client.files.get(name=name)
            state = getattr(info, "state", None)
            if str(state).endswith("ACTIVE") or str(state) == "ACTIVE":
                return
            if time.time() - start > timeout_sec:
                raise TimeoutError(f"文件 {name} 在 {timeout_sec}秒后未激活")
            time.sleep(2)
    
    def upload_media_file(self, file_path: Path, display_name: str) -> Dict[str, Any]:
        """上传媒体文件"""
        suffix = file_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")
        
        with open(file_path, "rb") as f:
            upload_config = types.UploadFileConfig(
                mime_type=mime_type,
                display_name=display_name,
            )
            file_obj = self.client.files.upload(file=f, config=upload_config)
        
        name = getattr(file_obj, "name", None)
        if name:
            self._wait_file_active(name, timeout_sec=120)
        
        file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
        
        return {
            "name": name,
            "mime_type": mime_type,
            "uri": file_uri,
            "display_name": display_name,
        }
    
    def analyze_with_retry(
        self,
        media_files: List[Dict[str, Any]],
        desc: str
    ) -> Dict[str, Any]:
        """使用优化参数重新分析"""
        user_prompt = f"""帖子描述: {desc}

请分析上述图片内容，提取所有护肤/美妆达人的名称。
重要：请确保返回完整的JSON列表，不要截断。"""
        
        contents = []
        for media_file in media_files:
            if media_file["uri"]:
                contents.append(
                    types.Part.from_uri(
                        file_uri=media_file["uri"],
                        mime_type=media_file["mime_type"]
                    )
                )
        contents.append(user_prompt)
        
        # 增加输出tokens限制，降低温度以提高稳定性
        config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8000,  # 增加到8000
            response_mime_type="application/json",
            system_instruction=self.system_prompt,
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            
            text = getattr(response, "text", None) or ""
            if not text and hasattr(response, 'candidates') and response.candidates:
                first_candidate = response.candidates[0]
                if hasattr(first_candidate, 'content') and hasattr(first_candidate.content, 'parts'):
                    text = "".join([p.text for p in first_candidate.content.parts if hasattr(p, 'text')])
            
            if not text:
                return {"error": "Gemini返回空响应"}
            
            # 去除markdown包裹
            if text.startswith("```json"):
                text = text[7:].strip()
            if text.endswith("```"):
                text = text[:-3].strip()
            if text.startswith("```"):
                text = text[3:].strip()
            
            analysis = json.loads(text)
            return analysis
            
        except json.JSONDecodeError as e:
            # 如果JSON解析失败，尝试提取部分内容
            return {
                "error": f"JSON解析失败: {e}",
                "raw_text": text[:500] if 'text' in locals() else "无文本",
                "partial_success": True  # 标记为部分成功，可能包含有用信息
            }
        except Exception as e:
            return {"error": f"API调用失败: {e}"}
    
    def retry_failed_item(self, item_dir: Path) -> Dict[str, Any]:
        """重试单个失败的帖子"""
        aweme_id = item_dir.name
        
        # 读取原始分析结果
        analysis_file = item_dir / "analysis.json"
        if not analysis_file.exists():
            return {"aweme_id": aweme_id, "error": "原始分析文件不存在"}
        
        with open(analysis_file, 'r', encoding='utf-8') as f:
            original_analysis = json.load(f)
        
        # 检查是否真的失败了
        if "error" not in original_analysis.get("analysis", {}):
            return {"aweme_id": aweme_id, "skipped": "原始分析成功，无需重试"}
        
        print(f"\n重试帖子: {aweme_id}")
        print(f"  原始错误: {original_analysis['analysis']['error'][:100]}...")
        
        # 读取元数据
        metadata_file = item_dir / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        content_type = metadata.get("content_type")
        desc = metadata.get("desc", "")
        
        print(f"  类型: {content_type}")
        
        # 收集媒体文件（优化：图片过多时只取前5张）
        media_files_to_upload = []
        
        if content_type == "视频":
            video_file = item_dir / "video.mp4"
            if video_file.exists():
                media_files_to_upload.append(video_file)
        elif content_type == "图文":
            image_files = sorted(
                list(item_dir.glob("image_*.jpg")) +
                list(item_dir.glob("image_*.jpeg")) +
                list(item_dir.glob("image_*.png")) +
                list(item_dir.glob("image_*.webp"))
            )
            # 只取前5张图片
            media_files_to_upload.extend(image_files[:5])
            if len(image_files) > 5:
                print(f"  注意: 图片总数{len(image_files)}张，只上传前5张")
        
        # 上传媒体文件
        uploaded_files = []
        if media_files_to_upload:
            print(f"  上传 {len(media_files_to_upload)} 个媒体文件...")
            for media_path in media_files_to_upload:
                try:
                    file_info = self.upload_media_file(media_path, media_path.name)
                    uploaded_files.append(file_info)
                    print(f"    ✓ {media_path.name}")
                except Exception as e:
                    print(f"    ✗ {media_path.name}: {e}")
        
        # 重新分析
        print(f"  调用Gemini API（优化参数）...")
        retry_analysis = self.analyze_with_retry(uploaded_files, desc)
        
        # 保存重试结果
        retry_result = {
            "aweme_id": aweme_id,
            "content_type": content_type,
            "desc": desc,
            "retry_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "original_error": original_analysis['analysis']['error'],
            "retry_analysis": retry_analysis,
            "media_count": len(uploaded_files)
        }
        
        retry_file = item_dir / "analysis_retry.json"
        with open(retry_file, 'w', encoding='utf-8') as f:
            json.dump(retry_result, f, ensure_ascii=False, indent=2)
        
        if "error" not in retry_analysis:
            print(f"  ✓ 重试成功！发现 {retry_analysis.get('total_kols_found', 0)} 位达人")
        else:
            print(f"  ✗ 重试仍然失败: {retry_analysis['error'][:100]}...")
        
        return retry_result


def main() -> None:
    print("=" * 80)
    print("失败分析重试脚本")
    print("=" * 80)
    
    print("\n[1/4] 加载环境变量...")
    api_key = load_env_vars()
    print("✓ API Key已加载")
    
    print("\n[2/4] 创建重试器...")
    retrier = FailedAnalysisRetrier(api_key)
    print("✓ 重试器已创建")
    
    print("\n[3/4] 查找失败的分析...")
    output_dir = Path(__file__).resolve().parent.parent / "output"
    media_root_dir = output_dir / "file"
    
    # 找到所有有error的分析
    failed_items = []
    for item_dir in media_root_dir.iterdir():
        if not item_dir.is_dir():
            continue
        
        analysis_file = item_dir / "analysis.json"
        if not analysis_file.exists():
            continue
        
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            
            if "error" in analysis.get("analysis", {}):
                failed_items.append(item_dir)
        except:
            continue
    
    print(f"✓ 找到 {len(failed_items)} 个失败的分析")
    
    if not failed_items:
        print("\n没有需要重试的失败分析！")
        return
    
    print("\n[4/4] 开始重试...")
    
    retry_results = {
        "retry_time": datetime.now().isoformat(),
        "total_retried": len(failed_items),
        "success": 0,
        "failed": 0,
        "results": []
    }
    
    for i, item_dir in enumerate(failed_items, 1):
        print(f"\n进度: {i}/{len(failed_items)}")
        result = retrier.retry_failed_item(item_dir)
        
        retry_results["results"].append(result)
        
        if "error" not in result.get("retry_analysis", {}):
            retry_results["success"] += 1
        else:
            retry_results["failed"] += 1
        
        # 避免API限流，每次请求后稍微等待
        if i < len(failed_items):
            time.sleep(2)
    
    # 保存汇总结果
    print("\n[5/5] 保存汇总结果...")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    summary_file = output_dir / f"8_retry_summary_{stamp}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(retry_results, f, ensure_ascii=False, indent=2)
    print(f"✓ 汇总结果已保存: {summary_file}")
    
    print("\n" + "=" * 80)
    print("重试统计")
    print("=" * 80)
    print(f"重试总数: {retry_results['total_retried']}")
    print(f"成功: {retry_results['success']}")
    print(f"失败: {retry_results['failed']}")
    print(f"成功率: {retry_results['success'] / retry_results['total_retried'] * 100:.1f}%")
    print("=" * 80)
    print("\n完成！重试结果已保存到各自的 analysis_retry.json 文件中。")
    print("建议：手动查看 analysis_retry.json 文件，提取有用的达人信息。")


if __name__ == "__main__":
    main()

