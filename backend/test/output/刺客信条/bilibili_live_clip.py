#!/usr/bin/env python3
import os
import argparse
import time
import json
import shutil
import subprocess
from pathlib import Path
import requests


def ensure_output_dir() -> Path:
	"""确保输出目录存在：在当前脚本目录下创建 `output/` 目录。"""
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


def analyze_stream(url: str, sample_seconds: int = 5, estimate_seconds: int | None = None) -> dict:
	"""
	基于短时采样估算直播流的平均码率，并据此估算给定时长的体积大小。

	参数：
	- url: 直播 flv 播放地址
	- sample_seconds: 采样秒数，默认 5 秒
	- estimate_seconds: 可选，要估算的时长（秒），例如 4 小时=14400 秒

	返回：包含 HEAD 信息、采样结果、平均码率（kbps）与估算大小（MB/GB）的字典
	"""
	result: dict[str, object] = {}

	# 1) HEAD 请求（直播流常见无固定 Content-Length，仅作参考）
	try:
		head = requests.head(url, timeout=10, allow_redirects=True)
		result["head_status"] = head.status_code
		result["content_length"] = head.headers.get("Content-Length")
		result["transfer_encoding"] = head.headers.get("Transfer-Encoding")
		result["content_type"] = head.headers.get("Content-Type")
	except Exception as exc:
		result["head_error"] = str(exc)

	# 2) 流式采样下载 sample_seconds 秒，估算平均码率
	bytes_read = 0
	start = time.time()
	deadline = start + max(1, int(sample_seconds))
	try:
		with requests.get(url, stream=True, timeout=15) as r:
			for chunk in r.iter_content(chunk_size=8192):
				if not chunk:
					continue
				bytes_read += len(chunk)
				if time.time() >= deadline:
					break
	except Exception as exc:
		result["sample_error"] = str(exc)

	elapsed = max(0.001, time.time() - start)
	bytes_per_sec = bytes_read / elapsed
	kbps = bytes_per_sec * 8.0 / 1000.0
	mb_per_min = bytes_per_sec * 60.0 / (1024.0 * 1024.0)

	result.update({
		"sample_seconds": round(elapsed, 2),
		"sample_bytes": bytes_read,
		"avg_kbps": round(kbps, 2),
		"est_MB_per_min": round(mb_per_min, 2),
	})

	if estimate_seconds is not None and estimate_seconds > 0:
		est_bytes = bytes_per_sec * estimate_seconds
		est_mb = est_bytes / (1024.0 * 1024.0)
		est_gb = est_mb / 1024.0
		result.update({
			"estimate_seconds": int(estimate_seconds),
			"estimate_MB": round(est_mb, 2),
			"estimate_GB": round(est_gb, 3),
		})

	return result


def download_clip(url: str, duration: int, output_dir: Path, filename_prefix: str = "bilibili_live_clip") -> Path:
	"""
	仅下载直播流的前 N 秒，依赖本机 ffmpeg。

	参数：
	- url: 播放地址
	- duration: 下载时长（秒）
	- output_dir: 输出目录
	- filename_prefix: 文件名前缀
	"""
	ffmpeg = shutil.which("ffmpeg")
	if not ffmpeg:
		raise RuntimeError("未找到 ffmpeg，请安装后再试。")

	stamp = time.strftime("%Y%m%d-%H%M%S")
	outfile = output_dir / f"{filename_prefix}_{stamp}_{duration}s.flv"

	cmd = [
		ffmpeg,
		"-y",
		"-i",
		url,
		"-t",
		str(int(duration)),
		"-c",
		"copy",
		str(outfile),
	]

	# 执行下载
	subprocess.run(cmd, check=True)
	return outfile


def main() -> None:
	"""
	命令行工具：
	- 支持对直播流 URL 进行采样分析并输出估算
	- 支持仅下载前 N 秒到本地 `output/` 目录

	示例：
	python3 bilibili_live_clip.py \\
	  --url "https://.../live_xxx.flv?..." \\
	  --analyze --sample 5 --estimate 14400 \\
	  --download --duration 120
	"""
	parser = argparse.ArgumentParser(description="Analyze and clip bilibili live FLV stream")
	parser.add_argument("--url", required=True, help="直播 flv URL")
	parser.add_argument("--analyze", action="store_true", help="启用分析模式：HEAD + 采样估算码率与大小")
	parser.add_argument("--sample", type=int, default=5, help="分析采样秒数，默认5s")
	parser.add_argument("--estimate", type=int, default=None, help="按给定秒数估算大小，例如四小时=14400")
	parser.add_argument("--download", action="store_true", help="下载前 N 秒片段")
	parser.add_argument("--duration", type=int, default=120, help="下载时长(秒)，默认120s")
	args = parser.parse_args()

	output_dir = ensure_output_dir()

	# 分析（可选或自动）
	# 若显式 --analyze，则使用传入的 --estimate；
	# 若未显式 --analyze 但需要下载，则自动进行一次采样，并按下载时长进行估算输出。
	auto_analysis_done = False
	if args.analyze:
		analysis = analyze_stream(url=args.url, sample_seconds=args.sample, estimate_seconds=args.estimate)
		print(json.dumps(analysis, ensure_ascii=False, indent=2))
		auto_analysis_done = True

	# 下载（可选）
	if args.download:
		if not auto_analysis_done:
			analysis = analyze_stream(url=args.url, sample_seconds=args.sample, estimate_seconds=(args.estimate or args.duration))
			print(json.dumps(analysis, ensure_ascii=False, indent=2))
		try:
			outfile = download_clip(url=args.url, duration=args.duration, output_dir=output_dir)
			print(str(outfile))
		except subprocess.CalledProcessError as e:
			print("下载失败：", e)
			raise

	if not args.analyze and not args.download:
		print("未指定操作。可加 --analyze 或 --download。")


if __name__ == "__main__":
	main()


