from astro_viewer.app.services.catalogue_presentation import (
    catalogue_object_type_label,
    catalogue_observation_type_label,
)


def test_catalogue_object_types_have_italian_display_labels() -> None:
    assert catalogue_object_type_label("Open cluster") == "Ammasso aperto"
    assert catalogue_object_type_label("Dwarf elliptical galaxy") == "Galassia ellittica nana"
    assert catalogue_object_type_label("H II region nebula with cluster") == "Nebulosa H II con ammasso"


def test_catalogue_observation_types_have_italian_display_labels() -> None:
    assert catalogue_observation_type_label("WideField") == "Campo largo"
    assert catalogue_observation_type_label("General") == "Generale"
    assert catalogue_observation_type_label("HighMagnification") == "Alto ingrandimento"


def test_unknown_catalogue_values_remain_unchanged() -> None:
    assert catalogue_object_type_label("Future catalogue type") == "Future catalogue type"
    assert catalogue_observation_type_label("FutureMode") == "FutureMode"
