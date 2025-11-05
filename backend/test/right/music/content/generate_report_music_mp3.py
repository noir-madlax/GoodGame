#!/usr/bin/env python3
"""
音频比对分析报告生成器 - 使用 Gemini 2.5 Pro 生成专业报告并输出为 PDF
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[4]  # backend 目录
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

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    log.error("需要安装 reportlab: pip install reportlab")
    sys.exit(1)


# Gemini 配置
GEMINI_MODEL = "gemini-2.0-flash-exp"  # 使用 Pro 模型生成更专业的报告


def extract_video_thumbnail(video_path: Path, output_path: Path, timestamp: str = "00:00:01") -> Optional[Path]:
    """从视频中提取缩略图
    
    Args:
        video_path: 视频文件路径
        output_path: 输出图片路径
        timestamp: 截图时间点，格式 HH:MM:SS
        
    Returns:
        输出的图片路径，失败返回 None
    """
    try:
        command = [
            'ffmpeg',
            '-ss', timestamp,
            '-i', str(video_path),
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            str(output_path)
        ]
        
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        
        if output_path.exists():
            log.info(f"✓ 视频截图成功: {output_path.name}")
            return output_path
        else:
            log.error(f"截图文件未生成: {output_path}")
            return None
    except subprocess.CalledProcessError as e:
        log.error(f"视频截图失败: {e.stderr}")
        return None
    except Exception as e:
        log.error(f"提取视频缩略图时出错: {e}")
        return None


def get_audio_info(audio_path: Path) -> Dict[str, Any]:
    """获取音频信息
    
    Args:
        audio_path: 音频文件路径
        
    Returns:
        包含音频信息的字典
    """
    try:
        # 获取文件大小
        size_mb = audio_path.stat().st_size / (1024 * 1024)
        
        # 获取音频时长
        command = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        duration_sec = float(result.stdout.strip())
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        duration_str = f"{minutes}分{seconds}秒"
        
        return {
            "filename": audio_path.name,
            "size_mb": round(size_mb, 1),
            "duration": duration_str,
            "duration_seconds": duration_sec
        }
    except Exception as e:
        log.error(f"获取音频信息失败: {e}")
        return {
            "filename": audio_path.name,
            "size_mb": 0,
            "duration": "未知",
            "duration_seconds": 0
        }


def load_api_key_from_env() -> str:
    """从 .env 文件加载 Gemini API Key"""
    # 先尝试从环境变量获取
    for env_var in ["GEMINI_API_KEY_ANALYZE", "GEMINI_API_KEY"]:
        api_key = os.getenv(env_var, "")
        if api_key:
            return api_key
    
    # 尝试从多个位置查找 .env 文件
    # 当前文件在 backend/test/right/music/content/，需要找到 backend/.env
    env_paths = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[3] / ".env",
        Path(__file__).resolve().parents[4] / ".env",  # backend 目录
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


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, api_key: str):
        """初始化报告生成器
        
        Args:
            api_key: Gemini API密钥
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = GEMINI_MODEL
    
    def generate_report_text(
        self,
        audio_analysis: Dict[str, Any],
        video1_info: Dict[str, Any],
        video2_info: Dict[str, Any]
    ) -> str:
        """使用 Gemini 生成报告文本
        
        Args:
            audio_analysis: 音频比对分析结果
            video1_info: 视频1的基本信息
            video2_info: 视频2的基本信息
            
        Returns:
            生成的报告文本
        """
        log.info("开始生成报告文本...")
        
        # 构建提示词
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(audio_analysis, video1_info, video2_info)
        
        # 配置生成参数
        config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=16000,  # 增加输出 token 限制，确保报告完整
            system_instruction=system_prompt,
        )
        
        # 调用 Gemini API
        log.info(f"调用 Gemini {self.model} 模型生成报告...")
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
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
            
            log.info("✓ 报告文本生成完成")
            return text
        
        except Exception as e:
            log.error(f"生成报告文本失败: {e}", exc_info=True)
            raise
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一位专业的音频内容分析专家和音乐版权顾问，擅长撰写音频相似度分析报告。

你的任务是：
1. 基于提供的详细音频比对分析数据，撰写一份专业、全面的分析报告
2. 报告应当结构清晰、逻辑严密、证据充分
3. 使用专业但易懂的语言，准确描述音频特征和相似性
4. 保持客观中立的立场，基于事实和数据进行分析
5. **必须完整展开原始分析数据的所有细节和颗粒度，逐条列举所有证据、差异和发现**

报告结构要求（必须包含以下所有部分）：
1. 报告标题和概述
2. 音频文件基本信息对比
3. 总体相似度评估（包含总分和详细说明）
4. 各维度详细分析（旋律、节奏、音色、人声、结构）
   - 每个维度必须包含：评分、详细描述、所有证据点
5. 差异分析（完整列举所有差异项）
6. 音频特征对比（两个音频的完整特征描述）
7. 内容重叠分析（共同旋律模式、歌词、音乐元素）
8. 变换分析（调性、速度、编曲、人声处理的变化）
9. 元数据对比（时长、音质、格式）
10. 综合结论和关键发现
11. 技术附录（Token 使用统计）

写作要求：
- 使用正式、专业的技术报告语气
- 段落之间逻辑连贯，论述清晰
- **必须引用所有具体数据、评分和证据，不要省略任何细节**
- 保留所有时间戳和具体音频特征描述
- 避免使用第一人称，保持客观中立
- 使用中文撰写，表达准确、流畅
- 报告应详尽完整，不少于3000字

请直接输出报告正文，不要包含 Markdown 格式标记。"""
    
    def _build_user_prompt(
        self,
        audio_analysis: Dict[str, Any],
        video1_info: Dict[str, Any],
        video2_info: Dict[str, Any]
    ) -> str:
        """构建用户提示词
        
        Args:
            audio_analysis: 音频比对分析结果
            video1_info: 视频1的基本信息
            video2_info: 视频2的基本信息
            
        Returns:
            用户提示词
        """
        # 提取完整的分析数据
        sim_analysis = audio_analysis.get("similarity_analysis", {})
        diff_analysis = audio_analysis.get("difference_analysis", {})
        transform_analysis = audio_analysis.get("transformation_analysis", {})
        audio_features = audio_analysis.get("audio_features", {})
        content_overlap = audio_analysis.get("content_overlap", {})
        metadata = audio_analysis.get("metadata_comparison", {})
        summary = audio_analysis.get("summary", {})
        token_usage = audio_analysis.get("_token_usage", {})
        
        # 序列化完整的 JSON 数据
        analysis_json = json.dumps(audio_analysis, ensure_ascii=False, indent=2)
        
        # 缩短文件名以避免格式问题
        def shorten_filename(filename: str, max_len: int = 50) -> str:
            if len(filename) <= max_len:
                return filename
            return filename[:max_len-3] + "..."
        
        return f"""请基于以下音频比对分析数据，撰写一份专业、全面的音频相似度分析报告。

【音频文件信息】

音频文件1：
- 文件名：{shorten_filename(video1_info.get('filename', 'N/A'))}
- 文件大小：{video1_info.get('size_mb', 0)} MB
- 时长：{video1_info.get('duration', 'N/A')}

音频文件2：
- 文件名：{shorten_filename(video2_info.get('filename', 'N/A'))}
- 文件大小：{video2_info.get('size_mb', 0)} MB
- 时长：{video2_info.get('duration', 'N/A')}

【完整分析数据】

以下是完整的音频比对分析 JSON 数据，请完整保留所有细节和颗粒度：

{analysis_json}

【报告撰写要求】

请撰写一份完整的专业分析报告，包括但不限于：

1. 报告标题和概述
   - 分析日期
   - 音频文件基本信息对比
   
2. 总体相似度评估
   - 总体相似度评分：{sim_analysis.get('overall_similarity_score', 0)}/100
   - 整体评估结论

3. 各维度详细分析（完整引用所有数据和证据）
   - 旋律相似度：{sim_analysis.get('melody_similarity', {}).get('score', 0)}/100
   - 节奏相似度：{sim_analysis.get('rhythm_similarity', {}).get('score', 0)}/100
   - 音色相似度：{sim_analysis.get('timbre_similarity', {}).get('score', 0)}/100
   - 人声相似度：{sim_analysis.get('vocal_similarity', {}).get('score', 0)}/100
   - 结构相似度：{sim_analysis.get('structure_similarity', {}).get('score', 0)}/100
   
4. 差异分析（详细列举所有差异点）
   - 旋律差异
   - 节奏差异
   - 音色差异
   - 人声差异
   - 制作差异

5. 音频特征对比
   - 音频1特征：{audio_features.get('audio1_features', {})}
   - 音频2特征：{audio_features.get('audio2_features', {})}

6. 内容重叠分析
   - 共同旋律模式
   - 共同歌词片段
   - 共同音乐元素

7. 变换分析
   - 调性变化
   - 速度变化
   - 编曲变化
   - 人声处理变化

8. 综合结论
   - 关键发现：{chr(10).join('   - ' + f for f in summary.get('key_findings', []))}
   - 分析置信度说明
   - 专业意见和建议

9. 技术附录
   - Token 使用统计：输入 {token_usage.get('prompt_token_count', 0):,}, 输出 {token_usage.get('candidates_token_count', 0):,}, 总计 {token_usage.get('total_token_count', 0):,}

**重要提示**：
- 必须完整保留原始分析数据中的所有时间戳、具体描述和证据
- 所有评分和数值必须准确引用
- 保持报告的专业性和客观性
- 使用清晰的段落结构和逻辑论述

请直接输出完整的报告正文。"""


def setup_chinese_font():
    """设置中文字体"""
    # 尝试使用系统中文字体
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",  # macOS
        "/System/Library/Fonts/STHeiti Light.ttc",  # macOS
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Linux
        "C:\\Windows\\Fonts\\simhei.ttf",  # Windows
        "C:\\Windows\\Fonts\\simsun.ttc",  # Windows
    ]
    
    for font_path in font_paths:
        if Path(font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont('Chinese', font_path))
                log.info(f"使用中文字体: {font_path}")
                return 'Chinese'
            except Exception as e:
                log.error(f"注册字体失败 {font_path}: {e}")
                continue
    
    log.error("未找到可用的中文字体，将使用默认字体（可能无法正确显示中文）")
    return 'Helvetica'


def create_pdf_report(
    report_text: str,
    audio_analysis: Dict[str, Any],
    video1_info: Dict[str, Any],
    video2_info: Dict[str, Any],
    output_path: Path,
    video1_thumbnail: Optional[Path],
    video2_thumbnail: Optional[Path],
):
    """创建 PDF 报告
    
    Args:
        report_text: 报告文本
        audio_analysis: 音频分析结果
        video1_info: 视频1信息
        video2_info: 视频2信息
        output_path: 输出文件路径
        video1_thumbnail: 视频1缩略图路径
        video2_thumbnail: 视频2缩略图路径
    """
    log.info("开始生成 PDF 报告...")
    
    # 设置中文字体
    chinese_font = setup_chinese_font()
    
    # 创建 PDF 文档
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    
    # 创建样式
    styles = getSampleStyleSheet()
    
    # 标题样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=chinese_font,
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    # 标题2样式
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
    )
    
    # 正文样式
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontName=chinese_font,
        fontSize=11,
        leading=18,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
    )
    
    # 构建文档内容
    story = []
    
    # 标题
    story.append(Paragraph("音频比对分析报告", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 日期
    date_text = f"报告日期：{datetime.now().strftime('%Y年%m月%d日')}"
    story.append(Paragraph(date_text, body_style))
    story.append(Spacer(1, 1*cm))
    
    # === 展示音频文件信息 ===
    story.append(Paragraph("音频文件信息", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 缩短文件名函数
    def shorten_filename_for_pdf(filename: str, max_len: int = 40) -> str:
        """缩短文件名用于 PDF 显示"""
        if len(filename) <= max_len:
            return filename
        # 保留开头和扩展名
        name_part = filename[:max_len-10]
        ext_idx = filename.rfind('.')
        if ext_idx > 0:
            ext = filename[ext_idx:]
            return name_part + "..." + ext
        return name_part + "..."
    
    # 音频信息表格
    audio_data = [
        ['', '音频文件1', '音频文件2'],
        ['文件名', 
         shorten_filename_for_pdf(video1_info.get('filename', 'N/A')), 
         shorten_filename_for_pdf(video2_info.get('filename', 'N/A'))],
        ['文件大小', f"{video1_info.get('size_mb', 0)} MB", f"{video2_info.get('size_mb', 0)} MB"],
        ['时长', video1_info.get('duration', 'N/A'), video2_info.get('duration', 'N/A')],
    ]
    
    audio_table = Table(audio_data, colWidths=[4*cm, 6*cm, 6*cm])
    audio_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), chinese_font),
        ('FONTNAME', (0, 1), (-1, -1), chinese_font),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(audio_table)
    story.append(Spacer(1, 1*cm))
    
    # 如果有视频截图则添加（本例中没有）
    if video1_thumbnail and video1_thumbnail.exists():
        story.append(Paragraph("视频开始帧截图", heading_style))
        story.append(Spacer(1, 0.5*cm))
        
        max_width = 15*cm
        max_height = 10*cm
        
        try:
            story.append(Paragraph(f"音频来源1: {video1_info.get('filename', 'N/A')}", body_style))
            img1 = Image(str(video1_thumbnail))
            img1._restrictSize(max_width, max_height)
            story.append(img1)
            story.append(Spacer(1, 1*cm))
        except Exception as e:
            log.error(f"添加视频1截图失败: {e}")
    
    if video2_thumbnail and video2_thumbnail.exists():
        try:
            story.append(Paragraph(f"音频来源2: {video2_info.get('filename', 'N/A')}", body_style))
            img2 = Image(str(video2_thumbnail))
            img2._restrictSize(max_width, max_height)
            story.append(img2)
            story.append(Spacer(1, 1*cm))
        except Exception as e:
            log.error(f"添加视频2截图失败: {e}")
    
    # 添加分页，分隔音频信息和报告文本
    if video1_thumbnail or video2_thumbnail:
        story.append(PageBreak())
    
    # === 报告正文 ===
    story.append(Paragraph("分析报告", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 分割报告文本并添加到文档
    paragraphs = report_text.split('\n\n')
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # 跳过报告文本中的标题（已经在上面添加了）
        if para.startswith('##') or '图片侵权分析报告' in para:
            continue
        
        # 判断是否是标题（简单规则：以"【"开头或包含"案例"、"结论"等关键词）
        if para.startswith('【') or para.startswith('**') and para.endswith('**'):
            # 移除 Markdown 标记
            clean_para = para.replace('**', '').replace('*', '').replace('【', '').replace('】', '')
            story.append(Paragraph(clean_para, heading_style))
        else:
            # 移除 Markdown 标记
            clean_para = para.replace('**', '').replace('*', '')
            story.append(Paragraph(clean_para, body_style))
    
    # 生成 PDF
    doc.build(story)
    log.info(f"✓ PDF 报告已生成: {output_path}")


def main():
    """主函数"""
    # 目录路径
    script_dir = Path(__file__).resolve().parent
    output_dir = script_dir / "output"
    
    # 输入文件
    analysis_json = output_dir / "content_audio_comparison_analysis.json"
    
    # 音频文件
    audio1_filename = "正版3元购买-obj_w5rDlsOJwrLDjj7CmsOj_43959726538_da4a_6bca_811d_4e7ffd4f26828be7ca983453d32b7ae1.m4a"
    audio2_filename = "播客版本-obj_w5zDlMODwrDDiGjCn8Ky_31659156232_3a42_f683_3526_a247cd5af3d1f170fd118f04214509de.mp3"
    audio1_path = script_dir / audio1_filename
    audio2_path = script_dir / audio2_filename
    
    # 输出文件
    report_text_file = output_dir / "content_audio_analysis_report.txt"
    report_pdf_file = output_dir / "content_audio_analysis_report.pdf"
    
    print("\n" + "=" * 80)
    print("音频比对分析报告生成器 - 基于 Gemini 2.0 Flash")
    print("=" * 80 + "\n")
    
    # 验证文件存在
    if not analysis_json.exists():
        raise FileNotFoundError(f"分析结果不存在: {analysis_json}")
    if not audio1_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio1_path}")
    if not audio2_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio2_path}")
    
    print(f"✓ 加载分析结果: {analysis_json.name}")
    print(f"✓ 音频文件1: {audio1_filename}")
    print(f"✓ 音频文件2: {audio2_filename}\n")
    
    # 加载分析结果
    with open(analysis_json, encoding="utf-8") as f:
        audio_analysis = json.load(f)
    
    # 步骤 0: 获取音频信息（无需截图）
    print("步骤 0: 获取音频文件信息")
    print("-" * 80)
    
    audio1_info = get_audio_info(audio1_path)
    audio2_info = get_audio_info(audio2_path)
    
    log.info(f"音频1: {audio1_info['filename']}, {audio1_info['size_mb']} MB, {audio1_info['duration']}")
    log.info(f"音频2: {audio2_info['filename']}, {audio2_info['size_mb']} MB, {audio2_info['duration']}")
    print()
    
    # 加载 API Key
    api_key = load_api_key_from_env()
    print(f"✓ API Key: {api_key[:20]}...\n")
    
    # 创建报告生成器
    generator = ReportGenerator(api_key=api_key)
    
    try:
        # 步骤 1: 生成报告文本
        print("步骤 1: 使用 Gemini 生成报告文本")
        print("-" * 80)
        report_text = generator.generate_report_text(
            audio_analysis=audio_analysis,
            video1_info=audio1_info,
            video2_info=audio2_info
        )
        print()
        
        # 保存报告文本
        with open(report_text_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"✓ 报告文本已保存: {report_text_file}\n")
        
        # 步骤 2: 生成 PDF 报告（无视频截图）
        print("步骤 2: 生成 PDF 报告")
        print("-" * 80)
        create_pdf_report(
            report_text=report_text,
            audio_analysis=audio_analysis,
            video1_info=audio1_info,
            video2_info=audio2_info,
            output_path=report_pdf_file,
            video1_thumbnail=None,
            video2_thumbnail=None,
        )
        print()
        
        # 打印报告预览
        print("=" * 80)
        print("报告预览（前500字）")
        print("=" * 80 + "\n")
        print(report_text[:500] + "...\n")
        
        print("=" * 80)
        print("✅ 报告生成完成！")
        print("=" * 80 + "\n")
        print(f"📄 报告文本: {report_text_file}")
        print(f"📋 PDF 报告: {report_pdf_file}\n")
        
        # 显示分析摘要
        sim_analysis = audio_analysis.get("similarity_analysis", {})
        token_usage = audio_analysis.get("_token_usage", {})
        
        print("=" * 80)
        print("分析摘要")
        print("=" * 80 + "\n")
        print(f"📊 总体相似度: {sim_analysis.get('overall_similarity_score', 0)}/100")
        print(f"💰 Token 使用: 输入 {token_usage.get('prompt_token_count', 0):,}, "
              f"输出 {token_usage.get('candidates_token_count', 0):,}, "
              f"总计 {token_usage.get('total_token_count', 0):,}\n")
        
    except Exception as e:
        log.error(f"生成报告时出错: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

