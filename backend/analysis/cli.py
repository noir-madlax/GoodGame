from __future__ import annotations
import argparse
import os

# 运行脚本前请确保已激活后端虚拟环境，并设置 OPENROUTER_API_KEY
# 例如：source backend/.venv/bin/activate

from . import ScreeningService


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen posts via OpenRouter and heuristics")
    parser.add_argument("command", choices=["run", "run-one"], help="run: 按 unknown 批处理；run-one: 指定 id 初筛一次")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--id", type=int, default=0, help="要初筛的帖子 id（配合 run-one 使用）")
    parser.add_argument("--model", type=str, default=os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-pro"))
    args = parser.parse_args()

    svc = ScreeningService(model=args.model)
    if args.command == "run-one":
        if not args.id:
            raise SystemExit("请提供 --id 来指定要初筛的帖子 ID")
        result = svc.process_one_by_id(args.id)
        print({"processed_one": result})
    elif args.command == "run":
        # 与当前 ScreeningService 定义对齐：先拿候选，再处理
        rows = svc.fetch_candidates(limit=args.limit, offset=args.offset)
        result = svc.process_batch(rows)
        print({"processed": result})


if __name__ == "__main__":
    main()

