from __future__ import annotations

from import_utils import optional_int, parser, read_rows, run_import


REQUIRED = {"city_name", "country", "latitude", "longitude", "timezone"}


def main() -> None:
    args = parser("Import offline city catalog CSV").parse_args()
    rows = read_rows(args.csv_path, REQUIRED)

    def import_rows(connection):
        connection.executemany(
            """
            INSERT INTO City (
                city_name, ascii_name, country, country_code, admin_region,
                latitude, longitude, timezone, population, search_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(city_name, country) DO UPDATE SET
                ascii_name = excluded.ascii_name,
                country_code = excluded.country_code,
                admin_region = excluded.admin_region,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                timezone = excluded.timezone,
                population = excluded.population,
                search_name = excluded.search_name
            """,
            [
                (
                    row["city_name"],
                    row.get("ascii_name") or row["city_name"],
                    row["country"],
                    row.get("country_code", ""),
                    row.get("admin_region", ""),
                    float(row["latitude"]),
                    float(row["longitude"]),
                    row["timezone"],
                    optional_int(row.get("population")),
                    row.get("search_name") or row["city_name"].lower(),
                )
                for row in rows
            ],
        )
        return len(rows)

    run_import(args.database, import_rows)


if __name__ == "__main__":
    main()
