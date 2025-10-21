from __future__ import annotations
from contextvars import ContextVar, Token
from typing import Optional

# Request/Job scoped context for project_id
_project_id_var: ContextVar[Optional[str]] = ContextVar("project_id", default=None)

def set_project_id(value: Optional[str]) -> Token:
    """Set project_id for current context and return the reset token."""
    return _project_id_var.set(value)

def reset_project_id(token: Token) -> None:
    """Reset project_id to previous value using the token returned by set()."""
    _project_id_var.reset(token)

def get_project_id() -> Optional[str]:
    """Get current context's project_id (None if not set)."""
    return _project_id_var.get()


# Request/Job scoped context for batch_id (用于标识一次搜索任务的批次)
_batch_id_var: ContextVar[Optional[str]] = ContextVar("batch_id", default=None)

def set_batch_id(value: Optional[str]) -> Token:
    """Set batch_id for current context and return the reset token."""
    return _batch_id_var.set(value)

def reset_batch_id(token: Token) -> None:
    """Reset batch_id to previous value using the token returned by set()."""
    _batch_id_var.reset(token)

def get_batch_id() -> Optional[str]:
    """Get current context's batch_id (None if not set)."""
    return _batch_id_var.get()

