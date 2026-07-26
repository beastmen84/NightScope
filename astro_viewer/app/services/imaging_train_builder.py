from __future__ import annotations

import math
from collections.abc import Iterable
from typing import TypeVar

from astro_viewer.app.models.equipment import Barlow, FocalReducer, Telescope
from astro_viewer.app.models.imaging import (
    ImagingCamera,
    ImagingCameraKind,
    ImagingModifierKind,
    ImagingTrainConfiguration,
)
from astro_viewer.app.services.barlow_equivalence import (
    optically_distinct_barlows,
)


ARCSECONDS_PER_RADIAN = 206_264.80624709636
_EquipmentT = TypeVar("_EquipmentT")


class ImagingTrainBuilder:
    """Enumerates valid target-agnostic photographic optical trains."""

    def build(
        self,
        telescopes: Iterable[Telescope],
        cameras: Iterable[ImagingCamera],
        reducers: Iterable[FocalReducer] = (),
        barlows: Iterable[Barlow] = (),
    ) -> list[ImagingTrainConfiguration]:
        valid_telescopes = self._unique_valid_telescopes(telescopes)
        valid_cameras = self._unique_valid_cameras(cameras)
        valid_reducers = self._unique_valid_reducers(reducers)
        valid_barlows = self._unique_valid_barlows(barlows)

        configurations: list[ImagingTrainConfiguration] = []
        for telescope in valid_telescopes:
            telescope_reducers = [
                reducer
                for reducer in valid_reducers
                if telescope.id in reducer.compatible_telescope_ids
            ]
            for camera in valid_cameras:
                configurations.append(
                    self._configuration(telescope, camera)
                )
                configurations.extend(
                    self._configuration(
                        telescope,
                        camera,
                        reducer=reducer,
                    )
                    for reducer in telescope_reducers
                )
                configurations.extend(
                    self._configuration(
                        telescope,
                        camera,
                        barlow=barlow,
                    )
                    for barlow in valid_barlows
                )
        return configurations

    @staticmethod
    def _configuration(
        telescope: Telescope,
        camera: ImagingCamera,
        *,
        reducer: FocalReducer | None = None,
        barlow: Barlow | None = None,
    ) -> ImagingTrainConfiguration:
        if reducer is not None and barlow is not None:
            raise ValueError("Reducer and Barlow cannot share one imaging train.")

        if reducer is not None:
            modifier_kind = ImagingModifierKind.FOCAL_REDUCER
            focal_length_factor = float(reducer.reduction_factor)
            modifier_id = f"reducer:{reducer.id}"
        elif barlow is not None:
            modifier_kind = ImagingModifierKind.BARLOW
            focal_length_factor = float(barlow.multiplier)
            modifier_id = f"barlow:{barlow.id}"
        else:
            modifier_kind = ImagingModifierKind.NONE
            focal_length_factor = 1.0
            modifier_id = "none"

        effective_focal_length_mm = (
            float(telescope.focal_length_mm) * focal_length_factor
        )
        effective_focal_ratio = (
            effective_focal_length_mm / float(telescope.aperture_mm)
        )
        pixel_scale = (
            ARCSECONDS_PER_RADIAN
            * (float(camera.pixel_size_um) / 1000.0)
            / effective_focal_length_mm
        )
        field_width_deg = ImagingTrainBuilder._field_of_view_deg(
            float(camera.sensor_width_mm),
            effective_focal_length_mm,
        )
        field_height_deg = ImagingTrainBuilder._field_of_view_deg(
            float(camera.sensor_height_mm),
            effective_focal_length_mm,
        )
        field_diagonal_deg = ImagingTrainBuilder._field_of_view_deg(
            camera.sensor_diagonal_mm,
            effective_focal_length_mm,
        )

        return ImagingTrainConfiguration(
            configuration_id=(
                f"imaging:telescope:{telescope.id}:camera:{camera.id}:"
                f"modifier:{modifier_id}"
            ),
            telescope=telescope,
            camera=camera,
            reducer=reducer,
            barlow=barlow,
            modifier_kind=modifier_kind,
            focal_length_factor=focal_length_factor,
            effective_focal_length_mm=effective_focal_length_mm,
            effective_focal_ratio=effective_focal_ratio,
            pixel_scale_arcsec_per_pixel=pixel_scale,
            field_width_deg=field_width_deg,
            field_height_deg=field_height_deg,
            field_diagonal_deg=field_diagonal_deg,
        )

    @staticmethod
    def _field_of_view_deg(
        sensor_dimension_mm: float,
        effective_focal_length_mm: float,
    ) -> float:
        return math.degrees(
            2.0
            * math.atan(
                sensor_dimension_mm / (2.0 * effective_focal_length_mm)
            )
        )

    @classmethod
    def _unique_valid_telescopes(
        cls,
        telescopes: Iterable[Telescope],
    ) -> list[Telescope]:
        return cls._unique_by_id(
            telescope
            for telescope in telescopes
            if telescope.id.strip()
            and telescope.name.strip()
            and cls._positive_finite(telescope.aperture_mm)
            and cls._positive_finite(telescope.focal_length_mm)
        )

    @classmethod
    def _unique_valid_cameras(
        cls,
        cameras: Iterable[ImagingCamera],
    ) -> list[ImagingCamera]:
        return cls._unique_by_id(
            camera
            for camera in cameras
            if camera.id.strip()
            and camera.name.strip()
            and isinstance(camera.kind, ImagingCameraKind)
            and cls._positive_finite(camera.sensor_width_mm)
            and cls._positive_finite(camera.sensor_height_mm)
            and cls._positive_finite(camera.resolution_width_px)
            and cls._positive_finite(camera.resolution_height_px)
            and cls._positive_finite(camera.pixel_size_um)
            and cls._positive_finite(camera.bit_depth)
        )

    @classmethod
    def _unique_valid_reducers(
        cls,
        reducers: Iterable[FocalReducer],
    ) -> list[FocalReducer]:
        return cls._unique_by_id(
            reducer
            for reducer in reducers
            if reducer.id.strip()
            and reducer.name.strip()
            and reducer.imaging_compatible
            and cls._positive_finite(reducer.reduction_factor)
            and reducer.reduction_factor < 1.0
        )

    @classmethod
    def _unique_valid_barlows(
        cls,
        barlows: Iterable[Barlow],
    ) -> list[Barlow]:
        return optically_distinct_barlows(
            cls._unique_by_id(
                barlow
                for barlow in barlows
                if barlow.id.strip()
                and barlow.name.strip()
                and cls._positive_finite(barlow.multiplier)
                and barlow.multiplier > 1.0
            )
        )

    @staticmethod
    def _unique_by_id(items: Iterable[_EquipmentT]) -> list[_EquipmentT]:
        unique: list[_EquipmentT] = []
        seen: set[str] = set()
        for item in items:
            item_id = str(getattr(item, "id", "")).strip()
            if item_id in seen:
                continue
            seen.add(item_id)
            unique.append(item)
        return unique

    @staticmethod
    def _positive_finite(value: object) -> bool:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return False
        return math.isfinite(number) and number > 0
