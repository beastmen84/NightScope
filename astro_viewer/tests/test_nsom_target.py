"""Protect runtime-target identity, classification, deduplication, and intrinsic quality."""

from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from astro_viewer.app.models.nsom import NsomTargetClass
from astro_viewer.app.services.nsom_target import (
    target_class_from_runtime_target,
    unique_targets_by_id,
)


CATALOGUE_TYPE_CLASSES = {
    "Asterism": NsomTargetClass.OPEN_CLUSTER,
    "Barred spiral galaxy": NsomTargetClass.GALAXY,
    "Barred Spiral galaxy": NsomTargetClass.GALAXY,
    "Dark nebula": NsomTargetClass.DIFFUSE_NEBULA,
    "Diffuse nebula": NsomTargetClass.DIFFUSE_NEBULA,
    "Dwarf elliptical galaxy": NsomTargetClass.GALAXY,
    "Elliptical galaxy": NsomTargetClass.GALAXY,
    "Emission nebula": NsomTargetClass.DIFFUSE_NEBULA,
    "Galaxy": NsomTargetClass.GALAXY,
    "Galaxy group": NsomTargetClass.GALAXY,
    "Galaxy pair": NsomTargetClass.GALAXY,
    "Galaxy triplet": NsomTargetClass.GALAXY,
    "Globular cluster": NsomTargetClass.GLOBULAR_CLUSTER,
    "H II region nebula": NsomTargetClass.DIFFUSE_NEBULA,
    "H II region nebula (part of the Orion Nebula)": NsomTargetClass.DIFFUSE_NEBULA,
    "H II region nebula with cluster": NsomTargetClass.DIFFUSE_NEBULA,
    "Irregular galaxy": NsomTargetClass.GALAXY,
    "Lenticular galaxy": NsomTargetClass.GALAXY,
    "Milky Way star cloud": NsomTargetClass.OPEN_CLUSTER,
    "Nebula": NsomTargetClass.DIFFUSE_NEBULA,
    "Nebula with cluster": NsomTargetClass.DIFFUSE_NEBULA,
    "Open cluster": NsomTargetClass.OPEN_CLUSTER,
    "Optical Double": NsomTargetClass.DOUBLE_STAR,
    "Optical double": NsomTargetClass.DOUBLE_STAR,
    "Peculiar galaxy": NsomTargetClass.GALAXY,
    "Planetary nebula": NsomTargetClass.PLANETARY_NEBULA,
    "Reflection nebula": NsomTargetClass.DIFFUSE_NEBULA,
    "Seyfert galaxy": NsomTargetClass.GALAXY,
    "Spiral galaxy": NsomTargetClass.GALAXY,
    "Starburst galaxy": NsomTargetClass.GALAXY,
    "Star": NsomTargetClass.DOUBLE_STAR,
    "Supernova remnant": NsomTargetClass.DIFFUSE_NEBULA,
    "Unclassified object": NsomTargetClass.DOUBLE_STAR,
}


@pytest.mark.parametrize(("object_type", "expected"), CATALOGUE_TYPE_CLASSES.items())
def test_shared_target_classifier_covers_every_catalogue_type(
    object_type: str,
    expected: NsomTargetClass,
) -> None:
    target = SimpleNamespace(id="catalogue-test", name="Test", object_type=object_type)

    assert target_class_from_runtime_target(target) is expected


def test_catalogue_seed_types_all_map_to_nsom_classes() -> None:
    seed_path = Path(__file__).resolve().parents[1] / "data" / "catalogue_objects_seed.csv"
    with seed_path.open(encoding="utf-8", newline="") as source:
        rows = tuple(csv.DictReader(source))

    assert {row["tipo"] for row in rows} == set(CATALOGUE_TYPE_CLASSES)
    for row in rows:
        target = SimpleNamespace(
            id=row["object_id"],
            name=row["nome"],
            object_type=row["tipo"],
        )
        assert target_class_from_runtime_target(target) is CATALOGUE_TYPE_CLASSES[row["tipo"]]


@pytest.mark.parametrize(
    ("object_type", "expected"),
    (
        ("Nebulosa planetaria", NsomTargetClass.PLANETARY_NEBULA),
        ("Resto di supernova", NsomTargetClass.DIFFUSE_NEBULA),
        ("Remanente di supernova", NsomTargetClass.DIFFUSE_NEBULA),
        ("Planet", NsomTargetClass.PLANET),
        ("Pianeta", NsomTargetClass.PLANET),
    ),
)
def test_shared_target_classifier_covers_supported_localized_types(
    object_type: str,
    expected: NsomTargetClass,
) -> None:
    target = SimpleNamespace(id="localized-test", name="Test", object_type=object_type)

    assert target_class_from_runtime_target(target) is expected


def test_shared_target_classifier_covers_messier_outliers() -> None:
    targets = (
        ("M24", "Milky Way star cloud", NsomTargetClass.OPEN_CLUSTER),
        ("M40", "Optical Double", NsomTargetClass.DOUBLE_STAR),
        ("M73", "Asterism", NsomTargetClass.OPEN_CLUSTER),
    )

    for name, object_type, expected in targets:
        target = SimpleNamespace(id=f"messier-{name}", name=name, object_type=object_type)
        assert target_class_from_runtime_target(target) is expected


def test_unique_targets_use_normalized_non_empty_id_and_keep_stable_order() -> None:
    first = SimpleNamespace(id=" Messier-M31 ", name="M31")
    duplicate = {"id": "messier-m31", "name": "M31 duplicate"}
    anonymous_first = SimpleNamespace(id="", name="Anonymous 1")
    anonymous_second = SimpleNamespace(id="", name="Anonymous 2")

    unique = unique_targets_by_id(
        (first, duplicate, anonymous_first, anonymous_second)
    )

    assert unique == (first, anonymous_first, anonymous_second)
