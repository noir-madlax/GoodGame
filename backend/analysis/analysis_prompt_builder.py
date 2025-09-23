from __future__ import annotations
from typing import Optional
import os

from tikhub_api.orm.prompt_template_repository import PromptTemplateRepository
from tikhub_api.orm.enums import PromptName

from common.prompt_renderer import render_prompt

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


def get_system_prompt(name: PromptName = PromptName.ANALYZE_VIDEO, custom_path: Optional[str] = None) -> str:
    """
    根据 PromptName 返回系统提示词：
    - 优先从数据库 prompt_templates 表读取激活版本（name = name.value）
    - 若未配置则回落到本地文件（若提供 custom_path 则优先使用 custom_path）
    """
    # 1) 优先从 DB 读取激活模板
    try:
        tpl = PromptTemplateRepository.get_active_by_name(name.value)
        if tpl and getattr(tpl, "content", None):
            return render_prompt(str(tpl.content))
    except Exception:
        log.exception("从数据库读取 prompt 模板失败")

    # 2) 回落到本地文件
    path = custom_path or PROMPT_FILE
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return render_prompt(f.read())
    except Exception:
        log.exception("读取本地 prompt 文件失败")
    return ""

