#!/usr/bin/env python3
import os
import json
import time
from pathlib import Path

try:
	from dotenv import load_dotenv  # type: ignore
except Exception:
	load_dotenv = None  # fallback if python-dotenv is not installed

import requests


def load_api_key() -> str:
	"""Load TikHub API key from backend/.env or environment.

	Priorities:
	- Environment variable `tikhub_API_KEY`
	- `backend/.env` file relative to repo root
	- `.env` in current working directory
	"""
	# 1) Already in environment
	api_key = os.getenv("tikhub_API_KEY")
	if api_key:
		return api_key

	# 2) Explicitly load backend/.env then default .env
	project_root = Path(__file__).resolve().parents[4]
	backend_env = project_root / "backend/.env"
	default_env = project_root / ".env"
	if load_dotenv:
		# load backend/.env if exists
		if backend_env.exists():
			load_dotenv(backend_env)  # type: ignore
			api_key = os.getenv("tikhub_API_KEY")
			if api_key:
				return api_key
		# load root .env as fallback
		if default_env.exists():
			load_dotenv(default_env)  # type: ignore
			api_key = os.getenv("tikhub_API_KEY")
			if api_key:
				return api_key

	# 3) Manual parse as a final fallback
	for env_path in (backend_env, default_env):
		if env_path.exists():
			for line in env_path.read_text(encoding="utf-8").splitlines():
				if line.strip().startswith("tikhub_API_KEY"):
					parts = line.split("=", 1)
					if len(parts) == 2:
						return parts[1].strip()

	raise RuntimeError("tikhub_API_KEY not found in environment or .env files")


def ensure_output_dir() -> Path:
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


def build_payload(keyword: str) -> dict:
	return {
		"keyword": keyword,
		"cursor": 0,
		"sort_type": "0",
		"publish_time": "0",
		"filter_duration": "0",
		"content_type": "2",
		"search_id": "",
	}


def request_search_once(api_key: str, keyword: str) -> dict:
	"""调用抖音图文搜索接口(fetch_image_search)并返回 JSON。

	会轮询多个常见 TikHub 基础域名，提升可用性。
	"""
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}
	payload = build_payload(keyword)
	base_urls = [
		"https://api.tikhub.io",
		"https://open.tikhub.cn",
		"https://tikhub.io",
	]
	last_error = None
	for base in base_urls:
		url = f"{base}/api/v1/douyin/search/fetch_image_search"
		try:
			resp = requests.post(url, headers=headers, json=payload, timeout=30)
			if resp.status_code == 200:
				data = resp.json()
				return {"base_url": base, "status_code": resp.status_code, "data": data}
		except Exception as exc:  # network/json errors
			last_error = exc
			continue
	# If we got here, all bases failed
	if last_error:
		raise last_error
	raise RuntimeError("All base URLs failed for the TikHub API call")


def main() -> None:
	api_key = load_api_key()
	output_dir = ensure_output_dir()
	keyword = "海底捞"
	result = request_search_once(api_key=api_key, keyword=keyword)
	# Persist a single-shot result with timestamped filename
	stamp = time.strftime("%Y%m%d-%H%M%S")
	outifle_name = f"douyin_image_search_{stamp}.json"
	outfile = output_dir / outifle_name
	with outfile.open("w", encoding="utf-8") as f:
		json.dump(result, f, ensure_ascii=False, indent=2)
	print(str(outfile))


if __name__ == "__main__":
	main()

