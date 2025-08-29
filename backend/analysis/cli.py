from __future__ import annotations
import argparse
import os

# 运行脚本前请确保已激活后端虚拟环境，并设置 OPENROUTER_API_KEY
# 例如：source backend/.venv/bin/activate

from . import ScreeningService


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen posts via OpenRouter and heuristics")
    parser.add_argument("command", choices=["run"], help="run: process a batch of init posts")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--model", type=str, default=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"))
    args = parser.parse_args()

    if args.command == "run":
        svc = ScreeningService(model=args.model)
        result = svc.process_batch(limit=args.limit, offset=args.offset)
        print({"processed": result})


if __name__ == "__main__":
    main()

