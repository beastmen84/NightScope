"""Parse and validate equipment form payloads at the application boundary."""

from __future__ import annotations

import math
from collections.abc import Mapping


class EquipmentInputError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def parse_astronomy_camera_inputs(
    payload: Mapping[str, object],
) -> tuple:
    try:
        sensor_width = required_float_input(payload.get("sensor_width_mm"))
        sensor_height = required_float_input(payload.get("sensor_height_mm"))
        resolution_width = positive_int(
            str(payload.get("resolution_width_px") or "")
        )
        resolution_height = positive_int(
            str(payload.get("resolution_height_px") or "")
        )
        pixel_size = required_float_input(payload.get("pixel_size_um"))
        bit_depth = positive_int(str(payload.get("bit_depth") or ""))
        max_fps = optional_float_input(str(payload.get("max_fps") or ""))
        cooling_delta = optional_float_input(
            str(payload.get("cooling_delta_c") or "")
        )
        backfocus = optional_float_input(
            str(payload.get("backfocus_mm") or "")
        )
    except (TypeError, ValueError) as exc:
        raise EquipmentInputError("astronomy_camera_invalid") from exc
    return (
        str(payload.get("brand") or ""),
        str(payload.get("model") or ""),
        str(payload.get("camera_class") or ""),
        str(payload.get("sensor_model") or ""),
        str(payload.get("sensor_technology") or ""),
        str(payload.get("color_mode") or ""),
        sensor_width,
        sensor_height,
        resolution_width,
        resolution_height,
        pixel_size,
        bit_depth,
        max_fps,
        bool(payload.get("cooled")),
        cooling_delta,
        str(payload.get("shutter_type") or ""),
        backfocus,
        str(payload.get("source_url") or ""),
    )


def parse_camera_body_inputs(payload: Mapping[str, object]) -> tuple:
    try:
        sensor_width = required_float_input(payload.get("sensor_width_mm"))
        sensor_height = required_float_input(payload.get("sensor_height_mm"))
        resolution_width = positive_int(
            str(payload.get("resolution_width_px") or "")
        )
        resolution_height = positive_int(
            str(payload.get("resolution_height_px") or "")
        )
        raw_bit_depth = positive_int(str(payload.get("raw_bit_depth") or ""))
        video_width = optional_positive_int_input(
            payload.get("max_video_width_px")
        )
        video_height = optional_positive_int_input(
            payload.get("max_video_height_px")
        )
        video_fps = optional_float_input(
            str(payload.get("max_video_fps") or "")
        )
    except (TypeError, ValueError) as exc:
        raise EquipmentInputError("camera_body_invalid") from exc
    return (
        str(payload.get("brand") or ""),
        str(payload.get("model") or ""),
        str(payload.get("body_type") or ""),
        str(payload.get("sensor_format") or ""),
        str(payload.get("lens_mount") or ""),
        sensor_width,
        sensor_height,
        resolution_width,
        resolution_height,
        raw_bit_depth,
        video_width,
        video_height,
        video_fps,
        bool(payload.get("live_view")),
        bool(payload.get("bulb_mode")),
        str(payload.get("source_url") or ""),
    )


def parse_filter_inputs(
    central_wavelength: str,
    bandwidth: str,
    transmission: str,
    minimum_aperture: str,
) -> tuple[float | None, float | None, float | None, int | None]:
    try:
        central = optional_float_input(central_wavelength)
        width = optional_float_input(bandwidth)
        transmission_pct = optional_float_input(transmission)
        aperture_value = optional_float_input(minimum_aperture)
        if aperture_value is not None and not aperture_value.is_integer():
            raise ValueError
        aperture = int(aperture_value) if aperture_value is not None else None
    except ValueError as exc:
        raise EquipmentInputError("filter_invalid") from exc
    return central, width, transmission_pct, aperture


def parse_reducer_inputs(
    reduction_factor: str,
    backfocus: str,
) -> tuple[float, float | None]:
    try:
        factor = float(reduction_factor.replace(",", "."))
        if not math.isfinite(factor):
            raise ValueError
        backfocus_mm = optional_float_input(backfocus)
    except ValueError as exc:
        raise EquipmentInputError("reducer_invalid") from exc
    return factor, backfocus_mm


def parse_binocular_inputs(
    magnification: str,
    objective_diameter: str,
) -> tuple[int, int]:
    try:
        return positive_int(magnification), positive_int(objective_diameter)
    except ValueError as exc:
        raise EquipmentInputError("binocular_invalid") from exc


def parse_eyepiece_inputs(
    eyepiece_type: str,
    focal: str,
    min_focal: str,
    max_focal: str,
    apparent_field: str,
    afov_range: str,
) -> tuple[float, float, float | None, float | None, float | None, float | None]:
    try:
        apparent = float(apparent_field.replace(",", "."))
        if eyepiece_type == "Zoom":
            min_value = float(min_focal.replace(",", "."))
            max_value = float(max_focal.replace(",", "."))
            focal_value = max_value
            if (
                not all(
                    math.isfinite(value)
                    for value in (apparent, min_value, max_value)
                )
                or min_value <= 0
                or max_value <= 0
                or min_value >= max_value
            ):
                raise ValueError
        else:
            focal_value = float(focal.replace(",", "."))
            min_value = None
            max_value = None
            if not all(
                math.isfinite(value) for value in (apparent, focal_value)
            ):
                raise ValueError
    except ValueError as exc:
        raise EquipmentInputError("eyepiece_invalid") from exc

    afov_min = None
    afov_max = None
    if afov_range.strip():
        parts = [
            part.strip()
            for part in afov_range.replace(",", ".").replace("-", " ").split()
            if part.strip()
        ]
        try:
            if len(parts) != 2:
                raise ValueError
            afov_min = float(parts[0])
            afov_max = float(parts[1])
            if (
                not all(math.isfinite(value) for value in (afov_min, afov_max))
                or afov_min <= 0
                or afov_min > afov_max
                or afov_max > 180
            ):
                raise ValueError
        except ValueError as exc:
            raise EquipmentInputError("eyepiece_afov_invalid") from exc
    if focal_value <= 0 or apparent <= 0:
        raise EquipmentInputError("eyepiece_non_positive")
    return focal_value, apparent, min_value, max_value, afov_min, afov_max


def catalog_id_list(value: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            item.strip()
            for item in str(value or "").split(",")
            if item.strip()
        )
    )


def optional_float_input(value: str) -> float | None:
    clean_value = value.strip()
    if not clean_value:
        return None
    parsed = float(clean_value.replace(",", "."))
    if not math.isfinite(parsed):
        raise ValueError
    return parsed


def required_float_input(value: object) -> float:
    parsed = float(str(value or "").strip().replace(",", "."))
    if not math.isfinite(parsed):
        raise ValueError
    return parsed


def optional_positive_int_input(value: object) -> int | None:
    clean_value = str(value or "").strip()
    return positive_int(clean_value) if clean_value else None


def positive_int(value: str) -> int:
    parsed = float(value.strip().replace(",", "."))
    if not math.isfinite(parsed) or parsed <= 0 or not parsed.is_integer():
        raise ValueError
    return int(parsed)
