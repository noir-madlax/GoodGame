
#!/usr/bin/env python3
"""
脚本用途：
- 读取环境/数据库提供的抖音作者 sec_uid，调用 TikHub Douyin App V3 用户详情接口，
  将接口原始返回（完整 JSON，对应 raw_response）落盘至 output 目录，并 Upsert 到
  Supabase 数据库表 public.gg_authors（按 platform+platform_author_id 去重）。

行为特性：
- 自动加载 tikhub_API_KEY、SUPABASE_URL、SUPABASE_KEY 等环境变量（优先 backend/.env）。
- 兼容接口参数名（sec_uid/sec_user_id）与 GET/POST，两种域名均尝试，保证可用性。
- 保存原始响应 raw_response，同时写入常用业务字段
  （uid、nickname、avatar_url、share_url、follower_count 等）。
- 通过环境变量 DOUYIN_SEC_UID 指定目标作者；未指定时使用脚本内默认示例。
"""
import os
import json
import time
from pathlib import Path

try:
	from dotenv import load_dotenv  # type: ignore
except Exception:
	load_dotenv = None  # fallback if python-dotenv is not installed

import requests
import typing as t


def load_api_key() -> str:
	"""加载 TikHub API Key，优先级如下：

	1) 环境变量 `tikhub_API_KEY`
	2) 项目根目录下的 `backend/.env`
	3) 项目根目录下的 `.env`
	"""
	# 1) 环境已有
	api_key = os.getenv("tikhub_API_KEY")
	if api_key:
		return api_key

	# 2) 显式加载 backend/.env 和根目录 .env
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

	# 3) 兜底：手动解析 .env
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


def choose_avatar_url(user: dict) -> t.Optional[str]:
	"""从多个头像字段里选择一条可用 URL。"""
	for key in ("avatar_larger", "avatar_300x300", "avatar_medium", "avatar_168x168"):
		val = user.get(key) or {}
		urls = val.get("url_list") if isinstance(val, dict) else None
		if isinstance(urls, list) and urls:
			return urls[-1]
	return None


def upsert_author_to_supabase(raw_response: dict) -> None:
	"""仅保存原始响应 raw_response 到 public.gg_authors。

	使用项目的 Supabase 客户端：tikhub_api.orm.supabase_client.get_client
	"""
	try:
		from backend.tikhub_api.orm.supabase_client import get_client  # type: ignore
	except Exception:
		from tikhub_api.orm.supabase_client import get_client  # type: ignore

	# 保证 env 可用
	if load_dotenv:
		project_root = Path(__file__).resolve().parents[4]
		backend_env = project_root / "backend/.env"
		if backend_env.exists():
			load_dotenv(backend_env)  # type: ignore

	client = get_client()
	user = (((raw_response.get("data") or {}).get("data") or {}).get("user") or {})
	if not user:
		return

	platform = "douyin"
	platform_author_id = user.get("uid") or ""
	sec_uid = user.get("sec_uid") or ""
	nickname = user.get("nickname") or ""
	avatar_url = None
	for key in ("avatar_larger", "avatar_300x300", "avatar_medium", "avatar_168x168"):
		urls = (user.get(key) or {}).get("url_list")
		if isinstance(urls, list) and urls:
			avatar_url = urls[-1]
			break
	share_url = (user.get("share_info") or {}).get("share_url")
	follower_count = int(user.get("follower_count") or 0)
	signature = user.get("signature") or ""
	location = user.get("ip_location") or ""
	account_cert_info = user.get("account_cert_info") or ""
	verification_type = user.get("verification_type")

	payload = {
		"platform": platform,
		"platform_author_id": platform_author_id,
		"sec_uid": sec_uid,
		"nickname": nickname,
		"avatar_url": avatar_url,
		"share_url": share_url,
		"follower_count": follower_count,
		"signature": signature,
		"location": location,
		"account_cert_info": account_cert_info,
		"verification_type": verification_type,
		"raw_response": raw_response,
	}

	# upsert
	client.table("gg_authors").upsert(payload, on_conflict=("platform","platform_author_id")).execute()

def request_user_profile_once(api_key: str, sec_uid: str) -> dict:
	"""调用抖音用户详情接口（App V3 handler_user_profile）。

	- 参考 `backend/test/output/douyin/archive/test- video-search.py` 的调用风格
	- 通过多个常见 TikHub 域名尝试，提升兼容性
	- GET 参数：sec_uid
	"""
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}
	# 兼容不同参数名/方法
	param_variants = [
		{"sec_uid": sec_uid},
		{"sec_user_id": sec_uid},
	]
	methods = ["GET", "POST"]
	base_urls = [
		"https://api.tikhub.io",
		"https://open.tikhub.cn",
		"https://tikhub.io",
	]
	last_error = None
	for base in base_urls:
		url = f"{base}/api/v1/douyin/app/v3/handler_user_profile"
		for params in param_variants:
			for method in methods:
				try:
					if method == "GET":
						resp = requests.get(url, headers=headers, params=params, timeout=30)
					else:
						resp = requests.post(url, headers=headers, json=params, timeout=30)
					if resp.status_code == 200:
						try:
							data = resp.json()
						except Exception:
							data = {"non_json_body": resp.text[:1000]}
						return {
							"base_url": base,
							"status_code": resp.status_code,
							"method": method,
							"params": params,
							"data": data,
						}
					# 非 200 也记录一份便于排查
					last_error = RuntimeError(
						f"HTTP {resp.status_code} {method} {url} resp-snippet={resp.text[:200]}"
					)
				except Exception as exc:
					last_error = exc
					continue
	if last_error:
		raise last_error
	raise RuntimeError("All base URLs failed for the TikHub user profile API call")


def resolve_sec_uid_default() -> str:
	"""确定要使用的 sec_uid。

	优先级：
	1) 环境变量 `DOUYIN_SEC_UID`
	2) 数据库中查询到的示例值（会根据 MCP 预查询到的一个样本硬编码作为兜底）
	"""
	sec_uid_env = os.getenv("DOUYIN_SEC_UID")
	if sec_uid_env:
		return sec_uid_env
	# 兜底：来自数据库中已查询到的一个有效样本（平台 douyin）
	return "MS4wLjABAAAA0XYDGdylDyDP8Y0O-j5mBESef2okd6YsZHMTYDwoKE8"


def main() -> None:
	api_key = load_api_key()
	output_dir = ensure_output_dir()
	sec_uid = resolve_sec_uid_default()
	result = request_user_profile_once(api_key=api_key, sec_uid=sec_uid)
	# 入库：仅 raw_response
	try:
		upsert_author_to_supabase(result)
	except Exception:
		pass
	stamp = time.strftime("%Y%m%d-%H%M%S")
	outfile = output_dir / f"douyin_user_profile_{stamp}.json"
	with outfile.open("w", encoding="utf-8") as f:
		json.dump(result, f, ensure_ascii=False, indent=2)
	print(str(outfile))


if __name__ == "__main__":
	main()


