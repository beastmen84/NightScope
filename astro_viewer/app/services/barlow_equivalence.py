"""Collapse optically equivalent Barlows into stable configuration choices."""

from __future__ import annotations

from collections.abc import Iterable

from astro_viewer.app.models.equipment import Barlow
from astro_viewer.app.services.localization import (
    format_compact_number,
    tr,
)


def optically_distinct_barlows(
    barlows: Iterable[Barlow],
) -> list[Barlow]:
    """Collapse Barlows that are indistinguishable to the current model."""

    groups: dict[float, list[Barlow]] = {}
    for barlow in barlows:
        groups.setdefault(round(float(barlow.multiplier), 6), []).append(
            barlow
        )

    distinct: list[Barlow] = []
    for multiplier, alternatives in sorted(groups.items()):
        ordered = sorted(
            alternatives,
            key=lambda item: (str(item.name).casefold(), item.id),
        )
        if len(ordered) == 1:
            distinct.append(ordered[0])
            continue
        distinct.append(
            Barlow(
                id=f"equivalent-barlow:{multiplier:.6g}",
                name=tr(
                    "Barlow {factor}× ({count} opzioni equivalenti)",
                    factor=format_compact_number(
                        multiplier,
                        max_decimals=2,
                    ),
                    count=len(ordered),
                ),
                multiplier=multiplier,
            )
        )
    return distinct
