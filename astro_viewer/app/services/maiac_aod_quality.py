"""Decode the MAIAC AOD quality bitfield used by provider eligibility checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaiacAodQuality:
    raw: int
    cloud_mask: int
    adjacency_mask: int
    aod_quality: int

    @property
    def is_best_quality(self) -> bool:
        return self.cloud_mask == 1 and self.adjacency_mask == 0 and self.aod_quality == 0


def decode_maiac_aod_qa(value: int | None) -> MaiacAodQuality | None:
    if value is None:
        return None
    raw = int(value) & 0xFFFF
    # MAIAC AOD_QA uses bits 0-2 for cloud, 5-7 for adjacency and 8-11 for AOD quality.
    return MaiacAodQuality(
        raw=raw,
        cloud_mask=raw & 0b111,
        adjacency_mask=(raw >> 5) & 0b111,
        aod_quality=(raw >> 8) & 0b1111,
    )


def is_best_quality_maiac_aod(value: int | None) -> bool:
    quality = decode_maiac_aod_qa(value)
    return quality is not None and quality.is_best_quality
