from __future__ import annotations

from import_utils import optional_float, parser, read_rows, run_import


EYEPIECE_REQUIRED = {"brand", "model", "eyepiece_type", "focal_length_mm", "apparent_field_deg"}
BARLOW_REQUIRED = {"brand", "model", "multiplier"}


def main() -> None:
    args = parser("Import eyepiece catalog CSV").parse_args()
    rows = read_rows(args.csv_path, {"brand", "model"})
    fieldnames = set(rows[0].keys()) if rows else set()
    if EYEPIECE_REQUIRED <= fieldnames:
        run_import(args.database, lambda connection: _import_eyepieces(connection, rows))
    elif BARLOW_REQUIRED <= fieldnames:
        run_import(args.database, lambda connection: _import_barlows(connection, rows))
    else:
        raise ValueError("CSV must contain eyepiece columns or Barlow columns.")


def _import_eyepieces(connection, rows: list[dict]) -> int:
    connection.executemany(
        """
        INSERT INTO EyepieceCatalog (
            brand, model, eyepiece_type, focal_length_mm, min_focal_length_mm,
            max_focal_length_mm, apparent_field_deg, afov_min, afov_max,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(brand, model, focal_length_mm) DO UPDATE SET
            eyepiece_type = excluded.eyepiece_type,
            min_focal_length_mm = excluded.min_focal_length_mm,
            max_focal_length_mm = excluded.max_focal_length_mm,
            apparent_field_deg = excluded.apparent_field_deg,
            afov_min = excluded.afov_min,
            afov_max = excluded.afov_max,
            notes = excluded.notes
        """,
        [
            (
                row["brand"],
                row["model"],
                row.get("eyepiece_type", "Fixed") or "Fixed",
                float(row["focal_length_mm"]),
                optional_float(row.get("min_focal_length_mm")),
                optional_float(row.get("max_focal_length_mm")),
                float(row["apparent_field_deg"]),
                optional_float(row.get("afov_min")),
                optional_float(row.get("afov_max")),
                row.get("notes", ""),
            )
            for row in rows
        ],
    )
    return len(rows)


def _import_barlows(connection, rows: list[dict]) -> int:
    connection.executemany(
        """
        INSERT INTO BarlowCatalog (brand, model, multiplier, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(brand, model, multiplier) DO UPDATE SET
            notes = excluded.notes
        """,
        [
            (
                row["brand"],
                row["model"],
                float(row["multiplier"]),
                row.get("notes", ""),
            )
            for row in rows
        ],
    )
    return len(rows)


if __name__ == "__main__":
    main()
