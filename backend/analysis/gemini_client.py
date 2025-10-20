from __future__ import annotations
from typing import Dict, Any, Optional, BinaryIO, IO, Union
import os
import json
import time
import io

from jobs.logger import get_logger

log = get_logger(__name__)

try:
    # 新版 Google Generative AI 官方 SDK（https://pypi.org/project/google-genai/）
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except Exception as e:  # pragma: no cover
    genai = None  # type: ignore
    types = None  # type: ignore


ANALYSIS_MODEL_NAME = "gemini-2.5-flash"
SCREENING_MODEL_NAME = "gemini-2.5-flash"

def _normalize_model_name(model: str | None) -> str:
    """兼容传入类似 "google/gemini-2.5-pro" 的名字，转为 SDK 需要的 "gemini-2.5-pro"。
    若未提供按默认值处理。
    """
    name = (model).strip()
    # 常见前缀：openrouter 默认可能传 "google/gemini-2.5-pro"
    if "/" in name:
        name = name.split("/")[-1]
    return name


class GeminiClient:
    """
    与 OpenRouterClient 对齐的最小封装：
    - classify_value(system_prompt, user_text, max_tokens=200, temperature=0.2) -> Dict[str, Any]
    - 使用 google genai 的 generate_content，要求返回 JSON
    - 新增：upload_file(file_stream, display_name=None, mime_type=None, ...) 上传文件流至 Files API
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, timeout: int = 30) -> None:
        if genai is None or types is None:  # pragma: no cover
            raise RuntimeError(
                "google-genai SDK 未安装。请先在 backend 虚拟环境中执行: pip install google-genai"
            )
        self.screening_model = _normalize_model_name(SCREENING_MODEL_NAME)
        self.analysis_model = _normalize_model_name(ANALYSIS_MODEL_NAME)
        self.api_key = (api_key or "").strip()
        self.timeout = timeout  # 目前 SDK 暂无直接超时参数，保留占位
        if not self.api_key:
            raise RuntimeError("api_key is required when creating GeminiClient")
        self.client = genai.Client(api_key=self.api_key)

    def _wait_file_active(self, name: str, timeout_sec: int = 120) -> None:
        """轮询文件状态，直到 ACTIVE 或超时。"""
        start = time.time()
        while True:
            info = self.client.files.get(name=name)
            state = getattr(info, "state", None)
            if str(state).endswith("ACTIVE") or str(state) == "ACTIVE":
                return
            if time.time() - start > timeout_sec:
                raise TimeoutError(f"File {name} not ACTIVE after {timeout_sec}s (state={state})")
            time.sleep(2)

    def upload_file(
        self,
        file_stream: Union[BinaryIO, IO[bytes], bytes],
        display_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        wait_active: bool = True,
        timeout_sec: int = 120,
    ) -> Dict[str, Any]:
        """上传文件流到 Gemini Files（google-genai >= 1.33.0，支持直接上传 IO 流）。

        - 若传入的是 IO 流，SDK 要求必须提供 config.mime_type；本方法通过 mime_type 参数传入。
        - 若传入的是 bytes/bytearray，会封装为 io.BytesIO（可 seek）。
        - display_name 仅用于传递给 UploadFileConfig 以便在控制台/日志中展示。
        """
        # 统一构造 IOBase，确保可 seek
        if isinstance(file_stream, (bytes, bytearray)):
            upload_io: IO[bytes] = io.BytesIO(bytes(file_stream))
        else:
            upload_io = file_stream  # BinaryIO / IO[bytes]

        # 当使用 IO 流时，必须提供 mime_type
        if mime_type is None:
            raise ValueError("mime_type is required when uploading from an IO stream (e.g., 'video/mp4')")

        upload_config = types.UploadFileConfig(
            mime_type=mime_type,
            display_name=display_name,
        )
        file_obj = self.client.files.upload(file=upload_io, config=upload_config)

        name = getattr(file_obj, "name", None)
        if wait_active and name:
            self._wait_file_active(name, timeout_sec=timeout_sec)

        file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
        result = {
            "name": name,
            "mime_type": getattr(file_obj, "mime_type", None) or mime_type,
            "uri": file_uri,
            "raw": file_obj,
            "display_name": display_name,
        }
        log.info({"uploaded_file": {k: v for k, v in result.items() if k != "raw"}})
        return result

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
                    model=self.screening_model,
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

