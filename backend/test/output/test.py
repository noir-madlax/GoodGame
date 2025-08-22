import asyncio
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import requests


PROJECT_ROOT = "/Users/rigel/project/goodgame"
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
OUTPUT_DIR = os.path.join(BACKEND_DIR, "test", "output")
ENV_PATH = os.path.join(BACKEND_DIR, ".env")


def read_env_api_key(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f".env not found at {path}")
    api_key: Optional[str] = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("tikhub_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break
    if not api_key:
        raise RuntimeError("tikhub_API_KEY is missing in backend/.env")
    return api_key


def pick_first_play_url(video_obj: Dict[str, Any]) -> Optional[str]:
    # Common Douyin schema from App V3
    try:
        url_list = (
            video_obj.get("video", {})
            .get("play_addr", {})
            .get("url_list", [])
        )
        if url_list:
            return url_list[0]
    except Exception:
        pass

    # Some responses may place url under play_addr.url
    try:
        direct_url = (
            video_obj.get("video", {})
            .get("play_addr", {})
            .get("url")
        )
        if isinstance(direct_url, str) and direct_url.startswith("http"):
            return direct_url
    except Exception:
        pass
    return None


def extract_videos_from_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Try common paths
    if "aweme_list" in data and isinstance(data["aweme_list"], list):
        return data["aweme_list"]
    if "data" in data and isinstance(data["data"], dict):
        inner = data["data"]
        if "aweme_list" in inner and isinstance(inner["aweme_list"], list):
            return inner["aweme_list"]
        if "list" in inner and isinstance(inner["list"], list):
            return inner["list"]
    # General search may return list with aweme_info nested
    if isinstance(data, dict):
        container = data.get("data") or data
        if isinstance(container, list):
            vids: List[Dict[str, Any]] = []
            for item in container:
                if isinstance(item, dict) and "aweme_info" in item:
                    v = item.get("aweme_info")
                    if isinstance(v, dict):
                        vids.append(v)
            if vids:
                return vids
    return []


def normalize_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name[:200]


async def download_file(url: str, dest_path: str, headers: Optional[Dict[str, str]] = None) -> None:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=600)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers, allow_redirects=True) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1 << 14):
                    if chunk:
                        f.write(chunk)


def try_http_search(api_key: str, keyword: str, count: int = 1) -> Tuple[List[Dict[str, Any]], str]:
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    candidates = [
        # Primary domain
        "https://api.tikhub.io/douyin/search/video",
        "https://api.tikhub.io/douyin/search",
        "https://api.tikhub.io/douyin/app/v3/search",
        # Mainland China acceleration domain
        "https://api.tikhub.dev/douyin/search/video",
        "https://api.tikhub.dev/douyin/search",
        "https://api.tikhub.dev/douyin/app/v3/search",
    ]

    # Try both param styles often seen in docs
    param_sets = [
        {"keyword": keyword, "count": count, "offset": 0},
        {"q": keyword, "count": count, "offset": 0},
    ]

    last_error: Optional[str] = None
    for url in candidates:
        for params in param_sets:
            try:
                r = requests.get(url, params=params, headers=headers, timeout=60)
                if r.status_code == 200:
                    body = r.json()
                    videos = extract_videos_from_response(body)
                    if videos:
                        return videos, url
                else:
                    last_error = f"{url} -> HTTP {r.status_code}"
            except Exception as e:
                last_error = f"{url} -> {e}"
    raise RuntimeError(f"Search failed. Last error: {last_error}")


def try_http_web_search_verbose(api_key: str, keyword: str, count: int = 10) -> Tuple[List[Dict[str, Any]], str]:
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    base_candidates = ["https://api.tikhub.dev", "https://api.tikhub.io"]
    paths = [
        "/api/v1/douyin/web/fetch_video_search_result",
        "/api/v1/douyin/web/fetch_general_search_result",
    ]
    params_common = {
        "keyword": keyword,
        "offset": 0,
        "count": count,
        "sort_type": "0",
        "publish_time": "0",
        "filter_duration": "0",
        "content_type": "video",
    }
    last_detail = None
    for base in base_candidates:
        for path in paths:
            url = base + path
            try:
                r = requests.get(url, params=params_common, headers=headers, timeout=60)
                try:
                    body = r.json()
                except Exception:
                    body = {"text": r.text}
                if r.status_code == 200:
                    videos = extract_videos_from_response(body)
                    if videos:
                        return videos, url
                last_detail = {"url": r.url, "status": r.status_code, "body": body}
            except Exception as e:
                last_detail = {"url": url, "error": str(e)}
    raise RuntimeError(f"Web search failed: {last_detail}")


async def main() -> None:
    api_key = read_env_api_key(ENV_PATH)
    keyword = "海底捞"
    want_count = 3

    # Prefer SDK if available, otherwise fallback to HTTP
    videos: List[Dict[str, Any]] = []
    used_endpoint = ""
    try:
        from tikhub import Client  # type: ignore

        async def sdk_try(base_url: str) -> Tuple[List[Dict[str, Any]], str]:
            client = Client(base_url=base_url, api_key=api_key)
            # Try multiple parameter combinations commonly accepted by the API
            for sort_type in ["0", "1", "2"]:
                for publish_time in ["0", "7", "30"]:
                    for filter_duration in ["0", "1", "2"]:
                        try:
                            resp = await client.DouyinAppV3.fetch_video_search_result(
                                keyword=keyword,
                                offset=0,
                                count=max(1, want_count),
                                sort_type=sort_type,
                                publish_time=publish_time,
                                filter_duration=filter_duration,
                            )  # type: ignore
                            vids = extract_videos_from_response(resp)
                            if vids:
                                return vids, f"SDK:{base_url}:DouyinAppV3.fetch_video_search_result"
                        except Exception:
                            pass

            for content_type in ["video", "general", "aweme"]:
                for sort_type in ["0", "1", "2"]:
                    for publish_time in ["0", "7", "30"]:
                        for filter_duration in ["0", "1", "2"]:
                            try:
                                resp = await client.DouyinAppV3.fetch_general_search_result(
                                    keyword=keyword,
                                    offset=0,
                                    count=max(1, want_count),
                                    sort_type=sort_type,
                                    publish_time=publish_time,
                                    filter_duration=filter_duration,
                                    content_type=content_type,
                                )  # type: ignore
                                vids = extract_videos_from_response(resp)
                                if vids:
                                    return vids, f"SDK:{base_url}:DouyinAppV3.fetch_general_search_result"
                            except Exception:
                                pass

            try:
                resp = await client.DouyinAppV3.fetch_user_search_result(
                    keyword=keyword,
                    offset=0,
                    count=max(1, want_count),
                    douyin_user_fans="0",
                    douyin_user_type="0",
                )  # type: ignore
                vids = extract_videos_from_response(resp)
                if vids:
                    return vids, f"SDK:{base_url}:DouyinAppV3.fetch_user_search_result"
            except Exception:
                pass

            # Try DouyinWeb as well (its search result often returns play URLs)
            try:
                resp = await client.DouyinWeb.fetch_video_search_result(
                    keyword=keyword,
                    count=max(1, want_count),
                    offset=0,
                    sort_type="0",
                    publish_time="0",
                    filter_duration="0",
                )  # type: ignore
                vids = extract_videos_from_response(resp)
                if vids:
                    return vids, f"SDK:{base_url}:DouyinWeb.fetch_video_search_result"
            except Exception:
                pass
            return [], ""

        # Mainland China: prefer .dev first
        videos, used_endpoint = await sdk_try("https://api.tikhub.dev")
        if not videos:
            videos, used_endpoint = await sdk_try("https://api.tikhub.io")
    except Exception:
        try:
            videos, used_endpoint = try_http_web_search_verbose(api_key, keyword, count=max(10, want_count))
        except Exception:
            videos, used_endpoint = try_http_search(api_key, keyword, count=want_count)

    if not videos:
        raise RuntimeError("No videos found for keyword '海底捞'")

    first = videos[0]
    aweme_id = str(first.get("aweme_id") or first.get("id") or "douyin_video")
    play_url = pick_first_play_url(first)
    if not play_url:
        # Some responses may include download_addr
        play_url = (
            first.get("video", {})
            .get("download_addr", {})
            .get("url_list", [None])
        )[0]
    if not play_url:
        raise RuntimeError("Unable to extract play/download URL from the first video result")

    filename = normalize_filename(f"douyin_{aweme_id}.mp4")
    dest = os.path.join(OUTPUT_DIR, filename)
    print(json.dumps({
        "endpoint": used_endpoint,
        "aweme_id": aweme_id,
        "download_url": play_url,
        "output_path": dest,
    }, ensure_ascii=False, indent=2))

    # Some providers require header spoofing for media; try no header first.
    try:
        await download_file(play_url, dest)
    except Exception:
        # Retry with a common user-agent header
        await download_file(
            play_url,
            dest,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Referer": "https://www.douyin.com/",
            },
        )

    print(f"Saved: {dest}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(2)

