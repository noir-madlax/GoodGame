
#!/usr/bin/env python3
"""
脚本用途：
- 读取环境提供的小红书作者 userid（或 author_id/user_id），调用 TikHub 小红书 App 用户详情接口
  `/api/v1/xiaohongshu/app/get_user_info`，将接口原始返回（完整 JSON，对应 raw_response）
  落盘至 output 目录，并 Upsert 到 Supabase 数据库表 public.gg_authors（按 platform+platform_author_id 去重）。

行为特性：
- 自动加载 tikhub_API_KEY、SUPABASE_URL、SUPABASE_KEY 等环境变量（优先 backend/.env）。
- 兼容接口参数名（userid/user_id/author_id）与 GET/POST，多域名均尝试，保证可用性。
- 保存原始响应 raw_response，同时尽量写入常用业务字段（nickname、avatar_url、follower_count 等，字段缺失则为空）。
- 通过环境变量 XHS_USER_ID 指定目标作者；未指定时使用脚本内默认示例。
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
import subprocess
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
		return api_key.strip()

	# 2) 显式加载 backend/.env 和根目录 .env
	project_root = Path(__file__).resolve().parents[4]
	backend_env = project_root / "backend/.env"
	default_env = project_root / ".env"
	if load_dotenv:
		if backend_env.exists():
			load_dotenv(backend_env)  # type: ignore
			api_key = os.getenv("tikhub_API_KEY")
			if api_key:
				return api_key.strip()
		if default_env.exists():
			load_dotenv(default_env)  # type: ignore
			api_key = os.getenv("tikhub_API_KEY")
			if api_key:
				return api_key.strip()

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
	"""从常见头像字段里选择一条可用 URL（兼容 Douyin/XHS 返回差异）。"""
	# Douyin 风格
	for key in ("avatar_larger", "avatar_300x300", "avatar_medium", "avatar_168x168"):
		val = user.get(key) or {}
		urls = val.get("url_list") if isinstance(val, dict) else None
		if isinstance(urls, list) and urls:
			return urls[-1]
	# XHS 常见字段
	for key in ("image", "image_url", "avatar", "avatar_url"):
		val = user.get(key)
		if isinstance(val, str) and val:
			return val
		if isinstance(val, dict):
			# 可能存在 {url: ..., url_list: [...]}
			if isinstance(val.get("url"), str) and val.get("url"):
				return val.get("url")
			urls = val.get("url_list")
			if isinstance(urls, list) and urls:
				return urls[-1]
	return None

def find_deep_value(obj: t.Any, candidate_keys: t.Tuple[str, ...]) -> t.Optional[t.Any]:
	"""在嵌套 dict/list 中深度查找任一候选键的值（首个命中即返回）。"""
	if isinstance(obj, dict):
		for k, v in obj.items():
			if k in candidate_keys:
				return v
			res = find_deep_value(v, candidate_keys)
			if res is not None:
				return res
	elif isinstance(obj, list):
		for item in obj:
			res = find_deep_value(item, candidate_keys)
			if res is not None:
				return res
	return None


def upsert_author_to_supabase(raw_response: dict) -> None:
	"""仅保存原始响应 raw_response 到 public.gg_authors。

	使用项目的 Supabase 客户端：tikhub_api.orm.supabase_client.get_client
	- platform 固定为 "xiaohongshu"
	- platform_author_id 取原始返回中的 userid（若找不到则为空字符串）
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
	# 兼容多层 data 包裹：XHS 常见结构在 data -> data -> data 下
	root = raw_response
	xhs_user = (
		((((root.get("data") or {}).get("data") or {}).get("data") or {}))
		if isinstance(root, dict) else {}
	)
	# 仍保留 user/user_info 的兜底（极少数返回形态）
	user_fallback = (
		find_deep_value(root, ("user", "user_info"))
		if isinstance(root, dict) else None
	) or {}
	user = xhs_user if xhs_user else user_fallback

	platform = "xiaohongshu"
	# 深度查找 userid/user_id/author_id（优先 XHS data.data.data.userid）
	platform_author_id_val = (
		user.get("userid")
		or find_deep_value(root, ("userid", "user_id", "author_id"))
	)
	platform_author_id = str(platform_author_id_val) if platform_author_id_val is not None else ""

	# 精确取 XHS 字段，避免误取 interactions.name=关注
	nickname = user.get("nickname") or ""
	# 头像优先 XHS 字段 images/imageb，再兜底 choose_avatar_url
	avatar_url = (
		user.get("images")
		or user.get("imageb")
		or choose_avatar_url(user)
	)
	# 粉丝数 = fans（若无再兜底）
	follower_count_val = (
		user.get("fans")
		or user.get("follower_count")
		or user.get("fans_count")
		or find_deep_value(root, ("fans","follower_count","fans_count"))
		or 0
	)
	try:
		follower_count = int(follower_count_val or 0)
	except Exception:
		follower_count = 0
	# 个性签名/简介
	signature = (
		user.get("desc")
		or user.get("bio")
		or user.get("signature")
		or ""
	)
	# IP 属地映射到 payload.location（与抖音保持一致）
	location = user.get("ip_location") or ""
	# 分享链接
	share_url = user.get("share_link") or None

	payload = {
		"platform": platform,
		"platform_author_id": platform_author_id,
		"sec_uid": None,
		"nickname": nickname,
		"avatar_url": avatar_url,
		"share_url": share_url,
		"follower_count": follower_count,
		"signature": signature,
		"location": location,
		"account_cert_info": None,
		"verification_type": None,
		"raw_response": raw_response,
	}

	# upsert：优先尝试 on_conflict；若表未建唯一约束则回退为“先查再更/插”。
	if not platform_author_id:
		return
	try:
		client.table("gg_authors").upsert(payload, on_conflict="platform,platform_author_id").execute()
	except Exception:
		# 手动合并
		existing = client.table("gg_authors").select("id").eq("platform", platform).eq("platform_author_id", platform_author_id).limit(1).execute()
		rows = getattr(existing, "data", None) or []
		if rows:
			client.table("gg_authors").update(payload).eq("platform", platform).eq("platform_author_id", platform_author_id).execute()
		else:
			client.table("gg_authors").insert(payload).execute()

def _curl_fetch_user_info(api_key: str, user_id: str, base: str) -> t.Optional[dict]:
	"""使用 curl 作为回退方案请求 XHS 用户信息，避免 requests 层面偶发超时问题。"""
	try:
		url = f"{base}/api/v1/xiaohongshu/app/get_user_info"
		cmd = [
			"curl","-sS","-G",url,
			"--data-urlencode",f"user_id={user_id}",
			"-H",f"Authorization: Bearer {api_key}",
			"-H","Accept: application/json",
			"-H","User-Agent: goodgame-xhs-author-fetch/1.0",
		]
		res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
		text = res.stdout.strip()
		if not text:
			return None
		try:
			data = json.loads(text)
		except Exception:
			return None
		return {
			"base_url": base,
			"status_code": 200,
			"method": "GET(curl)",
			"params": {"user_id": user_id},
			"data": data,
		}
	except Exception:
		return None


def request_user_profile_once(api_key: str, user_id: str) -> dict:
	"""调用小红书用户详情接口（App get_user_info）。

	- 文档参考：`https://api.tikhub.io/#/Xiaohongshu-App-API/get_user_info_api_v1_xiaohongshu_app_get_user_info_get`
	- 通过多个常见 TikHub 域名尝试，提升兼容性
	- 参数兼容：userid/user_id/author_id
	"""
	headers = {
		"Authorization": f"Bearer {api_key}",
		"X-API-KEY": api_key,
		"Accept": "application/json",
		"Content-Type": "application/json",
		"User-Agent": "goodgame-xhs-author-fetch/1.0",
	}
	# 兼容不同参数名/方法
	param_variants = [
		{"user_id": user_id},
		{"userid": user_id},
		{"author_id": user_id},
	]
	methods = ["GET", "POST"]
	base_urls = [
		"https://api.tikhub.io",
		"https://open.tikhub.cn",
		"https://tikhub.io",
	]
	last_error = None
	attempt_logs: t.List[str] = []
	for base in base_urls:
		url = f"{base}/api/v1/xiaohongshu/app/get_user_info"
		for params in param_variants:
			for method in methods:
				try:
					if method == "GET":
						resp = requests.get(url, headers=headers, params=params, timeout=(10,60))
					else:
						resp = requests.post(url, headers=headers, json=params, timeout=(10,60))
					print(f"TRY {method} {url} params={params} -> status={resp.status_code}")
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
					msg = f"HTTP {resp.status_code} {method} {url} params={params} resp-snippet={resp.text[:200]}"
					attempt_logs.append(msg)
					last_error = RuntimeError(msg)
				except Exception as exc:
					last_error = exc
					attempt_logs.append(f"EXC {method} {url} params={params} err={exc}")
					continue
		# 如果 requests 未成功，尝试 curl 回退一次（对所有 base）
		fallback = _curl_fetch_user_info(api_key, user_id, base)
		if fallback is not None:
			return fallback
	if last_error:
		# 打印尝试日志，便于排查（stdout）
		for line in attempt_logs:
			print(line)
		raise last_error


def resolve_userid_default() -> str:
	"""确定要使用的小红书 userid。

	优先级：
	1) 环境变量 `XHS_USER_ID`
	2) 一个已知示例："59699f425e87e71130535afa"
	"""
	user_id_env = os.getenv("XHS_USER_ID")
	if user_id_env:
		return user_id_env
	return "59699f425e87e71130535afa"


def main() -> None:
	api_key = load_api_key()
	output_dir = ensure_output_dir()
	user_id = resolve_userid_default()
	result = request_user_profile_once(api_key=api_key, user_id=user_id)
	# 入库：仅 raw_response
	try:
		upsert_author_to_supabase(result)
	except Exception:
		pass
	stamp = time.strftime("%Y%m%d-%H%M%S")
	outfilename = f"xhs_user_info_{stamp}.json"
	outfile = output_dir / outfilename
	with outfile.open("w", encoding="utf-8") as f:
		json.dump(result, f, ensure_ascii=False, indent=2)
	print(str(outfile))


if __name__ == "__main__":
	main()


