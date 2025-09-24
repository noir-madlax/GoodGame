"""视频和评论一起给llm做分析，输入本地的video文件和comments.json文件给llm"""
"""输出视频分析，音频字幕，评论分析等内容用Json格式输出"""
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
VIDEO_FILE = "/Users/rigel/project/goodgame/backend/tikhub_api/downloads/douyin/7383012850161241385/7383012850161241385.mp4"
#这酒你就喝吧 一喝一个不吱声
ID=29
#VIDEO_FILE = "/Users/rigel/project/goodgame/backend/test/output/douyin/video/download_20250819-120621.mp4"
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
	# Added to distinguish source of the event
	source: str | None = None  # "video" | "comment"
	# If source == "comment", include identifiers to locate the comment
	comment_id: str | None = None
	comment_index: int | None = None


class RiskItem(BaseModel):
	timestamp: str
	risk_type: str
	evidence: list[EvidenceItem] | None = None
	recommendation: str | None = None


class TranscriptSegment(BaseModel):
	start: str  # mm:ss 或 hh:mm:ss
	end: str  # mm:ss 或 hh:mm:ss
	text: str
	speaker: str | None = None  # 作者 | 人物 | 旁白 | 不确定


class TranscriptResult(BaseModel):
	segments: list[TranscriptSegment]
	speakers: list[str] | None = None  # 可选：出现过的说话者类别去重列表


class VideoAnalysisV3(BaseModel):
	summary: str
	sentiment: str
	brand: str
	brand_relevance: str | None = None  # "相关" | "疑似相关" | "无关"
	relevance_evidence: str | None = None
	# 新增：整篇内容严重性及其判定理由（与 prompt 对齐，必填）
	total_risk: str  # 取值：高 | 中 | 低
	total_risk_reason: str  # 判定为高/中/低的精炼客观依据
	risk_type_total: list[str]
	key_points: list[str]
	events: list[EventItem]
	# 新增：结构化字幕输出
	transcript: TranscriptResult | None = None


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
	prompt_path = Path(__file__).resolve().parent / "transcript+video+comment-prompt.txt"
	system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

	# Build video part with explicit metadata (fps)
	file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
	mime_type = getattr(file_obj, "mime_type", None) or ("video/x-flv" if local_path.suffix.lower() == ".flv" else "video/mp4")
	video_part = types.Part(
		file_data=types.FileData(file_uri=file_uri, mime_type=mime_type),
		video_metadata=types.VideoMetadata(fps=5),
	)

	return client.models.generate_content(
		model=model,
		contents=[
			video_part,
			"请基于系统提示对视频和评论进行舆情与合规风险分析，并严格输出 JSON；必须包含顶层 transcript（结构化字幕）。",
		],
		config=types.GenerateContentConfig(
			temperature=0.3,
			response_mime_type="application/json",
			response_schema=VideoAnalysisV3,
			system_instruction=system_prompt,
		),
	)


def analyze_with_inputs(
	client: genai.Client,
	video_path: Path,
	model: str,
	comments: list[dict] | None = None,
	include_comment_images: bool = True,
) -> types.GenerateContentResponse:
	file_obj = client.files.upload(file=str(video_path))
	_wait_file_active(client, file_obj.name)
	prompt_path = Path(__file__).resolve().parent / "transcript+video+comment-prompt.txt"
	system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

	file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
	mime_type = getattr(file_obj, "mime_type", None) or ("video/x-flv" if video_path.suffix.lower() == ".flv" else "video/mp4")
	video_part = types.Part(
		file_data=types.FileData(file_uri=file_uri, mime_type=mime_type),
		video_metadata=types.VideoMetadata(fps=5),
	)

	contents: list[types.Part | str] = [
		video_part,
		"以下是与该视频对应的评论数据，请一并纳入分析，并在 events 中标注来源 source=video 或 source=comment。",
	]

	if comments:
		comments_payload = {
			"schema": {
				"id": "string",
				"text": "string",
				"images": ["string (local path or url)"]
			},
			"items": comments,
		}
		contents.append("[COMMENTS_JSON_START]")
		contents.append(json.dumps(comments_payload, ensure_ascii=False))
		contents.append("[COMMENTS_JSON_END]")

		if include_comment_images:
			image_paths: list[str | Path] = []
			for c in comments:
				for img in c.get("images", []) or []:
					image_paths.append(img)
			image_parts = _upload_image_parts(client, image_paths)
			if image_parts:
				contents.append("[COMMENT_IMAGES]")
				contents.extend(image_parts)

	contents.append("请基于系统提示对视频与评论进行舆情与合规风险分析，并严格输出 JSON；必须包含顶层 transcript（结构化字幕）。")

	return client.models.generate_content(
		model=model,
		contents=contents,
		config=types.GenerateContentConfig(
			temperature=0.3,
			response_mime_type="application/json",
			response_schema=VideoAnalysisV3,
			system_instruction=system_prompt,
		),
	)


def _load_comments_json(path: Path, max_comments: int | None = None) -> list[dict]:
	"""Load comments from a JSON file with best-effort field normalization.

	Expected formats (robust):
	- {"comments": [ {"id": str|int, "text": str, "images": [url|path], ...}, ...]}
	- [ {"id": str|int, "text": str, "images": [url|path], ...}, ...]
	- TikHub style nested fields: will attempt to find common keys.
	"""
	try:
		data = json.loads(path.read_text(encoding="utf-8"))
	except Exception as e:
		raise RuntimeError(f"Failed to read comments JSON: {path}: {e}")

	if isinstance(data, dict) and "comments" in data and isinstance(data["comments"], list):
		items = data["comments"]
	elif isinstance(data, list):
		items = data
	else:
		# Fallback: try common container keys
		for k in ("data", "items", "list"):
			if isinstance(data, dict) and isinstance(data.get(k), list):
				items = data[k]
				break
		else:
			raise RuntimeError("Unsupported comments JSON shape. Expect an array or {comments: []}.")

	def _norm(x: dict, idx: int) -> dict:
		cid = str(x.get("id") or x.get("cid") or x.get("comment_id") or x.get("uid") or idx)
		text = x.get("text") or x.get("content") or x.get("desc") or x.get("comment") or ""
		imgs = x.get("images") or x.get("image_urls") or x.get("imgs") or []
		if isinstance(imgs, str):
			imgs = [imgs]
		return {
			"id": cid,
			"text": str(text),
			"images": [str(u) for u in imgs if isinstance(u, (str, Path))],
		}

	normalized = [_norm(it or {}, i) for i, it in enumerate(items)]
	if max_comments is not None and max_comments >= 0:
		normalized = normalized[: max_comments]
	return normalized


def _upload_image_parts(client: genai.Client, images: list[str | Path]) -> list[types.Part]:
	parts: list[types.Part] = []
	for img in images:
		p = Path(img)
		if not p.exists():
			# Skip non-existing local files; remote URLs are not uploaded here
			continue
		file_obj = client.files.upload(file=str(p))
		_wait_file_active(client, file_obj.name)
		mime = getattr(file_obj, "mime_type", None) or "image/jpeg"
		file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
		parts.append(types.Part(file_data=types.FileData(file_uri=file_uri, mime_type=mime)))
	return parts


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
	parser.add_argument("--comments", dest="comments_path", default="", type=str)
	parser.add_argument("--max-comments", dest="max_comments", default="-1", type=str)
	args, _ = parser.parse_known_args()
	if args.api_key_flag:
		api_key = args.api_key_flag

	# Resolve provided path precedence: function param > positional > --file > top-level constant
	candidate_path_str = video_path or args.file or args.file_flag or VIDEO_FILE
	custom_file = Path(candidate_path_str) if candidate_path_str else None

	# Validate file（允许 .mp4 与 .flv）
	if not custom_file.exists():
		raise FileNotFoundError(f"Video file not found: {custom_file}")
	allowed_ext = {".mp4", ".flv"}
	if custom_file.suffix.lower() not in allowed_ext:
		raise ValueError(f"Unsupported file type: {custom_file.suffix}. Expected one of {sorted(allowed_ext)}")

	# Load comments if provided
	comments: list[dict] | None = None
	if args.comments_path:
		cpath = Path(args.comments_path)
		if not cpath.exists():
			raise FileNotFoundError(f"Comments JSON not found: {cpath}")
		try:
			max_c = int(args.max_comments) if args.max_comments else -1
		except Exception:
			max_c = -1
		comments = _load_comments_json(cpath, None if max_c < 0 else max_c)

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
			resp = analyze_with_inputs(client, local_video, model, comments=comments, include_comment_images=True)
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


