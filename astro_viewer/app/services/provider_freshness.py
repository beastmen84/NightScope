"""Define canonical freshness weights shared by aerosol provider policies."""

from __future__ import annotations


def aod_freshness_weight(
    age_days: float | None = None,
    freshness_category: str | None = None,
) -> float:
    """Return the canonical NASA AOD freshness weight."""

    if age_days is not None:
        age = max(0.0, age_days)
        if age <= 3.0:
            return 1.0
        if age <= 7.0:
            return 0.5
        return 0.0
    return {
        "current": 1.0,
        "recent": 1.0,
        "stale": 0.5,
        "historical": 0.0,
    }.get(freshness_category_code(freshness_category or ""), 0.0)


def particulate_freshness_weight(
    age_days: float | None = None,
    freshness_category: str | None = None,
) -> float:
    """Return the canonical OpenAQ particulate freshness weight."""

    if age_days is not None:
        age = max(0.0, age_days)
        if age <= 1.0:
            return 1.0
        if age <= 3.0:
            return 0.7
        if age <= 7.0:
            return 0.3
        return 0.0
    return {
        "current": 1.0,
        "recent": 0.7,
        "stale": 0.3,
        "historical": 0.0,
    }.get(freshness_category_code(freshness_category or ""), 0.0)


def freshness_category_code(category: str) -> str:
    normalized = category.strip().lower().replace(" ", "_")
    return normalized or "unavailable"
