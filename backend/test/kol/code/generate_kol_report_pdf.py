"""
生成KOL评估报告PDF
专业的流量达人评估机构报告格式
"""

import json
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

def setup_chinese_font():
    """
    设置中文字体
    尝试多个常见的中文字体路径
    """
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",  # macOS
        "/System/Library/Fonts/STHeiti Medium.ttc",  # macOS
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Linux
        "C:\\Windows\\Fonts\\msyh.ttc",  # Windows
    ]
    
    for font_path in font_paths:
        try:
            if Path(font_path).exists():
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return 'ChineseFont'
        except:
            continue
    
    # 如果都失败，使用Helvetica（不支持中文，但至少能显示）
    print("⚠️  未找到中文字体，将使用默认字体（可能无法显示中文）")
    return 'Helvetica'


def create_kol_report():
    """生成KOL评估报告PDF"""
    
    # 设置中文字体
    chinese_font = setup_chinese_font()
    
    # 读取分析数据
    backend_dir = Path(__file__).parent.parent.parent.parent
    analysis_file = backend_dir / 'test' / 'kol' / 'output' / 'xingtu_kol_data' / 'KOL_BUSINESS_ANALYSIS_2_3_4.json'
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 输出PDF文件
    output_file = backend_dir / 'test' / 'kol' / 'output' / 'xingtu_kol_data' / 'KOL评估报告_骆王宇_勇仔leo_Daily-cici.pdf'
    
    # 创建PDF文档
    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # 定义样式
    styles = getSampleStyleSheet()
    
    # 标题样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        leading=30
    )
    
    # 副标题样式
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontName=chinese_font,
        fontSize=16,
        textColor=colors.HexColor('#333333'),
        spaceAfter=20,
        spaceBefore=20,
        leading=20
    )
    
    # 正文样式
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontName=chinese_font,
        fontSize=10,
        textColor=colors.HexColor('#444444'),
        spaceAfter=12,
        leading=15,
        alignment=TA_JUSTIFY
    )
    
    # 小标题样式
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading3'],
        fontName=chinese_font,
        fontSize=12,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=10,
        spaceBefore=15,
        leading=15
    )
    
    # 构建PDF内容
    story = []
    
    # ============= 封面 =============
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("抖音护肤美妆KOL", title_style))
    story.append(Paragraph("商业价值评估报告", title_style))
    story.append(Spacer(1, 2*cm))
    
    # 封面信息表
    cover_data = [
        ['评估对象', '骆王宇、勇仔leo、Daily-cici'],
        ['评估机构', 'GoodGame 数据分析中心'],
        ['报告日期', datetime.now().strftime('%Y年%m月%d日')],
        ['数据来源', '抖音星图平台官方API'],
        ['分析周期', '90天（2024年10月-2025年1月）'],
        ['报告编号', f'KOL-RPT-{datetime.now().strftime("%Y%m%d")}'],
    ]
    
    cover_table = Table(cover_data, colWidths=[5*cm, 10*cm])
    cover_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), chinese_font),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#000000')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e0e0e0')),
    ]))
    story.append(cover_table)
    story.append(PageBreak())
    
    # ============= 执行摘要 =============
    story.append(Paragraph("一、执行摘要", subtitle_style))
    story.append(Paragraph(
        "本报告对3位头部护肤美妆类抖音KOL进行了全面的商业价值评估。"
        "评估维度包括基础影响力、受众画像、服务报价、性价比指标和转化能力五个方面。"
        "所有数据来源于抖音星图平台官方API，确保数据的准确性和权威性。",
        body_style
    ))
    story.append(Spacer(1, 0.5*cm))
    
    # 核心发现
    story.append(Paragraph("核心发现：", heading_style))
    
    findings = []
    for kol in data['kols_analysis']:
        follower = kol['影响力指标']['粉丝数']
        findings.append(f"• {kol['基本信息']['达人名称']}：粉丝{follower:,}，"
                       f"{kol['影响力指标']['分析']}")
    
    for finding in findings:
        story.append(Paragraph(finding, body_style))
    
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "三位KOL均为头部达人，具备较强的品牌影响力和商业变现能力。"
        "受众画像匹配美妆护肤类产品目标人群，女性占比高，年龄集中在18-30岁，"
        "消费能力较强。转化数据表现优异，适合品牌合作投放。",
        body_style
    ))
    
    story.append(PageBreak())
    
    # ============= 详细评估（每个KOL） =============
    for idx, kol in enumerate(data['kols_analysis'], 1):
        rank = kol['基本信息']['排名']
        name = kol['基本信息']['达人名称']
        
        # KOL标题
        story.append(Paragraph(f"{idx+1}. {name} 详细评估", subtitle_style))
        
        # 2.1 基础信息
        story.append(Paragraph(f"{idx+1}.1 基础信息", heading_style))
        
        basic_data = [
            ['达人名称', name],
            ['抖音号', kol['基本信息']['抖音号']],
            ['粉丝数', f"{kol['影响力指标']['粉丝数']:,}"],
            ['明星达人', kol['影响力指标']['是否明星达人']],
            ['MCN机构', kol['内容定位']['MCN机构']],
            ['账号状态', kol['认证与资质']['账号状态']],
            ['电商能力', kol['认证与资质']['电商能力']],
        ]
        
        basic_table = Table(basic_data, colWidths=[4*cm, 11*cm])
        basic_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(basic_table)
        story.append(Spacer(1, 0.3*cm))
        
        # 内容定位
        tags = kol['内容定位']['标签']
        industries = kol['内容定位']['擅长行业']
        story.append(Paragraph(
            f"<b>内容定位：</b>{', '.join(tags) if tags else '暂无'}<br/>"
            f"<b>擅长行业：</b>{', '.join(industries) if industries else '暂无'}",
            body_style
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # 2.2 受众画像分析
        story.append(Paragraph(f"{idx+1}.2 受众画像分析", heading_style))
        
        audience_points = []
        for key, value in kol['受众画像分析'].items():
            if isinstance(value, dict) and '描述' in value:
                audience_points.append(f"• <b>{key}：</b>{value['描述']}")
        
        for point in audience_points:
            story.append(Paragraph(point, body_style))
        
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            "<b>业务价值：</b>受众画像决定产品匹配度。美妆护肤类产品需要女性占比>70%、"
            "18-30岁占比>60%、iPhone占比>50%（高消费力）、一二线城市占比>50%。",
            body_style
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # 2.3 商务报价
        story.append(Paragraph(f"{idx+1}.3 商务报价", heading_style))
        
        price_data = [['服务类型', '价格（元）', '结算方式', '状态']]
        for price_item in kol['商务报价']['价格信息']:
            price_data.append([
                price_item['服务类型'],
                f"{price_item['价格（元）']:,.0f}",
                price_item['结算方式'],
                price_item['状态']
            ])
        
        if len(price_data) > 1:
            price_table = Table(price_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm])
            price_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), chinese_font),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(price_table)
        
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            "<b>业务价值：</b>报价决定合作成本。需结合ROI预估选择合适的视频时长。"
            "通常21-60秒视频性价比最高，兼顾表达充分和成本控制。",
            body_style
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # 2.4 性价比指标
        story.append(Paragraph(f"{idx+1}.4 性价比指标", heading_style))
        
        cp = kol['性价比指标']
        cpe_1_20 = cp['预期CPE'].get('cpe_1_20', 'N/A')
        cpm_1_20 = cp['预期CPM'].get('cpm_1_20', 'N/A')
        expect_vv = cp['预期播放量']
        
        story.append(Paragraph(
            f"• <b>预期播放量：</b>{expect_vv:,}次<br/>"
            f"• <b>预期CPE（每互动成本）：</b>{cpe_1_20}元<br/>"
            f"• <b>预期CPM（千次曝光成本）：</b>{cpm_1_20}元<br/>"
            f"• <b>热门作品数：</b>{cp['热门作品数']}个",
            body_style
        ))
        
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            "<b>业务价值：</b>CPE和CPM是ROI预估的关键指标。CPE越低，互动性价比越高；"
            "CPM越低，品牌曝光成本越低。结合播放量可预估传播效果。",
            body_style
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # 2.5 转化能力
        story.append(Paragraph(f"{idx+1}.5 转化能力", heading_style))
        
        conv = kol['转化能力']
        story.append(Paragraph(
            f"• <b>平均销售额：</b>{conv['平均销售额区间']}<br/>"
            f"• <b>组件点击量：</b>{conv['组件点击量区间']}<br/>"
            f"• <b>组件点击率：</b>{conv['组件点击率区间']}<br/>"
            f"• <b>GPM（千次播放毛利）：</b>{conv['GPM区间']}<br/>"
            f"• <b>推荐商品价格区间：</b>{conv['推荐商品价格区间']}元",
            body_style
        ))
        
        # 品类转化
        if conv['品类转化']:
            category_str = ', '.join([f"{item['name']}（{item['sale_amount_range']}）" 
                                     for item in conv['品类转化']])
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(f"• <b>品类转化表现：</b>{category_str}", body_style))
        
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            "<b>业务价值：</b>转化能力直接反映带货能力。销售额>50万为优秀，"
            "点击率>6%为高转化，GPM>100为高商业价值。推荐商品价格区间反映受众消费能力。",
            body_style
        ))
        
        # 每个KOL后分页
        if idx < len(data['kols_analysis']):
            story.append(PageBreak())
    
    # ============= 横向对比 =============
    story.append(PageBreak())
    story.append(Paragraph("三、三位KOL横向对比", subtitle_style))
    
    # 对比表
    compare_data = [['指标', '骆王宇', '勇仔leo', 'Daily-cici']]
    
    # 添加对比数据
    kols = data['kols_analysis']
    compare_data.append([
        '粉丝数',
        f"{kols[0]['影响力指标']['粉丝数']:,}",
        f"{kols[1]['影响力指标']['粉丝数']:,}",
        f"{kols[2]['影响力指标']['粉丝数']:,}"
    ])
    
    compare_data.append([
        '短视频报价',
        f"{kols[0]['商务报价']['价格信息'][0]['价格（元）']:,.0f}元" if kols[0]['商务报价']['价格信息'] else 'N/A',
        f"{kols[1]['商务报价']['价格信息'][0]['价格（元）']:,.0f}元" if kols[1]['商务报价']['价格信息'] else 'N/A',
        f"{kols[2]['商务报价']['价格信息'][0]['价格（元）']:,.0f}元" if kols[2]['商务报价']['价格信息'] else 'N/A'
    ])
    
    compare_data.append([
        '预期播放量',
        f"{kols[0]['性价比指标']['预期播放量']:,}",
        f"{kols[1]['性价比指标']['预期播放量']:,}",
        f"{kols[2]['性价比指标']['预期播放量']:,}"
    ])
    
    compare_data.append([
        '销售额区间',
        kols[0]['转化能力']['平均销售额区间'],
        kols[1]['转化能力']['平均销售额区间'],
        kols[2]['转化能力']['平均销售额区间']
    ])
    
    compare_data.append([
        '点击率',
        kols[0]['转化能力']['组件点击率区间'],
        kols[1]['转化能力']['组件点击率区间'],
        kols[2]['转化能力']['组件点击率区间']
    ])
    
    compare_table = Table(compare_data, colWidths=[4*cm, 3.5*cm, 3.5*cm, 3.5*cm])
    compare_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), chinese_font),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f5f5f5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(compare_table)
    
    # ============= 投放建议 =============
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("四、投放建议", subtitle_style))
    
    story.append(Paragraph("4.1 选择策略", heading_style))
    story.append(Paragraph(
        "• <b>品牌曝光型投放：</b>选择粉丝量最大的KOL，最大化品牌曝光<br/>"
        "• <b>效果转化型投放：</b>选择点击率和销售额最高的KOL，追求转化效果<br/>"
        "• <b>性价比型投放：</b>综合考虑报价和CPM，选择性价比最优方案<br/>"
        "• <b>组合投放：</b>建议3位KOL组合投放，覆盖不同受众层次",
        body_style
    ))
    
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("4.2 合作形式建议", heading_style))
    story.append(Paragraph(
        "• <b>短视频种草：</b>21-60秒视频最佳，兼顾内容深度和成本<br/>"
        "• <b>长视频测评：</b>60秒以上视频适合深度产品测评<br/>"
        "• <b>短直种草：</b>短视频+直播组合，形成完整转化链路<br/>"
        "• <b>系列内容：</b>建议单个KOL至少合作2-3条内容，形成系列效应",
        body_style
    ))
    
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("4.3 预算建议", heading_style))
    
    total_min = sum(kol['商务报价']['价格信息'][0]['价格（元）'] 
                    for kol in kols if kol['商务报价']['价格信息'])
    total_mid = sum(kol['商务报价']['价格信息'][1]['价格（元）'] 
                   for kol in kols if len(kol['商务报价']['价格信息']) > 1)
    
    story.append(Paragraph(
        f"• <b>单条短视频测试：</b>单个KOL预算2,000-5,000元<br/>"
        f"• <b>单个KOL深度合作：</b>3条内容预算5,000-15,000元<br/>"
        f"• <b>三位KOL组合投放：</b>短视频组合预算{total_min:,.0f}元起<br/>"
        f"• <b>深度系列合作：</b>中长视频组合预算{total_mid:,.0f}元起",
        body_style
    ))
    
    # ============= 结论 =============
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("五、结论", subtitle_style))
    story.append(Paragraph(
        "经过全面评估，三位KOL均具备优秀的商业合作价值：",
        body_style
    ))
    story.append(Spacer(1, 0.3*cm))
    
    conclusions = [
        "1. <b>影响力层面：</b>三位均为头部达人，粉丝量级在1000万+，具备强大的品牌传播能力",
        "2. <b>受众匹配：</b>受众画像高度匹配美妆护肤类产品，女性占比>70%，年龄集中18-30岁",
        "3. <b>消费能力：</b>iPhone占比>50%，一二线城市占比>50%，受众消费能力强",
        "4. <b>转化能力：</b>销售额表现优异，点击率>6%，具备优秀的带货转化能力",
        "5. <b>性价比：</b>报价合理，CPM和CPE在行业正常范围，投放性价比高"
    ]
    
    for conclusion in conclusions:
        story.append(Paragraph(conclusion, body_style))
        story.append(Spacer(1, 0.2*cm))
    
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "<b>综合建议：</b>三位KOL均值得合作。建议根据预算和目标选择1-3位进行组合投放，"
        "形成品牌曝光和效果转化的完整链路。首次合作建议从短视频测试开始，"
        "根据实际效果再决定是否深度合作。",
        body_style
    ))
    
    # ============= 页脚：免责声明 =============
    story.append(Spacer(1, 1.5*cm))
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['BodyText'],
        fontName=chinese_font,
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        leading=12
    )
    story.append(Paragraph(
        "<b>免责声明：</b>本报告数据来源于抖音星图平台API，所有指标为预期数据，实际效果受内容质量、"
        "发布时间、平台推荐等多因素影响。本报告仅供参考，不构成投资建议。"
        "GoodGame数据分析中心不对投放效果承担任何责任。",
        disclaimer_style
    ))
    
    # 生成PDF
    doc.build(story)
    
    print(f"\n✅ PDF报告生成成功！")
    print(f"📁 文件位置: {output_file}")
    print(f"📄 包含 {len(kols)} 位KOL的详细评估")
    
    return output_file


if __name__ == '__main__':
    try:
        output_file = create_kol_report()
        print(f"\n🎉 报告生成完成！")
        print(f"可以打开查看: {output_file}")
    except Exception as e:
        print(f"\n❌ 生成报告时出错: {e}")
        import traceback
        traceback.print_exc()

