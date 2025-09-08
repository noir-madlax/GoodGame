import json
import os
import sys
from typing import Any, Dict, Optional

try:
    from supabase import create_client, Client
except ImportError:
    print("[错误] 缺少 supabase 依赖，请先安装：pip install supabase", file=sys.stderr)
    sys.exit(1)


def load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"缺少环境变量: {name}")
    return val


def ensure_row_exists(client: Client, post_id: int) -> int:
    resp = client.table("gg_video_analysis").select("id").eq("post_id", post_id).execute()
    if resp.data:
        return resp.data[0]["id"]
    # 如不存在，创建一条仅含 post_id 的记录
    insert_resp = client.table("gg_video_analysis").insert({"post_id": post_id}).execute()
    return insert_resp.data[0]["id"]


def update_json_fields(
    client: Client,
    post_id: int,
    comments_json: Optional[Dict[str, Any]],
    transcript_json: Optional[Dict[str, Any]],
) -> None:
    payload: Dict[str, Any] = {}
    if comments_json is not None:
        payload["comments_json"] = comments_json
    if transcript_json is not None:
        payload["transcript_json"] = transcript_json
    if not payload:
        return
    client.table("gg_video_analysis").update(payload).eq("post_id", post_id).execute()


def fetch_and_verify(client: Client, post_id: int) -> Dict[str, Any]:
    resp = client.table("gg_video_analysis").select("id, post_id, comments_json, transcript_json").eq("post_id", post_id).single().execute()
    row = resp.data or {}
    comments = (row.get("comments_json") or {}).get("comments") or []
    segments = (row.get("transcript_json") or {}).get("segments") or []
    return {
        "id": row.get("id"),
        "post_id": row.get("post_id"),
        "comments_top_level_count": len(comments),
        "transcript_segment_count": len(segments),
    }


def main() -> None:
    # 环境变量（推荐从外部注入）
    supabase_url = get_env("SUPABASE_URL")
    supabase_key = get_env("SUPABASE_ANON_KEY")

    # 目标 post_id（“下次请善待我们小吃房好吗”）
    post_id = int(os.getenv("GG_TARGET_POST_ID", "4"))

    # 本地文件路径（绝对路径）
    comments_path = "/Users/rigel/project/goodgame/backend/test/output/douyin/output/prd/#下次请善待我们小吃房好吗🥺#海底捞 #回答我/comments.json"
    transcript_path = "/Users/rigel/project/goodgame/backend/test/output/音频字幕提取/output/douyin_video_gemini_20250905-161103.json"

    # 读取 JSON
    comments_obj = load_json(comments_path)
    transcript_obj_full = load_json(transcript_path)
    transcript_obj = transcript_obj_full.get("result", {}).get("transcript", {})
    if not transcript_obj:
        raise ValueError("字幕 JSON 中缺少 result.transcript 字段")

    # 建立客户端
    client: Client = create_client(supabase_url, supabase_key)

    # 确保行存在
    _ = ensure_row_exists(client, post_id)

    # 更新两个 JSONB 字段
    update_json_fields(client, post_id, comments_obj, transcript_obj)

    # 校验
    verify = fetch_and_verify(client, post_id)
    print(json.dumps({"verify": verify}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


