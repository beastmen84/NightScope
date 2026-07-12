from __future__ import annotations

from import_utils import parser, read_rows, run_import


IMAGE_COLUMNS = {"object_id", "image_path", "attribution"}
DESCRIPTION_COLUMNS = {"object_id", "short_description", "observing_notes"}


def main() -> None:
    args = parser("Import object images or descriptions CSV").parse_args()
    rows = read_rows(args.csv_path, {"object_id"})
    fieldnames = set(rows[0].keys()) if rows else set()
    if IMAGE_COLUMNS <= fieldnames:
        _import_images(args.database, rows)
    elif DESCRIPTION_COLUMNS <= fieldnames:
        _import_descriptions(args.database, rows)
    else:
        raise ValueError("CSV must contain image columns or description columns.")


def _import_images(database_path, rows: list[dict]) -> None:
    def import_rows(connection):
        connection.executemany(
            """
            INSERT INTO ObjectImages (
                object_id, image_path, thumbnail_path, attribution, source_url, license, verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
                image_path = excluded.image_path,
                thumbnail_path = excluded.thumbnail_path,
                attribution = excluded.attribution,
                source_url = excluded.source_url,
                license = excluded.license,
                verified = excluded.verified
            """,
            [
                (
                    row["object_id"],
                    row["image_path"],
                    row.get("thumbnail_path", ""),
                    row["attribution"],
                    row.get("source_url", ""),
                    row.get("license", ""),
                    1 if str(row.get("verified", "")).strip().lower() in {"1", "true", "yes"} else 0,
                )
                for row in rows
            ],
        )
        return len(rows)

    run_import(database_path, import_rows)


def _import_descriptions(database_path, rows: list[dict]) -> None:
    def import_rows(connection):
        connection.executemany(
            """
            INSERT INTO ObjectDescription (
                object_id, short_description, observing_notes, best_seen,
                difficulty_naked_eye, difficulty_binocular, difficulty_small_scope,
                difficulty_medium_scope, difficulty_large_scope, is_builtin
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(object_id) DO UPDATE SET
                short_description = excluded.short_description,
                observing_notes = excluded.observing_notes,
                best_seen = excluded.best_seen,
                difficulty_naked_eye = excluded.difficulty_naked_eye,
                difficulty_binocular = excluded.difficulty_binocular,
                difficulty_small_scope = excluded.difficulty_small_scope,
                difficulty_medium_scope = excluded.difficulty_medium_scope,
                difficulty_large_scope = excluded.difficulty_large_scope,
                is_builtin = 0
            """,
            [
                (
                    row["object_id"],
                    row["short_description"],
                    row["observing_notes"],
                    row.get("best_seen", ""),
                    row.get("difficulty_naked_eye", ""),
                    row.get("difficulty_binocular", ""),
                    row.get("difficulty_small_scope", ""),
                    row.get("difficulty_medium_scope", ""),
                    row.get("difficulty_large_scope", ""),
                )
                for row in rows
            ],
        )
        return len(rows)

    run_import(database_path, import_rows)


if __name__ == "__main__":
    main()
