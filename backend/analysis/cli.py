from __future__ import annotations
import argparse
import os
import json

# 运行脚本前请确保已激活后端虚拟环境，并设置 GEMINI_API_KEY
# 例如：source backend/.venv/bin/activate

from . import ScreeningService
from .analysis_service import AnalysisService


def main() -> None:
    parser = argparse.ArgumentParser(description="Analysis and screening CLI")
    parser.add_argument("command", choices=["run", "run-one", "analyze"], help="run: 按 unknown 批处理；run-one: 指定 id 初筛一次；analyze: 调用 Gemini 分析并入库")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--id", type=int, default=0, help="帖子 id（run-one / analyze 使用）")
    parser.add_argument("--model", type=str, default=os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-pro"))
    args = parser.parse_args()

    if args.command in ("run", "run-one"):
        svc = ScreeningService(model=args.model)
        if args.command == "run-one":
            if not args.id:
                raise SystemExit("请提供 --id 来指定要初筛的帖子 ID")
            result = svc.process_one_by_id(args.id)
            print({"processed_one": result})
        else:
            # 与当前 ScreeningService 定义对齐：先拿候选，再处理
            rows = svc.fetch_candidates(limit=args.limit, offset=args.offset)
            result = svc.process_batch(rows)
            print({"processed": result})
    elif args.command == "analyze":
        if not args.id:
            raise SystemExit("请提供 --id 来指定要分析的帖子 ID")
        analyzer = AnalysisService()
        out = analyzer.analyze_post(args.id)
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

