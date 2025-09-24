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


# ====== 可配置参数 ======
# 直播间房间号（按你的需求默认 1792362541，可通过命令行或修改常量调整）
ROOM_ID = os.getenv("BILI_ROOM_ID", "23307253")

#ROOM_ID = os.getenv("BILI_ROOM_ID", "274763")


#ROOM_ID = os.getenv("BILI_ROOM_ID", "1792362541")
# 基础域名列表（轮询以提高可用性）
BASE_URLS = [
	"https://api.tikhub.io",
	"https://open.tikhub.cn",
	"https://tikhub.io",
]
# 文档链接（方便追踪与核对字段）
DOCS = "https://api.tikhub.io/#/Bilibili-Web-API/fetch_collect_folders_api_v1_bilibili_web_fetch_live_room_detail_get"
# ========================


def request_live_room_detail(api_key: str, room_id: str) -> dict:
	"""调用 Bilibili 直播间详情接口并返回 JSON。

	接口：GET /api/v1/bilibili/web/fetch_live_room_detail
	参数：room_id
	"""
	headers = {
		"Authorization": f"Bearer {api_key}",
	}
	params = {"room_id": room_id}
	last_error = None
	for base in BASE_URLS:
		url = f"{base}/api/v1/bilibili/web/fetch_live_room_detail"
		try:
			resp = requests.get(url, headers=headers, params=params, timeout=60)
			if resp.status_code == 200:
				data = resp.json()
				return {
					"base_url": base,
					"status_code": resp.status_code,
					"docs": DOCS,
					"params": params,
					"data": data,
				}
		except Exception as exc:
			last_error = exc
			continue
	if last_error:
		raise last_error
	raise RuntimeError("All base URLs failed for the TikHub API call")


def main() -> None:
	"""以房间号发起一次 Bilibili 直播间详情请求，并把结果保存为时间戳 JSON 文件。"""
	api_key = load_api_key()
	output_dir = ensure_output_dir()
	room_id = str(ROOM_ID)
	result = request_live_room_detail(api_key=api_key, room_id=room_id)
	stamp = time.strftime("%Y%m%d-%H%M%S")
	out_name = f"bilibili_live_room_detail_{room_id}_{stamp}.json"
	out_file = output_dir / out_name
	with out_file.open("w", encoding="utf-8") as f:
		json.dump(result, f, ensure_ascii=False, indent=2)
	print(str(out_file))


if __name__ == "__main__":
	main()


