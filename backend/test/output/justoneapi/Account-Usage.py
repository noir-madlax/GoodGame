import json
import os
import time
from urllib.parse import urlencode

import requests


def fetch_api_usage(token: str, year: int, month: int) -> dict:
    """
    调用 justoneapi 的 API Usage 接口，返回 JSON。
    文档路径：/user/get-record?token=&orderYear=&orderMonth=
    """
    base_url = "http://47.117.133.51:30015/user/get-record"
    params = {"token": token, "orderYear": year, "orderMonth": month}
    url = f"{base_url}?{urlencode(params)}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def save_output(payload: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(output_dir, f"api-usage-{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def main():
    token = os.environ.get("JUSTONEAPI_TOKEN", "")
    if not token:
        token = "wp7KhV0G"

    # 默认查询当前年月
    now = time.localtime()
    year = now.tm_year
    month = now.tm_mon

    data = fetch_api_usage(token, year, month)
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


