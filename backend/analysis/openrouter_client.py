from __future__ import annotations
from typing import Dict, Any, Optional
import os
import json
import time
import requests
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore
    find_dotenv = None  # type: ignore

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# 优先全局查找 .env（兼容项目其他模块的方式）
if 'OPENROUTER_API_KEY' not in os.environ and load_dotenv and find_dotenv:
    try:
        load_dotenv(find_dotenv())  # 向上查找最近的 .env
    except Exception:
        pass
# 补充尝试 backend/.env（相对 analysis 目录）
if 'OPENROUTER_API_KEY' not in os.environ and load_dotenv:
    try:
        _here = os.path.abspath(os.path.dirname(__file__))
        _backend_env = os.path.abspath(os.path.join(_here, '..', '.env'))
        if os.path.exists(_backend_env):
            load_dotenv(_backend_env, override=False)
    except Exception:
        pass

DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gemini-2.5-pro")
API_KEY = os.getenv("OPENROUTER_API_KEY", "")

class OpenRouterClient:
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 30) -> None:
        self.model = model or DEFAULT_MODEL
        self.api_key = api_key or API_KEY
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required")

    def classify_value(self, system_prompt: str, user_text: str, max_tokens: int = 200, temperature: float = 0.2) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_status = 0
        for i in range(3):
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=self.timeout)
            last_status = resp.status_code
            if resp.status_code == 200:
                data = resp.json()
                content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
                try:
                    return json.loads(content)
                except Exception:
                    return {
                        "has_value": False,
                        "reason": "非JSON响应",
                        "signals": [],
                        "confidence": 0.0,
                        "suggested_status": "no_value",
                    }
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (i + 1))
                continue
            break
        return {
            "has_value": False,
            "reason": f"HTTP {last_status}",
            "signals": [],
            "confidence": 0.0,
            "suggested_status": "no_value",
        }

