import json
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent
OUTPUT_FILE = BASE_DIR / "summary.json"


def discover_input_files(target_dir: Path):
    candidates = []
    for suffix in ("__差评.json", "__踩雷.json", "__脏.json"):
        candidates.extend(sorted(target_dir.glob(f"*{suffix}")))
    return candidates


def load_records(file_path: Path):
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("extracted", [])


def month_key_from_create_time(create_time: str) -> str:
    # format: YYMMDD-HHMM -> month YYMM
    if not create_time or len(create_time) < 4:
        return "unknown"
    return create_time[:4]


def summarize_directory(target_dir: Path):
    input_files = discover_input_files(target_dir)
    seen_aweme_ids = set()
    all_items_count = 0
    deduped_items = []

    for fp in input_files:
        items = load_records(fp)
        all_items_count += len(items)
        for item in items:
            aweme_id = item.get("aweme_id")
            if not aweme_id:
                continue
            if aweme_id in seen_aweme_ids:
                continue
            seen_aweme_ids.add(aweme_id)
            deduped_items.append(item)

    total_unique = len(deduped_items)

    per_month_counts = defaultdict(int)
    per_month_engagement = defaultdict(int)
    total_engagement = 0

    for item in deduped_items:
        month_key = month_key_from_create_time(item.get("create_time", ""))
        per_month_counts[month_key] += 1
        engagement = item.get("engagement_sum") or 0
        if isinstance(engagement, str):
            try:
                engagement = int(engagement)
            except Exception:
                engagement = 0
        per_month_engagement[month_key] += engagement
        total_engagement += engagement

    per_month_counts = dict(sorted(per_month_counts.items(), key=lambda x: x[0]))
    per_month_engagement = dict(sorted(per_month_engagement.items(), key=lambda x: x[0]))

    summary = {
        "total_videos_before_dedup": all_items_count,
        "total_unique_videos": total_unique,
        "engagement_sum_total": total_engagement,
        "per_month_counts": per_month_counts,
        "per_month_engagement_sum": per_month_engagement,
    }

    with (target_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    summarize_directory(BASE_DIR)


if __name__ == "__main__":
    main()


