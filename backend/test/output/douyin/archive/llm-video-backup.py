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

# REQUIRED: set the target video file here if not supplying via CLI
# You can modify this constant directly to change the target file.
#⼩狗已经沉浸在海底捞⽆法⾃拔了-已分析
#VIDEO_FILE = "/Users/rigel/project/goodgame/backend/tikhub_api/downloads/douyin/7383012850161241385/7383012850161241385.mp4"
#这酒你就喝吧 一喝一个不吱声
ID=29
VIDEO_FILE = "/Users/rigel/project/goodgame/backend/tikhub_api/downloads/douyin/7499608775142608186/7499608775142608186.mp4"
#下次请善待我们小吃房好吗🥺#海底捞 #回答我-已分析
#VIDEO_FILE = "/Users/rigel/project/goodgame/backend/tikhub_api/downloads/douyin/7505583378596646180/7505583378596646180.mp4"

# Optional: set Gemini API key here to avoid VSCode Run Python not inheriting shell env
API_KEY = os.getenv("GEMINI_API_KEY", "")


def ensure_output_dir() -> Path:
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


class EvidenceItem(BaseModel):
	scene_area: str
	subject_type: str
	subject_behavior: str
	objects_involved: str | None = None
	contact_path: str | None = None
	brand_assets: str | None = None
	audio_quote: str | None = None
	visibility: str | None = None
	details: str | None = None


class EventItem(BaseModel):
	timestamp: str
	scene_description: str
	audio_transcript: str | None = None
	issue: str
	risk_type: list[str] | str
	evidence: list[EvidenceItem] | None = None


class RiskItem(BaseModel):
	timestamp: str
	risk_type: str
	evidence: list[EvidenceItem] | None = None
	recommendation: str | None = None


class VideoAnalysisV3(BaseModel):
	summary: str
	sentiment: str
	brand: str
	risk_type_total: list[str]
	key_points: list[str]
	events: list[EventItem]


def build_client(api_key: str) -> genai.Client:
	return genai.Client(api_key=api_key)



def _to_jsonable(obj):
	"""Best-effort conversion of arbitrary objects into JSON-serializable structures."""
	# Primitives
	if obj is None or isinstance(obj, (str, int, float, bool)):
		return obj
	# Containers
	if isinstance(obj, (list, tuple, set)):
		return [_to_jsonable(x) for x in obj]
	if isinstance(obj, dict):
		return {str(_to_jsonable(k)): _to_jsonable(v) for k, v in obj.items()}
	# Library-provided conversions
	if hasattr(obj, "to_dict"):
		try:
			return _to_jsonable(obj.to_dict())
		except Exception:
			pass
	# Fallback to __dict__
	try:
		return _to_jsonable(vars(obj))
	except Exception:
		pass
	# Last resort
	try:
		return str(obj)
	except Exception:
		return repr(obj)


def _read_env_key_from_files(paths: list[Path], key: str) -> str:
	"""Minimal .env reader: reads KEY=VALUE lines without external deps."""
	for p in paths:
		try:
			if not p.exists():
				continue
			for line in p.read_text(encoding="utf-8").splitlines():
				line = line.strip()
				if not line or line.startswith("#"):
					continue
				if "=" not in line:
					continue
				k, v = line.split("=", 1)
				if k.strip() == key:
					return v.strip().strip('"\'')
		except Exception:
			pass
	return ""


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

	# Build video part with explicit metadata (fps)
	file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
	mime_type = getattr(file_obj, "mime_type", None) or "video/mp4"
	video_part = types.Part(
		file_data=types.FileData(file_uri=file_uri, mime_type=mime_type),
		video_metadata=types.VideoMetadata(fps=5),
	)

	return client.models.generate_content(
		model=model,
		contents=[
			video_part,
			"请基于系统提示对视频进行舆情与合规风险分析，并严格输出 JSON。",
		],
		config=types.GenerateContentConfig(
			temperature=0.3,
			response_mime_type="application/json",
			response_schema=VideoAnalysisV3,
			system_instruction=system_prompt,
		),
	)


def main(video_path: str | None = None, api_key_param: str | None = None) -> None:
	# Resolve GEMINI_API_KEY with precedence suitable for VSCode Run Python
	api_key = api_key_param or (os.getenv("GEMINI_API_KEY") or API_KEY)
	# Try dotenv if available
	if not api_key and load_dotenv:
		candidates: list[Path] = [
			Path(__file__).resolve().parent / ".env",
			Path(__file__).resolve().parents[4] / "backend/.env",
			Path(__file__).resolve().parents[4] / ".env",
		]
		for env_path in candidates:
			try:
				if env_path.exists():
					load_dotenv(env_path)  # type: ignore
					api_key = os.getenv("GEMINI_API_KEY")
					if api_key:
						break
			except Exception:
				pass
	# Manual .env parsing fallback when python-dotenv missing or failed
	if not api_key:
		api_key = _read_env_key_from_files([
			Path(__file__).resolve().parent / ".env",
			Path(__file__).resolve().parents[4] / "backend/.env",
			Path(__file__).resolve().parents[4] / ".env",
		], "GEMINI_API_KEY") or api_key
	if not api_key:
		raise RuntimeError("GEMINI_API_KEY not found. Provide via --api-key, API_KEY constant, or .env next to script.")

	client = build_client(api_key)
	output_dir = ensure_output_dir()
	stamp = time.strftime("%Y%m%d-%H%M%S")
	outfile = output_dir / f"douyin_video_gemini_{stamp}.json"

	# Try multiple models and input methods to avoid quota/feature limits
	model_candidates = ["gemini-2.5-pro"]
	#model_candidates = ["gemini-2.0-flash-001", "gemini-1.5-flash-8b", "gemini-2.0-pro-exp-02-05"]
	last_err: Exception | None = None
	resp = None

	# Param/CLI only: the video path must be explicitly provided (no ENV or fallbacks)
	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument("file", nargs="?", default="", type=str)
	parser.add_argument("--file", dest="file_flag", default="", type=str)
	parser.add_argument("--api-key", dest="api_key_flag", default="", type=str)
	args, _ = parser.parse_known_args()
	if args.api_key_flag:
		api_key = args.api_key_flag

	# Resolve provided path precedence: function param > positional > --file > top-level constant
	candidate_path_str = video_path or args.file or args.file_flag or VIDEO_FILE
	custom_file = Path(candidate_path_str) if candidate_path_str else None

	# Validate file
	if not custom_file.exists():
		raise FileNotFoundError(f"Video file not found: {custom_file}")
	if custom_file.suffix.lower() != ".mp4":
		raise ValueError(f"Unsupported file type: {custom_file.suffix}. Expected .mp4")

	# Emit request parameters for debugging
	debug_params = {
		"model_candidates": ["gemini-2.5-pro"],
		"video_file": str(custom_file),
		"request_config": {
			"temperature": 0.3,
			"response_mime_type": "application/json",
			"response_schema": "VideoAnalysisV3(pydantic)",
			"video_metadata": {"fps": 5},
			"contents_order": ["video", "text"],
		},
	}
	print(json.dumps({"request": debug_params}, ensure_ascii=False, indent=2))
	for model in model_candidates:
		try:
			local_video = custom_file
			resp = analyze_with_local_file(client, local_video, model)
			break
		except Exception as e:
			last_err = e
	if resp is None and last_err is not None:
		raise last_err

	# Persist raw response and parsed content for debugging
	raw_outfile = output_dir / f"douyin_video_gemini_{stamp}_raw.json"
	# Best-effort raw dump including non-serializable fields
	raw_bundle = {
		"request": debug_params,
		"raw_response_type": type(resp).__name__,
		"raw_response": _to_jsonable(resp),
		"raw_text": getattr(resp, "text", None),
	}
	with raw_outfile.open("w", encoding="utf-8") as rf:
		json.dump(raw_bundle, rf, ensure_ascii=False, indent=2)

	# Parse JSON string from response.text (already JSON via response_mime_type)
	result_text = getattr(resp, "text", None)
	try:
		parsed = json.loads(result_text) if result_text else {"raw_text": result_text}
	except Exception:
		parsed = {"raw_text": result_text}

	with outfile.open("w", encoding="utf-8") as f:
		json.dump({"model": resp.model_version if hasattr(resp, "model_version") else "gemini",
			"result": parsed}, f, ensure_ascii=False, indent=2)
	print(str(outfile))


if __name__ == "__main__":
	main()


