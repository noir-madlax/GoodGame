#!/usr/bin/env python3
"""
视频抄袭分析报告生成器 - 使用 Gemini 2.0 Flash Thinking 生成专业报告并输出为 PDF
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

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
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    log.error("需要安装 reportlab: pip install reportlab")
    sys.exit(1)


# Gemini 配置 - 使用 Thinking 模型生成更专业的报告
GEMINI_MODEL = "gemini-2.0-flash-thinking-exp"


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


class VideoReportGenerator:
    """视频分析报告生成器"""
    
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
        analysis: Dict[str, Any]
    ) -> str:
        """使用 Gemini 生成报告文本
        
        Args:
            analysis: 视频对比分析结果
            
        Returns:
            生成的报告文本
        """
        log.info("开始生成报告文本...")
        
        # 构建提示词
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(analysis)
        
        # 配置生成参数
        config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=8000,
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
        return """你是一位专业的知识产权法律顾问和视频内容分析专家，擅长撰写视频抄袭和搬运分析报告。

你的任务是：
1. 基于提供的完整视频对比分析数据（JSON格式），撰写一份专业、详尽的视频抄袭/搬运分析报告
2. 报告必须涵盖所有原始数据中的细节，包括所有评分、描述、证据列表、差异项、修改分析等
3. 不得概括、简化或遗漏任何原始数据中的信息
4. 保持原始分析的颗粒度和细节层次

核心要求（极其重要）：
- **保留所有证据列表**：每个维度的 evidence 列表必须完整呈现，逐条列出
- **保留所有描述**：每个分析维度的 description 必须完整引用或改写
- **保留所有差异项**：difference_analysis 中的所有列表项必须完整呈现
- **保留所有修改分析**：modification_analysis 的所有字段必须详细说明
- **保留完整的侵权评估**：reasoning、key_indicators、mitigating_factors、aggravating_factors 必须完整呈现

报告结构要求：
1. 报告标题和日期
2. 执行摘要（简要概述核心结论和风险等级）
3. 视频信息概览
   - 原始视频信息
   - 疑似抄袭/搬运视频信息
   - 分析时间
4. 相似度分析
   - 内容相似度（评分、描述、所有证据项）
   - 视觉相似度（评分、描述、所有证据项）
   - 音频相似度（评分、描述、所有证据项）
   - 时间结构相似度（评分、描述、所有证据项）
5. 差异分析
   - 内容差异（列出所有项）
   - 视觉差异（列出所有项）
   - 音频差异（列出所有项）
6. 修改分析
   - 检测到的修改（列出所有项）
   - 裁剪分析（完整描述）
   - 镜像分析（完整描述）
   - 变速分析（完整描述）
   - 水印变化（完整描述）
   - 调色分析（完整描述）
   - 其他修改（完整描述）
7. 创作性评估
   - 是否有实质性创作
   - 创作性评分
   - 详细描述和证据
8. 侵权评估
   - 综合相似度评分
   - 风险等级和风险评分
   - 推理过程（完整引用）
   - 关键指标（列出所有项）
   - 减轻因素（列出所有项）
   - 加重因素（列出所有项）
9. 结论和建议
   - 是否涉嫌抄袭
   - 置信度
   - 综合总结
   - 核心发现（列出所有项）
   - 建议（列出所有项）

写作风格：
- 使用正式、专业的法律和技术报告语气
- 逐项列举证据和发现，使用项目符号或编号列表
- 保持客观中立，但论述要有力且有说服力
- 避免使用第一人称
- 使用中文撰写，表达准确、流畅、专业

特别强调：
- 你的任务是将结构化的 JSON 数据转化为流畅的报告文本，而不是重新分析或概括
- 所有数值、证据、描述都必须来自原始数据，不得自行创作或省略
- 报告的长度和细节应与原始数据的丰富程度相匹配

请直接输出报告正文，不要包含 Markdown 格式标记。"""
    
    def _build_user_prompt(
        self,
        analysis: Dict[str, Any]
    ) -> str:
        """构建用户提示词 - 提供完整的 JSON 数据
        
        Args:
            analysis: 完整的视频对比分析结果
            
        Returns:
            用户提示词（包含完整的 JSON 数据）
        """
        # 将 JSON 数据格式化为字符串
        analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)
        
        # 提取关键信息
        video_info = analysis.get("video_info", {})
        original_video = video_info.get("original_video", "视频1")
        suspected_video = video_info.get("suspected_video", "视频2")
        
        return f"""请基于以下视频对比分析的完整数据（JSON格式），撰写一份专业、详尽的视频抄袭/搬运分析报告。

重要提示：
1. 以下提供的是完整的 JSON 分析数据，包含所有维度的评分、描述、证据列表、差异分析、修改分析等
2. 你必须将这些结构化数据转化为流畅、专业的报告文本
3. 不得遗漏任何数据字段或列表项
4. 保持原始数据的细节颗粒度和专业深度

==================== 视频对比分析数据 ====================

视频信息：
- 原始视频：{original_video}
- 疑似抄袭/搬运视频：{suspected_video}
- 分析类型：视频内容抄袭和搬运检测

完整分析数据（JSON）：
{analysis_json}

==================== 报告撰写要求 ====================

请按照以下结构撰写报告，确保涵盖所有上述 JSON 数据中的信息：

1. 报告标题和日期

2. 执行摘要
   - 简要说明报告目的
   - 概述核心结论和风险等级

3. 视频信息概览
   - 原始视频名称
   - 疑似抄袭/搬运视频名称
   - 分析时间

4. 相似度分析
   4.1 内容相似度
       - 评分（score）
       - 完整描述（description）
       - 所有证据项（evidence）：逐条列出
   
   4.2 视觉相似度
       - 评分（score）
       - 完整描述（description）
       - 所有证据项（evidence）：逐条列出
   
   4.3 音频相似度
       - 评分（score）
       - 完整描述（description）
       - 所有证据项（evidence）：逐条列出
   
   4.4 时间结构相似度
       - 评分（score）
       - 完整描述（description）
       - 所有证据项（evidence）：逐条列出

5. 差异分析
   - 内容差异（content_differences）：列出所有项
   - 视觉差异（visual_differences）：列出所有项
   - 音频差异（audio_differences）：列出所有项

6. 修改分析
   - 检测到的修改（detected_modifications）：列出所有项
   - 裁剪（cropping）：完整描述
   - 镜像（mirroring）：完整描述
   - 变速（speed_change）：完整描述
   - 水印变化（watermark_changes）：完整描述
   - 调色（color_grading）：完整描述
   - 其他修改（other_modifications）：完整描述

7. 创作性评估
   - 是否有实质性创作（has_substantial_creativity）
   - 创作性评分（creativity_score）
   - 详细描述（description）
   - 证据列表（evidence）：逐条列出

8. 侵权评估
   - 综合相似度评分（overall_similarity_score）
   - 风险等级（risk_level）和风险评分（risk_score）
   - 推理过程（reasoning）：完整引用
   - 关键指标（key_indicators）：列出所有项
   - 减轻因素（mitigating_factors）：列出所有项
   - 加重因素（aggravating_factors）：列出所有项

9. 结论和建议
   - 是否涉嫌抄袭（is_plagiarism）
   - 置信度（confidence_level）
   - 综合总结（summary）
   - 核心发现（key_findings）：列出所有项
   - 建议（recommendations）：列出所有项

请开始撰写报告。记住：必须保留所有数据细节，不得概括或省略。"""


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
    analysis: Dict[str, Any],
    output_path: Path,
):
    """创建 PDF 报告
    
    Args:
        report_text: 报告文本
        analysis: 分析结果
        output_path: 输出文件路径
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
    story.append(Paragraph("视频抄袭与搬运分析报告", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 日期
    date_text = f"报告日期：{datetime.now().strftime('%Y年%m月%d日')}"
    story.append(Paragraph(date_text, body_style))
    story.append(Spacer(1, 1*cm))
    
    # 添加视频信息表格
    video_info = analysis.get("video_info", {})
    original_video = video_info.get("original_video", "N/A")
    suspected_video = video_info.get("suspected_video", "N/A")
    analysis_date = video_info.get("analysis_date", "N/A")
    
    story.append(Paragraph("视频信息", heading_style))
    story.append(Spacer(1, 0.3*cm))
    
    video_data = [
        ["项目", "内容"],
        ["原始视频", original_video],
        ["疑似抄袭视频", suspected_video],
        ["分析时间", analysis_date],
    ]
    
    video_table = Table(video_data, colWidths=[4*cm, 13*cm])
    video_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), chinese_font),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), chinese_font),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(video_table)
    story.append(Spacer(1, 1*cm))
    
    # 添加关键指标表格
    infringement = analysis.get("infringement_assessment", {})
    
    story.append(Paragraph("关键指标", heading_style))
    story.append(Spacer(1, 0.3*cm))
    
    metrics_data = [
        ["指标", "数值"],
        ["内容相似度", f"{analysis.get('content_similarity', {}).get('score', 0)}/100"],
        ["视觉相似度", f"{analysis.get('visual_similarity', {}).get('score', 0)}/100"],
        ["音频相似度", f"{analysis.get('audio_similarity', {}).get('score', 0)}/100"],
        ["时间结构相似度", f"{analysis.get('temporal_similarity', {}).get('score', 0)}/100"],
        ["综合相似度", f"{infringement.get('overall_similarity_score', 0)}/100"],
        ["风险等级", infringement.get('risk_level', 'N/A')],
        ["风险评分", f"{infringement.get('risk_score', 0)}/100"],
    ]
    
    metrics_table = Table(metrics_data, colWidths=[6*cm, 11*cm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), chinese_font),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, 1), (-1, -1), chinese_font),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(metrics_table)
    story.append(Spacer(1, 1*cm))
    
    # 添加分页，分隔表格和报告文本
    story.append(PageBreak())
    
    # === 报告正文 ===
    story.append(Paragraph("详细分析报告", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 分割报告文本并添加到文档
    paragraphs = report_text.split('\n\n')
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # 跳过报告文本中的标题（已经在上面添加了）
        if para.startswith('##') or '视频抄袭' in para or '分析报告' in para:
            continue
        
        # 判断是否是标题（简单规则：以"【"开头或包含特定关键词）
        is_heading = (
            para.startswith('【') or 
            (para.startswith('**') and para.endswith('**')) or
            any(keyword in para for keyword in ['执行摘要', '相似度分析', '差异分析', 
                                                 '修改分析', '创作性评估', '侵权评估', 
                                                 '结论', '建议'])
        )
        
        if is_heading:
            # 移除 Markdown 标记
            clean_para = para.replace('**', '').replace('*', '').replace('【', '').replace('】', '')
            story.append(Paragraph(clean_para, heading_style))
        else:
            # 移除 Markdown 标记
            clean_para = para.replace('**', '').replace('*', '')
            # 处理过长的段落
            if len(clean_para) > 1000:
                # 按句子分割
                sentences = clean_para.replace('。', '。\n').split('\n')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        story.append(Paragraph(sentence, body_style))
            else:
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
    analysis_json = output_dir / "video_comparison_analysis.json"
    
    # 输出文件
    report_text_file = output_dir / "video_analysis_report.txt"
    report_pdf_file = output_dir / "video_analysis_report.pdf"
    
    print("\n" + "=" * 80)
    print("视频抄袭分析报告生成器 - 基于 Gemini 2.0 Flash Thinking")
    print("=" * 80 + "\n")
    
    # 验证文件存在
    if not analysis_json.exists():
        raise FileNotFoundError(f"分析结果不存在: {analysis_json}")
    
    print(f"✓ 加载分析结果: {analysis_json.name}\n")
    
    # 加载分析结果
    with open(analysis_json, encoding="utf-8") as f:
        analysis = json.load(f)
    
    # 加载 API Key
    api_key = load_api_key_from_env()
    print(f"✓ API Key: {api_key[:20]}...\n")
    
    # 创建报告生成器
    generator = VideoReportGenerator(api_key=api_key)
    
    try:
        # 步骤 1: 生成报告文本
        print("步骤 1: 使用 Gemini 生成报告文本")
        print("-" * 80)
        report_text = generator.generate_report_text(analysis=analysis)
        print()
        
        # 保存报告文本
        with open(report_text_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"✓ 报告文本已保存: {report_text_file}\n")
        
        # 步骤 2: 生成 PDF 报告
        print("步骤 2: 生成 PDF 报告")
        print("-" * 80)
        create_pdf_report(
            report_text=report_text,
            analysis=analysis,
            output_path=report_pdf_file,
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
        
    except Exception as e:
        log.error(f"生成报告时出错: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
