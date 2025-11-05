#!/usr/bin/env python3
"""
图片侵权分析报告生成器 - 使用 Gemini 2.5 Pro 生成专业报告并输出为 PDF
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

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
        team1_analysis: Dict[str, Any],
        team2_analysis: Dict[str, Any]
    ) -> str:
        """使用 Gemini 生成报告文本
        
        Args:
            team1_analysis: Team1 的分析结果
            team2_analysis: Team2 的分析结果
            
        Returns:
            生成的报告文本
        """
        log.info("开始生成报告文本...")
        
        # 构建提示词
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(team1_analysis, team2_analysis)
        
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
        return """你是一位专业的知识产权法律顾问和视觉内容分析专家，擅长撰写图片侵权分析报告。

你的任务是：
1. 基于提供的两个案例的完整分析数据（JSON格式），撰写一份专业、详尽的侵权分析报告
2. 报告必须涵盖所有原始数据中的细节，包括所有评分、描述、证据列表、差异项、修改分析等
3. 不得概括、简化或遗漏任何原始数据中的信息
4. 保持原始分析的颗粒度和细节层次

核心要求（极其重要）：
- **保留所有证据列表**：每个维度的 evidence 列表必须完整呈现，逐条列出
- **保留所有描述**：每个分析维度的 description 必须完整引用或改写
- **保留所有差异项**：difference_analysis 中的所有列表项必须完整呈现
- **保留所有修改分析**：modification_analysis 的所有字段必须详细说明
- **保留所有重叠内容**：content_overlap 的所有共享元素必须列举
- **保留完整的侵权评估**：reasoning、key_indicators、mitigating_factors、aggravating_factors 必须完整呈现

报告结构要求：
1. 报告标题和日期
2. 执行摘要（简要概述两个案例的核心结论）
3. 案例一详细分析
   - 相似度分析（包含5个维度的评分、描述和证据）
   - 差异分析（视觉、构图、色彩、风格、技术差异）
   - 修改分析（检测到的修改、裁剪、滤镜、水印、质量变化）
   - 内容重叠（共享元素、主题、设计元素）
   - 侵权评估（风险等级、评分、推理、关键指标、减轻/加重因素）
4. 案例二详细分析（同案例一结构）
5. 综合结论和建议

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
        team1_analysis: Dict[str, Any],
        team2_analysis: Dict[str, Any]
    ) -> str:
        """构建用户提示词 - 提供完整的 JSON 数据
        
        Args:
            team1_analysis: Team1 的完整分析结果
            team2_analysis: Team2 的完整分析结果
            
        Returns:
            用户提示词（包含完整的 JSON 数据）
        """
        # 将 JSON 数据格式化为字符串
        team1_json = json.dumps(team1_analysis, ensure_ascii=False, indent=2)
        team2_json = json.dumps(team2_analysis, ensure_ascii=False, indent=2)
        
        return f"""请基于以下两个图片侵权案例的完整分析数据（JSON格式），撰写一份专业、详尽的侵权分析报告。

重要提示：
1. 以下提供的是完整的 JSON 分析数据，包含所有维度的评分、描述、证据列表、差异分析、修改分析等
2. 你必须将这些结构化数据转化为流畅、专业的报告文本
3. 不得遗漏任何数据字段或列表项
4. 保持原始数据的细节颗粒度和专业深度

==================== 案例一：影响者营销案例 ====================

文件信息：
- 原图文件名：inf-1-org.webp
- 疑似侵权图文件名：inf-1-copy.webp
- 案例类型：影响者营销场景中的图片使用

完整分析数据（JSON）：
{team1_json}

==================== 案例二：插画创作案例 ====================

文件信息：
- 原图文件名：tes-2-org.webp
- 疑似侵权图文件名：tes-2-copy.webp
- 案例类型：插画作品的商业化使用

完整分析数据（JSON）：
{team2_json}

==================== 报告撰写要求 ====================

请按照以下结构撰写报告，确保涵盖所有上述 JSON 数据中的信息：

1. 报告标题和日期

2. 执行摘要
   - 简要说明报告目的
   - 概述两个案例的核心结论和风险等级

3. 案例一详细分析（影响者营销案例）
   3.1 相似度分析
       - 总体相似度评分（overall_similarity_score）
       - 视觉相似度（visual_similarity）：评分 + 完整描述 + 所有证据项
       - 构图相似度（composition_similarity）：评分 + 完整描述 + 所有证据项
       - 色彩相似度（color_similarity）：评分 + 完整描述 + 所有证据项
       - 风格相似度（style_similarity）：评分 + 完整描述 + 所有证据项
       - 细节相似度（detail_similarity）：评分 + 完整描述 + 所有证据项
   
   3.2 差异分析
       - 视觉差异（visual_differences）：列出所有项
       - 构图差异（composition_differences）：列出所有项
       - 色彩差异（color_differences）：列出所有项
       - 风格差异（style_differences）：列出所有项
       - 技术差异（technical_differences）：列出所有项
   
   3.3 修改分析
       - 检测到的修改（detected_modifications）：列出所有项
       - 裁剪分析（cropping）：完整描述
       - 滤镜和特效（filters_effects）：完整描述
       - 水印变化（watermark_changes）：完整描述
       - 质量变化（quality_changes）：完整描述
   
   3.4 内容重叠
       - 共享元素（shared_elements）：列出所有项
       - 共享主题（shared_subjects）：列出所有项
       - 共享设计元素（shared_design_elements）：列出所有项
   
   3.5 侵权评估
       - 风险等级（risk_level）和风险评分（risk_score）
       - 推理过程（reasoning）：完整引用
       - 关键指标（key_indicators）：列出所有项
       - 减轻因素（mitigating_factors）：列出所有项
       - 加重因素（aggravating_factors）：列出所有项
   
   3.6 总结
       - 核心发现（key_findings）：列出所有项
       - 结论（conclusion）：完整引用
       - 置信度（confidence_level）

4. 案例二详细分析（插画创作案例）
   [采用与案例一完全相同的结构和详细程度]

5. 综合结论和建议
   - 对比两个案例的异同
   - 总体风险评估
   - 法律建议和后续行动建议

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
    team1_analysis: Dict[str, Any],
    team2_analysis: Dict[str, Any],
    output_path: Path,
    team1_org_img: Path,
    team1_copy_img: Path,
    team2_org_img: Path,
    team2_copy_img: Path,
):
    """创建 PDF 报告
    
    Args:
        report_text: 报告文本
        team1_analysis: Team1 分析结果
        team2_analysis: Team2 分析结果
        output_path: 输出文件路径
        team1_org_img: Team1 原图路径
        team1_copy_img: Team1 疑似侵权图路径
        team2_org_img: Team2 原图路径
        team2_copy_img: Team2 疑似侵权图路径
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
    story.append(Paragraph("图片侵权分析报告", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 日期
    date_text = f"报告日期：{datetime.now().strftime('%Y年%m月%d日')}"
    story.append(Paragraph(date_text, body_style))
    story.append(Spacer(1, 1*cm))
    
    # === 优先展示图片证据 ===
    story.append(Paragraph("证据展示", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    # 图片尺寸设置
    max_width = 15*cm
    max_height = 8*cm
    
    # 案例一图片
    story.append(Paragraph("【案例一：影响者营销案例】", heading_style))
    story.append(Spacer(1, 0.3*cm))
    
    if team1_org_img.exists():
        try:
            img1 = Image(str(team1_org_img))
            img1._restrictSize(max_width, max_height)
            story.append(Paragraph("原图 (inf-1-org.webp)", body_style))
            story.append(img1)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            log.error(f"添加图片失败 {team1_org_img}: {e}")
    
    if team1_copy_img.exists():
        try:
            img2 = Image(str(team1_copy_img))
            img2._restrictSize(max_width, max_height)
            story.append(Paragraph("疑似侵权图 (inf-1-copy.webp)", body_style))
            story.append(img2)
            story.append(Spacer(1, 1*cm))
        except Exception as e:
            log.error(f"添加图片失败 {team1_copy_img}: {e}")
    
    # 案例二图片
    story.append(Paragraph("【案例二：插画创作案例】", heading_style))
    story.append(Spacer(1, 0.3*cm))
    
    if team2_org_img.exists():
        try:
            img3 = Image(str(team2_org_img))
            img3._restrictSize(max_width, max_height)
            story.append(Paragraph("原图 (tes-2-org.webp)", body_style))
            story.append(img3)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            log.error(f"添加图片失败 {team2_org_img}: {e}")
    
    if team2_copy_img.exists():
        try:
            img4 = Image(str(team2_copy_img))
            img4._restrictSize(max_width, max_height)
            story.append(Paragraph("疑似侵权图 (tes-2-copy.webp)", body_style))
            story.append(img4)
            story.append(Spacer(1, 1*cm))
        except Exception as e:
            log.error(f"添加图片失败 {team2_copy_img}: {e}")
    
    # 添加分页，分隔图片和报告文本
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
    source_dir = script_dir / "source-pic"
    
    # 输入文件
    team1_json = output_dir / "team1_analysis.json"
    team2_json = output_dir / "team2_analysis.json"
    
    # 图片文件
    team1_org_img = source_dir / "team1" / "inf-1-org.webp"
    team1_copy_img = source_dir / "team1" / "inf-1-copy.webp"
    team2_org_img = source_dir / "team2" / "tes-2-org.webp"
    team2_copy_img = source_dir / "team2" / "tes-2-copy.webp"
    
    # 输出文件
    report_text_file = output_dir / "analysis_report.txt"
    report_pdf_file = output_dir / "analysis_report.pdf"
    
    print("\n" + "=" * 80)
    print("图片侵权分析报告生成器 - 基于 Gemini 2.5 Pro")
    print("=" * 80 + "\n")
    
    # 验证文件存在
    if not team1_json.exists():
        raise FileNotFoundError(f"分析结果不存在: {team1_json}")
    if not team2_json.exists():
        raise FileNotFoundError(f"分析结果不存在: {team2_json}")
    
    print(f"✓ 加载分析结果: team1_analysis.json")
    print(f"✓ 加载分析结果: team2_analysis.json\n")
    
    # 加载分析结果
    with open(team1_json, encoding="utf-8") as f:
        team1_analysis = json.load(f)
    with open(team2_json, encoding="utf-8") as f:
        team2_analysis = json.load(f)
    
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
            team1_analysis=team1_analysis,
            team2_analysis=team2_analysis
        )
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
            team1_analysis=team1_analysis,
            team2_analysis=team2_analysis,
            output_path=report_pdf_file,
            team1_org_img=team1_org_img,
            team1_copy_img=team1_copy_img,
            team2_org_img=team2_org_img,
            team2_copy_img=team2_copy_img,
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

