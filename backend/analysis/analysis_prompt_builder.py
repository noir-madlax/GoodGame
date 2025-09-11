from __future__ import annotations
from typing import Optional
import os

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
    加载系统提示词文本。默认读取项目内：
    backend/test/output/douyin/处理建议/suggestion+video+comment-prompt.txt

    可通过 custom_path 覆盖。
    """
    path = os.path.abspath(custom_path or PROMPT_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

