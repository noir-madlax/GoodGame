#!/usr/bin/env python3
import os
import json
import time
from pathlib import Path

try:
	from dotenv import load_dotenv  # type: ignore
except Exception:
	load_dotenv = None

import requests


VIDEO_URL = (
	"https://v3-search.douyinvod.com/0aff1f7d548f7843529f4b43ffd16305/68a3fada/video/tos/cn/tos-cn-ve-15/"
	"oQwUPBIc6gGVAkAHQD2BCxYueEL47rlIfX39eo/?a=615883&ch=11&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=996&bt=996&cs=0&ds=6&ft=Xo0TLaZqsQOCCp5Sup-Q6_Mme-rLWa5eFnLN5Sd-IiUFjqkwUBMEq&mime_type=video_mp4&qs=0&rc=Ojg7ZTw2PDllZ2YzMzloNkBpanM3b3E5cmpkeTMzNGkzM0AzMS00NDEtXzIxMV4xL15fYSNjXmU0MmRzYl9gLS1kLS9zcw%3D%3D&btag=c0000e00028000&dy_q=1755573353&feature_id=f0150a16a324336cda5d6dd0b69ed299&l=20250819111552C3E4C9A3D38DE83A2477"
)


def load_api_key() -> str:
	api_key = os.getenv("OPENROUTER_API_KEY")
	if api_key:
		return api_key
	project_root = Path(__file__).resolve().parents[4]
	backend_env = project_root / "backend/.env"
	root_env = project_root / ".env"
	if load_dotenv:
		for env_path in (backend_env, root_env):
			if env_path.exists():
				load_dotenv(env_path)  # type: ignore
				api_key = os.getenv("OPENROUTER_API_KEY")
				if api_key:
					return api_key
	# manual parse as last resort
	for env_path in (backend_env, root_env):
		if env_path.exists():
			for line in env_path.read_text(encoding="utf-8").splitlines():
				if line.strip().startswith("OPENROUTER_API_KEY"):
					return line.split("=", 1)[1].strip()
	raise RuntimeError("OPENROUTER_API_KEY not found")


def ensure_output_dir() -> Path:
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


def call_openrouter_gemini(video_url: str, api_key: str) -> dict:
	url = "https://openrouter.ai/api/v1/chat/completions"
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
		"HTTP-Referer": "https://goodgame.local/",
		"X-Title": "GoodGame Douyin Video Analyzer",
	}
	# Model name per OpenRouter. If unavailable, provider will error; caller handles it.
	model = "google/gemini-2.5-pro"
	system_prompt = (
		"You are an expert Chinese social-listening analyst. Analyze Douyin video content. "
		"Output concise Chinese JSON with fields: summary, sentiment (positive|neutral|negative), "
		"key_points (array), risks (array), brand='海底捞'."
	)
	user_prompt = (
		"请你基于此视频链接，对视频的主要内容进行概括，总结与‘海底捞’相关的关键舆论点，"
		"并判断整体情感倾向（positive/neutral/negative）。如果无法直接访问视频或解析画面，"
		"请依据标题/页面可得元数据和常识进行稳健推断，并用‘可能/不确定’标注。"
		f"\n视频链接: {video_url}"
	)
	payload = {
		"model": model,
		"temperature": 0.3,
		"messages": [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		],
	}
	resp = requests.post(url, headers=headers, json=payload, timeout=60)
	resp.raise_for_status()
	return resp.json()


def extract_text(response_json: dict) -> str:
	try:
		return response_json["choices"][0]["message"]["content"].strip()
	except Exception:
		return json.dumps(response_json, ensure_ascii=False)


def main() -> None:
	api_key = load_api_key()
	output_dir = ensure_output_dir()
	response = call_openrouter_gemini(VIDEO_URL, api_key)
	text = extract_text(response)
	stamp = time.strftime("%Y%m%d-%H%M%S")
	outfile = output_dir / f"douyin_video_llm_{stamp}.json"
	with outfile.open("w", encoding="utf-8") as f:
		json.dump({"model": "google/gemini-2.5-pro", "raw": response, "result": text}, f, ensure_ascii=False, indent=2)
	print(str(outfile))


if __name__ == "__main__":
	main()


