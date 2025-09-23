import logging
import os

_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
from common.request_context import get_project_id

class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.project_id = get_project_id() or "-"
        return True



def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = "%(asctime)s %(levelname)s %(name)s project_id=%(project_id)s - %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        handler.addFilter(ContextFilter())
        logger.addHandler(handler)
        logger.setLevel(_LEVEL)
        logger.propagate = False
    return logger

