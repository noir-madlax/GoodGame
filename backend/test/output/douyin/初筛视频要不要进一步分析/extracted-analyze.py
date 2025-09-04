#!/usr/bin/env python3
"""基于 extraced.json 与 extracted.prompt 对抓取视频做初筛，挑选值得进一步分析的条目。

参考调用方式：
  python extracted-analyze.py --api-key $GEMINI_API_KEY

输出：在同目录 output/ 下生成 douyin_extracted_screen_{timestamp}.json，包含每条视频的筛选结论与一个通过清单。
"""
import os
import json
import time
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

from pydantic import BaseModel
from google import genai
from google.genai import types
import argparse


class ScreeningItem(BaseModel):
    item_ref: str
    brand_relevance: str  # 相关 | 疑似相关 | 无关
    has_negative_cue: bool
    marketing_type: str  # "带货/达人" | "官方/门店宣发" | "集体营销疑似" | "无"
    marketing_evidence: str
    relevance_evidence: str
    time_window_flag: bool
    decision: str  # 通过 | 拒绝 | 需要进一步核验
    decision_reason: str


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to read JSON: {path}: {e}")


def ensure_output_dir(base: Path) -> Path:
    out = base / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


def build_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def load_api_key(cli_param: str | None = None) -> str:
    if cli_param:
        return cli_param
    api_key = os.getenv("GEMINI_API_KEY") or ""
    if api_key:
        return api_key
    # Try dotenv
    if load_dotenv:
        for env_path in [
            Path(__file__).resolve().parent / ".env",
            Path(__file__).resolve().parents[4] / "backend/.env",
            Path(__file__).resolve().parents[4] / ".env",
        ]:
            try:
                if env_path.exists():
                    load_dotenv(env_path)  # type: ignore
                    api_key = os.getenv("GEMINI_API_KEY") or ""
                    if api_key:
                        return api_key
            except Exception:
                pass
    # Fallback: minimal .env parse
    for p in [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parents[4] / "backend/.env",
        Path(__file__).resolve().parents[4] / ".env",
    ]:
        try:
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "GEMINI_API_KEY":
                    return v.strip().strip("\"'")
        except Exception:
            pass
    raise RuntimeError("GEMINI_API_KEY not found. Provide via --api-key or .env.")


def generate_screening(
    client: genai.Client,
    model: str,
    prompt_text: str,
    items: list[dict],
) -> list[ScreeningItem]:
    # 将 items 以 JSON 文本提供，并要求返回严格数组结构
    payload = {
        "schema": {"aweme_id": "string", "desc": "string", "create_time": "string", "hashtags": ["string"]},
        "items": items,
    }

    contents: list[types.Part | str] = [
        "以下为抓取到的视频文本信息数组（不包含画面）。请使用系统提示进行初筛，每个输入输出一条 JSON 结果：",
        json.dumps(payload, ensure_ascii=False),
        "请仅输出 JSON 数组，不要包含解释或额外文字。",
    ]

    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=list[ScreeningItem],
            system_instruction=prompt_text,
        ),
    )

    text = getattr(resp, "text", None) or ""
    try:
        data = json.loads(text)
    except Exception:
        # 尝试容错：包一层
        data = {"raw_text": text}

    if isinstance(data, list):
        return [ScreeningItem(**x) for x in data]
    # 若模型未严格遵循，尝试从 result 或 data 字段取
    for key in ("result", "data"):  # type: ignore
        maybe = data.get(key) if isinstance(data, dict) else None
        if isinstance(maybe, list):
            return [ScreeningItem(**x) for x in maybe]
    raise RuntimeError("LLM response not in expected JSON array format")


def main() -> None:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--api-key", dest="api_key", default="", type=str)
    parser.add_argument("--model", dest="model", default="gemini-2.5-pro", type=str)
    parser.add_argument("--max", dest="max_items", default="-1", type=str)
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    json_path = base_dir / "extraced.json"
    prompt_path = base_dir / "extracted.prompt"

    data = read_json(json_path)
    if not isinstance(data, dict) or not isinstance(data.get("extracted"), list):
        raise RuntimeError("extraced.json shape error: expect { extracted: [...] }")

    items: list[dict] = data["extracted"]
    try:
        max_items = int(args.max_items)
    except Exception:
        max_items = -1
    if max_items >= 0:
        items = items[:max_items]

    # 为 LLM 提供必要字段，移除不需要的键
    norm_items: list[dict] = []
    for it in items:
        norm_items.append(
            {
                "aweme_id": str(it.get("aweme_id", "")),
                "desc": str(it.get("desc", "")),
                "create_time": str(it.get("create_time", "")),
                "hashtags": list(it.get("hashtags", []) or []),
            }
        )

    prompt_text = prompt_path.read_text(encoding="utf-8")
    api_key = load_api_key(args.api_key or None)
    client = build_client(api_key)

    out_dir = ensure_output_dir(base_dir)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    outfile = out_dir / f"douyin_extracted_screen_{stamp}.json"

    results = generate_screening(client, args.model, prompt_text, norm_items)

    # 汇总输出 + 通过清单
    passed_ids = [r.item_ref for r in results if r.decision == "通过"]
    bundle = {
        "model": args.model,
        "generated_at": stamp,
        "total": len(results),
        "passed_count": len(passed_ids),
        "passed_ids": passed_ids,
        "results": [json.loads(r.model_dump_json()) for r in results],
    }
    outfile.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(outfile))


if __name__ == "__main__":
    main()

