from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "astro_viewer" / "data"
DEFAULT_SOURCE = (
    DATA_DIR
    / "sources"
    / "openngc-36cb178a0f69dba8bfc03a99c10512831edf1c6b-ngc.csv.gz"
)
DEFAULT_OBJECTS = DATA_DIR / "catalogue_objects_seed.csv"
DEFAULT_DESIGNATIONS = DATA_DIR / "catalogue_designations_seed.csv"

OPENNGC_COMMIT = "36cb178a0f69dba8bfc03a99c10512831edf1c6b"
OPENNGC_SOURCE_URL = (
    "https://github.com/mattiaverga/OpenNGC/blob/"
    f"{OPENNGC_COMMIT}/database_files/NGC.csv"
)
OPENNGC_SOURCE_SHA256 = (
    "e4acd595ed13888f888273fc5cb47c7934430a13348a294abdc8879b1d66fef7"
)
CANONICAL_NGC_COUNT = 7_840
USABLE_NGC_DESIGNATION_COUNT = 7_839
WORK_IN_PROGRESS = "Work in progress"

OBJECT_FIELDNAMES = (
    "object_id",
    "nome",
    "tipo",
    "costellazione",
    "magnitudine",
    "ascensione_retta",
    "declinazione",
    "dimensione_apparente",
    "max_angular_size_deg",
    "recommended_observation_type",
    "best_filter_class",
    "fallback_filter_class",
    "optional_color_filter_class",
    "imaging_reducer_recommended",
    "recommendation_enabled_by_default",
    "descrizione",
)
DESIGNATION_FIELDNAMES = (
    "object_id",
    "catalogue",
    "designation",
    "sort_index",
    "is_primary",
)

_CANONICAL_NAME = re.compile(r"NGC(\d{4})")
_NGC_REFERENCE = re.compile(
    r"\bNGC\s*(\d{1,4})(?:\s*([/-])\s*(\d{1,4}))?",
    re.IGNORECASE,
)

_OBJECT_TYPES = {
    "*": "Star",
    "**": "Optical double",
    "*Ass": "Asterism",
    "OCl": "Open cluster",
    "GCl": "Globular cluster",
    "Cl+N": "Nebula with cluster",
    "G": "Galaxy",
    "GPair": "Galaxy pair",
    "GTrpl": "Galaxy triplet",
    "GGroup": "Galaxy group",
    "PN": "Planetary nebula",
    "HII": "H II region nebula",
    "DrkN": "Dark nebula",
    "EmN": "Emission nebula",
    "Neb": "Nebula",
    "RfN": "Reflection nebula",
    "SNR": "Supernova remnant",
    "Nova": "Star",
    "Other": "Unclassified object",
}

_CONSTELLATIONS = {
    "And": "Andromeda",
    "Ant": "Antlia",
    "Aps": "Apus",
    "Aql": "Aquila",
    "Aqr": "Aquarius",
    "Ara": "Ara",
    "Ari": "Aries",
    "Aur": "Auriga",
    "Boo": "Bootes",
    "CMa": "Canis Major",
    "CMi": "Canis Minor",
    "CVn": "Canes Venatici",
    "Cae": "Caelum",
    "Cam": "Camelopardalis",
    "Cap": "Capricornus",
    "Car": "Carina",
    "Cas": "Cassiopeia",
    "Cen": "Centaurus",
    "Cep": "Cepheus",
    "Cet": "Cetus",
    "Cha": "Chamaeleon",
    "Cir": "Circinus",
    "Cnc": "Cancer",
    "Col": "Columba",
    "Com": "Coma Berenices",
    "CrA": "Corona Australis",
    "CrB": "Corona Borealis",
    "Crt": "Crater",
    "Cru": "Crux",
    "Crv": "Corvus",
    "Cyg": "Cygnus",
    "Del": "Delphinus",
    "Dor": "Dorado",
    "Dra": "Draco",
    "Equ": "Equuleus",
    "Eri": "Eridanus",
    "For": "Fornax",
    "Gem": "Gemini",
    "Gru": "Grus",
    "Her": "Hercules",
    "Hor": "Horologium",
    "Hya": "Hydra",
    "Hyi": "Hydrus",
    "Ind": "Indus",
    "LMi": "Leo Minor",
    "Lac": "Lacerta",
    "Leo": "Leo",
    "Lep": "Lepus",
    "Lib": "Libra",
    "Lup": "Lupus",
    "Lyn": "Lynx",
    "Lyr": "Lyra",
    "Men": "Mensa",
    "Mic": "Microscopium",
    "Mon": "Monoceros",
    "Mus": "Musca",
    "Nor": "Norma",
    "Oct": "Octans",
    "Oph": "Ophiuchus",
    "Ori": "Orion",
    "Pav": "Pavo",
    "Peg": "Pegasus",
    "Per": "Perseus",
    "Phe": "Phoenix",
    "Pic": "Pictor",
    "PsA": "Piscis Austrinus",
    "Psc": "Pisces",
    "Pup": "Puppis",
    "Pyx": "Pyxis",
    "Ret": "Reticulum",
    "Scl": "Sculptor",
    "Sco": "Scorpius",
    "Sct": "Scutum",
    "Se1": "Serpens",
    "Se2": "Serpens",
    "Sex": "Sextans",
    "Sge": "Sagitta",
    "Sgr": "Sagittarius",
    "Tau": "Taurus",
    "Tel": "Telescopium",
    "TrA": "Triangulum Australe",
    "Tri": "Triangulum",
    "Tuc": "Tucana",
    "UMa": "Ursa Major",
    "UMi": "Ursa Minor",
    "Vel": "Vela",
    "Vir": "Virgo",
    "Vol": "Volans",
    "Vul": "Vulpecula",
}


def generate_catalogue(
    source_path: Path = DEFAULT_SOURCE,
    objects_path: Path = DEFAULT_OBJECTS,
    designations_path: Path = DEFAULT_DESIGNATIONS,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, int | str]]:
    source_rows = _read_openngc_rows(source_path)
    base_objects = [
        row
        for row in _read_csv(objects_path, OBJECT_FIELDNAMES)
        if not row["object_id"].startswith("ngc-")
    ]
    base_designations = [
        row
        for row in _read_csv(designations_path, DESIGNATION_FIELDNAMES)
        if row["catalogue"].casefold() != "ngc"
    ]
    return build_catalogue_rows(source_rows, base_objects, base_designations)


def build_catalogue_rows(
    source_rows: list[dict[str, str]],
    base_objects: list[dict[str, str]],
    base_designations: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, int | str]]:
    canonical_rows: dict[int, dict[str, str]] = {}
    rows_by_name = {row["Name"]: row for row in source_rows}
    for row in source_rows:
        match = _CANONICAL_NAME.fullmatch(row["Name"])
        if match:
            canonical_rows[int(match.group(1))] = row
    if set(canonical_rows) != set(range(1, CANONICAL_NGC_COUNT + 1)):
        raise ValueError("OpenNGC snapshot does not contain the canonical NGC 1-7840 range.")

    base_object_ids = {row["object_id"] for row in base_objects}
    curated_identity = _curated_ngc_identity_map(base_objects)
    source_identity: dict[str, str] = {}
    source_row_by_new_object: dict[str, dict[str, str]] = {}

    for number, row in canonical_rows.items():
        if row["Type"] in {"Dup", "NonEx"}:
            continue
        object_id = curated_identity.get(number)
        if object_id is None and row["M"].strip():
            object_id = f"messier-M{int(row['M'])}"
        if object_id is None:
            object_id = f"ngc-NGC{number}"
            source_row_by_new_object[object_id] = row
        if object_id not in base_object_ids and not object_id.startswith("ngc-"):
            raise ValueError(f"OpenNGC references missing curated object {object_id}.")
        source_identity[row["Name"]] = object_id

    for number, row in canonical_rows.items():
        if row["Type"] != "Dup" or number in curated_identity:
            continue
        target_name = f"NGC{row['NGC'].strip()}"
        if target_name in source_identity:
            continue
        target_row = rows_by_name.get(target_name)
        if target_row is None:
            raise ValueError(f"OpenNGC duplicate {row['Name']} has no target {target_name}.")
        object_id = f"ngc-NGC{number}"
        source_identity[target_name] = object_id
        source_row_by_new_object[object_id] = target_row

    designation_identity: dict[int, str] = {}
    for number, row in canonical_rows.items():
        if row["Type"] == "NonEx":
            continue
        object_id = curated_identity.get(number)
        if object_id is None:
            source_name = (
                f"NGC{row['NGC'].strip()}"
                if row["Type"] == "Dup"
                else row["Name"]
            )
            object_id = source_identity[source_name]
        designation_identity[number] = object_id

    ngc_numbers_by_object: dict[str, list[int]] = defaultdict(list)
    for number, object_id in designation_identity.items():
        ngc_numbers_by_object[object_id].append(number)

    generated_objects = []
    for object_id in sorted(
        source_row_by_new_object,
        key=lambda value: min(ngc_numbers_by_object[value]),
    ):
        primary_number = _primary_ngc_number(
            ngc_numbers_by_object[object_id],
            canonical_rows,
        )
        generated_objects.append(
            _catalogue_object_row(
                object_id,
                primary_number,
                source_row_by_new_object[object_id],
            )
        )

    generated_designations = []
    for number, object_id in sorted(designation_identity.items()):
        is_primary = 0
        if object_id not in base_object_ids:
            is_primary = int(
                number
                == _primary_ngc_number(
                    ngc_numbers_by_object[object_id],
                    canonical_rows,
                )
            )
        generated_designations.append(
            {
                "object_id": object_id,
                "catalogue": "NGC",
                "designation": f"NGC {number}",
                "sort_index": str(number),
                "is_primary": str(is_primary),
            }
        )

    object_rows = [*base_objects, *generated_objects]
    designation_rows = [*base_designations, *generated_designations]
    _validate_generated_rows(object_rows, designation_rows)
    report: dict[str, int | str] = {
        "source_commit": OPENNGC_COMMIT,
        "canonical_designations": len(canonical_rows),
        "usable_designations": len(generated_designations),
        "physical_ngc_targets": len(set(designation_identity.values())),
        "existing_identity_matches": len(
            set(designation_identity.values()).intersection(base_object_ids)
        ),
        "new_physical_targets": len(generated_objects),
        "total_physical_targets": len(object_rows),
        "excluded_nonexistent_entries": sum(
            row["Type"] == "NonEx" for row in canonical_rows.values()
        ),
    }
    return object_rows, designation_rows, report


def update_catalogue(
    source_path: Path = DEFAULT_SOURCE,
    objects_path: Path = DEFAULT_OBJECTS,
    designations_path: Path = DEFAULT_DESIGNATIONS,
) -> dict[str, int | str]:
    object_rows, designation_rows, report = generate_catalogue(
        source_path,
        objects_path,
        designations_path,
    )
    objects_path.write_text(
        _serialize_csv(object_rows, OBJECT_FIELDNAMES),
        encoding="utf-8",
        newline="",
    )
    designations_path.write_text(
        _serialize_csv(designation_rows, DESIGNATION_FIELDNAMES),
        encoding="utf-8",
        newline="",
    )
    return report


def validate_catalogue(
    source_path: Path = DEFAULT_SOURCE,
    objects_path: Path = DEFAULT_OBJECTS,
    designations_path: Path = DEFAULT_DESIGNATIONS,
) -> dict[str, int | str]:
    object_rows, designation_rows, report = generate_catalogue(
        source_path,
        objects_path,
        designations_path,
    )
    expected_objects = _serialize_csv(object_rows, OBJECT_FIELDNAMES)
    expected_designations = _serialize_csv(
        designation_rows,
        DESIGNATION_FIELDNAMES,
    )
    if objects_path.read_text(encoding="utf-8") != expected_objects:
        raise ValueError("Catalogue object seed is stale; regenerate the NGC snapshot.")
    if designations_path.read_text(encoding="utf-8") != expected_designations:
        raise ValueError("Catalogue designation seed is stale; regenerate the NGC snapshot.")
    return report


def _read_openngc_rows(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rb") as file:
        payload = file.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != OPENNGC_SOURCE_SHA256:
        raise ValueError(
            f"Unexpected OpenNGC source digest {digest}; expected "
            f"{OPENNGC_SOURCE_SHA256}."
        )
    reader = csv.DictReader(
        io.StringIO(payload.decode("utf-8-sig")),
        delimiter=";",
    )
    rows = list(reader)
    required_fields = {
        "Name",
        "Type",
        "RA",
        "Dec",
        "Const",
        "MajAx",
        "MinAx",
        "B-Mag",
        "V-Mag",
        "M",
        "NGC",
        "Common names",
    }
    if not required_fields.issubset(reader.fieldnames or ()):
        raise ValueError("OpenNGC source columns are not current.")
    return rows


def _read_csv(
    path: Path,
    expected_fieldnames: tuple[str, ...],
) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != expected_fieldnames:
            raise ValueError(f"Unexpected columns in {path.name}.")
        return list(reader)


def _curated_ngc_identity_map(
    base_objects: list[dict[str, str]],
) -> dict[int, str]:
    identity: dict[int, str] = {}
    for row in base_objects:
        text = f"{row['nome']} | {row['descrizione']}"
        for match in _NGC_REFERENCE.finditer(text):
            start = int(match.group(1))
            numbers = [start]
            if match.group(3):
                end = int(match.group(3))
                if match.group(2) == "-" and 0 < end - start <= 10:
                    numbers.extend(range(start + 1, end + 1))
                else:
                    numbers.append(end)
            for number in numbers:
                existing = identity.get(number)
                if existing is not None and existing != row["object_id"]:
                    raise ValueError(
                        f"Curated NGC {number} identity conflicts between "
                        f"{existing} and {row['object_id']}."
                    )
                identity[number] = row["object_id"]
    return identity


def _primary_ngc_number(
    numbers: list[int],
    canonical_rows: dict[int, dict[str, str]],
) -> int:
    physical_entries = [
        number
        for number in numbers
        if canonical_rows[number]["Type"] != "Dup"
    ]
    return min(physical_entries or numbers)


def _catalogue_object_row(
    object_id: str,
    primary_number: int,
    source: dict[str, str],
) -> dict[str, str]:
    object_type = _OBJECT_TYPES.get(source["Type"])
    if object_type is None:
        raise ValueError(
            f"Unsupported OpenNGC type {source['Type']} for {source['Name']}."
        )
    constellation = _CONSTELLATIONS.get(source["Const"])
    if constellation is None:
        raise ValueError(
            f"Unsupported OpenNGC constellation {source['Const']} for "
            f"{source['Name']}."
        )
    designation = f"NGC {primary_number}"
    common_name = source["Common names"].split(",", maxsplit=1)[0].strip()
    apparent_size, max_angular_size = _angular_size(source)
    magnitude = source["V-Mag"].strip() or source["B-Mag"].strip()
    return {
        "object_id": object_id,
        "nome": common_name or designation,
        "tipo": object_type,
        "costellazione": constellation,
        "magnitudine": _number_text(magnitude),
        "ascensione_retta": source["RA"].strip(),
        "declinazione": source["Dec"].strip(),
        "dimensione_apparente": apparent_size,
        "max_angular_size_deg": max_angular_size,
        "recommended_observation_type": _observation_type(
            object_type,
            max_angular_size,
        ),
        "best_filter_class": "",
        "fallback_filter_class": "",
        "optional_color_filter_class": "",
        "imaging_reducer_recommended": "0",
        "recommendation_enabled_by_default": "0",
        "descrizione": WORK_IN_PROGRESS,
    }


def _angular_size(source: dict[str, str]) -> tuple[str, str]:
    major_text = source["MajAx"].strip()
    minor_text = source["MinAx"].strip()
    if not major_text:
        return "", ""
    major = float(major_text)
    apparent_size = f"{_number_text(major_text)}′"
    if minor_text:
        apparent_size = (
            f"{_number_text(major_text)}′ × {_number_text(minor_text)}′"
        )
    return apparent_size, _number_text(str(major / 60.0), precision=8)


def _observation_type(
    object_type: str,
    max_angular_size: str,
) -> str:
    if object_type in {"Star", "Optical double", "Planetary nebula"}:
        return "HighMagnification"
    if object_type in {"Open cluster", "Asterism"}:
        return "WideField"
    if max_angular_size and float(max_angular_size) >= 1.0:
        return "WideField"
    return "General"


def _number_text(value: str, *, precision: int = 6) -> str:
    clean = value.strip()
    if not clean:
        return ""
    number = float(clean)
    return f"{number:.{precision}f}".rstrip("0").rstrip(".")


def _validate_generated_rows(
    object_rows: list[dict[str, str]],
    designation_rows: list[dict[str, str]],
) -> None:
    object_ids = [row["object_id"] for row in object_rows]
    if len(object_ids) != len({value.casefold() for value in object_ids}):
        raise ValueError("Generated catalogue contains duplicate physical object IDs.")
    known_ids = set(object_ids)
    designation_keys: set[tuple[str, str]] = set()
    primary_counts: dict[str, int] = defaultdict(int)
    for row in designation_rows:
        if row["object_id"] not in known_ids:
            raise ValueError(
                f"Generated designation references missing {row['object_id']}."
            )
        key = (
            row["catalogue"].casefold(),
            row["designation"].casefold(),
        )
        if key in designation_keys:
            raise ValueError(
                f"Generated catalogue contains duplicate designation {key}."
            )
        designation_keys.add(key)
        primary_counts[row["object_id"]] += int(row["is_primary"])
    invalid_primary = [
        object_id
        for object_id in object_ids
        if primary_counts[object_id] != 1
    ]
    if invalid_primary:
        raise ValueError(
            "Generated physical objects need exactly one primary designation: "
            + ", ".join(invalid_primary[:5])
        )
    ngc_designations = [
        row
        for row in designation_rows
        if row["catalogue"] == "NGC"
    ]
    if len(ngc_designations) != USABLE_NGC_DESIGNATION_COUNT:
        raise ValueError(
            f"Unexpected usable NGC designation count: {len(ngc_designations)}."
        )


def _serialize_csv(
    rows: list[dict[str, str]],
    fieldnames: tuple[str, ...],
) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate or validate NightScope's OpenNGC-derived catalogue "
            "seeds without network access."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the source digest and generated seeds",
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--objects", type=Path, default=DEFAULT_OBJECTS)
    parser.add_argument(
        "--designations",
        type=Path,
        default=DEFAULT_DESIGNATIONS,
    )
    args = parser.parse_args()
    if args.check:
        report = validate_catalogue(
            args.source,
            args.objects,
            args.designations,
        )
        report["status"] = "validated"
    else:
        report = update_catalogue(
            args.source,
            args.objects,
            args.designations,
        )
        report["status"] = "updated"
    report["source"] = str(args.source)
    report["source_url"] = OPENNGC_SOURCE_URL
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
