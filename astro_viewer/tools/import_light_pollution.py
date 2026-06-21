from __future__ import annotations

import shutil

from import_utils import parser, read_rows


REQUIRED = {
    "latitude",
    "longitude",
    "radius_km",
    "bortle_class",
    "sky_brightness",
    "limiting_magnitude",
    "source",
    "confidence",
}


def main() -> None:
    args = parser("Validate and install local light pollution CSV").parse_args()
    rows = read_rows(args.csv_path, REQUIRED)
    for row in rows:
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
        bortle = int(float(row["bortle_class"]))
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180 or not 1 <= bortle <= 9:
            raise ValueError(f"Invalid light pollution row: {row}")
    target = args.database.parent / "light_pollution_seed.csv"
    shutil.copy2(args.csv_path, target)
    print(f"Import complete: {len(rows)} rows validated and copied to {target}")


if __name__ == "__main__":
    main()
