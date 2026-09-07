"""Protect detached QML equipment lists, notification routing and localized snapshot parity."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QObject, Signal, Slot, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from astro_viewer.app.services.localization import (
    activate_language_pack,
    render_payload,
    tr,
)
from astro_viewer.app.services.translation_manager import discover_language_packs
from astro_viewer.app.viewmodels.app_controller import AppController


ROOT = Path(__file__).resolve().parents[2]
CATALOGUES = {
    "telescopeCatalogModels": ("_telescope_catalog_models", "equipmentChanged"),
    "eyepieceCatalog": ("_catalog_eyepieces", "equipmentChanged"),
    "barlowCatalog": ("_catalog_barlows", "equipmentChanged"),
    "binocularCatalog": ("_catalog_binoculars", "equipmentChanged"),
    "filterCatalog": ("_catalog_filters", "equipmentChanged"),
    "reducerCatalog": ("_catalog_reducers", "equipmentChanged"),
    "astronomyCameraCatalog": ("_astronomy_camera_catalog", "cameraCatalogChanged"),
    "cameraBodyCatalog": ("_camera_body_catalog", "cameraCatalogChanged"),
    "profileEquipmentCatalog": (None, "profileInventoryChanged"),
    "profileAssignedEquipment": (None, "profileInventoryChanged"),
}


class SnapshotSource(QObject):
    equipmentChanged = Signal()
    cameraCatalogChanged = Signal()
    profileInventoryChanged = Signal()

    def __init__(self):
        super().__init__()
        self.calls = 0
        self.rows = [{"id": str(index), "name": f"Model {index}", "nested": {"value": index}} for index in range(150)]

    @Slot(str, result="QVariantList")
    def equipmentCatalogueSnapshot(self, _catalogue):
        self.calls += 1
        return deepcopy(self.rows)


@pytest.mark.parametrize("catalogue", CATALOGUES)
def test_qml_sequence_is_detached_and_only_reloads_for_its_notification(catalogue):
    app = QCoreApplication.instance() or QCoreApplication([])
    source = SnapshotSource()
    engine = QQmlEngine()
    warnings = []
    engine.warnings.connect(lambda entries: warnings.extend(str(entry) for entry in entries))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(
        ROOT / "astro_viewer/app/ui/components/EquipmentCatalogueSnapshot.qml"
    )))
    assert component.isReady(), [str(error) for error in component.errors()]
    snapshot = component.createWithInitialProperties({"controller": source, "catalogue": catalogue})
    assert snapshot is not None
    calls = source.calls
    assert 1 <= calls <= 3

    def rows():
        value = snapshot.property("items")
        return value.toVariant() if hasattr(value, "toVariant") else value

    for _ in range(5):
        assert rows() == source.rows
    assert source.calls == calls
    source.rows[0]["name"] = "Edited model"
    assert rows()[0]["name"] == "Model 0"
    selected_signal = CATALOGUES[catalogue][1]
    for signal in ("equipmentChanged", "cameraCatalogChanged", "profileInventoryChanged"):
        if signal != selected_signal:
            getattr(source, signal).emit()
    assert source.calls == calls
    getattr(source, selected_signal).emit()
    assert source.calls == calls + 1
    assert rows() == source.rows
    source.rows.append({"id": "custom", "name": "New model"})
    getattr(source, selected_signal).emit()
    assert rows()[-1]["id"] == "custom"
    source.rows.pop(0)
    getattr(source, selected_signal).emit()
    assert rows() == source.rows
    assert not warnings
    snapshot.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("language", ["it", "en", "es"])
@pytest.mark.parametrize("catalogue", [name for name, (field, _) in CATALOGUES.items() if field])
def test_snapshot_matches_existing_getter_and_never_mutates_localized_source(language, catalogue):
    QCoreApplication.instance() or QCoreApplication([])
    packs = discover_language_packs(ROOT / "astro_viewer/translations")
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    rows = [{"label": tr("{value} mm", value=25), "nested": [{"label": tr("Sì")}]}]
    setattr(controller, CATALOGUES[catalogue][0], rows)
    before = deepcopy(rows)
    try:
        activate_language_pack(packs[language].payload)
        expected = render_payload(rows)
        actual = controller.equipmentCatalogueSnapshot(catalogue)
        assert actual == getattr(controller, catalogue) == expected
        actual[0]["nested"][0]["label"] = "changed by caller"
        assert rows == before
        assert controller.equipmentCatalogueSnapshot(catalogue) == expected
    finally:
        activate_language_pack(packs["it"].payload)


def test_snapshot_name_is_allowlisted_and_profile_payloads_retain_existing_contract():
    proxy = SimpleNamespace(profileEquipmentCatalog=[{"assigned": False}], profileAssignedEquipment=[{"assigned": True}])
    for name in ("profileEquipmentCatalog", "profileAssignedEquipment"):
        assert AppController.equipmentCatalogueSnapshot(proxy, name) == getattr(proxy, name)
    for name in ("_location", "__dict__", "unknown", ""):
        assert AppController.equipmentCatalogueSnapshot(proxy, name) == []
