from __future__ import annotations

from collections.abc import Callable

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observation_configuration import ObservationConfiguration
from astro_viewer.app.services.equipment_service import EquipmentService

FocalPositionProvider = Callable[[Telescope, Eyepiece, Barlow | None], list[dict]]


class ObservationConfigurationBuilder:
    TELESCOPE = "Telescope"
    BINOCULAR = "Binocular"

    def __init__(self, equipment_service: EquipmentService | None = None) -> None:
        self._equipment_service = equipment_service or EquipmentService()

    def build(
        self,
        telescopes: list[Telescope],
        eyepieces: list[Eyepiece],
        barlows: list[Barlow] | None = None,
        binoculars: list[Binocular] | None = None,
        focal_position_provider: FocalPositionProvider | None = None,
    ) -> list[ObservationConfiguration]:
        configurations: list[ObservationConfiguration] = []
        configurations.extend(
            self.build_telescope_configurations(
                telescopes,
                eyepieces,
                barlows or [],
                focal_position_provider,
            )
        )
        configurations.extend(self._binocular_configurations(binoculars or []))
        return configurations

    def build_telescope_configurations(
        self,
        telescopes: list[Telescope],
        eyepieces: list[Eyepiece],
        barlows: list[Barlow],
        focal_position_provider: FocalPositionProvider | None = None,
    ) -> list[ObservationConfiguration]:
        if not eyepieces:
            return []

        configurations = []
        for telescope in telescopes:
            if not self._equipment_service.can_use_eyepieces(telescope):
                continue
            for eyepiece in eyepieces:
                for barlow in self._equipment_service.barlow_options(barlows):
                    focal_positions = (
                        focal_position_provider(telescope, eyepiece, barlow)
                        if focal_position_provider
                        else self._equipment_service.eyepiece_focal_positions(eyepiece)
                    )
                    for focal_position in focal_positions:
                        values = self._equipment_service.telescope_configuration_values(
                            telescope,
                            eyepiece,
                            focal_position["focal"],
                            barlow,
                        )
                        configurations.append(
                            ObservationConfiguration(
                                configuration_id=self._telescope_configuration_id(
                                    telescope,
                                    eyepiece,
                                    focal_position["position"],
                                    barlow,
                                ),
                                equipment_type=self.TELESCOPE,
                                telescope=telescope,
                                eyepiece=eyepiece,
                                barlow=barlow,
                                focal_position_mm=focal_position["focal"],
                                focal_position_label=focal_position["position"],
                                magnification=values["magnification"],
                                true_field_of_view_deg=values["true_field_of_view_deg"],
                                exit_pupil_mm=values["exit_pupil_mm"],
                                limiting_magnitude_estimate=values["limiting_magnitude_estimate"],
                                resolution_estimate=values["resolution_estimate"],
                                image_stabilized=False,
                            )
                        )
        return configurations

    def _binocular_configurations(self, binoculars: list[Binocular]) -> list[ObservationConfiguration]:
        configurations = []
        for binocular in binoculars:
            if binocular.magnification <= 0 or binocular.objective_diameter_mm <= 0:
                continue
            configurations.append(
                ObservationConfiguration(
                    configuration_id=f"binocular:{binocular.id}",
                    equipment_type=self.BINOCULAR,
                    binocular=binocular,
                    magnification=float(binocular.magnification),
                    exit_pupil_mm=binocular.objective_diameter_mm / binocular.magnification,
                    image_stabilized=binocular.image_stabilized,
                )
            )
        return configurations

    @staticmethod
    def _telescope_configuration_id(
        telescope: Telescope,
        eyepiece: Eyepiece,
        focal_position_label: str,
        barlow: Barlow | None,
    ) -> str:
        barlow_id = barlow.id if barlow else "none"
        return f"telescope:{telescope.id}:eyepiece:{eyepiece.id}:focal:{focal_position_label}:barlow:{barlow_id}"
