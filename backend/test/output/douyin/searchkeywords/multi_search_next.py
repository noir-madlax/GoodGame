#!/usr/bin/env python3
import os
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

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
	"""确保输出目录存在。"""
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


def find_latest_multi_search_file(output_dir: Path) -> Path:
	"""查找最新的 multi_search 结果 JSON 文件。"""
	candidates = sorted(
		[p for p in output_dir.glob("douyin_multi_search_*.json") if p.is_file()],
		key=lambda p: p.stat().st_mtime,
		reverse=True,
	)
	if not candidates:
		raise FileNotFoundError("未找到上一页的 multi_search 输出文件")
	return candidates[0]


def extract_pagination_params(payload: Dict[str, Any]) -> Dict[str, Any]:
	"""从上一页结果中提取翻页所需参数：keyword、cursor、search_id。

	结构示例路径：root.data.data[0].business_config.next_page
	做健壮性处理，遍历 data 列表查找包含 business_config 的对象。
	"""
	keyword: Optional[str] = None
	cursor: Optional[int] = None
	search_id: Optional[str] = None

	# 顶层 keyword 兜底（有些在 data.params.keyword 提供）
	try:
		keyword = payload["data"]["params"]["keyword"]
	except Exception:
		pass

	try:
		blocks = payload["data"]["data"]
		if isinstance(blocks, list):
			for block in blocks:
				cfg = block.get("business_config")
				if not cfg:
					continue
				next_page = cfg.get("next_page") or {}
				if not keyword:
					keyword = next_page.get("keyword")
				cursor = next_page.get("cursor")
				search_id = next_page.get("search_id") or next_page.get("search_request_id")
				# 一旦拿到 cursor 即可返回
				if cursor is not None:
					break
	except Exception:
		pass

	if not keyword or cursor is None or not search_id:
		raise ValueError("未能从上一页结果中解析到翻页参数(keyword/cursor/search_id)")

	return {
		"keyword": keyword,
		"cursor": cursor,
		"search_id": search_id,
	}


# ====== 可配置参数（在顶部便于修改） ======
COUNT = 20  # 返回数量
SORT_TYPE = "0"  # 0综合 1最多点赞 2最新发布
PUBLISH_TIME = "0"  # 0不限 1一天 7一周 180半年
FILTER_DURATION = "0"  # 0不限 0-1,1-5,5-10000
CONTENT_TYPE = "0"  # 0不限 1视频 2图片 3文章
BASE_URLS = [
	"https://api.tikhub.io",
	"https://open.tikhub.cn",
	"https://tikhub.io",
]
DOCS = "https://api.tikhub.io/#/Douyin-Search-API/fetch_multi_search_api_v1_douyin_search_fetch_multi_search_post"
# ======================================


def build_payload(keyword: str, cursor: int, search_id: str) -> Dict[str, Any]:
	"""构建下一页请求体。"""
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


def request_multi_search_next(api_key: str, payload: Dict[str, Any]) -> dict:
	"""请求多类型搜索下一页。"""
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
				data = resp.json()
				return {
					"base_url": base,
					"status_code": resp.status_code,
					"docs": DOCS,
					"params": payload,
					"data": data,
				}
		except Exception as exc:
			last_error = exc
			continue
	if last_error:
		raise last_error
	raise RuntimeError("All base URLs failed for the TikHub API call")


def main() -> None:
	"""读取最新第一页结果，解析 cursor/search_id，请求下一页并保存 JSON。"""
	api_key = load_api_key()
	output_dir = ensure_output_dir()
	prev_file = find_latest_multi_search_file(output_dir)
	prev_payload = json.loads(prev_file.read_text(encoding="utf-8"))
	page_params = extract_pagination_params(prev_payload)
	payload = build_payload(
		keyword=page_params["keyword"],
		cursor=int(page_params["cursor"]),
		search_id=str(page_params["search_id"]),
	)
	result = request_multi_search_next(api_key=api_key, payload=payload)
	stamp = time.strftime("%Y%m%d-%H%M%S")
	outfile_name = f"douyin_multi_search_{stamp}.json"
	outfile = output_dir / outfile_name
	with outfile.open("w", encoding="utf-8") as f:
		json.dump(result, f, ensure_ascii=False, indent=2)
	print(str(outfile))


if __name__ == "__main__":
	main()


