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


def extract(raw_dir = RAW_DIR, output_path = None):
    missing_files = []
    file_info = []

    for key in REQUIRED_RAW_KEYS:
        filename = RAW_FILES[key]
        file_path = raw_dir / filename

        file_info.append({
            "key": key,
            "filename": filename,
            "path": str(file_path),
            "size_bytes": file_path.stat().st_size
        })
    
    manifest = {
        "pipeline": "ecommerce_distributed_warehouse",
        "step": "extract",
        "status": "success",
        "raw_dir": str(raw_dir),
        "file_counts": len(file_info),
        "file": file_info,
        "create_at": datetime.now(timezone.utc).isoformat()
    }

    if output_path is None:
        output_path = PROJECT_ROOT / "data" / "processed" / "extract_manifest.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    return manifest


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Thư mục chứa file nguồn"
    )

    parser.add_argument(
        "--output-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "extract_manifest.json",
        help="Đường dẫn lưu file manifest"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    extract(args.raw_dir, args.output_path)