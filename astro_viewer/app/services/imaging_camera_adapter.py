"""Normalize catalogue and smart-telescope cameras into one domain shape."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.imaging import ImagingCamera, ImagingCameraKind


class ImagingCameraAdapter:
    """Normalizes persisted and integrated photographic camera shapes."""

    @staticmethod
    def from_integrated_telescope(telescope: Telescope) -> ImagingCamera:
        system = telescope.integrated_imaging
        if (
            not telescope.has_complete_integrated_imaging
            or system is None
        ):
            raise ValueError(
                "Smart telescope integrated sensor geometry is incomplete."
            )
        return ImagingCamera(
            id=f"smart-integrated-camera:{telescope.id}",
            name=f"{telescope.name} - {system.sensor_model}",
            kind=ImagingCameraKind.SMART_INTEGRATED,
            sensor_width_mm=float(system.sensor_width_mm),
            sensor_height_mm=float(system.sensor_height_mm),
            resolution_width_px=int(system.resolution_width_px),
            resolution_height_px=int(system.resolution_height_px),
            pixel_size_um=float(system.pixel_size_um),
            bit_depth=int(system.bit_depth),
            camera_class="ALL_ROUND",
            sensor_technology="CMOS",
            color_mode=system.color_mode,
            full_resolution_fps=system.full_resolution_fps,
            cooled=False,
            shutter_type="ROLLING",
            supports_live_stacking=system.supports_live_stacking,
            supports_video=system.supports_video,
            supports_mosaic=system.supports_mosaic,
            exposure_control_mode=system.exposure_control_mode,
            integrated_filter_codes=system.filter_codes,
        )

    @classmethod
    def from_astronomy_catalogue(
        cls,
        item: Mapping[str, object],
    ) -> ImagingCamera:
        return ImagingCamera(
            id=cls._text(item, "catalog_id"),
            name=cls._display_name(item),
            kind=ImagingCameraKind.ASTRONOMY_CAMERA,
            sensor_width_mm=cls._required_float(item, "sensor_width_mm"),
            sensor_height_mm=cls._required_float(item, "sensor_height_mm"),
            resolution_width_px=cls._required_int(item, "resolution_width_px"),
            resolution_height_px=cls._required_int(item, "resolution_height_px"),
            pixel_size_um=cls._required_float(item, "pixel_size_um"),
            bit_depth=cls._required_int(item, "bit_depth"),
            camera_class=cls._text(item, "camera_class"),
            sensor_technology=cls._text(item, "sensor_technology"),
            color_mode=cls._text(item, "color_mode"),
            full_resolution_fps=cls._optional_float(item, "max_fps"),
            cooled=cls._boolean(item.get("cooled")),
            cooling_delta_c=cls._optional_float(item, "cooling_delta_c"),
            shutter_type=cls._text(item, "shutter_type"),
            backfocus_mm=cls._optional_float(item, "backfocus_mm"),
        )

    @classmethod
    def from_camera_body_catalogue(
        cls,
        item: Mapping[str, object],
    ) -> ImagingCamera:
        sensor_width_mm = cls._required_float(item, "sensor_width_mm")
        sensor_height_mm = cls._required_float(item, "sensor_height_mm")
        resolution_width_px = cls._required_int(item, "resolution_width_px")
        resolution_height_px = cls._required_int(item, "resolution_height_px")
        pixel_size_um = cls._pixel_size_from_geometry(
            sensor_width_mm,
            sensor_height_mm,
            resolution_width_px,
            resolution_height_px,
        )
        return ImagingCamera(
            id=cls._text(item, "catalog_id"),
            name=cls._display_name(item),
            kind=ImagingCameraKind.CAMERA_BODY,
            sensor_width_mm=sensor_width_mm,
            sensor_height_mm=sensor_height_mm,
            resolution_width_px=resolution_width_px,
            resolution_height_px=resolution_height_px,
            pixel_size_um=pixel_size_um,
            bit_depth=cls._required_int(item, "raw_bit_depth"),
            body_type=cls._text(item, "body_type"),
            sensor_format=cls._text(item, "sensor_format"),
            lens_mount=cls._text(item, "lens_mount"),
            video_width_px=cls._optional_int(item, "max_video_width_px"),
            video_height_px=cls._optional_int(item, "max_video_height_px"),
            video_fps=cls._optional_float(item, "max_video_fps"),
            live_view=cls._boolean(item.get("live_view")),
            bulb_mode=cls._boolean(item.get("bulb_mode")),
        )

    @classmethod
    def from_catalogues(
        cls,
        astronomy_cameras: Iterable[Mapping[str, object]],
        camera_bodies: Iterable[Mapping[str, object]],
    ) -> list[ImagingCamera]:
        return [
            *(
                cls.from_astronomy_catalogue(item)
                for item in astronomy_cameras
            ),
            *(cls.from_camera_body_catalogue(item) for item in camera_bodies),
        ]

    @staticmethod
    def _pixel_size_from_geometry(
        sensor_width_mm: float,
        sensor_height_mm: float,
        resolution_width_px: int,
        resolution_height_px: int,
    ) -> float:
        if (
            not math.isfinite(sensor_width_mm)
            or not math.isfinite(sensor_height_mm)
            or sensor_width_mm <= 0
            or sensor_height_mm <= 0
            or resolution_width_px <= 0
            or resolution_height_px <= 0
        ):
            raise ValueError("Camera sensor geometry must be positive and finite.")
        horizontal_um = sensor_width_mm * 1000.0 / resolution_width_px
        vertical_um = sensor_height_mm * 1000.0 / resolution_height_px
        return round((horizontal_um + vertical_um) / 2.0, 3)

    @staticmethod
    def _display_name(item: Mapping[str, object]) -> str:
        display_name = str(item.get("display_name") or "").strip()
        if display_name:
            return display_name
        return " ".join(
            value
            for value in (
                str(item.get("brand") or "").strip(),
                str(item.get("model") or "").strip(),
            )
            if value
        )

    @staticmethod
    def _text(item: Mapping[str, object], key: str) -> str:
        return str(item.get(key) or "").strip()

    @staticmethod
    def _required_float(item: Mapping[str, object], key: str) -> float:
        try:
            return float(item[key])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid required camera field: {key}.") from error

    @staticmethod
    def _required_int(item: Mapping[str, object], key: str) -> int:
        try:
            return int(item[key])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid required camera field: {key}.") from error

    @staticmethod
    def _optional_float(
        item: Mapping[str, object],
        key: str,
    ) -> float | None:
        value = item.get(key)
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid optional camera field: {key}.") from error

    @staticmethod
    def _optional_int(
        item: Mapping[str, object],
        key: str,
    ) -> int | None:
        value = item.get(key)
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid optional camera field: {key}.") from error

    @staticmethod
    def _boolean(value: object) -> bool:
        if isinstance(value, str):
            return value.strip().casefold() in {"1", "true", "yes", "on"}
        return bool(value)
