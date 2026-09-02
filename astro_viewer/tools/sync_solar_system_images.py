"""Download, normalize, verify, and index curated NASA/JPL object imagery."""

from __future__ import annotations

import argparse
import csv
import io
import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image, ImageStat, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[2]
IMAGE_SEED_PATH = ROOT / "astro_viewer" / "data" / "object_images_seed.csv"
OUTPUT_DIR = ROOT / "astro_viewer" / "resources" / "images" / "solar_system"
IMAGE_SIZE = 512
CONTENT_SIZE = 480
MEDIA_TERMS = "NASA/JPL media; use subject to NASA and JPL image use policies"
SEED_FIELDS = [
    "object_id",
    "image_path",
    "thumbnail_path",
    "attribution",
    "source_url",
    "license",
    "verified",
]


@dataclass(frozen=True)
class SolarSystemImage:
    object_id: str
    pia_id: str
    source_url: str
    attribution: str
    source_crop: tuple[int, int, int, int] | None = None

    @property
    def download_url(self) -> str:
        return (
            f"https://images-assets.nasa.gov/image/{self.pia_id}/{self.pia_id}~orig.jpg"
        )

    @property
    def path(self) -> Path:
        return OUTPUT_DIR / f"{self.object_id}.jpg"

    @property
    def relative_path(self) -> str:
        return f"resources/images/solar_system/{self.object_id}.jpg"


IMAGES = (
    SolarSystemImage(
        "sun",
        "PIA26681",
        "https://science.nasa.gov/photojournal/image-of-sun-from-nasas-solar-dynamics-observatory/",
        "NASA/GSFC/Solar Dynamics Observatory",
        # Remove the instrument timestamp while retaining the full solar limb and corona.
        (128, 0, 3968, 3840),
    ),
    SolarSystemImage(
        "moon",
        "PIA00405",
        "https://science.nasa.gov/photojournal/earths-moon/",
        "NASA/JPL/USGS",
    ),
    SolarSystemImage(
        "mercury",
        "PIA10189",
        "https://science.nasa.gov/photojournal/mercury-in-color/",
        "NASA/Johns Hopkins University Applied Physics Laboratory/Carnegie Institution of Washington",
    ),
    SolarSystemImage(
        "venus",
        "PIA23791",
        "https://science.nasa.gov/photojournal/venus-from-mariner-10/",
        "NASA/JPL-Caltech",
        # The original contains two panels; Figure B is the contrast-enhanced cloud view.
        (1149, 0, 2245, 1096),
    ),
    SolarSystemImage(
        "mars",
        "PIA00407",
        "https://science.nasa.gov/photojournal/global-color-views-of-mars/",
        "NASA/JPL/USGS",
    ),
    SolarSystemImage(
        "jupiter",
        "PIA04866",
        "https://science.nasa.gov/resource/cassini-jupiter-portrait/",
        "NASA/JPL/Space Science Institute",
    ),
    SolarSystemImage(
        "saturn",
        "PIA11141",
        "https://science.nasa.gov/image-detail/amf-pia11141/",
        "NASA/JPL/Space Science Institute",
    ),
    SolarSystemImage(
        "uranus",
        "PIA18182",
        "https://science.nasa.gov/photojournal/uranus-as-seen-by-nasas-voyager-2/",
        "NASA/JPL-Caltech",
    ),
    SolarSystemImage(
        "neptune",
        "PIA01492",
        "https://science.nasa.gov/photojournal/neptune-full-disk-view/",
        "NASA/JPL",
    ),
)


def _normalize(content: bytes, image: SolarSystemImage) -> Image.Image:
    try:
        with Image.open(io.BytesIO(content)) as source:
            source.load()
            normalized = source.convert("RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise RuntimeError(
            f"{image.object_id}: NASA did not return a valid image"
        ) from exc

    if image.source_crop:
        left, top, right, bottom = image.source_crop
        if (
            left < 0
            or top < 0
            or right > normalized.width
            or bottom > normalized.height
        ):
            raise RuntimeError(
                f"{image.object_id}: crop {image.source_crop} exceeds source size {normalized.size}"
            )
        normalized = normalized.crop(image.source_crop)

    normalized.thumbnail((CONTENT_SIZE, CONTENT_SIZE), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), "black")
    offset = (
        (IMAGE_SIZE - normalized.width) // 2,
        (IMAGE_SIZE - normalized.height) // 2,
    )
    canvas.paste(normalized, offset)
    return canvas


def _validate_file(image: SolarSystemImage) -> None:
    try:
        with Image.open(image.path) as source:
            source.load()
            if source.format != "JPEG":
                raise RuntimeError(
                    f"{image.object_id}: expected JPEG, got {source.format}"
                )
            if source.size != (IMAGE_SIZE, IMAGE_SIZE):
                raise RuntimeError(
                    f"{image.object_id}: unexpected dimensions {source.size}"
                )
            if source.mode != "RGB":
                raise RuntimeError(
                    f"{image.object_id}: expected RGB, got {source.mode}"
                )
            if ImageStat.Stat(source.convert("L")).stddev[0] < 2.0:
                raise RuntimeError(f"{image.object_id}: image appears blank")
    except (OSError, UnidentifiedImageError) as exc:
        raise RuntimeError(f"{image.object_id}: unreadable JPEG") from exc


def _download(image: SolarSystemImage, *, force: bool) -> str:
    if image.path.exists() and not force:
        _validate_file(image)
        return "cached"

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(
                image.download_url,
                timeout=60,
                headers={"User-Agent": "NightScope Solar System asset sync/1.0"},
            )
            response.raise_for_status()
            normalized = _normalize(response.content, image)
            image.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = image.path.with_suffix(".jpg.part")
            normalized.save(
                temporary,
                format="JPEG",
                quality=92,
                optimize=True,
                progressive=True,
            )
            os.replace(temporary, image.path)
            _validate_file(image)
            return "downloaded"
        except (OSError, requests.RequestException, RuntimeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(
        f"{image.object_id}: download failed: {last_error}"
    ) from last_error


def _seed_row(image: SolarSystemImage) -> dict[str, str]:
    return {
        "object_id": image.object_id,
        "image_path": image.relative_path,
        "thumbnail_path": image.relative_path,
        "attribution": image.attribution,
        "source_url": image.source_url,
        "license": MEDIA_TERMS,
        "verified": "1",
    }


def _seed_source_urls() -> dict[str, str]:
    with IMAGE_SEED_PATH.open("r", encoding="utf-8", newline="") as file:
        return {
            row["object_id"]: row.get("source_url", "") for row in csv.DictReader(file)
        }


def _write_seed() -> None:
    with IMAGE_SEED_PATH.open("r", encoding="utf-8", newline="") as file:
        existing = list(csv.DictReader(file))

    replacements = {image.object_id: _seed_row(image) for image in IMAGES}
    written_ids: set[str] = set()
    rows = []
    for row in existing:
        object_id = row["object_id"]
        replacement = replacements.get(object_id)
        rows.append(replacement or row)
        if replacement:
            written_ids.add(object_id)
    rows = [
        *(
            replacements[image.object_id]
            for image in IMAGES
            if image.object_id not in written_ids
        ),
        *rows,
    ]

    temporary = IMAGE_SEED_PATH.with_suffix(".csv.part")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SEED_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, IMAGE_SEED_PATH)


def _check_seed() -> None:
    with IMAGE_SEED_PATH.open("r", encoding="utf-8", newline="") as file:
        rows = {row["object_id"]: row for row in csv.DictReader(file)}
    for image in IMAGES:
        expected = _seed_row(image)
        row = rows.get(image.object_id)
        if row is None:
            raise RuntimeError(f"{image.object_id}: missing image seed")
        mismatches = [key for key, value in expected.items() if row.get(key) != value]
        if mismatches:
            raise RuntimeError(
                f"{image.object_id}: seed mismatch in {', '.join(mismatches)}"
            )


def _check() -> None:
    for image in IMAGES:
        _validate_file(image)
    _check_seed()
    print(f"Solar System image check passed: {len(IMAGES)} JPEG assets")


def _sync(*, force: bool) -> None:
    previous_sources = _seed_source_urls()
    counts = {"cached": 0, "downloaded": 0}
    for index, image in enumerate(IMAGES, start=1):
        status = _download(
            image,
            force=force or previous_sources.get(image.object_id) != image.source_url,
        )
        counts[status] += 1
        print(f"[{index:02d}/{len(IMAGES)}] {image.object_id}: {status}")
    _write_seed()
    _check()
    print(
        "Solar System images ready: "
        f"{counts['downloaded']} downloaded, {counts['cached']} cached"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and validate normalized NASA/JPL Solar System images."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate local assets without network access",
    )
    parser.add_argument(
        "--force", action="store_true", help="redownload existing valid assets"
    )
    args = parser.parse_args()
    if args.check:
        _check()
    else:
        _sync(force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
