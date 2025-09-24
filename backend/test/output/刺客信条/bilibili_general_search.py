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
	"""从环境变量或 .env 文件加载 TikHub 的 API Key。"""
	api_key = os.getenv("tikhub_API_KEY")
	if api_key:
		return api_key
	project_root = Path(__file__).resolve().parents[4]
	backend_env = project_root / "backend/.env"
	default_env = project_root / ".env"
	if load_dotenv:
		if backend_env.exists():
			load_dotenv(backend_env)  # type: ignore
			api_key = os.getenv("tikhub_API_KEY")
			if api_key:
				return api_key
		if default_env.exists():
			load_dotenv(default_env)  # type: ignore
			api_key = os.getenv("tikhub_API_KEY")
			if api_key:
				return api_key
	for env_path in (backend_env, default_env):
		if env_path.exists():
			for line in env_path.read_text(encoding="utf-8").splitlines():
				if line.strip().startswith("tikhub_API_KEY"):
					parts = line.split("=", 1)
					if len(parts) == 2:
						return parts[1].strip()
	raise RuntimeError("tikhub_API_KEY not found in environment or .env files")


def ensure_output_dir() -> Path:
	"""确保输出目录存在：在当前脚本目录下创建 `output/` 目录。"""
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


# ====== 可配置参数 ======
KEYWORD = os.getenv("BILI_SEARCH_KEYWORD", "刺客信条")
PAGE = int(os.getenv("BILI_SEARCH_PAGE", "1"))
PAGE_SIZE = int(os.getenv("BILI_SEARCH_PAGE_SIZE", "42"))
ORDER = os.getenv("BILI_SEARCH_ORDER", "totalrank")  # 综合排序
DURATION = int(os.getenv("BILI_SEARCH_DURATION", "0"))
PUB_BEGIN = int(os.getenv("BILI_SEARCH_PUB_BEGIN", "0"))
PUB_END = int(os.getenv("BILI_SEARCH_PUB_END", "0"))
BASE_URLS = ["https://api.tikhub.io", "https://open.tikhub.cn", "https://tikhub.io"]
DOCS = "https://api.tikhub.io/#/Bilibili-Web-API/fetch_general_search_api_v1_bilibili_web_fetch_general_search_get"
# ========================


def request_general_search(api_key: str, keyword: str) -> dict:
	"""调用 Bilibili 综合搜索接口并返回 JSON。"""
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Accept": "application/json",
		"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
	}
	params = {
		"keyword": keyword,
		"order": ORDER,
		"page": PAGE,
		"page_size": PAGE_SIZE,
		"duration": DURATION,
		"pubtime_begin_s": PUB_BEGIN,
		"pubtime_end_s": PUB_END,
	}
	last_error = None
	for base in BASE_URLS:
		url = f"{base}/api/v1/bilibili/web/fetch_general_search"
		try:
			resp = requests.get(url, headers=headers, params=params, timeout=60)
			if resp.status_code == 200:
				try:
					data = resp.json()
					return {
						"base_url": base,
						"status_code": resp.status_code,
						"docs": DOCS,
						"params": params,
						"data": data,
					}
				except Exception:
					# 返回的不是 JSON，尝试下一个 base
					last_error = RuntimeError(f"Non-JSON response from {base}")
					continue
			else:
				last_error = RuntimeError(f"HTTP {resp.status_code} from {base}")
				continue
		except Exception as exc:
			last_error = exc
			continue
	# 所有 base 都失败，返回最后一次响应的原文（若有）
	return {
		"base_url": None,
		"status_code": None,
		"docs": DOCS,
		"params": params,
		"data": None,
		"error": str(last_error) if last_error else "Unknown error",
	}


def main() -> None:
	"""以关键词发起一次综合搜索请求，并把结果保存为时间戳 JSON 文件。"""
	api_key = load_api_key()
	output_dir = ensure_output_dir()
	keyword = str(KEYWORD)
	result = request_general_search(api_key=api_key, keyword=keyword)
	stamp = time.strftime("%Y%m%d-%H%M%S")
	out_name = f"bilibili_general_search_{keyword}_{stamp}.json"
	# 处理文件名中的中文与空格
	out_file = output_dir / out_name
	with out_file.open("w", encoding="utf-8") as f:
		json.dump(result, f, ensure_ascii=False, indent=2)
	print(str(out_file))


if __name__ == "__main__":
	main()


