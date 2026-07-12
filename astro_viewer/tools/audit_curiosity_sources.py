from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "astro_viewer" / "data" / "object_curiosities_seed.csv"


def _source_urls() -> list[str]:
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
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        parser.error("--workers must be between 1 and 16")

    urls = _source_urls()
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
