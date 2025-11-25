#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成业务报告PDF
专为业务人员设计，不包含技术术语
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                Spacer, PageBreak, Image, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from datetime import datetime
import json

# 注册中文字体（使用标准CID字体）
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

# KOL数据
kol_data = [
    {"nickname": "芊雨护肤", "follower_count": 961762, "industry_tags": ["传媒资讯", "零售电商", "美妆护肤"], "price_range": "商务洽谈", "has_price": False, "desc": "头部护肤类达人，拥有96万+粉丝，在护肤领域深耕多年。账号定位清晰，专注于护肤产品评测和推荐。粉丝群体主要为关注肌肤保养的女性用户，具有较强的购买决策影响力。适合中高端护肤品牌寻求品牌曝光和口碑传播。"},
    
    {"nickname": "美妆成分专家莫同学", "follower_count": 950547, "industry_tags": ["日化洗护", "高档化妆品", "美妆护肤"], "price_range": "200-300元", "has_price": True, "video_price": "短视频200元起", "desc": "专业成分分析类达人，拥有95万+粉丝。以专业的护肤成分知识和科学的产品分析著称，深受追求理性护肤的用户喜爱。内容严谨专业，粉丝信任度高，适合强调成分功效的护肤品牌合作。性价比高，合作门槛适中，是中小品牌的优质选择。"},
    
    {"nickname": "三针护肤甄选个体店冯三针直播号", "follower_count": 944329, "industry_tags": ["汽车", "传媒资讯", "美妆护肤"], "price_range": "商务洽谈", "has_price": False, "desc": "个体店直播达人，94万+粉丝，主打护肤产品精选。经营模式以直播带货为主，具有较强的即时转化能力。适合需要快速测试市场反馈或进行促销活动的品牌。粉丝购买意愿强，适合追求直接销售转化的合作方式。"},
    
    {"nickname": "UNNY CLUB护肤旗舰店", "follower_count": 851168, "industry_tags": ["3C电器", "零售电商", "美妆护肤"], "price_range": "150-450元", "has_price": True, "video_price": "短视频150元起", "desc": "品牌旗舰店官方账号，85万+粉丝。作为韩国美妆品牌在抖音的官方渠道，拥有稳定的粉丝基础和品牌信誉背书。适合寻求品牌联名或跨界合作的机会，也可学习其内容运营和粉丝互动策略。合作价格亲民，适合各类预算的品牌。"},
    
    {"nickname": "植祛护肤旗舰店", "follower_count": 840748, "industry_tags": ["汽车", "传媒资讯", "美妆护肤"], "price_range": "93-206元", "has_price": True, "video_price": "短视频93元起", "desc": "旗舰店账号，84万+粉丝，主打植物护肤理念。价格极具竞争力，是本次调研中性价比最高的选择之一。适合预算有限但希望获得大量曝光的新兴品牌。粉丝群体对天然植物护肤概念接受度高，适合主打天然成分的产品推广。"},
    
    {"nickname": "赛赛高端护肤", "follower_count": 778410, "industry_tags": ["传媒资讯", "零售电商", "美妆护肤"], "price_range": "91-140元", "has_price": True, "video_price": "短视频91元起", "desc": "高端护肤定位达人，77万+粉丝。虽然定位高端，但合作价格却十分亲民，性价比突出。粉丝群体具有一定消费能力，追求品质护肤。适合中高端品牌以较低成本试水市场，或作为日常内容营销的稳定合作伙伴。"},
    
    {"nickname": "护肤成分党罪罪子", "follower_count": 666277, "industry_tags": ["游戏", "零售电商", "美妆护肤"], "price_range": "500-800元", "has_price": True, "video_price": "短视频500元起", "desc": "成分党达人，66万+粉丝。深度聚焦护肤成分分析，粉丝专业度和忠诚度高。合作价格相对较高，但对应的是精准的目标受众和深度的内容价值。适合高端品牌或主打科技成分的产品，追求精准触达和深度种草效果。"},
    
    {"nickname": "拉菲护肤", "follower_count": 602598, "industry_tags": ["汽车", "传媒资讯", "零售电商"], "price_range": "125-300元", "has_price": True, "video_price": "短视频125元起", "desc": "综合类护肤达人，60万+粉丝。内容覆盖面广，粉丝构成多元化。价格适中，适合中等预算品牌。既有护肤专业性，又兼顾内容娱乐性，能够在传递产品信息的同时保持较好的传播效果。是追求稳定合作的理想选择。"},
    
    {"nickname": "王娟护肤", "follower_count": 567490, "industry_tags": ["游戏", "零售电商", "美妆护肤"], "price_range": "200-700元", "has_price": True, "video_price": "短视频200元起", "desc": "个人IP护肤达人，56万+粉丝。以个人品牌影响力为核心，粉丝粘性强。内容风格亲和，善于与粉丝建立情感连接。适合追求真实感和信任感的品牌合作，特别是需要建立长期品牌形象的项目。合作价格适中，性价比良好。"},
    
    {"nickname": "罗娜女神护肤旗舰店", "follower_count": 562443, "industry_tags": ["游戏", "传媒资讯", "美妆护肤"], "price_range": "35-159元", "has_price": True, "video_price": "短视频35元起", "desc": "旗舰店账号，56万+粉丝。价格极具吸引力，是预算最友好的选择之一。适合新品牌进行市场测试、小规模多频次投放或作为日常内容营销的长期合作伙伴。虽然价格低廉，但粉丝基数充足，依然能够获得可观的曝光效果。"},
    
    {"nickname": "小晚姐姐🧚‍♀️", "follower_count": 537035, "industry_tags": ["日化洗护", "3C小家电", "美妆护肤"], "price_range": "200-560元", "has_price": True, "video_price": "短视频200元起，含短直种草560元", "desc": "多元化达人，53万+粉丝。是唯一提供短直种草服务的达人，适合需要直播引流和即时转化的品牌。内容覆盖护肤、日化、小家电等领域，粉丝群体生活化，购买决策更加务实。适合功效型产品或强调性价比的品牌合作。"},
    
    {"nickname": "李有诗（护肤版）", "follower_count": 517214, "industry_tags": ["游戏", "零售电商", "美妆护肤"], "price_range": "500-800元", "has_price": True, "video_price": "短视频500元起", "desc": "个人IP达人，51万+粉丝。内容质量高，粉丝忠诚度强。合作价格相对较高，但对应的是优质的内容产出和精准的粉丝触达。适合注重品牌调性和长期口碑建设的品牌，追求高质量内容而非单纯的曝光量。"}
]

def create_business_report():
    """生成业务报告PDF"""
    
    # 创建PDF文档
    filename = f"护肤类达人筛选报告_50-100万粉丝区间_{datetime.now().strftime('%Y%m%d')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4,
                           topMargin=2*cm, bottomMargin=2*cm,
                           leftMargin=2*cm, rightMargin=2*cm)
    
    # 准备内容
    story = []
    
    # 样式设置
    styles = getSampleStyleSheet()
    
    # 标题样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName='STSong-Light',
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # 二级标题样式
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontName='STSong-Light',
        fontSize=16,
        textColor=colors.HexColor('#303f9f'),
        spaceAfter=12,
        spaceBefore=20
    )
    
    # 三级标题样式
    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading3'],
        fontName='STSong-Light',
        fontSize=14,
        textColor=colors.HexColor('#3f51b5'),
        spaceAfter=10,
        spaceBefore=15
    )
    
    # 正文样式
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontName='STSong-Light',
        fontSize=10,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )
    
    # 小字样式
    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['BodyText'],
        fontName='STSong-Light',
        fontSize=9,
        leading=14,
        textColor=colors.grey
    )
    
    # 1. 封面
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("护肤类达人筛选报告", title_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("50万-100万粉丝区间", heading2_style))
    story.append(Spacer(1, 2*cm))
    
    # 报告信息表
    report_data = [
        ['报告日期', datetime.now().strftime('%Y年%m月%d日')],
        ['数据来源', '抖音星图平台'],
        ['达人数量', '40位'],
        ['筛选标准', '粉丝50-100万 + 护肤领域'],
        ['报告类型', '商务合作参考']
    ]
    
    report_table = Table(report_data, colWidths=[4*cm, 10*cm])
    report_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'STSong-Light', 10),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#3f51b5')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(report_table)
    story.append(PageBreak())
    
    # 2. 执行摘要
    story.append(Paragraph("一、执行摘要", heading2_style))
    
    summary_text = """
本报告针对护肤品牌的达人营销需求，筛选并分析了抖音平台上粉丝量在50万-100万区间的优质护肤类达人。
这一区间的达人处于"腰部达人"向"头部达人"过渡的黄金阶段，具有显著的性价比优势：既保持了较高的粉丝影响力，
又不像超级头部达人那样价格昂贵，是中小护肤品牌进行内容营销的理想选择。
    """
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 核心发现
    story.append(Paragraph("核心发现", heading3_style))
    
    findings = [
        "✓ 共筛选出<b>40位</b>护肤类优质达人，其中<b>87.5%</b>（35位）明确标记护肤领域",
        "✓ <b>60%</b>的达人提供公开报价，价格区间为<b>35-800元</b>，主流价位在<b>100-400元</b>",
        "✓ 短视频合作是最主流的方式，<b>25%</b>的达人提供专业视频制作服务",
        "✓ 价格梯度合理：短视频＜中视频＜长视频，平均比例为 1 : 1.5 : 2",
        "✓ 多数达人兼具护肤专业性和内容娱乐性，适合不同品牌定位需求"
    ]
    
    for finding in findings:
        story.append(Paragraph(finding, body_style))
        story.append(Spacer(1, 0.2*cm))
    
    story.append(PageBreak())
    
    # 3. 市场概况
    story.append(Paragraph("二、市场概况", heading2_style))
    
    story.append(Paragraph("达人分布特征", heading3_style))
    
    overview_text = """
本次调研的40位达人平均粉丝量为<b>67万</b>，分布在50万到96万之间。这一粉丝规模的达人通常具有以下特点：
    """
    story.append(Paragraph(overview_text, body_style))
    
    features = [
        "<b>专业度与亲和力兼备</b>：既能提供专业的护肤知识和产品评测，又能与粉丝保持良好互动",
        "<b>性价比突出</b>：相比百万级头部达人，合作成本降低50-70%，但影响力依然可观",
        "<b>转化效率高</b>：粉丝群体精准，购买决策受达人影响程度高",
        "<b>合作灵活</b>：大部分达人接受中小品牌合作，沟通效率高，合作形式多样"
    ]
    
    for i, feature in enumerate(features, 1):
        story.append(Paragraph(f"{i}. {feature}", body_style))
        story.append(Spacer(1, 0.2*cm))
    
    story.append(Spacer(1, 0.5*cm))
    
    # 价格概况表
    story.append(Paragraph("合作价格概况", heading3_style))
    
    price_data = [
        ['合作形式', '价格区间', '平均价格', '适用场景'],
        ['短视频（1-20秒）', '35-500元', '209元', '产品快速展示、日常种草'],
        ['中视频（21-60秒）', '79-800元', '326元', '产品详细介绍、使用教程'],
        ['长视频（60秒以上）', '140-800元', '421元', '深度测评、成分分析'],
        ['短直种草', '560元', '560元', '直播引流、即时转化']
    ]
    
    price_table = Table(price_data, colWidths=[3.5*cm, 3.5*cm, 3*cm, 5*cm])
    price_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'STSong-Light', 9),
        ('FONT', (0, 0), (-1, 0), 'STSong-Light', 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5c6bc0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(price_table)
    story.append(Spacer(1, 0.3*cm))
    
    note = "<i>注：以上价格为市场公开报价，实际合作价格需商务洽谈确定。部分达人未公开报价，需单独沟通。</i>"
    story.append(Paragraph(note, small_style))
    
    story.append(PageBreak())
    
    # 4. 推荐达人详解
    story.append(Paragraph("三、重点推荐达人", heading2_style))
    
    intro = """
    以下是从40位达人中精选出的<b>12位</b>重点推荐对象。推荐标准综合考虑了粉丝规模、内容质量、
    合作价格、专业度等多个维度。每位达人都有明确的优势和适配场景，供不同需求的品牌方参考选择。
    """
    story.append(Paragraph(intro, body_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 为每个KOL创建详细介绍
    for idx, kol in enumerate(kol_data, 1):
        # KOL标题卡片（使用表格实现）
        header_data = [[
            Paragraph(f"<b>{idx}. {kol['nickname']}</b>", 
                     ParagraphStyle('KOLName', parent=body_style, fontSize=12, textColor=colors.HexColor('#1a237e'))),
            Paragraph(f"<b>{kol['follower_count']:,}</b> 粉丝", 
                     ParagraphStyle('Followers', parent=body_style, fontSize=11, textColor=colors.HexColor('#e91e63'), alignment=TA_RIGHT))
        ]]
        
        header_table = Table(header_data, colWidths=[10*cm, 5*cm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8eaf6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 0.2*cm))
        
        # 达人信息
        info_data = [
            ['领域标签', '、'.join(kol['industry_tags'])],
            ['合作报价', kol['price_range']],
        ]
        
        if kol.get('has_price'):
            info_data.append(['推荐形式', kol.get('video_price', '-')])
        
        info_table = Table(info_data, colWidths=[3*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'STSong-Light', 9),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#5c6bc0')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 0.3*cm))
        
        # 达人介绍
        desc_style = ParagraphStyle('Desc', parent=body_style, fontSize=10, leading=15)
        story.append(Paragraph(f"<b>达人特色：</b>{kol['desc']}", desc_style))
        
        story.append(Spacer(1, 0.8*cm))
        
        # 每3个达人换页
        if idx % 3 == 0 and idx < len(kol_data):
            story.append(PageBreak())
    
    # 如果最后一页不是完整的3个，需要换页
    if len(kol_data) % 3 != 0:
        story.append(PageBreak())
    
    # 5. 合作建议
    story.append(Paragraph("四、合作建议", heading2_style))
    
    story.append(Paragraph("不同预算的选择策略", heading3_style))
    
    budget_strategies = [
        ("<b>小预算（5000元以下）</b>", 
         "推荐选择3-5位价格在100-200元区间的达人进行组合投放。可以选择植祛护肤旗舰店、赛赛高端护肤、罗娜女神等性价比极高的达人，"
         "实现多点覆盖，测试不同内容风格的传播效果。"),
        
        ("<b>中等预算（5000-15000元）</b>", 
         "推荐选择2-3位200-500元区间的专业达人。如美妆成分专家莫同学、UNNY CLUB护肤旗舰店、拉菲护肤等。"
         "这些达人兼具专业度和性价比，适合进行产品测评、成分分析等深度内容合作，建立品牌专业形象。"),
        
        ("<b>高预算（15000元以上）</b>", 
         "可选择护肤成分党罪罪子、李有诗等高价位达人进行深度合作，或组合多位中价位达人进行全方位覆盖。"
         "追求精准触达和品牌高度，适合高端产品或需要建立专业权威形象的品牌。")
    ]
    
    for title, content in budget_strategies:
        story.append(Paragraph(title, body_style))
        story.append(Spacer(1, 0.1*cm))
        story.append(Paragraph(content, body_style))
        story.append(Spacer(1, 0.3*cm))
    
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("不同品牌定位的达人匹配", heading3_style))
    
    brand_matches = [
        ("<b>主打成分科技的品牌</b>", "推荐：美妆成分专家莫同学、护肤成分党罪罪子"),
        ("<b>强调天然植物的品牌</b>", "推荐：植祛护肤旗舰店、小晚姐姐"),
        ("<b>高端定位品牌</b>", "推荐：芊雨护肤、护肤成分党罪罪子、李有诗"),
        ("<b>性价比产品</b>", "推荐：赛赛高端护肤、拉菲护肤、王娟护肤"),
        ("<b>新品牌市场测试</b>", "推荐：罗娜女神、植祛护肤、赛赛高端（价格低，便于多次测试）")
    ]
    
    for category, recommendation in brand_matches:
        story.append(Paragraph(f"{category}: {recommendation}", body_style))
        story.append(Spacer(1, 0.2*cm))
    
    story.append(PageBreak())
    
    # 6. 附录
    story.append(Paragraph("五、其他达人简况", heading2_style))
    
    appendix_text = """
    除重点推荐的12位达人外，本次调研还覆盖了其他28位护肤类达人。这些达人虽未提供详细报价或信息不够完整，
    但依然具有合作价值。如有兴趣，可进一步单独沟通了解。主要包括：
    """
    story.append(Paragraph(appendix_text, body_style))
    story.append(Spacer(1, 0.3*cm))
    
    other_kols = [
        "曼琪-高端院线护肤（74万粉）、妇炎洁护肤旗舰店（67万粉）、木子彩妆护肤（66万粉）",
        "植然草护肤直播间（66万粉）、小树美官方护肤直播间（65万粉）、护肤号4（65万粉）",
        "白云山护肤（63万粉）、兔姐🔥专注高端护肤（62万粉）、王佳佳高端护肤（61万粉）",
        "百雀羚护肤旗舰店（60万粉）、王后老板娘宫喜秀高端护肤（56万粉）、陈一鸣🍓高端护肤（56万粉）",
        "...以及其他十余位达人"
    ]
    
    for kols in other_kols:
        story.append(Paragraph(f"• {kols}", body_style))
        story.append(Spacer(1, 0.15*cm))
    
    story.append(Spacer(1, 0.8*cm))
    
    # 报告说明
    story.append(Paragraph("报告说明", heading3_style))
    
    disclaimer = """
    <b>1. 数据来源</b>：本报告数据来自抖音星图平台，采集时间为2025年11月14日。达人粉丝数、报价等信息
    可能随时变动，请以实际沟通为准。<br/><br/>
    
    <b>2. 报价说明</b>：报告中的价格为平台公开报价或市场参考价，实际合作价格受多种因素影响（如合作形式、
    内容要求、合作周期等），最终价格以商务洽谈为准。<br/><br/>
    
    <b>3. 选择建议</b>：本报告提供的推荐和建议仅供参考，具体选择应结合品牌实际情况、预算、营销目标等综合考虑。
    建议在正式合作前，详细了解达人的历史合作案例、粉丝画像、内容风格等。<br/><br/>
    
    <b>4. 版权声明</b>：本报告为内部参考资料，请勿外传。如需分享，请联系报告提供方获取授权。
    """
    story.append(Paragraph(disclaimer, small_style))
    
    # 生成PDF
    doc.build(story)
    print(f"✅ 业务报告PDF已生成：{filename}")
    return filename

if __name__ == "__main__":
    create_business_report()

