from __future__ import annotations

from import_utils import optional_float, parser, read_rows, run_import


REQUIRED = {"brand", "model", "optical_type", "aperture_mm", "focal_length_mm", "mount_type"}


def main() -> None:
    args = parser("Import telescope catalog CSV").parse_args()
    rows = read_rows(args.csv_path, REQUIRED)

    def import_rows(connection):
        brands = sorted({row["brand"] for row in rows})
        connection.executemany("INSERT OR IGNORE INTO TelescopeBrand (name) VALUES (?)", [(brand,) for brand in brands])
        brand_ids = {row["name"]: row["id"] for row in connection.execute("SELECT id, name FROM TelescopeBrand")}
        connection.executemany(
            """
            INSERT INTO TelescopeModel (
                brand_id, name, optical_type, aperture_mm, focal_length_mm,
                focal_ratio, mount_type, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(brand_id, name) DO UPDATE SET
                optical_type = excluded.optical_type,
                aperture_mm = excluded.aperture_mm,
                focal_length_mm = excluded.focal_length_mm,
                focal_ratio = excluded.focal_ratio,
                mount_type = excluded.mount_type,
                notes = excluded.notes
            """,
            [
                (
                    brand_ids[row["brand"]],
                    row["model"],
                    row["optical_type"],
                    int(float(row["aperture_mm"])),
                    int(float(row["focal_length_mm"])),
                    optional_float(row.get("focal_ratio")),
                    row["mount_type"],
                    row.get("notes", ""),
                )
                for row in rows
            ],
        )
        return len(rows)

    run_import(args.database, import_rows)


if __name__ == "__main__":
    main()
