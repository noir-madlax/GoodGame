#!/usr/bin/env python3
import os
import json
import time
from pathlib import Path

try:
	from dotenv import load_dotenv  # type: ignore
except Exception:
	load_dotenv = None

from pydantic import BaseModel
from google import genai
from google.genai import types
import time as _time
import argparse


VIDEO_URL = (
	"https://v3-search.douyinvod.com/0aff1f7d548f7843529f4b43ffd16305/68a3fada/video/tos/cn/tos-cn-ve-15/"
	"oQwUPBIc6gGVAkAHQD2BCxYueEL47rlIfX39eo/?a=615883&ch=11&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=996&bt=996&cs=0&ds=6&ft=Xo0TLaZqsQOCCp5Sup-Q6_Mme-rLWa5eFnLN5Sd-IiUFjqkwUBMEq&mime_type=video_mp4&qs=0&rc=Ojg7ZTw2PDllZ2YzMzloNkBpanM3b3E5cmpkeTMzNGkzM0AzMS00NDEtXzIxMV4xL15fYSNjXmU0MmRzYl9gLS1kLS9zcw%3D%3D&btag=c0000e00028000&dy_q=1755573353&feature_id=f0150a16a324336cda5d6dd0b69ed299&l=20250819111552C3E4C9A3D38DE83A2477"
)


def ensure_output_dir() -> Path:
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


class TimelineItem(BaseModel):
	timestamp: str
	scene_description: str
	audio_transcript: str | None = None
	issue: str
	risk_type: list[str] | str
	severity: int | None = None
	evidence: str | None = None


class RiskItem(BaseModel):
	timestamp: str
	risk_type: str
	evidence: str | None = None
	recommendation: str | None = None


class VideoAnalysis(BaseModel):
	summary: str
	sentiment: str
	brand: str
	timeline: list[TimelineItem]
	key_points: list[str]
	risks: list[RiskItem] | None = None


def build_client(api_key: str) -> genai.Client:
	return genai.Client(api_key=api_key)



def _wait_file_active(client: genai.Client, name: str, timeout_sec: int = 120) -> None:
	"""Poll file state until ACTIVE or timeout."""
	start = _time.time()
	while True:
		info = client.files.get(name=name)
		state = getattr(info, "state", None) or getattr(info, "state", None)
		if str(state).endswith("ACTIVE") or str(state) == "ACTIVE":
			return
		if _time.time() - start > timeout_sec:
			raise TimeoutError(f"File {name} not ACTIVE after {timeout_sec}s (state={state})")
		_time.sleep(2)


def analyze_with_local_file(client: genai.Client, local_path: Path, model: str) -> types.GenerateContentResponse:
	file_obj = client.files.upload(file=str(local_path))
	# Wait until file is ACTIVE before use
	_wait_file_active(client, file_obj.name)
	# Load system prompt from txt next to this script
	prompt_path = Path(__file__).resolve().parent / "videoprompt.txt"
	system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
	return client.models.generate_content(
		model=model,
		contents=[
			"请基于系统提示对视频进行舆情与合规风险分析，并严格输出 JSON。",
			file_obj,
		],
		config=types.GenerateContentConfig(
			temperature=0.3,
			response_mime_type="application/json",
			response_schema=VideoAnalysis,
			system_instruction=system_prompt,
		),
	)


def main() -> None:
	# Switch to official Gemini SDK and GEMINI_API_KEY
	api_key = os.getenv("GEMINI_API_KEY")
	if not api_key and load_dotenv:
		project_root = Path(__file__).resolve().parents[4]
		for env_path in (project_root / "backend/.env", project_root / ".env"):
			if env_path.exists():
				load_dotenv(env_path)  # type: ignore
				api_key = os.getenv("GEMINI_API_KEY")
	if not api_key:
		raise RuntimeError("GEMINI_API_KEY not found")

	client = build_client(api_key)
	output_dir = ensure_output_dir()
	stamp = time.strftime("%Y%m%d-%H%M%S")
	outfile = output_dir / f"douyin_video_gemini_{stamp}.json"

	# Try multiple models and input methods to avoid quota/feature limits
	model_candidates = ["gemini-2.5-pro"]
	#model_candidates = ["gemini-2.0-flash-001", "gemini-1.5-flash-8b", "gemini-2.0-pro-exp-02-05"]
	last_err: Exception | None = None
	resp = None

	# Optional CLI: custom local video file
	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument("--file", dest="file", default="", type=str)
	args, _ = parser.parse_known_args()
	custom_file = Path(args.file) if args.file else None
	for model in model_candidates:
		try:
			local_video = custom_file if custom_file else (Path(__file__).resolve().parent / "video" / "douyin-1.mp4")
			resp = analyze_with_local_file(client, local_video, model)
			break
		except Exception as e:
			last_err = e
	if resp is None and last_err is not None:
		raise last_err

	# Parse clean JSON string from response.text (already JSON via response_mime_type)
	result_text = resp.text
	try:
		parsed = json.loads(result_text)
	except Exception:
		parsed = {"raw_text": result_text}

	with outfile.open("w", encoding="utf-8") as f:
		json.dump({"model": resp.model_version if hasattr(resp, "model_version") else "gemini",
			"result": parsed}, f, ensure_ascii=False, indent=2)
	print(str(outfile))


if __name__ == "__main__":
	main()


