"""Protect catalogue type, observation mode, and display-name localization."""

from astro_viewer.app.services.catalogue_presentation import (
    catalogue_display_name,
    catalogue_object_type_label,
    catalogue_observation_type_label,
)


def test_catalogue_object_types_have_italian_display_labels() -> None:
    assert catalogue_object_type_label("Open cluster") == "Ammasso aperto"
    assert catalogue_object_type_label("Dwarf elliptical galaxy") == "Galassia ellittica nana"
    assert catalogue_object_type_label("H II region nebula with cluster") == "Nebulosa H II con ammasso"
    assert catalogue_object_type_label("Dark nebula") == "Nebulosa oscura"
    assert catalogue_object_type_label("Irregular galaxy") == "Galassia irregolare"
    assert catalogue_object_type_label("Peculiar galaxy") == "Galassia peculiare"
    assert catalogue_object_type_label("Seyfert galaxy") == "Galassia di Seyfert"
    assert catalogue_object_type_label("Galaxy pair") == "Coppia di galassie"
    assert catalogue_object_type_label("Emission nebula") == "Nebulosa a emissione"
    assert catalogue_object_type_label("Star") == "Stella"
    assert (
        catalogue_object_type_label("Unclassified object")
        == "Oggetto non classificato"
    )


def test_catalogue_observation_types_have_italian_display_labels() -> None:
    assert catalogue_observation_type_label("WideField") == "Campo largo"
    assert catalogue_observation_type_label("General") == "Generale"
    assert catalogue_observation_type_label("HighMagnification") == "Alto ingrandimento"


def test_unknown_catalogue_values_remain_unchanged() -> None:
    assert catalogue_object_type_label("Future catalogue type") == "Future catalogue type"
    assert catalogue_observation_type_label("FutureMode") == "FutureMode"


def test_catalogue_display_name_is_derived_with_designation_first() -> None:
    assert catalogue_display_name("M1", "Crab Nebula") == "M1 Crab Nebula"
    assert catalogue_display_name("M93", "M93") == "M93"
    assert catalogue_display_name("C1", "") == "C1"
