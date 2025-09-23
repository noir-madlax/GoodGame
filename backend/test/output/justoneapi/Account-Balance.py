import json
import os
import time
from urllib.parse import urlencode

import requests


def fetch_account_balance(token: str) -> dict:
    """
    调用 justoneapi 的 Account Balance 接口，返回 JSON。
    文档: http://47.117.133.51:30015/user/get-balance?token=...
    """
    base_url = "http://47.117.133.51:30015/user/get-balance"
    params = {"token": token}
    url = f"{base_url}?{urlencode(params)}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def save_output(payload: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(output_dir, f"account-balance-{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def main():
    token = os.environ.get("JUSTONEAPI_TOKEN", "")
    if not token:
        # 允许直接在此处硬编码来自用户的临时 token，便于一次性验证
        token = "wp7KhV0G"

    data = fetch_account_balance(token)
    out_path = save_output(
        data,
        output_dir=os.path.join(
            os.path.dirname(__file__),
            "output",
        ),
    )
    print(out_path)


if __name__ == "__main__":
    main()


