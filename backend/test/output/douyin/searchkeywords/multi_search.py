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
	"""从环境变量或 .env 文件加载 TikHub 的 API Key。

	优先级：
	1) 环境变量 `tikhub_API_KEY`
	2) 项目根目录下的 `backend/.env`
	3) 项目根目录下的 `.env`
	"""
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


# ====== 可配置参数（放在文件开头，便于你后续修改） ======
# 搜索关键词
SEARCH_KEYWORD = "海底捞"
# 分页偏移量
OFFSET = 0
# 返回数量上限（根据官方文档及平台限制调整）
COUNT = 20
# 基础域名列表（轮询以提高可用性）
BASE_URLS = [
	"https://api.tikhub.io",
	"https://open.tikhub.cn",
	"https://tikhub.io",
]
# 文档链接（方便追踪与核对字段）
DOCS = "https://api.tikhub.io/#/Douyin-Search-API/fetch_multi_search_api_v1_douyin_search_fetch_multi_search_post"
# ==================================================


def build_payload(keyword: str) -> dict:
	"""构建抖音多类型搜索接口的请求体。

	接口文档参考：`DOCS`
	常用参数：`keyword`、`offset`、`count`
	"""
	return {
		"keyword": keyword,
		"offset": OFFSET,
		"count": COUNT,
	}


def request_multi_search(api_key: str, keyword: str) -> dict:
	"""调用抖音多类型搜索接口(fetch_multi_search)并返回 JSON。"""
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}
	payload = build_payload(keyword)
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
	"""以关键字“海底捞”发起一次多类型搜索请求，并把结果保存为时间戳 JSON 文件。"""
	api_key = load_api_key()
	output_dir = ensure_output_dir()
	keyword = SEARCH_KEYWORD
	result = request_multi_search(api_key=api_key, keyword=keyword)
	stamp = time.strftime("%Y%m%d-%H%M%S")
	outfile_name = f"douyin_multi_search_{stamp}.json"
	outfile = output_dir / outfile_name
	with outfile.open("w", encoding="utf-8") as f:
		json.dump(result, f, ensure_ascii=False, indent=2)
	print(str(outfile))


if __name__ == "__main__":
	main()


