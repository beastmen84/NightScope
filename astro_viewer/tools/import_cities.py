from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.geonames_importer import import_geonames_cities
from astro_viewer.tools.import_utils import connect


def main() -> None:
    args = _parser().parse_args()
    if args.geonames_path.name.lower() == "allcountries.txt":
        raise SystemExit("Use cities15000.txt for NightScope city imports; allCountries.txt is intentionally not imported.")
    schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
    initialize_database(args.database, schema_path)
    with connect(args.database) as connection:
        report = import_geonames_cities(
            connection,
            args.geonames_path,
            country_info_path=args.country_info,
            admin1_codes_path=args.admin1_codes,
            proximity_km=args.proximity_km,
        )
        connection.commit()
    payload = report.to_dict()
    payload["aliases_generated"] = report.aliases_added
    payload["db_size_bytes"] = args.database.stat().st_size if args.database.exists() else 0
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _parser() -> argparse.ArgumentParser:
    base_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Import a GeoNames geoname-table dump such as cities15000.txt, "
            "cities5000.txt or cities1000.txt. Use cities15000.txt for the first real NightScope dataset."
        )
    )
    parser.add_argument("geonames_path", type=Path, help="GeoNames tab-delimited geoname table file")
    parser.add_argument("--database", type=Path, default=base_dir.parent / "nightscope.db")
    parser.add_argument(
        "--country-info",
        type=Path,
        default=base_dir / "data" / "countryInfo.txt",
        help="Optional GeoNames countryInfo.txt",
    )
    parser.add_argument(
        "--admin1-codes",
        type=Path,
        default=base_dir / "data" / "admin1CodesASCII.txt",
        help="Optional GeoNames admin1CodesASCII.txt",
    )
    parser.add_argument("--proximity-km", type=float, default=5.0)
    return parser


if __name__ == "__main__":
    main()
