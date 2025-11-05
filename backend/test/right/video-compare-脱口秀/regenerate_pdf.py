#!/usr/bin/env python3
"""
重新生成 PDF 报告 - 添加视频截图，移除创作性评估
"""
import os
import sys
import json
import subprocess
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
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    log.error("需要安装 reportlab: pip install reportlab")
    sys.exit(1)


def extract_video_thumbnail(video_path: Path, output_path: Path, timestamp: str = "00:00:01"):
    """从视频中提取缩略图
    
    Args:
        video_path: 视频文件路径
        output_path: 输出图片路径
        timestamp: 时间戳（默认第1秒）
    """
    log.info(f"从视频提取缩略图: {video_path.name}")
    
    try:
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", timestamp,
            "-vframes", "1",
            "-q:v", "2",
            "-y",  # 覆盖已存在的文件
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        log.info(f"✓ 缩略图已保存: {output_path}")
        return True
    
    except Exception as e:
        log.error(f"提取缩略图失败: {e}")
        return False


def setup_chinese_font():
    """设置中文字体"""
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
    
    log.error("未找到可用的中文字体")
    return 'Helvetica'


def create_pdf_with_thumbnails(
    report_text: str,
    analysis: Dict[str, Any],
    output_path: Path,
    video1_thumbnail: Path,
    video2_thumbnail: Path,
):
    """创建带视频缩略图的 PDF 报告
    
    Args:
        report_text: 报告文本（已移除创作性评估部分）
        analysis: 分析结果
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
    story.append(Paragraph("视频抄袭与搬运分析报告", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 日期
    date_text = f"报告日期：{datetime.now().strftime('%Y年%m月%d日')}"
    story.append(Paragraph(date_text, body_style))
    story.append(Spacer(1, 1*cm))
    
    # === 视频缩略图展示 ===
    story.append(Paragraph("视频截图对比", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 图片尺寸设置
    max_width = 15*cm
    max_height = 8*cm
    
    video_info = analysis.get("video_info", {})
    
    # 原始视频缩略图
    if video1_thumbnail.exists():
        try:
            img1 = Image(str(video1_thumbnail))
            img1._restrictSize(max_width, max_height)
            story.append(Paragraph(f"原始视频: {video_info.get('original_video', 'N/A')}", body_style))
            story.append(img1)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            log.error(f"添加图片失败 {video1_thumbnail}: {e}")
    
    # 疑似抄袭视频缩略图
    if video2_thumbnail.exists():
        try:
            img2 = Image(str(video2_thumbnail))
            img2._restrictSize(max_width, max_height)
            story.append(Paragraph(f"疑似抄袭视频: {video_info.get('suspected_video', 'N/A')}", body_style))
            story.append(img2)
            story.append(Spacer(1, 1*cm))
        except Exception as e:
            log.error(f"添加图片失败 {video2_thumbnail}: {e}")
    
    # 添加视频信息表格
    story.append(Paragraph("视频信息", heading_style))
    story.append(Spacer(1, 0.3*cm))
    
    original_video = video_info.get("original_video", "N/A")
    suspected_video = video_info.get("suspected_video", "N/A")
    analysis_date = video_info.get("analysis_date", "N/A")
    
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
    
    # 添加 Token 使用信息（如果有）
    token_usage = analysis.get("token_usage", {})
    token_info = ""
    if token_usage:
        token_info = f"Token使用: {token_usage.get('total_tokens', 0):,}"
    
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
    
    if token_info:
        metrics_data.append(["Token使用量", token_info])
    
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
    
    # 添加分页
    story.append(PageBreak())
    
    # === 报告正文 ===
    story.append(Paragraph("详细分析报告", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 按行分割报告文本，精确匹配 txt 格式
    lines = report_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 跳过空行
        if not line:
            i += 1
            continue
        
        # 跳过已经添加的标题
        if '视频抄袭' in line or '分析报告' in line or line.startswith('日期') or line.startswith('报告日期'):
            i += 1
            continue
        
        # 识别章节标题（数字开头，如 "1. 执行摘要"）
        if line and len(line) > 2 and line[0].isdigit() and line[1] in ['.', '、']:
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph(line, heading_style))
            story.append(Spacer(1, 0.2*cm))
        
        # 识别子章节标题（如 "3.1 内容相似度"）
        elif line and len(line) > 4 and line[0].isdigit() and '.' in line[:5] and line.split()[0].count('.') == 1:
            story.append(Spacer(1, 0.2*cm))
            # 创建子标题样式
            subheading_style = ParagraphStyle(
                'SubHeading',
                parent=heading_style,
                fontSize=14,
                textColor=colors.HexColor('#34495e'),
            )
            story.append(Paragraph(line, subheading_style))
        
        # 识别字段标题（如 "评分：95"）
        elif ':' in line or '：' in line:
            # 使用粗体样式
            bold_style = ParagraphStyle(
                'Bold',
                parent=body_style,
                fontName=chinese_font,
                fontSize=11,
                textColor=colors.HexColor('#2c3e50'),
            )
            clean_line = line.replace('**', '').replace('*', '')
            story.append(Paragraph(clean_line, bold_style))
        
        # 识别列表项（以 * 或 - 开头）
        elif line.startswith('*') or line.startswith('-'):
            clean_line = line[1:].strip()
            # 使用缩进样式
            list_style = ParagraphStyle(
                'List',
                parent=body_style,
                leftIndent=20,
                bulletIndent=10,
            )
            story.append(Paragraph(f"• {clean_line}", list_style))
        
        # 普通段落
        else:
            clean_line = line.replace('**', '').replace('*', '')
            story.append(Paragraph(clean_line, body_style))
        
        i += 1
    
    # 生成 PDF
    doc.build(story)
    log.info(f"✓ PDF 报告已生成: {output_path}")


def remove_creativity_assessment(text: str) -> str:
    """从报告文本中移除创作性评估部分
    
    Args:
        text: 原始报告文本
        
    Returns:
        移除创作性评估后的文本
    """
    lines = text.split('\n')
    result_lines = []
    skip = False
    
    for line in lines:
        # 检测创作性评估章节开始
        if '创作性评估' in line or (line.startswith('6') and '创作性' in line):
            skip = True
            continue
        
        # 检测下一个章节开始（侵权评估或结论）
        if skip and (line.startswith('7') or line.startswith('8') or '侵权评估' in line):
            skip = False
        
        if not skip:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("重新生成 PDF 报告 - 添加视频截图，移除创作性评估")
    print("=" * 80 + "\n")
    
    # 处理两个目录
    projects = [
        {
            "name": "张雨绮视频对比",
            "dir": Path("/Users/rigel/project/hdl-tikhub-goodgame/backend/test/right/video-compare-张雨绮"),
            "video1": "video1_original.mp4",
            "video2": "video2_suspected.mp4",
        },
        {
            "name": "脱口秀视频对比",
            "dir": Path("/Users/rigel/project/hdl-tikhub-goodgame/backend/test/right/video-compare-脱口秀"),
            "video1": "video1_comedy_king.mp4",
            "video2": "video2_xhs_chenmingfei.mp4",
        }
    ]
    
    for project in projects:
        print(f"\n处理项目: {project['name']}")
        print("-" * 80)
        
        project_dir = project["dir"]
        output_dir = project_dir / "output"
        
        # 文件路径
        video1_path = project_dir / project["video1"]
        video2_path = project_dir / project["video2"]
        analysis_json = output_dir / "video_comparison_analysis.json"
        report_txt = output_dir / "video_analysis_report.txt"
        report_pdf = output_dir / "video_analysis_report.pdf"
        
        # 缩略图路径
        video1_thumb = output_dir / "video1_thumbnail.jpg"
        video2_thumb = output_dir / "video2_thumbnail.jpg"
        
        # 检查文件存在
        if not video1_path.exists():
            log.error(f"视频文件不存在: {video1_path}")
            continue
        if not video2_path.exists():
            log.error(f"视频文件不存在: {video2_path}")
            continue
        if not analysis_json.exists():
            log.error(f"分析结果不存在: {analysis_json}")
            continue
        if not report_txt.exists():
            log.error(f"报告文本不存在: {report_txt}")
            continue
        
        # 1. 提取视频缩略图
        print("\n步骤 1: 提取视频缩略图")
        extract_video_thumbnail(video1_path, video1_thumb)
        extract_video_thumbnail(video2_path, video2_thumb)
        
        # 2. 加载分析结果
        print("\n步骤 2: 加载分析结果")
        with open(analysis_json, encoding="utf-8") as f:
            analysis = json.load(f)
        print(f"✓ 加载分析结果: {analysis_json.name}")
        
        # 3. 加载并处理报告文本
        print("\n步骤 3: 处理报告文本（移除创作性评估）")
        with open(report_txt, encoding="utf-8") as f:
            report_text = f.read()
        
        # 移除创作性评估部分
        report_text = remove_creativity_assessment(report_text)
        print("✓ 已移除创作性评估部分")
        
        # 4. 生成新的 PDF
        print("\n步骤 4: 生成新的 PDF 报告")
        create_pdf_with_thumbnails(
            report_text=report_text,
            analysis=analysis,
            output_path=report_pdf,
            video1_thumbnail=video1_thumb,
            video2_thumbnail=video2_thumb,
        )
        
        print(f"\n✅ {project['name']} 处理完成！")
        print(f"📋 PDF 报告: {report_pdf}\n")
    
    print("=" * 80)
    print("✅ 所有 PDF 报告已更新！")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

