import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv, find_dotenv

# 尝试自动加载离当前运行目录最近的 .env（向上查找）
load_dotenv(find_dotenv())

_client: Optional[Client] = None


def get_client() -> Client:
    """Get a singleton Supabase client using environment variables.

    Required envs:
      - SUPABASE_URL
      - SUPABASE_KEY  (anon/service role; use service role on server side)
    """
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY env vars")

    _client = create_client(url, key)
    return _client

