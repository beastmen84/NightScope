from __future__ import annotations

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observation_configuration import ObservationConfiguration
from astro_viewer.app.services.equipment_service import EquipmentService


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
    ) -> list[ObservationConfiguration]:
        configurations: list[ObservationConfiguration] = []
        configurations.extend(self._telescope_configurations(telescopes, eyepieces, barlows or []))
        configurations.extend(self._binocular_configurations(binoculars or []))
        return configurations

    def _telescope_configurations(
        self,
        telescopes: list[Telescope],
        eyepieces: list[Eyepiece],
        barlows: list[Barlow],
    ) -> list[ObservationConfiguration]:
        if not eyepieces:
            return []

        configurations = []
        for telescope in telescopes:
            if not self._equipment_service.has_optical_telescope(telescope):
                continue
            for eyepiece in eyepieces:
                for barlow in self._equipment_service.barlow_options(barlows):
                    for focal_position in self._equipment_service.eyepiece_focal_positions(eyepiece):
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
