#!/usr/bin/env python3
import os
import json
import time
import argparse
import subprocess
import shutil
import requests
import datetime as dt
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
#OOM_ID = os.getenv("BILI_ROOM_ID", "1792362541")
ROOM_ID = os.getenv("BILI_ROOM_ID", "23307253")

#ROOM_ID = os.getenv("BILI_ROOM_ID", "26584172")
BASE_URLS = [
	"https://api.tikhub.io",
	"https://open.tikhub.cn",
	"https://tikhub.io",
]
DOCS = "https://api.tikhub.io/#/Bilibili-Web-API/fetch_collect_folders_api_v1_bilibili_web_fetch_live_videos_get"
# ========================


def request_live_videos(api_key: str, room_id: str) -> dict:
	"""调用 Bilibili 直播间视频流接口并返回 JSON。

	接口：GET /api/v1/bilibili/web/fetch_live_videos
	参数：room_id
	"""
	headers = {"Authorization": f"Bearer {api_key}"}
	params = {"room_id": room_id}
	last_error = None
	for base in BASE_URLS:
		url = f"{base}/api/v1/bilibili/web/fetch_live_videos"
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
	"""以房间号发起一次 Bilibili 直播间视频流请求，保存 JSON，并可选下载。"""
	parser = argparse.ArgumentParser(description="Fetch bilibili live videos (and optionally download)")
	parser.add_argument("--room", dest="room_id", default=os.getenv("BILI_ROOM_ID", ROOM_ID), help="直播间 room_id")
	parser.add_argument("--download", dest="download", action="store_true", help="同意后下载视频流")
	parser.add_argument("--index", dest="index", type=int, default=1, help="选择 durl 列表中的第几个地址(从1开始)")
	parser.add_argument("--duration", dest="duration", type=int, default=120, help="下载时长(秒)，默认120s")
	parser.add_argument("--analyze", dest="analyze", action="store_true", help="分析模式：HEAD + 采样若干秒估算码率与大小")
	parser.add_argument("--sample", dest="sample", type=int, default=5, help="分析模式采样秒数，默认5秒")
	args = parser.parse_args()

	api_key = load_api_key()
	output_dir = ensure_output_dir()
	room_id = str(args.room_id)
	result = request_live_videos(api_key=api_key, room_id=room_id)
	stamp = time.strftime("%Y%m%d-%H%M%S")
	out_name = f"bilibili_live_videos_{room_id}_{stamp}.json"
	out_file = output_dir / out_name
	with out_file.open("w", encoding="utf-8") as f:
		json.dump(result, f, ensure_ascii=False, indent=2)
	print(str(out_file))

	# 展示可用流地址
	try:
		durls = result["data"]["data"]["data"]["durl"]
	except Exception:
		print("未找到 durl 列表，请检查返回JSON。")
		return
	print("可用流地址(durl):")
	for i, item in enumerate(durls, start=1):
		print(f"[{i}] {item.get('url', '')}")

	# 分析模式：对所选 URL 做 HEAD 与采样
	if args.analyze:
		idx = max(1, min(args.index, len(durls)))
		url = durls[idx - 1].get("url")
		print(f"\n开始分析第 {idx} 个地址：{url}")
		analysis = {}
		# 1) HEAD 请求
		try:
			head = requests.head(url, timeout=10, allow_redirects=True)
			analysis["head_status"] = head.status_code
			analysis["content_length"] = head.headers.get("Content-Length")
			analysis["transfer_encoding"] = head.headers.get("Transfer-Encoding")
			analysis["content_type"] = head.headers.get("Content-Type")
		except Exception as exc:
			analysis["head_error"] = str(exc)
		# 2) 采样下载 N 秒，估算码率
		bytes_read = 0
		start = time.time()
		deadline = start + max(1, args.sample)
		try:
			with requests.get(url, stream=True, timeout=15) as r:
				for chunk in r.iter_content(chunk_size=8192):
					if not chunk:
						continue
					bytes_read += len(chunk)
					if time.time() >= deadline:
						break
		except Exception as exc:
			analysis["sample_error"] = str(exc)
		elapsed = max(0.001, time.time() - start)
		bytes_per_sec = bytes_read / elapsed
		kbps = bytes_per_sec * 8.0 / 1000.0
		mb_per_min = bytes_per_sec * 60.0 / (1024.0 * 1024.0)
		analysis.update({
			"sample_seconds": round(elapsed, 2),
			"sample_bytes": bytes_read,
			"avg_kbps": round(kbps, 2),
			"est_MB_per_min": round(mb_per_min, 2),
		})
		# 打印结论
		print("分析结果：")
		print(json.dumps(analysis, ensure_ascii=False, indent=2))
		print("结论：直播 flv 为持续推流，理论上大小随直播增长，不存在固定总大小；通常无法在下载前准确获知总时长/大小，只能基于当前码率做估算。")
		# 分析完成后不继续下载，等待人工确认
		return

	if not args.download:
		print("已仅获取URL。如需下载：在同目录运行： python3 bilibili_live_videos.py --download --index 1 --duration 120")
		return

	# 下载逻辑（需本机有 ffmpeg）
	ffmpeg = shutil.which("ffmpeg")
	if not ffmpeg:
		print("未找到 ffmpeg，无法下载。请安装后重试。")
		return
	idx = max(1, min(args.index, len(durls)))
	url = durls[idx - 1].get("url")
	if not url:
		print("选定项没有url。")
		return
	video_name = f"bilibili_live_{room_id}_{stamp}_i{idx}.flv"
	video_path = output_dir / video_name
	cmd = [
		ffmpeg,
		"-y",
		"-i",
		url,
		"-t",
		str(args.duration),
		"-c",
		"copy",
		str(video_path),
	]
	print("开始下载：", " ".join(cmd))
	try:
		subprocess.run(cmd, check=True)
		print("下载完成：", str(video_path))
	except subprocess.CalledProcessError as e:
		print("下载失败：", e)


if __name__ == "__main__":
	main()


