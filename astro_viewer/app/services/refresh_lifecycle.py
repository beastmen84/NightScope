from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable


class RefreshDomain(StrEnum):
    LOCATION = "location"
    ASTRONOMY = "astronomy"
    WEATHER = "weather"
    SKY_QUALITY = "sky_quality"
    AIR_QUALITY = "air_quality"
    AOD = "aod"
    EQUIPMENT = "equipment"
    PLANNER = "planner"
    COMPASS = "compass"
    CATALOG = "catalog"


class RefreshReason(StrEnum):
    STARTUP = "startup"
    MANUAL = "manual"
    LOCATION_CHANGED = "location_changed"
    PROVIDER_CHANGED = "provider_changed"
    API_KEY_CHANGED = "api_key_changed"
    EQUIPMENT_CHANGED = "equipment_changed"
    BORTLE_CHANGED = "bortle_changed"
    TTL_EXPIRED = "ttl_expired"
    ASYNC_COMPLETED = "async_completed"
    LIVE_TICK = "live_tick"


LOCATION_DEPENDENT_DOMAINS = frozenset(
    {
        RefreshDomain.LOCATION,
        RefreshDomain.ASTRONOMY,
        RefreshDomain.WEATHER,
        RefreshDomain.SKY_QUALITY,
        RefreshDomain.AIR_QUALITY,
        RefreshDomain.AOD,
        RefreshDomain.EQUIPMENT,
        RefreshDomain.PLANNER,
        RefreshDomain.COMPASS,
        RefreshDomain.CATALOG,
    }
)


REFRESH_DEPENDENCIES: dict[RefreshReason, frozenset[RefreshDomain]] = {
    RefreshReason.STARTUP: LOCATION_DEPENDENT_DOMAINS,
    RefreshReason.MANUAL: frozenset(
        {
            RefreshDomain.WEATHER,
            RefreshDomain.AIR_QUALITY,
            RefreshDomain.AOD,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.LOCATION_CHANGED: LOCATION_DEPENDENT_DOMAINS,
    RefreshReason.PROVIDER_CHANGED: frozenset(
        {
            RefreshDomain.WEATHER,
            RefreshDomain.SKY_QUALITY,
            RefreshDomain.AIR_QUALITY,
            RefreshDomain.AOD,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.API_KEY_CHANGED: frozenset(
        {
            RefreshDomain.SKY_QUALITY,
            RefreshDomain.AIR_QUALITY,
            RefreshDomain.AOD,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.EQUIPMENT_CHANGED: frozenset(
        {
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.BORTLE_CHANGED: frozenset(
        {
            RefreshDomain.SKY_QUALITY,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.TTL_EXPIRED: frozenset(
        {
            RefreshDomain.WEATHER,
            RefreshDomain.AIR_QUALITY,
            RefreshDomain.AOD,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.ASYNC_COMPLETED: frozenset(
        {
            RefreshDomain.SKY_QUALITY,
            RefreshDomain.AIR_QUALITY,
            RefreshDomain.AOD,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.LIVE_TICK: frozenset({RefreshDomain.COMPASS}),
}


@dataclass
class RefreshManager:
    """Tracks refresh lifecycle decisions without owning refresh work."""

    dirty_domains: set[RefreshDomain] = field(default_factory=set)
    last_reason: RefreshReason | None = None

    def domains_for_reason(self, reason: RefreshReason) -> frozenset[RefreshDomain]:
        return REFRESH_DEPENDENCIES[reason]

    def mark_dirty(
        self,
        reason: RefreshReason,
        domains: Iterable[RefreshDomain] | None = None,
    ) -> frozenset[RefreshDomain]:
        affected = (
            frozenset(domains)
            if domains is not None
            else self.domains_for_reason(reason)
        )
        self.dirty_domains.update(affected)
        self.last_reason = reason
        return affected

    def clear_domains(self, domains: Iterable[RefreshDomain]) -> None:
        for domain in domains:
            self.dirty_domains.discard(domain)

    def clear_all(self) -> None:
        self.dirty_domains.clear()

    def is_dirty(self, domain: RefreshDomain) -> bool:
        return domain in self.dirty_domains

    def snapshot(self) -> frozenset[RefreshDomain]:
        return frozenset(self.dirty_domains)
