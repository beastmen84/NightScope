from __future__ import annotations

import argparse
import csv
import sqlite3
from contextlib import closing
from pathlib import Path


def parser(description: str) -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description=description)
    base_dir = Path(__file__).resolve().parents[1]
    argument_parser.add_argument("csv_path", type=Path)
    argument_parser.add_argument("--database", type=Path, default=base_dir.parent / "nightscope.db")
    return argument_parser


def read_rows(csv_path: Path, required_columns: set[str]) -> list[dict]:
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = set(reader.fieldnames or [])
        missing = required_columns - fieldnames
        if missing:
            raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
        return [row for row in reader]


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def run_import(database_path: Path, import_fn) -> None:
    with closing(connect(database_path)) as connection:
        inserted_or_updated = import_fn(connection)
        connection.commit()
    print(f"Import complete: {inserted_or_updated} rows processed")


def optional_float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def optional_int(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))
