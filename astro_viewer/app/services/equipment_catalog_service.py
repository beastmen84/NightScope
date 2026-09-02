from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.models.equipment import (
    Barlow,
    Binocular,
    Eyepiece,
    FocalReducer,
    IntegratedImagingSystem,
    OpticalFilter,
    Telescope,
)
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.localization import content_key, content_text, tr


@dataclass(frozen=True)
class EquipmentCatalogSnapshot:
    telescope_brands: tuple[dict, ...]
    telescope_catalog_models: tuple[dict, ...]
    eyepiece_rows: tuple[dict, ...]
    barlow_rows: tuple[dict, ...]
    binocular_rows: tuple[dict, ...]
    astronomy_camera_rows: tuple[dict, ...]
    camera_body_rows: tuple[dict, ...]
    filter_rows: tuple[dict, ...]
    reducer_rows: tuple[dict, ...]
    telescopes: tuple[Telescope, ...]
    eyepieces: tuple[Eyepiece, ...]
    barlows: tuple[Barlow, ...]
    binoculars: tuple[Binocular, ...]
    filters: tuple[OpticalFilter, ...]
    reducers: tuple[FocalReducer, ...]


class EquipmentCatalogService:
    """Loads and maps equipment catalogues independently from the view model."""

    def __init__(
        self,
        repository: EquipmentCatalogRepository,
        equipment_service: EquipmentService,
    ) -> None:
        self._repository = repository
        self._equipment_service = equipment_service

    def load(self) -> EquipmentCatalogSnapshot:
        telescope_models = localized_equipment_catalog_rows(
            self._repository.models(),
            "telescopes",
        )
        eyepiece_rows = localized_equipment_catalog_rows(
            self._repository.eyepieces(),
            "eyepieces",
        )
        barlow_rows = localized_equipment_catalog_rows(
            self._repository.barlows(),
            "barlows",
        )
        binocular_rows = self._repository.binoculars()
        filter_rows = localized_equipment_catalog_rows(
            self._repository.filters(),
            "filters",
        )
        reducer_rows = localized_equipment_catalog_rows(
            self._repository.reducers(),
            "reducers",
        )
        return EquipmentCatalogSnapshot(
            telescope_brands=tuple(self._repository.brands()),
            telescope_catalog_models=tuple(telescope_models),
            eyepiece_rows=tuple(eyepiece_rows),
            barlow_rows=tuple(barlow_rows),
            binocular_rows=tuple(binocular_rows),
            astronomy_camera_rows=tuple(
                self._repository.astronomy_cameras()
            ),
            camera_body_rows=tuple(self._repository.camera_bodies()),
            filter_rows=tuple(filter_rows),
            reducer_rows=tuple(reducer_rows),
            telescopes=(
                self._equipment_service.naked_eye_telescope(),
                *(telescope_from_catalog_model(row) for row in telescope_models),
            ),
            eyepieces=tuple(eyepiece_from_catalog_row(row) for row in eyepiece_rows),
            barlows=tuple(barlow_from_catalog_row(row) for row in barlow_rows),
            binoculars=tuple(
                binocular_from_catalog_row(row) for row in binocular_rows
            ),
            filters=tuple(filter_from_catalog_row(row) for row in filter_rows),
            reducers=tuple(reducer_from_catalog_row(row) for row in reducer_rows),
        )

    def load_binoculars(self) -> tuple[tuple[dict, ...], tuple[Binocular, ...]]:
        rows = localized_equipment_catalog_rows(
            self._repository.binoculars(),
            "binoculars",
        )
        return tuple(rows), tuple(binocular_from_catalog_row(row) for row in rows)

    def load_cameras(self) -> tuple[tuple[dict, ...], tuple[dict, ...]]:
        return (
            tuple(self._repository.astronomy_cameras()),
            tuple(self._repository.camera_bodies()),
        )

    def telescope_from_profile(
        self,
        profile: dict,
        existing_telescopes: list[Telescope],
    ) -> Telescope | None:
        telescope_id = profile["telescope_id"]
        if telescope_id == "preset:naked-eye":
            return self._equipment_service.naked_eye_telescope()
        if telescope_id == "preset:binoculars":
            return Telescope(
                "preset:binoculars",
                tr("Binocolo 10x50"),
                50,
                500,
                tr("Binocolo"),
                "manuale",
            )
        if telescope_id.startswith("custom-"):
            return next(
                (
                    telescope
                    for telescope in existing_telescopes
                    if telescope.id == telescope_id
                ),
                None,
            )
        model = self._repository.model_by_catalog_id(telescope_id)
        return telescope_from_catalog_model(model) if model else None

    def normalize_telescope_catalog_id(self, telescope_id: str) -> str:
        if (
            not telescope_id
            or telescope_id == self._equipment_service.NAKED_EYE_ID
        ):
            return self._equipment_service.NAKED_EYE_ID
        if telescope_id.startswith("catalog-telescope-"):
            return telescope_id
        model = self._repository.model_by_catalog_id(telescope_id)
        return model["catalog_id"] if model else ""


def localized_equipment_catalog_rows(
    rows: list[dict],
    section_name: str,
) -> list[dict]:
    identity_fields = {
        "telescopes": ("brand", "name"),
        "eyepieces": (
            "brand",
            "model",
            "eyepiece_type",
            "focal_length_mm",
            "min_focal_length_mm",
            "max_focal_length_mm",
        ),
        "barlows": ("brand", "model", "multiplier"),
        "binoculars": ("brand", "model"),
        "filters": ("brand", "model"),
        "reducers": ("brand", "model", "reduction_factor"),
    }
    content_fields = {
        "telescopes": ("optical_type", "notes"),
        "eyepieces": ("notes",),
        "barlows": ("notes",),
        "binoculars": (),
        "filters": ("notes",),
        "reducers": ("connection", "notes"),
    }
    fields = identity_fields[section_name]
    translated_fields = content_fields[section_name]
    localized = []
    for source_row in rows:
        row = dict(source_row)
        if bool(row.get("is_builtin")) and not bool(
            row.get("is_user_modified")
        ):
            item_key = content_key(*(row.get(field) for field in fields))
            for field in translated_fields:
                row[field] = content_text(
                    f"equipment_{section_name}",
                    item_key,
                    field,
                    row.get(field, ""),
                )
        if section_name == "telescopes" and (
            bool(row.get("is_builtin"))
            and not bool(row.get("is_user_modified"))
        ):
            row["optical_type_label"] = row["optical_type"]
        localized.append(row)
    return localized


def telescope_from_catalog_model(model: dict) -> Telescope:
    category = str(model.get("instrument_category") or "TRADITIONAL")
    capabilities = model.get("smart_capabilities") or {}
    integrated_imaging = None
    if category == "SMART_INTEGRATED":
        integrated_imaging = IntegratedImagingSystem(
            sensor_model=str(capabilities.get("sensor_model") or ""),
            sensor_width_mm=capabilities.get("sensor_width_mm"),
            sensor_height_mm=capabilities.get("sensor_height_mm"),
            resolution_width_px=capabilities.get("resolution_width_px"),
            resolution_height_px=capabilities.get("resolution_height_px"),
            pixel_size_um=capabilities.get("pixel_size_um"),
            bit_depth=capabilities.get("bit_depth"),
            color_mode=str(capabilities.get("color_mode") or ""),
            full_resolution_fps=capabilities.get("full_resolution_fps"),
            supports_live_stacking=bool(
                capabilities.get("supports_live_stacking")
            ),
            supports_video=bool(capabilities.get("supports_video")),
            supports_mosaic=bool(capabilities.get("supports_mosaic")),
            exposure_control_mode=str(
                capabilities.get("exposure_control_mode") or "DEVICE_MANAGED"
            ),
            filter_codes=tuple(
                capabilities.get("integrated_filter_codes") or ()
            ),
            specification_source_url=str(
                capabilities.get("specification_source_url") or ""
            ),
        )
    return Telescope(
        id=model["catalog_id"],
        name=f"{model['brand']} {model['name']}",
        aperture_mm=int(model["aperture_mm"]),
        focal_length_mm=int(model["focal_length_mm"]),
        optical_type=model["optical_type"],
        mount=model["mount_type"],
        instrument_category=category,
        supports_optical_visual=bool(
            capabilities.get(
                "supports_optical_visual",
                category != "SMART_INTEGRATED",
            )
        ),
        supports_interchangeable_eyepieces=bool(
            capabilities.get(
                "supports_interchangeable_eyepieces",
                category != "SMART_INTEGRATED",
            )
        ),
        supports_external_cameras=bool(
            capabilities.get(
                "supports_external_cameras",
                category != "SMART_INTEGRATED",
            )
        ),
        supports_external_optical_modifiers=bool(
            capabilities.get(
                "supports_external_optical_modifiers",
                category != "SMART_INTEGRATED",
            )
        ),
        integrated_imaging=integrated_imaging,
    )


def eyepiece_from_catalog_row(row: dict) -> Eyepiece:
    return Eyepiece(
        id=row["catalog_id"],
        name=f"{row['brand']} {row['model']}",
        focal_length_mm=float(
            row.get("focal_length_mm") or row.get("max_focal_length_mm") or 0
        ),
        apparent_field_deg=float(row["apparent_field_deg"]),
        eyepiece_type=str(
            row.get("eyepiece_type") or row.get("type") or "Fixed"
        ),
        min_focal_length_mm=(
            float(row["min_focal_length_mm"])
            if row.get("min_focal_length_mm")
            else None
        ),
        max_focal_length_mm=(
            float(row["max_focal_length_mm"])
            if row.get("max_focal_length_mm")
            else None
        ),
        zoom_click_positions_mm=parse_zoom_click_positions(
            row.get("zoom_click_positions_mm", "")
        ),
    )


def parse_zoom_click_positions(value: str) -> tuple[float, ...]:
    positions = []
    seen = set()
    for part in str(value or "").replace(",", ".").replace("/", ";").split(";"):
        token = part.strip()
        if not token:
            continue
        try:
            position = float(token)
        except ValueError:
            continue
        key = round(position, 3)
        if position <= 0 or key in seen:
            continue
        seen.add(key)
        positions.append(position)
    return tuple(positions)


def barlow_from_catalog_row(row: dict) -> Barlow:
    return Barlow(
        id=row["catalog_id"],
        name=f"{row['brand']} {row['model']} {float(row['multiplier']):g}x",
        multiplier=float(row["multiplier"]),
    )


def binocular_from_catalog_row(row: dict) -> Binocular:
    return Binocular(
        id=row["catalog_id"],
        name=f"{row['brand']} {row['model']}",
        magnification=int(row["magnification"]),
        objective_diameter_mm=int(row["objective_diameter_mm"]),
        image_stabilized=bool(row["image_stabilized"]),
    )


def filter_from_catalog_row(row: dict) -> OpticalFilter:
    return OpticalFilter(
        id=row["catalog_id"],
        name=f"{row['brand']} {row['model']}",
        filter_class=str(row["filter_class"]),
        central_wavelength_nm=(
            float(row["central_wavelength_nm"])
            if row.get("central_wavelength_nm") is not None
            else None
        ),
        bandwidth_nm=(
            float(row["bandwidth_nm"])
            if row.get("bandwidth_nm") is not None
            else None
        ),
        transmission_pct=(
            float(row["transmission_pct"])
            if row.get("transmission_pct") is not None
            else None
        ),
        minimum_aperture_mm=(
            int(row["minimum_aperture_mm"])
            if row.get("minimum_aperture_mm") is not None
            else None
        ),
    )


def reducer_from_catalog_row(row: dict) -> FocalReducer:
    return FocalReducer(
        id=row["catalog_id"],
        name=f"{row['brand']} {row['model']}",
        reduction_factor=float(row["reduction_factor"]),
        optical_system=str(row["optical_system"]),
        connection=str(row.get("connection") or ""),
        backfocus_mm=(
            float(row["backfocus_mm"])
            if row.get("backfocus_mm") is not None
            else None
        ),
        visual_compatible=bool(row.get("visual_compatible")),
        imaging_compatible=bool(row.get("imaging_compatible")),
        corrected_field=bool(row.get("corrected_field")),
        compatible_telescope_ids=tuple(
            row.get("compatible_telescope_ids") or ()
        ),
        compatible_telescope_names=tuple(
            item.get("display_name", "")
            for item in row.get("compatible_telescopes", [])
            if item.get("display_name")
        ),
    )
