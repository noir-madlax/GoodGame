"""用来把数据库的评论弄成结构化的Json文件，然后才能给LLM和视频一起做分析"""
import os
import sys
import subprocess
from pathlib import Path
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

"""Ensure local orm package (backend/tikhub_api/orm) is importable."""
_CUR_DIR = Path(__file__).resolve().parent
# .../backend/test/output/douyin -> parents[0]=.../backend/test/output, [1]=.../backend/test, [2]=.../backend
_BACKEND_DIR = _CUR_DIR.parents[2]
_TIKHUB_API_DIR = _BACKEND_DIR / "tikhub_api"
if str(_TIKHUB_API_DIR) not in sys.path:
    sys.path.insert(0, str(_TIKHUB_API_DIR))

# Load environment variables from backend/.env if present and normalize common keys
def _load_env_vars() -> None:
    loaded = False
    try:
        from dotenv import load_dotenv
        # override=True to ensure values from backend/.env take effect when running via IDE
        if load_dotenv(_BACKEND_DIR / ".env", override=True):
            loaded = True
    except Exception:
        pass

    # Fallback manual parse if python-dotenv is unavailable
    if not loaded:
        env_path = _BACKEND_DIR / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().split("#", 1)[0].strip().strip('\"\'')
                    if k and v and os.getenv(k) is None:
                        os.environ[k] = v
            except Exception:
                pass

    # Accept multiple aliases and normalize to SUPABASE_URL and SUPABASE_KEY
    def _first(keys):
        for key in keys:
            val = os.getenv(key)
            if val:
                return val
        return None

    url_aliases = [
        "SUPABASE_URL",
        "SupabaseUrl",
        "NEXT_PUBLIC_SUPABASE_URL",
        "VITE_SUPABASE_URL",
        "SUPABASE_PROJECT_URL",
        "SUPABASE_API_URL",
    ]
    key_aliases = [
        "SUPABASE_KEY",
        "SupabaseKey",
        "SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "VITE_SUPABASE_ANON_KEY",
        "SUPABASE_PUBLIC_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_API_KEY",
    ]

    if not os.getenv("SUPABASE_URL"):
        url_val = _first(url_aliases)
        if url_val:
            os.environ["SUPABASE_URL"] = url_val
    if not os.getenv("SUPABASE_KEY"):
        key_val = _first(key_aliases)
        if key_val:
            os.environ["SUPABASE_KEY"] = key_val

_load_env_vars()

try:
    from orm.supabase_client import get_client
    from orm.comment_repository import CommentRepository
except ModuleNotFoundError as _e:
    # Auto-install backend requirements if missing (e.g., supabase)
    if "supabase" in str(_e):
        _REQ = _BACKEND_DIR / "requirements.txt"
        if _REQ.exists():
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(_REQ)])
            from orm.supabase_client import get_client
            from orm.comment_repository import CommentRepository
        else:
            raise
    else:
        raise

# ====== Global parameters for easy editing in Cursor IDE ======
# Set the post id to export. Modify this constant and click "Run Python File".
POST_ID: int = 29
# Output root directory (no per-title subfolder per your request)
OUTPUT_ROOT: str = os.path.join("backend", "test", "output", "douyin", "output")


def _slugify(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\n\r\t]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    # Keep CJK and most unicode letters; replace path-unfriendly chars
    value = re.sub(r'[\\/<>:"|?*]+', "_", value)
    return value[:64] if len(value) > 64 else value


def _isoformat(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.isoformat()


def _fetch_post_row(post_id: int) -> Optional[Dict[str, Any]]:
    client = get_client()
    resp = (
        client.table("gg_platform_post")
        .select("id, platform, platform_item_id, title")
        .eq("id", post_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def _fetch_all_comments(post_id: int, page_size: int = 100) -> List[Dict[str, Any]]:
    comments: List[Dict[str, Any]] = []
    offset = 0
    while True:
        batch = CommentRepository.list_by_post(post_id=post_id, limit=page_size, offset=offset)
        if not batch:
            break
        for c in batch:
            comments.append({
                "id": c.id,
                "post_id": c.post_id,
                "platform": c.platform,
                "platform_comment_id": c.platform_comment_id,
                "parent_comment_id": c.parent_comment_id,
                "parent_platform_comment_id": c.parent_platform_comment_id,
                "author_id": c.author_id,
                "author_name": c.author_name,
                "author_avatar_url": c.author_avatar_url,
                "content": c.content,
                "like_count": c.like_count,
                "reply_count": c.reply_count,
                "published_at": _isoformat(c.published_at),
            })
        if len(batch) < page_size:
            break
        offset += page_size
    return comments


def _build_nested_comments(flat_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[int, Dict[str, Any]] = {}
    roots: List[Dict[str, Any]] = []

    for c in flat_comments:
        c_copy = dict(c)
        c_copy["replies"] = []
        if isinstance(c_copy.get("id"), int):
            by_id[c_copy["id"]] = c_copy

    for c in flat_comments:
        c_id = c.get("id")
        parent_id = c.get("parent_comment_id")
        node = by_id.get(c_id)
        if not node:
            continue
        if parent_id and parent_id in by_id:
            by_id[parent_id]["replies"].append(node)
        else:
            roots.append(node)

    # Sort replies (optional): reverse chronological by published_at
    def _sort_key(x: Dict[str, Any]) -> Any:
        # Use published_at for ordering if present (not included in final output)
        return x.get("published_at") or ""

    def _sort_tree(nodes: List[Dict[str, Any]]):
        nodes.sort(key=_sort_key, reverse=True)
        for n in nodes:
            _sort_tree(n["replies"])

    _sort_tree(roots)
    return roots


def export_comments(post_id: int, output_root: str) -> str:
    post = _fetch_post_row(post_id)
    if not post:
        raise RuntimeError(f"Post id {post_id} not found")

    flat_comments = _fetch_all_comments(post_id)
    nested_comments = _build_nested_comments(flat_comments)

    # Write directly under OUTPUT_ROOT per request (no title subfolder)
    out_dir = output_root
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, "comments.json")
    def _strip_fields(node: Dict[str, Any]) -> Dict[str, Any]:
        # Keep only requested fields, remove author_name/published_at/platform/platform_comment_id
        return {
            "content": node.get("content"),
            "like_count": node.get("like_count", 0),
            "reply_count": node.get("reply_count", 0),
            "replies": [
                _strip_fields(child) for child in node.get("replies", [])
            ],
        }

    payload = {
        "post": {
            "id": post.get("id"),
            "title": post.get("title"),
        },
        "comments": [_strip_fields(n) for n in nested_comments],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return out_path


def main() -> None:
    # Validate env for Supabase client early
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")

    out_path = export_comments(POST_ID, OUTPUT_ROOT)
    print(out_path)


if __name__ == "__main__":
    main()


