from __future__ import annotations

from collections.abc import Mapping, Sequence

from astro_viewer.app.models.equipment import (
    Barlow,
    Binocular,
    Eyepiece,
    Telescope,
)
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.localization import (
    format_compact_number,
    format_number,
    join_text,
    tr,
)
from astro_viewer.app.services.profile_equipment_service import select_by_ids


class EquipmentPresentationService:
    """Builds equipment read models and status copy outside the Qt controller."""

    def __init__(self, equipment_service: EquipmentService) -> None:
        self._equipment_service = equipment_service

    def catalog_items(
        self,
        *,
        telescopes: Sequence[Telescope],
        eyepieces: Sequence[Eyepiece],
        barlows: Sequence[Barlow],
        binoculars: Sequence[Binocular],
        filter_rows: Sequence[dict],
        reducer_rows: Sequence[dict],
        astronomy_camera_rows: Sequence[dict],
        camera_body_rows: Sequence[dict],
    ) -> list[dict]:
        items = telescope_items(telescopes)
        items.extend(eyepiece_items(eyepieces))
        items.extend(barlow_items(barlows))
        items.extend(binocular_items(binoculars))
        items.extend(filter_items(filter_rows))
        items.extend(reducer_items(reducer_rows))
        items.extend(astronomy_camera_items(astronomy_camera_rows))
        items.extend(camera_body_items(camera_body_rows))
        return items

    def assigned_items(
        self,
        *,
        state: Mapping[str, list[str]],
        telescopes: Sequence[Telescope],
        eyepieces: Sequence[Eyepiece],
        barlows: Sequence[Barlow],
        binoculars: Sequence[Binocular],
        filter_rows: Sequence[dict],
        reducer_rows: Sequence[dict],
        astronomy_camera_rows: Sequence[dict],
        camera_body_rows: Sequence[dict],
    ) -> list[dict]:
        assigned_telescopes = select_by_ids(
            telescopes,
            state["telescope_ids"],
        )
        solar_filter_ids = set(
            state["full_aperture_solar_filter_telescope_ids"]
        )
        items = telescope_items(
            assigned_telescopes,
            full_aperture_solar_filter_ids=solar_filter_ids,
        )
        items.extend(
            eyepiece_items(
                select_by_ids(eyepieces, state["eyepiece_ids"]),
                assigned=True,
            )
        )
        items.extend(
            barlow_items(
                select_by_ids(barlows, state["barlow_ids"]),
                assigned=True,
            )
        )
        items.extend(
            binocular_items(
                select_by_ids(binoculars, state["binocular_ids"]),
                assigned=True,
            )
        )
        items.extend(
            filter_items(
                assigned_catalog_rows(filter_rows, state["filter_ids"]),
                assigned=True,
            )
        )
        items.extend(
            reducer_items(
                assigned_catalog_rows(reducer_rows, state["reducer_ids"]),
                assigned=True,
            )
        )
        items.extend(
            astronomy_camera_items(
                assigned_catalog_rows(
                    astronomy_camera_rows,
                    state["astronomy_camera_ids"],
                ),
                assigned=True,
            )
        )
        items.extend(
            camera_body_items(
                assigned_catalog_rows(
                    camera_body_rows,
                    state["camera_body_ids"],
                ),
                assigned=True,
            )
        )
        return items

    def status_message(
        self,
        *,
        telescope: Telescope,
        binoculars: Sequence[Binocular],
        eyepieces: Sequence[Eyepiece],
        barlows: Sequence[Barlow],
    ) -> str:
        if not self._equipment_service.has_optical_telescope(telescope):
            if binoculars:
                return tr(
                    "Profilo con binocolo: configura o seleziona un telescopio "
                    "per usare oculari e Barlow."
                )
            return tr(
                "Modalità Occhio nudo: configura o seleziona un telescopio "
                "per usare oculari e Barlow."
            )
        if not self._equipment_service.can_use_eyepieces(telescope):
            return tr(
                "Telescopio smart attivo: oculari, Barlow e ingrandimenti "
                "visuali non si applicano. Usa il piano EAA/fotografico "
                "integrato."
            )
        if not eyepieces:
            return tr(
                "Telescopio attivo senza oculari: suggerimenti limitati. "
                "Aggiungi oculari per calcoli completi."
            )
        barlow_count = len(barlows)
        barlow_text = (
            tr("1 Barlow")
            if barlow_count == 1
            else tr("{count} Barlow", count=barlow_count)
            if barlow_count > 1
            else tr("nessuna Barlow")
        )
        eyepiece_text = (
            tr("1 oculare")
            if len(eyepieces) == 1
            else tr("{count} oculari", count=len(eyepieces))
        )
        return tr(
            "Profilo attivo: {telescope}. Opzioni di ingrandimento: "
            "{eyepieces}, {barlows}.",
            telescope=telescope.name,
            eyepieces=eyepiece_text,
            barlows=barlow_text,
        )


def telescope_items(
    telescopes: Sequence[Telescope],
    *,
    full_aperture_solar_filter_ids: set[str] | None = None,
) -> list[dict]:
    items = []
    for telescope in telescopes:
        item = {
            "kind": "telescope",
            "id": telescope.id,
            "name": telescope.name,
            "badge": tr("Telescopio"),
            "details": tr(
                "{aperture} mm / {focal_length} mm",
                aperture=format_number(telescope.aperture_mm),
                focal_length=format_number(telescope.focal_length_mm),
            ),
        }
        if full_aperture_solar_filter_ids is None:
            item["type"] = telescope.optical_type
        else:
            item["hasFullApertureSolarFilter"] = (
                telescope.id in full_aperture_solar_filter_ids
            )
        items.append(item)
    return items


def eyepiece_items(
    eyepieces: Sequence[Eyepiece],
    *,
    assigned: bool = False,
) -> list[dict]:
    items = []
    for eyepiece in eyepieces:
        item = {
            "kind": "eyepiece",
            "id": eyepiece.id,
            "name": eyepiece.name,
            "badge": (
                tr("Zoom") if eyepiece.eyepiece_type == "Zoom" else tr("Oculare")
            ),
            "details": eyepiece.to_qml()["focalRangeLabel"],
        }
        if not assigned:
            item["type"] = eyepiece.eyepiece_type
        items.append(item)
    return items


def barlow_items(
    barlows: Sequence[Barlow],
    *,
    assigned: bool = False,
) -> list[dict]:
    items = []
    for barlow in barlows:
        item = {
            "kind": "barlow",
            "id": barlow.id,
            "name": barlow.name,
            "badge": tr("Barlow"),
            "details": tr(
                "{value}x",
                value=format_compact_number(barlow.multiplier),
            ),
        }
        if not assigned:
            item["type"] = tr("Barlow")
        items.append(item)
    return items


def binocular_items(
    binoculars: Sequence[Binocular],
    *,
    assigned: bool = False,
) -> list[dict]:
    items = []
    for binocular in binoculars:
        item = {
            "kind": "binocular",
            "id": binocular.id,
            "name": binocular.name,
            "badge": tr("Binocolo"),
            "details": binocular.to_qml()["specLabel"],
            "secondaryBadge": "IS" if binocular.image_stabilized else "",
        }
        if not assigned:
            item["type"] = (
                tr("Binocolo stabilizzato")
                if binocular.image_stabilized
                else tr("Binocolo")
            )
        items.append(item)
    return items


def filter_items(
    rows: Sequence[dict],
    *,
    assigned: bool = False,
) -> list[dict]:
    items = []
    for row in rows:
        item = {
            "kind": "filter",
            "id": row["catalog_id"],
            "name": row["display_name"],
            "badge": tr("Filtro"),
            "details": row["filter_class_label"],
        }
        if not assigned:
            item["type"] = row["filter_class_label"]
        items.append(item)
    return items


def reducer_items(
    rows: Sequence[dict],
    *,
    assigned: bool = False,
) -> list[dict]:
    items = []
    for row in rows:
        item = {
            "kind": "reducer",
            "id": row["catalog_id"],
            "name": row["display_name"],
            "badge": tr("Riduttore"),
            "details": join_text(
                [
                    tr(
                        "{value}x",
                        value=format_compact_number(
                            float(row["reduction_factor"])
                        ),
                    ),
                    row["optical_system_label"],
                ]
            ),
            "secondaryBadge": reducer_use_label(row),
        }
        if not assigned:
            item["type"] = row["optical_system_label"]
        items.append(item)
    return items


def astronomy_camera_items(
    rows: Sequence[dict],
    *,
    assigned: bool = False,
) -> list[dict]:
    items = []
    for row in rows:
        item = {
            "kind": "astronomy_camera",
            "id": row["catalog_id"],
            "name": row["display_name"],
            "badge": tr("Camera astronomica"),
            "details": join_text(
                [row["camera_class_label"], row["sensor_model"]]
            ),
            "secondaryBadge": row["color_mode_label"],
        }
        if not assigned:
            item["type"] = join_text(
                [row["sensor_technology_label"], row["color_mode_label"]]
            )
        items.append(item)
    return items


def camera_body_items(
    rows: Sequence[dict],
    *,
    assigned: bool = False,
) -> list[dict]:
    items = []
    for row in rows:
        item = {
            "kind": "camera_body",
            "id": row["catalog_id"],
            "name": row["display_name"],
            "badge": tr("Corpo macchina"),
            "details": join_text(
                [row["body_type_label"], row["sensor_format_label"]]
            ),
            "secondaryBadge": row["lens_mount"],
        }
        if not assigned:
            item["type"] = row["lens_mount"]
        items.append(item)
    return items


def reducer_use_label(reducer: Mapping[str, object]) -> str:
    visual = bool(reducer.get("visual_compatible"))
    imaging = bool(reducer.get("imaging_compatible"))
    if visual and imaging:
        return tr("Visuale + foto")
    if visual:
        return tr("Visuale")
    return tr("Fotografico")


def assigned_catalog_rows(
    rows: Sequence[dict],
    assigned_ids: Sequence[str],
) -> list[dict]:
    assigned = set(assigned_ids)
    return [row for row in rows if row["catalog_id"] in assigned]
