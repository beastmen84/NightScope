"""Validate bundled Solar System photographs and category artwork without network I/O."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageStat


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astro_viewer.app.services.object_imagery import (  # noqa: E402
    CATEGORY_IMAGE_KEYS,
    SOLAR_SYSTEM_IMAGE_IDS,
    category_image,
    image_category,
)


def validate_images(root: Path = ROOT) -> tuple[int, int]:
    """Require the complete compact asset family and reject retired shipped photos."""
    app_dir = root / "astro_viewer"
    with (app_dir / "data/object_images_seed.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != len(SOLAR_SYSTEM_IMAGE_IDS) or {row["object_id"] for row in rows} != SOLAR_SYSTEM_IMAGE_IDS:
        raise ValueError("The image seed must contain only the nine Solar System photographs")
    paths = [app_dir / row["image_path"] for row in rows]
    paths += [app_dir / category_image(category)["image_path"] for category in CATEGORY_IMAGE_KEYS]
    for path in paths:
        with Image.open(path) as source:
            source.load()
            if source.format != "JPEG" or source.mode != "RGB" or source.size != (512, 512):
                raise ValueError(f"Invalid normalized image: {path.name}")
            if ImageStat.Stat(source.convert("L")).stddev[0] < 2:
                raise ValueError(f"Blank image: {path.name}")
    actual_category_files = set((app_dir / "resources/images/categories").iterdir())
    if actual_category_files != set(paths[len(rows):]):
        raise ValueError("The category directory must contain exactly the declared artwork")
    retired_dir = app_dir / "resources/images/catalogue"
    if retired_dir.exists() and any(retired_dir.iterdir()):
        raise ValueError("Retired Messier/Caldwell images must not be shipped")
    manifest = json.loads((root / "docs/IMAGE_ASSET_MANIFEST.json").read_text(encoding="utf-8"))
    records = manifest["assets"]
    if (
        manifest["schema_version"] != 1
        or len(records) != len(CATEGORY_IMAGE_KEYS)
        or {record["category"] for record in records} != set(CATEGORY_IMAGE_KEYS)
    ):
        raise ValueError("Category provenance manifest has an invalid inventory")
    for record in records:
        content = (app_dir / category_image(record["category"])["image_path"]).read_bytes()
        if len(content) != record["bytes"] or hashlib.sha256(content).hexdigest() != record["asset_sha256"]:
            raise ValueError(f"Category artwork differs from reviewed manifest: {record['category']}")
    if manifest["total_bytes"] != sum(record["bytes"] for record in records):
        raise ValueError("Category manifest has an invalid size total")
    with (app_dir / "data/catalogue_objects_seed.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if row["tipo"] != "Unclassified object" and image_category(row["tipo"]) == "unclassified":
                raise ValueError(f"Unmapped catalogue type: {row['tipo']}")
    return len(paths), sum(path.stat().st_size for path in paths)


def main() -> int:
    count, size = validate_images()
    print(f"Object imagery validated: {count} assets, {size:,} bytes; no retired cutouts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
