from __future__ import annotations

from types import SimpleNamespace

from astro_viewer.app.models.nsom import NsomTargetClass
from astro_viewer.app.services.nsom_target import target_class_from_runtime_target


def test_shared_target_classifier_covers_messier_outliers() -> None:
    targets = (
        ("M24", "Milky Way star cloud", NsomTargetClass.OPEN_CLUSTER),
        ("M40", "Optical Double", NsomTargetClass.DOUBLE_STAR),
        ("M73", "Asterism", NsomTargetClass.OPEN_CLUSTER),
    )

    for name, object_type, expected in targets:
        target = SimpleNamespace(id=f"messier-{name}", name=name, object_type=object_type)
        assert target_class_from_runtime_target(target) is expected
