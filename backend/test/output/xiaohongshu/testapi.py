import os
import json
import time
import pathlib
import requests


def load_env_var(key: str, default: str | None = None) -> str | None:
	# Try environment first
	val = os.getenv(key)
	if val:
		return val
	# Fallback: search upwards for a .env file
	current = pathlib.Path(__file__).resolve().parent
	for _ in range(10):
		dotenv_path = current / ".env"
		if dotenv_path.exists():
			try:
				for line in dotenv_path.read_text(encoding="utf-8").splitlines():
					line = line.strip()
					if not line or line.startswith("#"):
						continue
					if "=" in line:
						k, v = line.split("=", 1)
						k = k.strip()
						v = v.strip().strip('"').strip("'")
						if k == key:
							return v
			except Exception:
				pass
		current = current.parent
	return default


def ensure_output_dir() -> pathlib.Path:
	output_dir = pathlib.Path(__file__).resolve().parent / "output"
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


def search_xhs_notes_once(keyword: str) -> dict:
	api_key = load_env_var("tikhub_API_KEY")
	if not api_key:
		raise RuntimeError("Missing tikhub_API_KEY in environment or .env file")

	url = "https://api.tikhub.io/api/v1/xiaohongshu/web/search_notes_v3"
	params = {
		"keyword": keyword,
		"page": 1,
		"sort": "general",
		"noteType": "_0",
		# "noteTime": "",  # no limit
	}
	# Try both common auth header styles to maximize compatibility
	headers = {
		"Accept": "application/json",
		"Authorization": f"Bearer {api_key}",
		"X-API-KEY": api_key,
	}

	resp = requests.get(url, params=params, headers=headers, timeout=30)
	resp.raise_for_status()
	return resp.json()


def main() -> None:
	keyword = "海底捞"
	data = search_xhs_notes_once(keyword)
	output_dir = ensure_output_dir()
	timestamp = time.strftime("%Y%m%d-%H%M%S")
	outfile = output_dir / f"xhs_search_v3_{timestamp}.json"
	with outfile.open("w", encoding="utf-8") as f:
		json.dump(data, f, ensure_ascii=False, indent=2)
	print(str(outfile))


if __name__ == "__main__":
	main()


