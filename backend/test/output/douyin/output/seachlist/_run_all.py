import subprocess
from pathlib import Path

ROOT = Path(__file__).parent


def is_brand_dir(p: Path) -> bool:
    if not p.is_dir():
        return False
    # must contain at least one of the three jsons
    for suffix in ("__差评.json", "__踩雷.json", "__脏.json"):
        if any(p.glob(f"*{suffix}")):
            return True
    return False


def main():
    brand_dirs = [p for p in ROOT.iterdir() if is_brand_dir(p)]
    successes = []
    failures = []
    for brand in sorted(brand_dirs):
        script_path = brand / "summary_brand.py"
        # ensure script exists. If not, copy from 海底捞 as template
        if not script_path.exists():
            template = ROOT / "海底捞" / "summary_brand.py"
            script_path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        try:
            subprocess.run(["python3", str(script_path)], check=True)
            if (brand / "summary.json").exists():
                successes.append(brand.name)
            else:
                failures.append(brand.name)
        except Exception:
            failures.append(brand.name)

    log_path = ROOT / "_batch_run.log"
    with log_path.open("w", encoding="utf-8") as f:
        f.write("OK:\n")
        for name in successes:
            f.write(f"  {name}\n")
        f.write("FAIL:\n")
        for name in failures:
            f.write(f"  {name}\n")


if __name__ == "__main__":
    main()


