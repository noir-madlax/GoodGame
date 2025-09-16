from __future__ import annotations
from typing import Optional
import os

from tikhub_api.orm.prompt_template_repository import PromptTemplateRepository
from tikhub_api.orm.enums import PromptName

from jobs.logger import get_logger

log = get_logger(__name__)

PROMPT_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "test",
    "output",
    "douyin",
    "处理建议",
    "suggestion+video+comment-prompt.txt",
)


def get_system_prompt(custom_path: Optional[str] = None) -> str:
    """
    获取“视频分析”系统提示词：优先从数据库 prompt_templates 表读取当前激活版本
    （name=ANALYZE_VIDEO），若未配置则回落到本地文件。

    可通过 custom_path 覆盖本地文件路径。
    """
    # 1) 优先从 DB 读取激活模板
    try:
        tpl = PromptTemplateRepository.get_active_by_name(PromptName.ANALYZE_VIDEO.value)
        if tpl and getattr(tpl, "content", None):
            return str(tpl.content)
    except Exception:
        log.error(f"从数据库读取 prompt 模板失败：{repr(e)}")
        return ""

