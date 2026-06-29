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
    COMPASS_LIVE = "compass_live"
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
    WEATHER_TTL_EXPIRED = "weather_ttl_expired"
    AIR_QUALITY_TTL_EXPIRED = "air_quality_ttl_expired"
    AOD_TTL_EXPIRED = "aod_ttl_expired"
    SKY_QUALITY_TTL_EXPIRED = "sky_quality_ttl_expired"
    ASYNC_COMPLETED = "async_completed"
    WEATHER_COMPLETED = "weather_completed"
    AIR_QUALITY_COMPLETED = "air_quality_completed"
    AOD_COMPLETED = "aod_completed"
    SKY_QUALITY_COMPLETED = "sky_quality_completed"
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
        }
    ),
    RefreshReason.API_KEY_CHANGED: frozenset(
        {
            RefreshDomain.SKY_QUALITY,
            RefreshDomain.AIR_QUALITY,
            RefreshDomain.AOD,
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
    # Generic TTL and async completion reasons are intentionally neutral. Use
    # domain-specific reasons below for operational dispatch.
    RefreshReason.TTL_EXPIRED: frozenset(),
    RefreshReason.WEATHER_TTL_EXPIRED: frozenset(
        {
            RefreshDomain.WEATHER,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.AIR_QUALITY_TTL_EXPIRED: frozenset({RefreshDomain.AIR_QUALITY}),
    RefreshReason.AOD_TTL_EXPIRED: frozenset({RefreshDomain.AOD}),
    RefreshReason.SKY_QUALITY_TTL_EXPIRED: frozenset({RefreshDomain.SKY_QUALITY}),
    RefreshReason.ASYNC_COMPLETED: frozenset(),
    RefreshReason.WEATHER_COMPLETED: frozenset(
        {
            RefreshDomain.WEATHER,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.AIR_QUALITY_COMPLETED: frozenset({RefreshDomain.AIR_QUALITY}),
    RefreshReason.AOD_COMPLETED: frozenset({RefreshDomain.AOD}),
    RefreshReason.SKY_QUALITY_COMPLETED: frozenset(
        {
            RefreshDomain.SKY_QUALITY,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        }
    ),
    RefreshReason.LIVE_TICK: frozenset({RefreshDomain.COMPASS_LIVE}),
}


@dataclass
class RefreshManager:
    """Tracks refresh lifecycle decisions without owning refresh work."""

    dirty_domains: set[RefreshDomain] = field(default_factory=set)
    dirty_reasons: dict[RefreshDomain, RefreshReason] = field(default_factory=dict)
    # Diagnostic only. Operational code must inspect dirty domains and, when
    # needed, per-domain reasons instead of assuming the last event is global.
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
        for domain in affected:
            self.dirty_reasons[domain] = reason
        self.last_reason = reason
        return affected

    def clear_domains(self, domains: Iterable[RefreshDomain]) -> None:
        for domain in domains:
            self.dirty_domains.discard(domain)
            self.dirty_reasons.pop(domain, None)

    def clear_all(self) -> None:
        self.dirty_domains.clear()
        self.dirty_reasons.clear()

    def is_dirty(self, domain: RefreshDomain) -> bool:
        return domain in self.dirty_domains

    def snapshot(self) -> frozenset[RefreshDomain]:
        return frozenset(self.dirty_domains)

    def reason_for_domain(self, domain: RefreshDomain) -> RefreshReason | None:
        return self.dirty_reasons.get(domain)
