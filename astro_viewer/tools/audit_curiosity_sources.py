"""Verify every distinct editorial curiosity URL through bounded parallel HTTP requests."""

from __future__ import annotations

import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "astro_viewer" / "data" / "object_curiosities_seed.csv"


def source_urls(batch_path: Path | None = None) -> list[str]:
    if batch_path is not None:
        payload = json.loads(batch_path.read_text(encoding="utf-8"))
        return sorted(
            {
                str(source.get("url") or "").strip()
                for item in payload.get("objects", [])
                for source in item.get("sources", [])
                if str(source.get("url") or "").strip()
            }
        )
    with SEED_PATH.open("r", encoding="utf-8", newline="") as file:
        return sorted({row["source_url"].strip() for row in csv.DictReader(file)})


def _check(url: str) -> tuple[str, int, str]:
    try:
        response = requests.get(
            url,
            timeout=30,
            allow_redirects=True,
            stream=True,
            headers={"User-Agent": "NightScope curiosity source audit/1.0"},
        )
        final_url = response.url
        status = response.status_code
        response.close()
        return url, status, final_url
    except requests.RequestException as exc:
        return url, 0, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check every distinct curiosity source URL.")
    parser.add_argument("--workers", type=int, default=8, help="parallel request count")
    parser.add_argument(
        "--batch",
        type=Path,
        help="check only evidence URLs recorded in one editorial batch manifest",
    )
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        parser.error("--workers must be between 1 and 16")

    urls = source_urls(args.batch)
    if not urls:
        parser.error("the selected source set is empty")
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(_check, url): url for url in urls}
        for future in as_completed(pending):
            url, status, detail = future.result()
            if status != 200:
                failures.append((url, status, detail))

    if failures:
        for url, status, detail in sorted(failures):
            print(f"FAILED {status}: {url} -> {detail}")
        return 1
    print(f"Curiosity source audit passed: {len(urls)} distinct URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
