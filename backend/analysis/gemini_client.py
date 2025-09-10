from __future__ import annotations
from typing import Dict, Any, Optional
import os
import json
import time

from jobs.logger import get_logger

log = get_logger(__name__)

try:
    # 新版 Google Generative AI 官方 SDK（https://pypi.org/project/google-genai/）
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except Exception as e:  # pragma: no cover
    genai = None  # type: ignore
    types = None  # type: ignore

try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore
    find_dotenv = None  # type: ignore

# 优先全局查找 .env（兼容项目其他模块的方式）
if 'GEMINI_API_KEY' not in os.environ and load_dotenv and find_dotenv:
    try:
        load_dotenv(find_dotenv())  # 向上查找最近的 .env
    except Exception:
        pass
# 补充尝试 backend/.env（相对 analysis 目录）
if 'GEMINI_API_KEY' not in os.environ and load_dotenv:
    try:
        _here = os.path.abspath(os.path.dirname(__file__))
        _backend_env = os.path.abspath(os.path.join(_here, '..', '.env'))
        if os.path.exists(_backend_env):
            load_dotenv(_backend_env, override=False)
    except Exception:
        pass

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
API_KEY = os.getenv("GEMINI_API_KEY", "")


def _normalize_model_name(model: str | None) -> str:
    """兼容传入类似 "google/gemini-2.5-pro" 的名字，转为 SDK 需要的 "gemini-2.5-pro"。
    若未提供按默认值处理。
    """
    name = (model or DEFAULT_MODEL).strip()
    # 常见前缀：openrouter 默认可能传 "google/gemini-2.5-pro"
    if "/" in name:
        name = name.split("/")[-1]
    return name


class GeminiClient:
    """
    与 OpenRouterClient 对齐的最小封装：
    - classify_value(system_prompt, user_text, max_tokens=200, temperature=0.2) -> Dict[str, Any]
    - 使用 google genai 的 generate_content，要求返回 JSON
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 30) -> None:
        if genai is None or types is None:  # pragma: no cover
            raise RuntimeError(
                "google-genai SDK 未安装。请先在 backend 虚拟环境中执行: pip install google-genai"
            )
        self.model = _normalize_model_name(model)
        self.api_key = (api_key or API_KEY).strip()
        self.timeout = timeout  # 目前 SDK 暂无直接超时参数，保留占位
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required")
        self.client = genai.Client(api_key=self.api_key)

    def classify_value(
        self,
        system_prompt: str,
        user_text: str,
        max_tokens: int = 3000,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        # 兼容 OpenRouterClient：尽量让模型仅输出 JSON 对象
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max(32, int(max_tokens)),
            response_mime_type="application/json",
            system_instruction=system_prompt,
        )

        # 最简 inputs：只传用户文本，由 system_instruction 提供角色与格式约束
        contents = [user_text]

        last_err: Optional[str] = None
        for i in range(3):
            try:
                resp = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                log.info({"response": resp})
                text = getattr(resp, "text", None) or getattr(resp, "output_text", None) or ""
                # 有些情况下响应是空，尝试从 candidates 聚合
                if not text:
                    try:
                        # SDK 兼容：取第一个候选的纯文本
                        cand = (getattr(resp, "candidates", None) or [None])[0]
                        text = getattr(cand, "content", None)
                        if hasattr(text, "parts"):
                            # 拼接 parts 的纯文本
                            text = "".join(getattr(p, "text", "") for p in text.parts)
                        elif not isinstance(text, str):
                            text = ""
                    except Exception:
                        text = ""
                if not text:
                    return {
                        "brand_relevance": "unknown",
                        "reason": "empty response",
                    }
                try:
                    return json.loads(text)
                except Exception:
                    # 不是严格 JSON，尝试截断到首尾花括号
                    s = text.strip()
                    l = s.find("{")
                    r = s.rfind("}")
                    if 0 <= l < r:
                        try:
                            return json.loads(s[l : r + 1])
                        except Exception:
                            pass
                    return {
                        "brand_relevance": "unknown",
                        "reason": "非JSON响应",
                        "raw": text,
                    }
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                # 简单退避
                time.sleep(1.5 * (i + 1))
                continue

        return {
            "brand_relevance": "unknown",
            "reason": last_err or "request_failed",
        }

