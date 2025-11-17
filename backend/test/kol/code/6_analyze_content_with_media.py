#!/usr/bin/env python3
"""
脚本名称: 6_analyze_content_with_media.py
功能描述: 使用Gemini API分析下载的媒体文件和描述，识别其中提及的护肤达人。
         本版本正确处理图片和视频上传，确保Gemini能够分析多模态内容。
输入: ../output/file/{aweme_id}/ (媒体文件目录和metadata.json)
      ./kol_analysis_prompt.txt (Gemini提示词)
输出: ../output/file/{aweme_id}/analysis.json (Gemini分析结果)
"""

import os
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

# 日志类
class SimpleLogger:
    """简化的日志类"""
    def info(self, msg):
        print(f"  {msg}")
    
    def error(self, msg):
        print(f"  ✗ {msg}")

log = SimpleLogger()

# 导入依赖
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


class KOLAnalyzer:
    """护肤达人分析器"""
    
    def __init__(self, api_key: str, prompt_file: Path):
        """初始化分析器
        
        Args:
            api_key: Gemini API密钥
            prompt_file: 提示词文件路径
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        
        # 读取提示词
        with open(prompt_file, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
    
    def _wait_file_active(self, name: str, timeout_sec: int = 120) -> None:
        """轮询文件状态，直到 ACTIVE 或超时"""
        start = time.time()
        while True:
            info = self.client.files.get(name=name)
            state = getattr(info, "state", None)
            if str(state).endswith("ACTIVE") or str(state) == "ACTIVE":
                return
            if time.time() - start > timeout_sec:
                raise TimeoutError(f"文件 {name} 在 {timeout_sec}秒后未激活 (state={state})")
            time.sleep(2)
    
    def upload_media_file(self, file_path: Path, display_name: str) -> Dict[str, Any]:
        """上传媒体文件到 Gemini Files API
        
        Args:
            file_path: 文件路径
            display_name: 显示名称
            
        Returns:
            包含文件信息的字典
        """
        # 根据文件扩展名确定 MIME 类型
        suffix = file_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
        }
        mime_type = mime_types.get(suffix, "application/octet-stream")
        
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
    
    def analyze_content(
        self,
        media_files: List[Dict[str, Any]],
        desc: str,
        author_nickname: str
    ) -> Dict[str, Any]:
        """使用 Gemini 分析内容
        
        Args:
            media_files: 已上传的媒体文件信息列表
            desc: 帖子描述
            author_nickname: 作者昵称
            
        Returns:
            包含分析结果的字典
        """
        # 构建用户提示
        user_prompt = f"""以下是抖音帖子的内容：

【标题/描述】: {desc}

【作者】: {author_nickname}

"""
        if media_files:
            if any(f["mime_type"].startswith("video") for f in media_files):
                user_prompt += "【媒体类型】: 视频\n\n"
            else:
                user_prompt += f"【媒体类型】: 图片（共{len(media_files)}张）\n\n"
            user_prompt += "请仔细分析上述描述和提供的媒体内容（图片或视频），识别其中提及的护肤/美妆达人信息。"
        else:
            user_prompt += "【媒体类型】: 无媒体文件\n\n请仅根据描述识别护肤/美妆达人信息。"
        
        # 构建请求内容
        contents = []
        
        # 添加媒体文件
        for media_file in media_files:
            if media_file["uri"]:
                contents.append(
                    types.Part.from_uri(
                        file_uri=media_file["uri"],
                        mime_type=media_file["mime_type"]
                    )
                )
        
        # 添加文本提示
        contents.append(user_prompt)
        
        # 配置生成参数
        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=4096,
            response_mime_type="application/json",
            system_instruction=self.system_prompt,
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
            if not text and hasattr(response, 'candidates') and response.candidates:
                first_candidate = response.candidates[0]
                if hasattr(first_candidate, 'content') and hasattr(first_candidate.content, 'parts'):
                    text = "".join([p.text for p in first_candidate.content.parts if hasattr(p, 'text')])
            
            if not text:
                return {
                    "error": "Gemini 返回空响应",
                    "raw_response": str(response)
                }
            
            # 去除可能的markdown包裹
            if text.startswith("```json") and text.endswith("```"):
                text = text[7:-3].strip()
            elif text.startswith("```") and text.endswith("```"):
                text = text[3:-3].strip()
            
            # 解析JSON
            analysis = json.loads(text)
            return analysis
            
        except json.JSONDecodeError as e:
            return {
                "error": f"JSON解析失败: {e}",
                "raw_text": text if 'text' in locals() else "无文本"
            }
        except Exception as e:
            return {
                "error": f"API调用失败: {e}"
            }
    
    def process_item(self, item_dir: Path) -> Dict[str, Any]:
        """处理单个帖子
        
        Args:
            item_dir: 帖子目录路径
            
        Returns:
            分析结果字典
        """
        aweme_id = item_dir.name
        
        # 检查是否已存在分析结果
        analysis_file = item_dir / "analysis.json"
        if analysis_file.exists():
            log.info("已存在分析结果，跳过")
            with open(analysis_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 读取元数据
        metadata_file = item_dir / "metadata.json"
        if not metadata_file.exists():
            return {
                "aweme_id": aweme_id,
                "error": "元数据文件不存在",
                "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        content_type = metadata.get("content_type")
        desc = metadata.get("desc", "")
        author = metadata.get("author", {})
        author_nickname = author.get("nickname", "未知")
        
        log.info(f"类型: {content_type}")
        log.info(f"描述: {desc[:100]}...")
        
        # 收集媒体文件
        media_files_to_upload = []
        
        if content_type == "视频":
            video_file = item_dir / "video.mp4"
            if video_file.exists():
                media_files_to_upload.append(video_file)
        elif content_type == "图文":
            # 收集所有图片文件
            image_files = sorted(
                list(item_dir.glob("image_*.jpg")) +
                list(item_dir.glob("image_*.jpeg")) +
                list(item_dir.glob("image_*.png")) +
                list(item_dir.glob("image_*.webp"))
            )
            media_files_to_upload.extend(image_files)
        
        # 上传媒体文件
        uploaded_files = []
        if media_files_to_upload:
            log.info(f"上传 {len(media_files_to_upload)} 个媒体文件...")
            for media_path in media_files_to_upload:
                try:
                    file_info = self.upload_media_file(media_path, media_path.name)
                    uploaded_files.append(file_info)
                    log.info(f"✓ 上传成功: {media_path.name}")
                except Exception as e:
                    log.error(f"上传失败: {media_path.name} - {e}")
                    # 继续处理其他文件
        
        # 调用Gemini分析
        analysis_result = self.analyze_content(
            media_files=uploaded_files,
            desc=desc,
            author_nickname=author_nickname
        )
        
        # 构建完整的分析结果
        full_result = {
            "aweme_id": aweme_id,
            "content_type": content_type,
            "desc": desc,
            "author": author,
            "statistics": metadata.get("statistics", {}),
            "analysis": analysis_result,
            "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "media_analyzed": len(uploaded_files) > 0,
            "media_count": len(uploaded_files)
        }
        
        # 保存结果
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(full_result, f, ensure_ascii=False, indent=2)
        
        log.info("✓ 分析完成并已保存")
        
        return full_result


def main() -> None:
    print("=" * 80)
    print("Gemini 多模态内容分析脚本 - 识别护肤达人")
    print("=" * 80)
    
    print("\n[1/5] 加载环境变量...")
    api_key = load_env_vars()
    print("✓ API Key已加载")
    
    print("\n[2/5] 读取分析提示词...")
    prompt_file = Path(__file__).resolve().parent / "kol_analysis_prompt.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
    print(f"✓ 提示词已加载")
    
    print("\n[3/5] 创建Gemini分析器...")
    analyzer = KOLAnalyzer(api_key, prompt_file)
    print("✓ 分析器已创建")
    
    print("\n[4/5] 扫描媒体文件目录...")
    output_dir = Path(__file__).resolve().parent.parent / "output"
    media_root_dir = output_dir / "file"
    
    if not media_root_dir.exists():
        raise RuntimeError(f"媒体文件根目录不存在: {media_root_dir}")
    
    # 获取所有包含metadata.json的子目录
    item_dirs = [d for d in media_root_dir.iterdir() if d.is_dir() and (d / "metadata.json").exists()]
    item_dirs.sort()
    
    print(f"✓ 找到 {len(item_dirs)} 个帖子目录")
    
    print("\n[5/5] 开始分析帖子内容...")
    
    results_summary = {
        "analysis_time": datetime.now().isoformat(),
        "total_items": len(item_dirs),
        "successful": 0,
        "failed": 0,
        "kols_summary": {}
    }
    
    for i, item_dir in enumerate(item_dirs):
        print(f"\n进度: {i+1}/{len(item_dirs)}")
        print(f"处理帖子: {item_dir.name}")
        
        try:
            result = analyzer.process_item(item_dir)
            
            if "error" not in result:
                results_summary["successful"] += 1
                
                # 汇总KOL信息
                analysis = result.get("analysis", {})
                if isinstance(analysis, dict) and analysis.get("content_analysis", {}).get("is_relevant"):
                    kols = analysis.get("kols_mentioned", [])
                    for kol in kols:
                        kol_name = kol.get("name", "").strip()
                        if kol_name:
                            if kol_name not in results_summary["kols_summary"]:
                                results_summary["kols_summary"][kol_name] = {
                                    "count": 0,
                                    "aweme_ids": []
                                }
                            results_summary["kols_summary"][kol_name]["count"] += 1
                            results_summary["kols_summary"][kol_name]["aweme_ids"].append(item_dir.name)
            else:
                results_summary["failed"] += 1
                print(f"  ✗ 分析失败: {result.get('error', '未知错误')}")
        
        except Exception as e:
            results_summary["failed"] += 1
            log.error(f"处理失败: {e}")
    
    # 保存汇总结果
    print("\n[6/6] 保存汇总结果...")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    summary_file = output_dir / f"6_analysis_summary_{stamp}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    print(f"✓ 汇总结果已保存: {summary_file}")
    
    print("\n" + "=" * 80)
    print("分析统计")
    print("=" * 80)
    print(f"总帖子数: {results_summary['total_items']}")
    print(f"分析成功: {results_summary['successful']}")
    print(f"分析失败: {results_summary['failed']}")
    print(f"发现独立达人数: {len(results_summary['kols_summary'])}")
    
    if results_summary['kols_summary']:
        print("\n提及次数最多的达人（前10位）:")
        sorted_kols = sorted(
            results_summary['kols_summary'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        for i, (kol_name, info) in enumerate(sorted_kols[:10], 1):
            print(f"  {i}. {kol_name} (提及{info['count']}次)")
    
    print("=" * 80)
    print("\n完成！所有帖子分析结果已保存到各自的 analysis.json 文件中。")


if __name__ == "__main__":
    main()

