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


VIDEO_URL = (
	"https://v3-search.douyinvod.com/0aff1f7d548f7843529f4b43ffd16305/68a3fada/video/tos/cn/tos-cn-ve-15/"
	"oQwUPBIc6gGVAkAHQD2BCxYueEL47rlIfX39eo/?a=615883&ch=11&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=996&bt=996&cs=0&ds=6&ft=Xo0TLaZqsQOCCp5Sup-Q6_Mme-rLWa5eFnLN5Sd-IiUFjqkwUBMEq&mime_type=video_mp4&qs=0&rc=Ojg7ZTw2PDllZ2YzMzloNkBpanM3b3E5cmpkeTMzNGkzM0AzMS00NDEtXzIxMV4xL15fYSNjXmU0MmRzYl9gLS1kLS9zcw%3D%3D&btag=c0000e00028000&dy_q=1755573353&feature_id=f0150a16a324336cda5d6dd0b69ed299&l=20250819111552C3E4C9A3D38DE83A2477"
)


def load_api_key() -> str:
	api_key = os.getenv("OPENROUTER_API_KEY")
	if api_key:
		return api_key
	project_root = Path(__file__).resolve().parents[4]
	backend_env = project_root / "backend/.env"
	root_env = project_root / ".env"
	if load_dotenv:
		for env_path in (backend_env, root_env):
			if env_path.exists():
				load_dotenv(env_path)  # type: ignore
				api_key = os.getenv("OPENROUTER_API_KEY")
				if api_key:
					return api_key
	# manual parse as last resort
	for env_path in (backend_env, root_env):
		if env_path.exists():
			for line in env_path.read_text(encoding="utf-8").splitlines():
				if line.strip().startswith("OPENROUTER_API_KEY"):
					return line.split("=", 1)[1].strip()
	raise RuntimeError("OPENROUTER_API_KEY not found")


def ensure_output_dir() -> Path:
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


class VideoAnalysis(BaseModel):
	summary: str
	sentiment: str
	key_points: list[str]
	risks: list[str] | None = None
	brand: str


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
	return client.models.generate_content(
		model=model,
		contents=[
			"你是一名中文舆情分析师。请分析该视频并输出 JSON。",
			file_obj,
		],
		config=types.GenerateContentConfig(
			temperature=0.3,
			response_mime_type="application/json",
			response_schema=VideoAnalysis,
			system_instruction=(
				"以简洁中文输出，字段: summary,sentiment(positive|neutral|negative),"
				"key_points[],risks[],brand='海底捞'。"
			),
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
	model_candidates = ["gemini-2.0-flash-001", "gemini-1.5-flash-8b", "gemini-2.0-pro-exp-02-05"]
	last_err: Exception | None = None
	resp = None
	for model in model_candidates:
		try:
			local_video = Path(__file__).resolve().parent / "video" / "douyin-1.mp4"
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


