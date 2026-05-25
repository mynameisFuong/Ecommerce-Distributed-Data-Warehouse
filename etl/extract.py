import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from .config import PROJECT_ROOT, RAW_DIR, RAW_FILES
except ImportError:
    from config import PROJECT_ROOT, RAW_DIR, RAW_FILES


REQUIRED_RAW_KEYS = [
    "orders",
    "order_items",
    "payments",
    "reviews",
    "customers",
    "sellers",
    "products",
    "category_translation",
]


def extract(raw_dir: Path = RAW_DIR, output_path: Path | None = None) -> dict:
    missing = []
    files = []

    for key in REQUIRED_RAW_KEYS:
        filename = RAW_FILES[key]
        path = raw_dir / filename
        if not path.exists():
            missing.append(str(path))
            continue
        files.append(
            {
                "key": key,
                "filename": filename,
                "path": str(path),
                "size_bytes": path.stat().st_size,
            }
        )

    if missing:
        raise FileNotFoundError(
            "Missing required raw CSV files:\n" + "\n".join(missing)
        )

    manifest = {
        "pipeline": "ecommerce_distributed_warehouse",
        "step": "extract",
        "status": "success",
        "raw_dir": str(raw_dir),
        "file_count": len(files),
        "files": files,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if output_path is None:
        output_path = PROJECT_ROOT / "data" / "processed" / "extract_manifest.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Extract validation completed: {len(files)} files")
    print(f"Wrote manifest: {output_path}")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Olist raw CSV files and write an extract manifest."
    )
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument(
        "--output-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "extract_manifest.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    extract(args.raw_dir, args.output_path)