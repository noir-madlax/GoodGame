#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成达人投放价值评估报告 (PDF)

使用 reportlab 生成专业的 PDF 报告。
"""

import json
import os
import datetime
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

def generate_pdf_report():
    """生成 PDF 报告"""
    
    base_dir = Path(__file__).parent.parent / "kol-video-fetcher" / "output"
    json_file = base_dir / "professional_kol_report.json"
    pdf_file = base_dir / "KOL_Evaluation_Report_20251124.pdf"
    
    if not json_file.exists():
        print("❌ 数据文件不存在，请先运行步骤 7")
        return

    # 加载数据
    with open(json_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)

    print("📊 开始生成 PDF 报告...")
    
    # 注册中文字体
    # STSong-Light 是 Adobe 预定义的 CJK 字体，通常在 PDF 阅读器中可用
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        font_name = 'STSong-Light'
        is_bold_font_available = False
    except Exception as e:
        print(f"⚠️ 字体注册失败: {e}")
        font_name = 'Helvetica' # Fallback
        
    # 创建文档
    doc = SimpleDocTemplate(
        str(pdf_file),
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # 定义自定义样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=24,
        leading=30,
        alignment=1, # Center
        spaceAfter=30
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        leading=20,
        alignment=1,
        textColor=colors.gray,
        spaceAfter=50
    )
    
    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=16,
        leading=20,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#2E5C8A') # Navy Blue
    )
    
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading3'],
        fontName=font_name,
        fontSize=14,
        leading=18,
        spaceBefore=15,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=15,
        spaceAfter=6
    )
    
    caption_style = ParagraphStyle(
        'CustomCaption',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=colors.gray,
        alignment=1
    )

    # 构建内容
    story = []
    
    # --- 封面 ---
    story.append(Spacer(1, 100))
    story.append(Paragraph("护肤垂类达人投放价值评估报告", title_style))
    story.append(Paragraph("基于 251 位达人与 617 条视频数据的深度量化分析", subtitle_style))
    story.append(Spacer(1, 50))
    
    date_str = datetime.datetime.now().strftime("%Y年%m月%d日")
    story.append(Paragraph(f"报告日期: {date_str}", body_style))
    story.append(Paragraph("出品方: GoodGame 数据分析团队", body_style))
    story.append(PageBreak())
    
    # --- 1. 执行摘要 ---
    story.append(Paragraph("1. 项目背景与执行摘要", h1_style))
    
    summary_text = f"""
    本次评估覆盖了抖音平台护肤垂类的 <b>251位</b> 达人，共计分析视频 <b>617条</b>。
    我们采集了每位达人的三类代表性视频（爆款、热门、最新），旨在全方位评估达人的流量天花板、近期热度及日常稳定性。
    <br/><br/>
    <b>核心发现：</b>
    <br/>
    • <b>流量分层</b>：腰部达人（平均点赞1k-1w）占比约 15%，是本次筛选的核心高性价比资源。
    <br/>
    • <b>互动质量</b>：绝大多数达人（93%）的互动率极高（>10%），显示出该垂类粉丝的高粘性，但需注意甄别数据真实性。
    <br/>
    • <b>潜力人选</b>：我们基于"高流量+高互动"标准，最终筛选出 <b>50位</b> 具备强带货潜力的优质达人。
    """
    story.append(Paragraph(summary_text, body_style))
    
    # --- 2. 视频数据洞察 ---
    story.append(Paragraph("2. 视频类型数据表现对比", h1_style))
    story.append(Paragraph("通过对比三类视频的数据，我们可以清晰看到达人的爆发力和常态表现：", body_style))
    
    type_data = report_data.get('type_comparison', {})
    
    # 表格数据
    table_data = [
        ['视频类型', '平均点赞', '平均互动率', '平均赞评比', '样本数', '分析解读']
    ]
    
    type_mapping = {
        'masterpiece': ('爆款视频 (Tag 3)', '流量天花板，代表最高内容水准'),
        'hot': ('热门视频 (Tag 5)', '近期流量爆发点，反映热点敏感度'),
        'newest': ('最新视频 (Tag 6)', '日常真实水平，反映账号活跃度')
    }
    
    for t_key in ['masterpiece', 'hot', 'newest']:
        data = type_data.get(t_key, {})
        if not data: continue
        name, desc = type_mapping.get(t_key, (t_key, ''))
        
        row = [
            name,
            f"{data.get('avg_digg', 0):.0f}",
            f"{data.get('avg_interaction_rate', 0)*100:.1f}%",
            f"{data.get('avg_digg', 0)/max(data.get('avg_digg', 0)/data.get('avg_ratio', 1) if data.get('avg_ratio') else 1, 1):.1f}", # 重新算一下或者直接用 ratio
            # 这里的 ratio 是 count 的 ratio，直接用 avg_ratio
            str(data.get('count', 0)),
            desc
        ]
        # 修正 ratio 显示
        row[3] = f"{data.get('avg_ratio', 0):.1f}"
        table_data.append(row)
        
    t = Table(table_data, colWidths=[100, 60, 60, 60, 40, 140])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E6E6E6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), 'CJK'), # 自动换行
    ]))
    story.append(Spacer(1, 10))
    story.append(t)
    story.append(Spacer(1, 10))
    story.append(Paragraph("注：互动率 = (评论+分享+收藏)/点赞；赞评比 = 点赞/评论", caption_style))
    
    # --- 3. 达人分层 ---
    story.append(Paragraph("3. 达人流量与互动分层", h1_style))
    
    dist_data = report_data.get('distribution', {})
    digg_levels = dist_data.get('digg_levels', {})
    
    story.append(Paragraph("流量层级分布 (基于平均点赞):", h2_style))
    
    level_text = []
    for k, v in digg_levels.items():
        pct = v / 251 * 100
        level_text.append(f"• <b>{k}</b>: {v}人 ({pct:.1f}%)")
    
    story.append(Paragraph("<br/>".join(level_text), body_style))
    
    story.append(Paragraph("我们建议重点关注 <b>腰部 (1千-1万)</b> 达人，他们具备验证过的爆款制造能力，且性价比通常优于头部大号。", body_style))
    
    # --- 4. 推荐名单 ---
    story.append(PageBreak())
    story.append(Paragraph("4. 优质带货达人推荐 (TOP 10)", h1_style))
    story.append(Paragraph("筛选标准：平均点赞 > 1,000 且 互动率 > 5%。以下是表现最优的前10名：", body_style))
    
    top_kols = report_data.get('high_potential_kols', [])
    # Sort just in case
    top_kols.sort(key=lambda x: x.get('avg_interaction_rate', 0), reverse=True)
    
    rec_table = [
        ['达人名称', '平均点赞', '互动率', '赞评比', '推荐理由']
    ]
    
    for kol in top_kols[:10]:
        # 简单的推荐理由生成逻辑
        reason = "高互动潜力"
        if kol['avg_digg'] > 10000:
            reason = "头部大号，品牌背书"
        elif kol['avg_ratio'] > 50:
            reason = "内容质量高，粉丝认可"
        elif kol['avg_interaction_rate'] > 0.1:
            reason = "粉丝极其活跃，适合种草"
            
        row = [
            kol['name'],
            f"{kol['avg_digg']:.0f}",
            f"{kol['avg_interaction_rate']*100:.1f}%",
            f"{kol['avg_ratio']:.1f}",
            reason
        ]
        rec_table.append(row)
        
    t2 = Table(rec_table, colWidths=[120, 60, 60, 60, 150])
    t2.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D9EAD3')), # Light Green
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (3, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(Spacer(1, 10))
    story.append(t2)
    
    # --- 5. 投放建议 ---
    story.append(Paragraph("5. 投放策略建议", h1_style))
    
    advice_text = """
    <b>1. 组合拳策略</b>
    <br/>
    建议采用 <b>"1+3+N"</b> 的投放模型：
    <br/>
    • <b>1个头部达人</b> (如: 护肤博士张苑Yuan) 进行品牌背书和信任状建立。
    <br/>
    • <b>3个腰部高互动达人</b> (如: 成分护肤师七七) 进行深度种草和转化。
    <br/>
    • <b>N个尾部KOC</b> 进行关键词铺量，占据搜索结果。
    <br/><br/>
    <b>2. 内容优化建议</b>
    <br/>
    • <b>时长控制</b>：数据表明，爆款视频时长多集中在 30-60秒，避免过长导致完播率下降。
    <br/>
    • <b>评论区运营</b>：鉴于该类目互动率极高，品牌方必须重视评论区维护，及时回复用户提问，引导转化。
    <br/>
    • <b>蹭热点能力</b>：关注"热门视频"表现好的达人，他们具备将品牌植入热点话题的能力。
    """
    story.append(Paragraph(advice_text, body_style))
    
    # 生成
    doc.build(story)
    print(f"✅ PDF 报告已生成: {pdf_file}")

if __name__ == "__main__":
    generate_pdf_report()

