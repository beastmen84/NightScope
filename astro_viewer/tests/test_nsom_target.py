from __future__ import annotations

from types import SimpleNamespace

from astro_viewer.app.models.nsom import NsomTargetClass
from astro_viewer.app.services.nsom_target import (
    target_class_from_runtime_target,
    unique_targets_by_id,
)


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
