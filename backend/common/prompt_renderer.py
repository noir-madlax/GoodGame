from __future__ import annotations
from typing import Optional, Dict, Any, List
import re
import json

from jobs.logger import get_logger
from common.request_context import get_project_id
from tikhub_api.orm.prompt_variable_repository import PromptVariableRepository

log = get_logger(__name__)

_VAR_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


def _to_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (dict, list)):
        try:
            return json.dumps(val, ensure_ascii=False)
        except Exception:
            return str(val)
    return str(val)


def _load_project_vars(project_id: str) -> Dict[str, Any]:
    """读取指定项目的所有变量，返回 {variable_name: variable_value}。
    若查询失败，抛出异常给上层处理。
    """
    rows: List[Any] = PromptVariableRepository.list_by_project(project_id, limit=500)
    result: Dict[str, Any] = {}
    for r in rows:
        try:
            name = getattr(r, "variable_name", None)
            if not name:
                continue
            result[str(name)] = getattr(r, "variable_value", None)
        except Exception:
            # 跳过异常行
            continue
    return result


def render_prompt(template: str, project_id: Optional[str] = None) -> str:
    """将模板字符串中的 {{var}} 占位符用 prompt_variables 表里的值替换。

    - project_id 缺省时，会通过 request 上下文 get_project_id() 获取。
    - 未找到变量时保留原占位符（便于排查与容错）。
    - dict/list 值会以 JSON 字符串注入，其他类型用 str()。
    """
    if not template:
        return template or ""

    pid = project_id or get_project_id()
    if not pid:
        # 无项目上下文时直接返回原模板，避免误替换
        return template

    try:
        var_map = _load_project_vars(pid)
    except Exception:
        log.exception("读取项目变量失败：project_id=%s", pid)
        return template

    def _repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key in var_map:
            return _to_str(var_map[key])
        # 未设置的变量：保留原样
        return m.group(0)

    try:
        return _VAR_PATTERN.sub(_repl, template)
    except Exception:
        log.exception("渲染 prompt 模板失败")
        return template

