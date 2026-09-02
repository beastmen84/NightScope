"""Build and query profile equipment assignments without QObject coupling."""

from __future__ import annotations

from collections.abc import Sequence

from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.models.equipment import (
    Barlow,
    Eyepiece,
    FocalReducer,
    Telescope,
)
from astro_viewer.app.models.imaging_runtime import ImagingRuntimeInventory
from astro_viewer.app.services.equipment_catalog_service import (
    EquipmentCatalogService,
)
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.imaging_camera_adapter import ImagingCameraAdapter


PROFILE_EQUIPMENT_KEYS = (
    "telescope_ids",
    "full_aperture_solar_filter_telescope_ids",
    "eyepiece_ids",
    "barlow_ids",
    "binocular_ids",
    "filter_ids",
    "reducer_ids",
    "astronomy_camera_ids",
    "camera_body_ids",
)


class ProfileEquipmentService:
    """Builds and queries profile equipment state without QObject coupling."""

    def __init__(
        self,
        repository: EquipmentCatalogRepository,
        equipment_service: EquipmentService,
        catalogue_service: EquipmentCatalogService,
    ) -> None:
        self._repository = repository
        self._equipment_service = equipment_service
        self._catalogue_service = catalogue_service

    def initial_profile_equipment(
        self,
        profiles: list[dict],
    ) -> dict[str, dict[str, list[str]]]:
        equipment: dict[str, dict[str, list[str]]] = {}
        for profile in profiles:
            profile_id = int(profile["id"])
            telescope_ids = [
                self._catalogue_service.normalize_telescope_catalog_id(
                    telescope_id
                )
                for telescope_id in self._repository.profile_telescope_ids(
                    profile_id
                )
            ]
            telescope_ids = [item for item in telescope_ids if item]
            solar_filter_telescope_ids = [
                self._catalogue_service.normalize_telescope_catalog_id(
                    telescope_id
                )
                for telescope_id in (
                    self._repository
                    .profile_full_aperture_solar_filter_telescope_ids(
                        profile_id
                    )
                )
            ]
            solar_filter_telescope_ids = [
                telescope_id
                for telescope_id in solar_filter_telescope_ids
                if telescope_id and telescope_id in telescope_ids
            ]
            legacy_telescope_id = (
                profile.get("telescope_id")
                or self._equipment_service.NAKED_EYE_ID
            )
            normalized_legacy_id = (
                self._catalogue_service.normalize_telescope_catalog_id(
                    legacy_telescope_id
                )
            )
            if (
                normalized_legacy_id
                and normalized_legacy_id
                != self._equipment_service.NAKED_EYE_ID
                and normalized_legacy_id not in telescope_ids
            ):
                telescope_ids.append(normalized_legacy_id)
                self._repository.assign_profile_telescope(
                    profile_id,
                    normalized_legacy_id,
                )
                self._repository.update_profile_telescope(
                    profile_id,
                    normalized_legacy_id,
                )
            equipment[str(profile_id)] = {
                "telescope_ids": telescope_ids,
                "full_aperture_solar_filter_telescope_ids": (
                    solar_filter_telescope_ids
                ),
                "eyepiece_ids": self._repository.profile_eyepiece_ids(
                    profile_id
                ),
                "barlow_ids": self._repository.profile_barlow_ids(profile_id),
                "binocular_ids": self._repository.profile_binocular_ids(
                    profile_id
                ),
                "filter_ids": self._repository.profile_filter_ids(profile_id),
                "reducer_ids": self._repository.profile_reducer_ids(profile_id),
                "astronomy_camera_ids": (
                    self._repository.profile_astronomy_camera_ids(profile_id)
                ),
                "camera_body_ids": self._repository.profile_camera_body_ids(
                    profile_id
                ),
            }
        return equipment

    def refresh_profiles(
        self,
        profile_equipment: dict[str, dict[str, list[str]]],
    ) -> list[dict]:
        profiles = self._repository.profiles()
        for profile in profiles:
            state = profile_equipment.setdefault(
                str(profile["id"]),
                empty_profile_equipment_state(),
            )
            ensure_profile_equipment_state(state)
        return profiles

    def active_profile(self, profiles: list[dict]) -> dict | None:
        return active_profile(profiles)

    def active_profile_state(
        self,
        profiles: list[dict],
        profile_equipment: dict[str, dict[str, list[str]]],
    ) -> dict[str, list[str]]:
        return active_profile_state(profiles, profile_equipment)

    def profile_key_by_name(
        self,
        profiles: list[dict],
        profile_name: str,
    ) -> str:
        return profile_key_by_name(profiles, profile_name)

    def imaging_inventory(
        self,
        *,
        profile: dict | None,
        state: dict[str, list[str]],
        telescopes: Sequence[Telescope],
        astronomy_camera_rows: Sequence[dict],
        camera_body_rows: Sequence[dict],
        reducers: Sequence[FocalReducer],
        barlows: Sequence[Barlow],
    ) -> ImagingRuntimeInventory:
        return imaging_inventory(
            profile=profile,
            state=state,
            telescopes=telescopes,
            astronomy_camera_rows=astronomy_camera_rows,
            camera_body_rows=camera_body_rows,
            reducers=reducers,
            barlows=barlows,
        )


def empty_profile_equipment_state() -> dict[str, list[str]]:
    return {key: [] for key in PROFILE_EQUIPMENT_KEYS}


def active_profile(profiles: list[dict]) -> dict | None:
    return next(
        (
            profile
            for profile in profiles
            if int(profile.get("active", 0)) == 1
        ),
        None,
    )


def active_profile_state(
    profiles: list[dict],
    profile_equipment: dict[str, dict[str, list[str]]],
) -> dict[str, list[str]]:
    profile = active_profile(profiles)
    if not profile:
        return empty_profile_equipment_state()
    state = profile_equipment.setdefault(
        str(profile["id"]),
        empty_profile_equipment_state(),
    )
    ensure_profile_equipment_state(state)
    return state


def profile_key_by_name(profiles: list[dict], profile_name: str) -> str:
    for profile in profiles:
        if (
            profile["profile_name"].strip().lower()
            == profile_name.strip().lower()
        ):
            return str(profile["id"])
    return profile_name.strip().lower()


def imaging_inventory(
    *,
    profile: dict | None,
    state: dict[str, list[str]],
    telescopes: Sequence[Telescope],
    astronomy_camera_rows: Sequence[dict],
    camera_body_rows: Sequence[dict],
    reducers: Sequence[FocalReducer],
    barlows: Sequence[Barlow],
) -> ImagingRuntimeInventory:
    if profile is None:
        return ImagingRuntimeInventory()
    assigned_telescopes = tuple(select_by_ids(telescopes, state["telescope_ids"]))
    assigned_telescope_ids = {
        telescope.id for telescope in assigned_telescopes
    }
    selected_astronomy_cameras = select_rows_by_catalog_id(
        astronomy_camera_rows,
        state["astronomy_camera_ids"],
    )
    selected_camera_bodies = select_rows_by_catalog_id(
        camera_body_rows,
        state["camera_body_ids"],
    )
    cameras = tuple(
        ImagingCameraAdapter.from_catalogues(
            selected_astronomy_cameras,
            selected_camera_bodies,
        )
    )
    solar_filter_ids = tuple(
        dict.fromkeys(
            telescope_id
            for telescope_id in state[
                "full_aperture_solar_filter_telescope_ids"
            ]
            if telescope_id in assigned_telescope_ids
        )
    )
    return ImagingRuntimeInventory(
        profile_id=str(profile.get("id") or "").strip(),
        telescopes=assigned_telescopes,
        cameras=cameras,
        reducers=tuple(select_by_ids(reducers, state["reducer_ids"])),
        barlows=tuple(select_by_ids(barlows, state["barlow_ids"])),
        full_aperture_solar_filter_telescope_ids=solar_filter_ids,
    )


def ensure_profile_equipment_state(state: dict[str, list[str]]) -> None:
    for key in PROFILE_EQUIPMENT_KEYS:
        state.setdefault(key, [])


def presented_equipment_profiles(profiles: list[dict]) -> list[dict]:
    return [dict(profile) for profile in profiles]


def select_by_ids(items: Sequence, item_ids: Sequence[str]) -> list:
    items_by_id = {item.id: item for item in items}
    return [items_by_id[item_id] for item_id in item_ids if item_id in items_by_id]


def select_rows_by_catalog_id(
    rows: Sequence[dict],
    item_ids: Sequence[str],
) -> list[dict]:
    rows_by_id = {str(item["catalog_id"]): item for item in rows}
    return [rows_by_id[item_id] for item_id in item_ids if item_id in rows_by_id]


def find_by_id(items: Sequence, item_id: str):
    return next((item for item in items if item.id == item_id), None)


def find_row_by_catalog_id(rows: Sequence[dict], item_id: str) -> dict | None:
    return next(
        (item for item in rows if item["catalog_id"] == item_id),
        None,
    )


def index_for_telescope(
    telescopes: Sequence[Telescope],
    telescope_id: str,
) -> int:
    for index, telescope in enumerate(telescopes):
        if telescope.id == telescope_id:
            return index
    return 0


def telescope_exists(
    telescopes: Sequence[Telescope],
    telescope: Telescope,
    naked_eye_id: str,
    ignore_id: str = "",
) -> bool:
    return any(
        existing.id != ignore_id
        and existing.id != naked_eye_id
        and existing.name.strip().lower() == telescope.name.strip().lower()
        and existing.aperture_mm == telescope.aperture_mm
        and existing.focal_length_mm == telescope.focal_length_mm
        and existing.optical_type.strip().lower()
        == telescope.optical_type.strip().lower()
        and existing.mount.strip().lower() == telescope.mount.strip().lower()
        for existing in telescopes
    )


def eyepiece_exists(
    eyepieces: Sequence[Eyepiece],
    eyepiece: Eyepiece,
    ignore_id: str = "",
) -> bool:
    return any(
        existing.id != ignore_id
        and existing.name.strip().lower() == eyepiece.name.strip().lower()
        and round(existing.focal_length_mm, 3)
        == round(eyepiece.focal_length_mm, 3)
        and round(existing.apparent_field_deg, 3)
        == round(eyepiece.apparent_field_deg, 3)
        and existing.eyepiece_type == eyepiece.eyepiece_type
        and round(existing.min_focal_length_mm or 0.0, 3)
        == round(eyepiece.min_focal_length_mm or 0.0, 3)
        and round(existing.max_focal_length_mm or 0.0, 3)
        == round(eyepiece.max_focal_length_mm or 0.0, 3)
        for existing in eyepieces
    )


def barlow_exists(
    barlows: Sequence[Barlow],
    barlow: Barlow,
    ignore_id: str = "",
) -> bool:
    return any(
        existing.id != ignore_id
        and existing.name.strip().lower() == barlow.name.strip().lower()
        and round(existing.multiplier, 3) == round(barlow.multiplier, 3)
        for existing in barlows
    )


def next_custom_id(prefix: str, existing_ids: list[str]) -> str:
    highest = 0
    for item_id in existing_ids:
        if not item_id.startswith(prefix):
            continue
        try:
            highest = max(highest, int(item_id.removeprefix(prefix)))
        except ValueError:
            continue
    return f"{prefix}{highest + 1}"
