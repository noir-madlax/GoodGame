"""仅图片与标题的多模态分析：
读取抖音图片搜索JSON，筛选指定desc（标题），
下载对应图片，上传至Gemini进行结构化风险与品牌相关性分析，
输出格式与视频版(VideoAnalysisV3)一致。

用法示例：
python3 "test- pic- analyze.py" \
  --json "/Users/rigel/project/goodgame/backend/test/output/douyin/archive/output/douyin_image_search_20250915-172405.json" \
  --title "欢迎光临海底捞。yxjiee_" \
  --max-images 8
"""
#!/usr/bin/env python3
import os
import json
import time
import shutil
import argparse
from pathlib import Path
from typing import Iterable, Optional, Union
import mimetypes

try:
	from dotenv import load_dotenv  # type: ignore
except Exception:
	load_dotenv = None

import urllib.request
import urllib.error

from pydantic import BaseModel
from google import genai
from google.genai import types
import time as _time


# 默认输入文件与目标标题，可通过CLI覆盖
DEFAULT_INPUT_JSON = \
	"/Users/rigel/project/goodgame/backend/test/output/douyin/archive/output/douyin_image_search_20250915-172405.json"
DEFAULT_TARGET_TITLE = "欢迎光临海底捞。yxjiee_"

# 可选：通过环境变量提供API Key
API_KEY = os.getenv("GEMINI_API_KEY", "")


def ensure_output_dir() -> Path:
	output_dir = Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


class EvidenceItem(BaseModel):
	scene_area: str
	subject_type: str
	subject_behavior: str
	objects_involved: Optional[str] = None
	contact_path: Optional[str] = None
	brand_assets: Optional[str] = None
	audio_quote: Optional[str] = None
	visibility: Optional[str] = None
	details: Optional[str] = None





class EventItem(BaseModel):
	timestamp: str
	scene_description: str
	issue: str
	risk_type: Union[list[str], str]
	evidence: Optional[list[EvidenceItem]] = None
	source: Optional[str] = None  # 这里图片用 "image"
	comment_id: Optional[str] = None
	comment_index: Optional[int] = None



class VideoAnalysisV3(BaseModel):
	summary: str
	sentiment: str
	brand: str
	brand_relevance: Optional[str] = None
	relevance_evidence: Optional[str] = None
	risk_type_total: list[str]
	key_points: list[str]
	events: list[EventItem]


def build_client(api_key: str) -> genai.Client:
	return genai.Client(api_key=api_key)


def _to_jsonable(obj):
	"""尽力将对象转换为可序列化JSON结构。"""
	if obj is None or isinstance(obj, (str, int, float, bool)):
		return obj
	if isinstance(obj, (list, tuple, set)):
		return [_to_jsonable(x) for x in obj]
	if isinstance(obj, dict):
		return {str(_to_jsonable(k)): _to_jsonable(v) for k, v in obj.items()}
	if hasattr(obj, "to_dict"):
		try:
			return _to_jsonable(obj.to_dict())
		except Exception:
			pass
	try:
		return _to_jsonable(vars(obj))
	except Exception:
		pass
	try:
		return str(obj)
	except Exception:
		return repr(obj)


def _read_env_key_from_files(paths: list[Path], key: str) -> str:
	"""最小化.env读取器：读取 KEY=VALUE 行。"""
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
					return v.strip().strip('\"\'')
		except Exception:
			pass
	return ""


def _wait_file_active(client: genai.Client, name: str, timeout_sec: int = 120) -> None:
	"""等待上传文件到ACTIVE。"""
	start = _time.time()
	while True:
		info = client.files.get(name=name)
		state = getattr(info, "state", None) or getattr(info, "state", None)
		if str(state).endswith("ACTIVE") or str(state) == "ACTIVE":
			return
		if _time.time() - start > timeout_sec:
			raise TimeoutError(f"File {name} not ACTIVE after {timeout_sec}s (state={state})")
		_time.sleep(2)


def _safe_download(url: str, save_to: Path, timeout: int = 20) -> bool:
	"""下载单张图片到本地，返回是否成功。"""
	try:
		# 简单的UA避免被部分CDN拒绝
		req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
		with urllib.request.urlopen(req, timeout=timeout) as resp:
			if resp.status != 200:
				return False
			data = resp.read()
			save_to.parent.mkdir(parents=True, exist_ok=True)
			save_to.write_bytes(data)
		return True
	except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
		return False


def _choose_best_url(image_item: dict) -> Optional[str]:
	"""为单个 images 元素选择一个最佳URL。

	优先级：download_url_list > url_list；
	扩展名优先：.jpeg/.jpg > .webp > .png > .heic > 其他。
	"""
	def _score(u: str) -> int:
		ul = u.lower()
		if ul.endswith((".jpeg", ".jpg")):
			return 100
		if ul.endswith(".webp"):
			return 90
		if ul.endswith(".png"):
			return 80
		if ul.endswith(".heic"):
			return 70
		return 60

	candidates: list[str] = []
	for key in ("download_url_list", "url_list"):
		lst = image_item.get(key) or []
		if isinstance(lst, list):
			candidates.extend([u for u in lst if isinstance(u, str) and u.startswith("http")])
	if not candidates:
		return None
	return sorted(candidates, key=_score, reverse=True)[0]


def _iter_images_from_json(data: Union[dict, list]) -> Iterable[dict]:
	"""深度遍历，产出包含url_list的图片对象。"""
	if isinstance(data, dict):
		# 常见字段名
		if "images" in data and isinstance(data["images"], list):
			for it in data["images"]:
				if isinstance(it, dict) and (it.get("url_list") or it.get("download_url_list")):
					yield it
		for v in data.values():
			yield from _iter_images_from_json(v)
	elif isinstance(data, list):
		for v in data:
			yield from _iter_images_from_json(v)


def _iter_desc_nodes(data: Union[dict, list]) -> Iterable[str]:
	"""深度遍历，产出desc字段。"""
	if isinstance(data, dict):
		if isinstance(data.get("desc"), str):
			yield data["desc"]
		for v in data.values():
			yield from _iter_desc_nodes(v)
	elif isinstance(data, list):
		for v in data:
			yield from _iter_desc_nodes(v)


def collect_images_and_title(json_path: Path, title_filter: Optional[str] = None, max_images: int = 12) -> tuple[str, list[Path]]:
	"""读取JSON并根据title_filter筛选图片；返回(标题, 本地图片路径列表)。

	策略：
	- 若存在与title_filter完全相等的desc所在节点，则采集该节点及其子树内的images；
	- 否则收集全局全部images，并将标题设为title_filter或"未提供标题"。
	- 对每个图片对象，从download_url_list/url_list中选择可访问的URL，下载成功的加入集合；
	- 最多下载max_images张。
	"""
	data = json.loads(json_path.read_text(encoding="utf-8"))

	# 粗匹配：找到包含目标desc的最小字典节点集合
	matched_subtrees: list[dict] = []

	def _find_matches(node):
		if not isinstance(node, dict):
			return
		if title_filter and node.get("desc") == title_filter:
			matched_subtrees.append(node)
		return

	def _walk(n):
		if isinstance(n, dict):
			_find_matches(n)
			for v in n.values():
				_walk(v)
		elif isinstance(n, list):
			for v in n:
				_walk(v)

	_walk(data)

	images_candidates: list[dict] = []
	if matched_subtrees:
		for st in matched_subtrees:
			images_candidates.extend(list(_iter_images_from_json(st)))
		title = title_filter or ""
	else:
		images_candidates.extend(list(_iter_images_from_json(data)))
		# 如果没有精确匹配，尝试从全局desc中选择第一个作为标题
		title = (title_filter or next(iter(_iter_desc_nodes(data)), "未提供标题"))

	# 以 uri 去重；每个 images 元素选一个最佳URL
	seen_uri: set[str] = set()
	chosen_urls: list[str] = []
	for img in images_candidates:
		uri = str(img.get("uri") or "")
		if uri and uri in seen_uri:
			continue
		u = _choose_best_url(img)
		if not u:
			continue
		if uri:
			seen_uri.add(uri)
		chosen_urls.append(u)
		if len(chosen_urls) >= max_images:
			break

	# 下载到本地临时目录
	base_dir = ensure_output_dir() / "images"
	stamp = time.strftime("%Y%m%d-%H%M%S")
	case_dir = base_dir / f"case_{stamp}"
	case_dir.mkdir(parents=True, exist_ok=True)

	local_paths: list[Path] = []
	for idx, url in enumerate(chosen_urls):
		ext = ".jpg"
		if ".png" in url:
			ext = ".png"
		elif ".webp" in url:
			ext = ".webp"
		elif ".jpeg" in url:
			ext = ".jpeg"
		elif ".heic" in url:
			ext = ".heic"
		p = case_dir / f"img_{idx:03d}{ext}"
		ok = _safe_download(url, p)
		if ok and p.exists() and p.stat().st_size > 0:
			local_paths.append(p)

	return title, local_paths


def _upload_image_parts(client: genai.Client, images: list[Path]) -> list[types.Part]:
	parts: list[types.Part] = []
	for p in images:
		if not p.exists():
			continue
		# 由于 SDK 不接受 mime_type 参数且会基于扩展名推断，
		# 对无法识别扩展名的文件，复制为 .jpg 临时文件再上传。
		ext = p.suffix.lower()
		upload_path = p
		if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
			upload_path = p.with_suffix(".jpg")
			try:
				shutil.copyfile(p, upload_path)
			except Exception:
				upload_path = p  # 回退原文件

		file_obj = client.files.upload(file=str(upload_path))
		_wait_file_active(client, file_obj.name)
		# 由后端确定 mime_type，此处仅透传
		mime = getattr(file_obj, "mime_type", None) or "image/jpeg"
		file_uri = getattr(file_obj, "uri", None) or getattr(file_obj, "file_uri", None)
		parts.append(types.Part(file_data=types.FileData(file_uri=file_uri, mime_type=mime)))
	return parts


def analyze_images_with_title(client: genai.Client, image_paths: list[Path], title: str, model: str) -> types.GenerateContentResponse:
	prompt_path = Path(__file__).resolve().parent / "pic-prompt.txt"
	system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

	contents: list[types.Part | str] = []
	contents.append("以下为图片集合与对应标题文本，请进行结构化风险与品牌相关性分析，并严格输出JSON。")
	contents.append("[TITLE_START]")
	contents.append(title)
	contents.append("[TITLE_END]")

	image_parts = _upload_image_parts(client, image_paths)
	if image_parts:
		contents.append("[IMAGES]")
		contents.extend(image_parts)

	# 将将要发送的输入落盘，便于审计
	try:
		output_root = ensure_output_dir()
		# 尽可能复用当前最新的case目录：按图片所在父目录推断
		case_dir = image_paths[0].parent if image_paths else (output_root / "images" / f"case_{time.strftime('%Y%m%d-%H%M%S')}")
		case_dir.mkdir(parents=True, exist_ok=True)
		inputs_path = case_dir / "inputs_for_llm.json"
		inputs_dump = {
			"model": model,
			"system_instruction": system_prompt,
			"title": title,
			"parts": [
				{"type": "text", "value": "以下为图片集合与对应标题文本，请进行结构化风险与品牌相关性分析，并严格输出JSON。"},
				{"type": "text", "value": "[TITLE_START]"},
				{"type": "text", "value": title},
				{"type": "text", "value": "[TITLE_END]"},
				{"type": "text", "value": "[IMAGES]"},
			] + [
				{"type": "file", "file_uri": getattr(p.file_data, 'file_uri', None), "mime_type": getattr(p.file_data, 'mime_type', None)}
				for p in image_parts
			],
		}
		inputs_path.write_text(json.dumps(inputs_dump, ensure_ascii=False, indent=2), encoding="utf-8")
	except Exception:
		pass

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


def main() -> None:
	# 解析参数
	parser = argparse.ArgumentParser()
	parser.add_argument("--json", dest="json_path", default=DEFAULT_INPUT_JSON, type=str)
	parser.add_argument("--title", dest="title_filter", default=DEFAULT_TARGET_TITLE, type=str)
	parser.add_argument("--max-images", dest="max_images", default=12, type=int)
	parser.add_argument("--api-key", dest="api_key_flag", default="", type=str)
	args = parser.parse_args()

	# 解析API Key
	api_key = args.api_key_flag or (os.getenv("GEMINI_API_KEY") or API_KEY)
	if not api_key and load_dotenv:
		# 构建候选 .env 路径：
		# 1) 当前脚本同目录 .env
		# 2) 从当前路径向上搜索名为 backend 的目录，并加载其中的 .env
		# 3) 仿照视频脚本的相对位置尝试若干父级目录
		current = Path(__file__).resolve()
		backend_envs: list[Path] = []
		for ancestor in [current.parent] + list(current.parents):
			if ancestor.name == "backend":
				backend_envs.append(ancestor / ".env")
		candidates: list[Path] = [
			current.parent / ".env",
			# 直接 backend/.env（若找到backend目录）
			*backend_envs,
			# 兼容旧逻辑的若干尝试
			current.parents[5] / ".env" if len(current.parents) > 5 else current.parent / "nonexistent",
			current.parents[6] / ".env" if len(current.parents) > 6 else current.parent / "nonexistent",
		]
		for env_path in candidates:
			try:
				if env_path and env_path.exists():
					load_dotenv(env_path)  # type: ignore
					api_key = os.getenv("GEMINI_API_KEY")
					if api_key:
						break
			except Exception:
				pass
	if not api_key:
		# 手工解析兜底
		current = Path(__file__).resolve()
		backend_envs: list[Path] = []
		for ancestor in [current.parent] + list(current.parents):
			if ancestor.name == "backend":
				backend_envs.append(ancestor / ".env")
		api_key = _read_env_key_from_files([
			current.parent / ".env",
			*backend_envs,
			current.parents[5] / ".env" if len(current.parents) > 5 else current.parent / "nonexistent",
			current.parents[6] / ".env" if len(current.parents) > 6 else current.parent / "nonexistent",
		], "GEMINI_API_KEY") or api_key
	if not api_key:
		raise RuntimeError("GEMINI_API_KEY 未找到。请通过 --api-key、环境变量或在脚本同目录 .env 提供。")

	json_file = Path(args.json_path)
	if not json_file.exists():
		raise FileNotFoundError(f"JSON文件不存在: {json_file}")

	client = build_client(api_key)
	output_dir = ensure_output_dir()
	stamp = time.strftime("%Y%m%d-%H%M%S")
	out_json = output_dir / f"douyin_pic_gemini_{stamp}.json"
	raw_out = output_dir / f"douyin_pic_gemini_{stamp}_raw.json"

	# 收集图片与标题
	title, local_images = collect_images_and_title(json_file, args.title_filter, args.max_images)
	if not local_images:
		raise RuntimeError("未能收集到可用的图片URL或下载失败。请检查输入JSON或增大 --max-images。")

	debug_params = {
		"model": "gemini-2.5-pro",
		"title": title,
		"image_count": len(local_images),
		"request_config": {
			"temperature": 0.3,
			"response_mime_type": "application/json",
			"response_schema": "VideoAnalysisV3(pydantic)",
		}
	}
	print(json.dumps({"request": debug_params}, ensure_ascii=False, indent=2))

	resp = analyze_images_with_title(client, local_images, title, model="gemini-2.5-pro")

	# 保存原始响应
	raw_bundle = {
		"request": debug_params,
		"raw_response_type": type(resp).__name__,
		"raw_response": _to_jsonable(resp),
		"raw_text": getattr(resp, "text", None),
	}
	raw_out.write_text(json.dumps(raw_bundle, ensure_ascii=False, indent=2), encoding="utf-8")

	# 解析JSON结果
	result_text = getattr(resp, "text", None)
	try:
		parsed = json.loads(result_text) if result_text else {"raw_text": result_text}
	except Exception:
		parsed = {"raw_text": result_text}

	out_json.write_text(json.dumps({
		"model": resp.model_version if hasattr(resp, "model_version") else "gemini",
		"result": parsed
	}, ensure_ascii=False, indent=2), encoding="utf-8")
	print(str(out_json))


if __name__ == "__main__":
	main()


