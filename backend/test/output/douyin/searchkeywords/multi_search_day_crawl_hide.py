#!/usr/bin/env python3
import os
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
	from dotenv import load_dotenv  # type: ignore
except Exception:
	load_dotenv = None  # fallback if python-dotenv is not installed

import requests


# ====== 可配置参数（放在文件开头，便于你后续修改） ======
SEARCH_KEYWORD = "火锅 隐藏吃法"  # 关键词（带空格）
COUNT = 100                # 每页数量（增大为100）
SORT_TYPE = "0"           # 0综合 1最多点赞 2最新发布
PUBLISH_TIME = "1"        # 1=最近一天
FILTER_DURATION = "0"     # 0不限 0-1,1-5,5-10000
CONTENT_TYPE = "0"        # 0不限 1视频 2图片 3文章
BASE_URLS = [
	"https://api.tikhub.io",
	"https://open.tikhub.cn",
	"https://tikhub.io",
]
DOCS = "https://api.tikhub.io/#/Douyin-Search-API/fetch_multi_search_api_v1_douyin_search_fetch_multi_search_post"
MAX_PAGES = 200            # 安全上限
# ==================================================


def load_api_key() -> str:
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
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


def post_multi_search(api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}
	last_error = None
	for base in BASE_URLS:
		url = f"{base}/api/v1/douyin/search/fetch_multi_search"
		try:
			resp = requests.post(url, headers=headers, json=payload, timeout=60)
			if resp.status_code == 200:
				return {
					"base_url": base,
					"status_code": resp.status_code,
					"docs": DOCS,
					"params": payload,
					"data": resp.json(),
				}
		except Exception as exc:
			last_error = exc
			continue
	if last_error:
		raise last_error
	raise RuntimeError("All base URLs failed for the TikHub API call")


def parse_next_page_info(page_payload: Dict[str, Any]) -> Tuple[int, Optional[int], Optional[str]]:
	has_more = 0
	cursor: Optional[int] = None
	search_id: Optional[str] = None
	try:
		blocks = page_payload["data"]["data"]
		if isinstance(blocks, list):
			for block in blocks:
				cfg = block.get("business_config")
				if not cfg:
					continue
				has_more = int(cfg.get("has_more", 0))
				next_page = cfg.get("next_page") or {}
				if cursor is None:
					cursor = next_page.get("cursor")
				if not search_id:
					search_id = next_page.get("search_id") or next_page.get("search_request_id")
				if cursor is not None and search_id:
					break
	except Exception:
		pass
	return has_more, cursor, search_id


def build_first_payload(keyword: str) -> Dict[str, Any]:
	return {
		"keyword": keyword,
		"cursor": 0,
		"sort_type": SORT_TYPE,
		"publish_time": PUBLISH_TIME,
		"filter_duration": FILTER_DURATION,
		"content_type": CONTENT_TYPE,
		"search_id": "",
		"count": COUNT,
	}


def build_next_payload(keyword: str, cursor: int, search_id: str) -> Dict[str, Any]:
	return {
		"keyword": keyword,
		"cursor": cursor,
		"sort_type": SORT_TYPE,
		"publish_time": PUBLISH_TIME,
		"filter_duration": FILTER_DURATION,
		"content_type": CONTENT_TYPE,
		"search_id": search_id,
		"count": COUNT,
	}


def save_page(output_dir: Path, prefix: str, page_index: int, payload: Dict[str, Any]) -> Path:
	stamp = time.strftime("%Y%m%d-%H%M%S")
	outfile = output_dir / f"{prefix}_{stamp}_p{page_index}.json"
	with outfile.open("w", encoding="utf-8") as f:
		json.dump(payload, f, ensure_ascii=False, indent=2)
	return outfile


def crawl_all_pages(keyword: str) -> Dict[str, Any]:
	api_key = load_api_key()
	output_dir = ensure_output_dir()
	page_files: List[str] = []
	page_count = 0
	requests_count = 0

	# 第1页
	payload = build_first_payload(keyword)
	page = post_multi_search(api_key=api_key, payload=payload)
	requests_count += 1
	page_count += 1
	path = save_page(output_dir, "douyin_multi_search_day_hide", page_count, page)
	page_files.append(str(path))

	while page_count < MAX_PAGES:
		has_more, next_cursor, next_search_id = parse_next_page_info(page)
		if not has_more or next_cursor is None or not next_search_id:
			break
		payload = build_next_payload(keyword, int(next_cursor), str(next_search_id))
		page = post_multi_search(api_key=api_key, payload=payload)
		requests_count += 1
		page_count += 1
		path = save_page(output_dir, "douyin_multi_search_day_hide", page_count, page)
		page_files.append(str(path))

	return {
		"keyword": keyword,
		"publish_time": PUBLISH_TIME,
		"count_per_page": COUNT,
		"pages": page_count,
		"requests": requests_count,
		"files": page_files,
	}


def main() -> None:
	result = crawl_all_pages(SEARCH_KEYWORD)
	print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
	main()


