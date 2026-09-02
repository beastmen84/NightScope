"""Normalize runtime targets into NSOM identity, class, and intrinsic quality."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any, TypeVar

from astro_viewer.app.models.nsom import (
    IntrinsicTargetQuality,
    NsomDiagnosticScalar,
    NsomTargetClass,
)
from astro_viewer.app.models.target_observation_traits import is_supernova_remnant_type


_SOLAR_SYSTEM_IDS = frozenset(
    {
        "sun",
        "sole",
        "moon",
        "luna",
        "mercury",
        "mercurio",
        "venus",
        "venere",
        "mars",
        "marte",
        "jupiter",
        "giove",
        "saturn",
        "saturno",
        "uranus",
        "urano",
        "neptune",
        "nettuno",
    }
)

_TargetT = TypeVar("_TargetT")


def unique_targets_by_id(targets: Iterable[_TargetT]) -> tuple[_TargetT, ...]:
    """Keep the first occurrence of each non-empty canonical target id."""

    unique: list[_TargetT] = []
    seen_ids: set[str] = set()
    for target in targets:
        target_id = _text_field(target, "id", "object_id").strip().casefold()
        if target_id:
            if target_id in seen_ids:
                continue
            seen_ids.add(target_id)
        unique.append(target)
    return tuple(unique)


def target_class_from_runtime_target(target: Any) -> NsomTargetClass | None:
    """Classify one runtime target through the shared NSOM taxonomy."""

    target_id = _text_field(target, "id", "object_id").lower()
    object_type = _text_field(target, "object_type", "type").lower()
    name = _text_field(target, "name").lower()
    text = f"{target_id} {object_type} {name}"

    if target_id in {"moon", "luna"} or "luna" in text or "moon" in text:
        return NsomTargetClass.MOON
    if "planetary nebula" in text or "nebulosa planetaria" in text:
        return NsomTargetClass.PLANETARY_NEBULA
    if target_id in _SOLAR_SYSTEM_IDS or "pianeta" in text or "planet" in text:
        return NsomTargetClass.PLANET
    if (
        object_type in {"star", "unclassified object"}
        or "stella singola" in text
    ):
        return NsomTargetClass.DOUBLE_STAR
    if "double star" in text or "optical double" in text or "stella doppia" in text:
        return NsomTargetClass.DOUBLE_STAR
    if "globular" in text or "globulare" in text:
        return NsomTargetClass.GLOBULAR_CLUSTER
    if (
        "open cluster" in text
        or "ammasso aperto" in text
        or "star cloud" in text
        or "asterism" in text
        or "asterismo" in text
    ):
        return NsomTargetClass.OPEN_CLUSTER
    if "galaxy" in object_type or "galassia" in object_type:
        return NsomTargetClass.GALAXY
    if is_supernova_remnant_type(text):
        return NsomTargetClass.DIFFUSE_NEBULA
    if "nebula" in text or "nebulosa" in text:
        return NsomTargetClass.DIFFUSE_NEBULA
    if "galaxy" in text or "galassia" in text:
        return NsomTargetClass.GALAXY
    return None


def build_intrinsic_target_quality(target: Any) -> IntrinsicTargetQuality:
    """Build Universe-owned quality without reusing location geometry."""

    object_id = _text_field(target, "id", "object_id")
    name = _text_field(target, "name")
    intrinsic_score = _value(target, "intrinsic_score")
    if intrinsic_score is None:
        intrinsic_score = _value(target, "score", default=0.0)
    source_fields = tuple(
        (key, scalar)
        for key, value in (
            ("object_id", object_id),
            ("name", name),
            ("object_type", _text_field(target, "object_type", "type")),
            ("intrinsic_score", intrinsic_score),
            ("compatibility_score", _value(target, "score")),
            ("magnitude", _text_field(target, "magnitude")),
            ("apparent_size", _text_field(target, "apparent_size")),
        )
        if (scalar := _diagnostic_scalar(value)) not in (None, "")
    )
    return IntrinsicTargetQuality.from_score(
        intrinsic_score,
        object_id=object_id,
        name=name,
        target_class=target_class_from_runtime_target(target),
        magnitude=_text_field(target, "magnitude"),
        angular_size=_text_field(target, "apparent_size"),
        astronomical_visibility=_bool_or_none(_value(target, "visible")),
        source_fields=source_fields,
    )


def _value(target: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(target, Mapping):
            value = target.get(name)
        else:
            value = getattr(target, name, None)
        if value is not None:
            return value
    return default


def _text_field(target: Any, *names: str) -> str:
    value = _value(target, *names, default="")
    return "" if value is None else str(value)


def _bool_or_none(value: Any) -> bool | None:
    return None if value is None else bool(value)


def _diagnostic_scalar(value: Any) -> NsomDiagnosticScalar:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return str(value)
