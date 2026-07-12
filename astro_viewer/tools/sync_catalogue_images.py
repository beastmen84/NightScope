from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

import requests
from PIL import Image, ImageStat, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from astro_viewer.app.astronomy.coordinates import parse_dec_degrees, parse_ra_hours  # noqa: E402


CATALOGUE_PATH = ROOT / "astro_viewer" / "data" / "catalogue_objects_seed.csv"
IMAGE_SEED_PATH = ROOT / "astro_viewer" / "data" / "object_images_seed.csv"
OUTPUT_DIR = ROOT / "astro_viewer" / "resources" / "images" / "catalogue"
HIPS2FITS_URL = "https://alasky.cds.unistra.fr/hips-image-services/hips2fits"
IMAGE_SIZE = 512
SURVEYS = {
    "2mass": {
        "hips_id": "CDS/P/2MASS/color",
        "attribution": "2MASS (UMass/IPAC-Caltech); HiPS a colori e ritaglio: CDS",
        "license": "2MASS public survey data; CDS/P/2MASS/color HiPS ODbL-1.0",
    },
    "panstarrs": {
        "hips_id": "CDS/P/PanSTARRS/DR1/color-i-r-g",
        "attribution": "Pan-STARRS1; HiPS a colori e ritaglio: CDS",
        "license": "Pan-STARRS1 public data; CDS Pan-STARRS DR1 HiPS ODbL-1.0",
    },
    "skymapper": {
        "hips_id": "CDS/P/Skymapper/DR4/color",
        "attribution": "SkyMapper Southern Survey DR4; HiPS a colori e ritaglio: CDS",
        "license": "SkyMapper DR4 public data; CDS SkyMapper DR4 HiPS ODbL-1.0",
    },
}
# Rounded Caldwell coordinates are not precise enough for compact planetary nebulae.
# These J2000 positions were resolved through CDS Sesame/SIMBAD on 2026-07-12.
COORDINATE_OVERRIDES = {
    "caldwell-C2": (3.25423754, 72.52195371),
    "caldwell-C6": (269.63918316, 66.63298631),
    "caldwell-C15": (296.20062509, 50.52506918),
    "caldwell-C22": (351.47429950, 42.53495440),
    "caldwell-C39": (112.29486308, 20.91179858),
    "caldwell-C55": (316.04506466, -11.36349449),
    "caldwell-C56": (11.76392514, -11.87193642),
    "caldwell-C59": (156.19222313, -18.64230468),
    "caldwell-C63": (337.41060585, -20.83715201),
    "caldwell-C69": (258.43540000, -37.10310000),
    "caldwell-C74": (151.75735684, -40.43642515),
    "caldwell-C90": (140.35576353, -58.31128519),
    "caldwell-C109": (152.33712500, -80.85853611),
}
FOV_OVERRIDES = {"caldwell-C59": 0.12}
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
class CatalogueImage:
    object_id: str
    path: Path
    relative_path: str
    source_url: str
    attribution: str
    license: str


def _fov_deg(row: dict[str, str]) -> float:
    if row["object_id"] in FOV_OVERRIDES:
        return FOV_OVERRIDES[row["object_id"]]
    apparent_size = float(row["max_angular_size_deg"])
    object_type = row["tipo"].lower()
    if "planetary nebula" in object_type:
        multiplier = 2.2
    elif "supernova remnant" in object_type or "dark nebula" in object_type:
        multiplier = 1.25
    elif "galaxy" in object_type:
        multiplier = 1.35 if apparent_size >= 1.0 else 1.8
    elif "globular cluster" in object_type:
        multiplier = 2.2
    elif "open cluster" in object_type:
        multiplier = 1.5
    elif "star cloud" in object_type:
        multiplier = 1.15
    elif "nebula" in object_type:
        multiplier = 1.5
    else:
        multiplier = 1.6
    return min(8.0, max(0.08, apparent_size * multiplier))


def _survey_key(row: dict[str, str]) -> str:
    object_type = row["tipo"].lower()
    if row["object_id"] != "messier-M1" and (
        "planetary nebula" in object_type or "supernova remnant" in object_type
    ):
        return "panstarrs" if parse_dec_degrees(row["declinazione"]) >= -30.0 else "skymapper"
    return "2mass"


def _source_url(row: dict[str, str], hips_id: str) -> str:
    ra_deg, dec_deg = COORDINATE_OVERRIDES.get(
        row["object_id"],
        (
            parse_ra_hours(row["ascensione_retta"]) * 15.0,
            parse_dec_degrees(row["declinazione"]),
        ),
    )
    params = {
        "hips": hips_id,
        "width": IMAGE_SIZE,
        "height": IMAGE_SIZE,
        "fov": f"{_fov_deg(row):.6f}",
        "projection": "TAN",
        "coordsys": "icrs",
        "ra": f"{ra_deg:.8f}",
        "dec": f"{dec_deg:.8f}",
        "format": "jpg",
    }
    return f"{HIPS2FITS_URL}?{urlencode(params)}"


def _catalogue_images() -> list[CatalogueImage]:
    with CATALOGUE_PATH.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    images = []
    for row in rows:
        filename = f"{row['object_id']}.jpg"
        survey = SURVEYS[_survey_key(row)]
        images.append(
            CatalogueImage(
                object_id=row["object_id"],
                path=OUTPUT_DIR / filename,
                relative_path=f"resources/images/catalogue/{filename}",
                source_url=_source_url(row, survey["hips_id"]),
                attribution=survey["attribution"],
                license=survey["license"],
            )
        )
    return images


def _validated_image(content: bytes, object_id: str) -> Image.Image:
    try:
        with Image.open(io.BytesIO(content)) as source:
            source.load()
            image = source.convert("RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise RuntimeError(f"{object_id}: hips2fits did not return a valid image") from exc
    if image.size != (IMAGE_SIZE, IMAGE_SIZE):
        raise RuntimeError(f"{object_id}: unexpected dimensions {image.size}")
    if ImageStat.Stat(image.convert("L")).stddev[0] < 2.0:
        raise RuntimeError(f"{object_id}: image appears blank")
    return image


def _validate_file(image: CatalogueImage) -> None:
    try:
        with Image.open(image.path) as source:
            source.load()
            if source.format != "JPEG":
                raise RuntimeError(f"{image.object_id}: expected JPEG, got {source.format}")
            if source.size != (IMAGE_SIZE, IMAGE_SIZE):
                raise RuntimeError(f"{image.object_id}: unexpected dimensions {source.size}")
            if source.mode != "RGB":
                raise RuntimeError(f"{image.object_id}: expected RGB, got {source.mode}")
            if ImageStat.Stat(source.convert("L")).stddev[0] < 2.0:
                raise RuntimeError(f"{image.object_id}: image appears blank")
    except (OSError, UnidentifiedImageError) as exc:
        raise RuntimeError(f"{image.object_id}: unreadable JPEG") from exc


def _download(image: CatalogueImage, *, force: bool) -> str:
    if image.path.exists() and not force:
        _validate_file(image)
        return "cached"
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(
                image.source_url,
                timeout=45,
                headers={"User-Agent": "NightScope catalogue asset sync/1.0"},
            )
            response.raise_for_status()
            normalized = _validated_image(response.content, image.object_id)
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
    raise RuntimeError(f"{image.object_id}: download failed: {last_error}") from last_error


def _write_seed(images: list[CatalogueImage]) -> None:
    with IMAGE_SEED_PATH.open("r", encoding="utf-8", newline="") as file:
        existing = list(csv.DictReader(file))
    catalogue_ids = {image.object_id for image in images}
    rows = [row for row in existing if row["object_id"] not in catalogue_ids]
    rows.extend(
        {
            "object_id": image.object_id,
            "image_path": image.relative_path,
            "thumbnail_path": image.relative_path,
            "attribution": image.attribution,
            "source_url": image.source_url,
            "license": image.license,
            "verified": "1",
        }
        for image in images
    )
    temporary = IMAGE_SEED_PATH.with_suffix(".csv.part")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SEED_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, IMAGE_SEED_PATH)


def _seed_source_urls() -> dict[str, str]:
    with IMAGE_SEED_PATH.open("r", encoding="utf-8", newline="") as file:
        return {
            row["object_id"]: row.get("source_url", "")
            for row in csv.DictReader(file)
        }


def _check_seed(images: list[CatalogueImage]) -> None:
    with IMAGE_SEED_PATH.open("r", encoding="utf-8", newline="") as file:
        rows = {row["object_id"]: row for row in csv.DictReader(file)}
    expected_ids = {image.object_id for image in images}
    if not expected_ids.issubset(rows):
        missing = sorted(expected_ids - rows)
        raise RuntimeError(f"image seed is missing {len(missing)} catalogue targets")
    for image in images:
        row = rows[image.object_id]
        expected = {
            "image_path": image.relative_path,
            "thumbnail_path": image.relative_path,
            "attribution": image.attribution,
            "source_url": image.source_url,
            "license": image.license,
            "verified": "1",
        }
        mismatches = [key for key, value in expected.items() if row.get(key) != value]
        if mismatches:
            raise RuntimeError(f"{image.object_id}: seed mismatch in {', '.join(mismatches)}")


def _sync(*, workers: int, force: bool) -> None:
    images = _catalogue_images()
    previous_sources = _seed_source_urls()
    failures: list[str] = []
    counts = {"cached": 0, "downloaded": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {
            pool.submit(
                _download,
                image,
                force=force or previous_sources.get(image.object_id) != image.source_url,
            ): image
            for image in images
        }
        for index, future in enumerate(as_completed(pending), start=1):
            image = pending[future]
            try:
                status = future.result()
                counts[status] += 1
                print(f"[{index:03d}/{len(images)}] {image.object_id}: {status}")
            except RuntimeError as exc:
                failures.append(str(exc))
                print(f"[{index:03d}/{len(images)}] {exc}", file=sys.stderr)
    if failures:
        raise RuntimeError(f"catalogue image sync failed for {len(failures)} targets")
    _write_seed(images)
    _check(images)
    print(f"Catalogue images ready: {counts['downloaded']} downloaded, {counts['cached']} cached")


def _check(images: list[CatalogueImage] | None = None) -> None:
    catalogue_images = images or _catalogue_images()
    for image in catalogue_images:
        _validate_file(image)
    _check_seed(catalogue_images)
    print(f"Catalogue image check passed: {len(catalogue_images)} JPEG assets")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and validate uniform 2MASS catalogue cutouts."
    )
    parser.add_argument("--check", action="store_true", help="validate local assets without network access")
    parser.add_argument("--force", action="store_true", help="redownload existing valid assets")
    parser.add_argument("--workers", type=int, default=8, help="parallel download count")
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        parser.error("--workers must be between 1 and 16")
    if args.check:
        _check()
    else:
        _sync(workers=args.workers, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
