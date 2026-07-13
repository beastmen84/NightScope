from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.services.sky_compass_service import SkyCompassService


APP_CONTROLLER = Path(__file__).resolve().parents[1] / "app" / "viewmodels" / "app_controller.py"
HOME_PAGE = Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "HomePage.qml"
GLASS_CARD = Path(__file__).resolve().parents[1] / "app" / "ui" / "components" / "GlassCard.qml"


def test_sky_compass_ranks_broad_direction_from_home_targets() -> None:
    service = SkyCompassService()
    m13 = _object("messier-M13", "M13", "Ammasso globulare", "Nord-Est", 72)
    m92 = _object("messier-M92", "M92", "Ammasso globulare", "Nord-Est", 58)
    venus = _object("venus", "Venere", "Pianeta", "Est", 94)
    plan = [_plan_item(m13)]

    result = service.compass([venus, m92, m13], plan, m13, has_location=True)

    assert result["available"] is True
    assert result["direction"] == "Nord-Est"
    assert result["targetCount"] == 2
    assert result["zoneLabel"] == "Migliore zona adesso"
    assert result["targetCountLabel"] == "2 target osservabili ora"
    assert result["primaryTargets"][0]["id"] == "messier-M13"
    assert [item["name"] for item in result["primaryTargets"]] == ["M13", "M92"]
    assert "targetNames" not in result
    assert "updatedLabel" not in result
    assert result["decisionReasons"][0] == "M13 guida la scelta in questo momento"
    assert any("Più ammassi nella stessa zona" in reason for reason in result["decisionReasons"])
    assert any("osservabili ora" in reason.lower() for reason in result["decisionReasons"])
    assert not any("Due ottimi oggetti deep sky" in reason for reason in result["decisionReasons"])
    assert result["alternatives"][0]["direction"] == "Est"


def test_sky_compass_skips_targets_without_current_direction() -> None:
    service = SkyCompassService()

    result = service.compass(
        [
            _object("messier-M13", "M13", "Ammasso globulare", "n/d", 80),
            _object("messier-M92", "M92", "Ammasso globulare", "Ovest", 60),
        ],
        [],
        None,
        has_location=True,
    )

    assert result["available"] is True
    assert result["direction"] == "Ovest"
    assert result["primaryTargets"][0]["name"] == "M92"


def test_sky_compass_counts_each_target_id_once() -> None:
    first = _object("messier-M13", "M13", "Ammasso globulare", "Nord-Est", 72)
    duplicate = replace(first, id=" MESSIER-M13 ", name="Duplicate", score=99)

    result = SkyCompassService().compass(
        [first, duplicate],
        [],
        None,
        has_location=True,
    )

    assert result["targetCount"] == 1
    assert [item["id"] for item in result["targets"]] == ["messier-M13"]


def test_sky_compass_no_location_fallback() -> None:
    service = SkyCompassService()

    result = service.compass([_object("mars", "Marte", "Pianeta", "Sud", 80)], [], None, has_location=False)

    assert result["available"] is False
    assert result["reason"] == "no_location"
    assert "località" in result["message"]


def test_sky_compass_direction_buckets_are_eight_sector() -> None:
    service = SkyCompassService()

    assert service.normalize_direction("Nord-Est") == "Nord-Est"
    assert service.normalize_direction("Sud-Est") == "Sud-Est"
    assert service.normalize_direction("Sud-Ovest") == "Sud-Ovest"
    assert service.normalize_direction("Nord-Ovest") == "Nord-Ovest"
    assert service.normalize_direction("Nord") == "Nord"
    assert service.normalize_direction("Est") == "Est"
    assert service.normalize_direction("Sud") == "Sud"
    assert service.normalize_direction("Ovest") == "Ovest"


def test_sky_compass_presents_max_three_primary_targets_and_other_count() -> None:
    service = SkyCompassService()

    result = service.compass(
        [
            _object("saturn", "Saturno", "Pianeta", "Sud", 92),
            _object("neptune", "Nettuno", "Pianeta", "Sud", 70),
            _object("messier-M11", "M11 Wild Duck Cluster", "Ammasso aperto", "Sud", 64),
            _object("messier-M15", "M15 Great Pegasus Cluster", "Ammasso globulare", "Sud", 62),
        ],
        [],
        None,
        has_location=True,
    )

    assert [item["name"] for item in result["primaryTargets"]] == [
        "Saturno",
        "Nettuno",
        "M11 Wild Duck Cluster",
    ]
    assert [item["id"] for item in result["targets"]] == [
        "saturn",
        "neptune",
        "messier-M11",
        "messier-M15",
    ]
    assert result["otherTargetCount"] == 1
    assert result["otherTargetCountLabel"] == "+1 altro target"
    assert len(result["decisionReasons"]) <= 3
    assert not any("score" in reason.lower() for reason in result["decisionReasons"])
    assert "Pianeti e deep sky nella stessa zona" in result["decisionReasons"]


def test_sky_compass_uses_home_filtered_planets_not_raw_solar_system_objects() -> None:
    body = _python_function_body("_sky_compass_candidates")
    pool_body = _python_function_body("_tonight_target_pool")

    assert "_tonight_target_pool()" in body
    assert "_home_visible_objects(self._visible_planets)" in pool_body
    assert "_solar_system_objects" not in body


def test_sky_compass_excludes_targets_that_are_not_observable_now() -> None:
    service = SkyCompassService()
    future_target = _object("future", "Future", "Pianeta", "Sud", 100)
    current_target = _object("current", "Current", "Pianeta", "Est", 60)

    result = service.compass(
        [
            replace(future_target, observable_now=False),
            replace(current_target, observable_now=True),
        ],
        [],
        None,
        has_location=True,
    )

    assert result["direction"] == "Est"
    assert [item["id"] for item in result["targets"]] == ["current"]


def test_home_replaces_sky_map_with_sky_compass_without_timer() -> None:
    source = HOME_PAGE.read_text(encoding="utf-8")
    glass_card_source = GLASS_CARD.read_text(encoding="utf-8")
    sky_compass_block = source[
        source.index("id: skyCompassCard") : source.index('text: qsTr("Piano della notte")')
    ]
    events_title_index = source.index('title: qsTr("Prossimi eventi")')
    events_start_index = source.rindex("\n            GlassCard {", 0, events_title_index)
    events_block = source[events_start_index:]

    assert source.index('title: qsTr("Sky Compass")') < source.index(
        'text: qsTr("Piano della notte")'
    )
    assert source.index('title: qsTr("Prossimi eventi")') > source.index(
        'title: root.nightAlternativesOverview.title || qsTr("Altri oggetti visibili stasera")'
    )
    assert 'title: qsTr("Mappa cielo")' not in source
    assert "controller.skyMap" not in source
    assert "columns: skyCompassCard.wide ? 3 : skyCompassCard.medium ? 2 : 1" in sky_compass_block
    assert "Layout.minimumHeight: skyCompassCard.compassData.available && wide ? 286 : 0" in sky_compass_block
    assert 'text: skyCompassCard.sessionRecommended ? qsTr("Inizia da") : qsTr("Guarda verso")' in sky_compass_block
    assert "accentColor: theme.teal" in sky_compass_block
    assert "property alias headerContent: headerContentRow.data" in glass_card_source
    assert "id: headerContentRow" in glass_card_source
    assert "headerContent: [" in sky_compass_block
    alternatives_binding = 'text: skyCompassCard.sessionRecommended ? qsTr("Alternative") : qsTr("Altre direzioni")'
    assert alternatives_binding in sky_compass_block
    assert sky_compass_block.index(alternatives_binding) < sky_compass_block.index("GridLayout {")
    assert "Nessuna alternativa utile" not in sky_compass_block
    assert 'function eventAccent(typeCode)' in source
    assert "root.eventAccent(modelData.typeCode)" in source
    assert 'if (typeCode === "meteor_shower")' in source
    assert "accentColor: root.eventAccent(modelData.typeCode)" in events_block
    assert "columns: root.width > 1040 ? 4 : root.width > 760 ? 2 : 1" in events_block
    assert "Layout.preferredHeight: 74" in events_block
    assert "Layout.alignment: Qt.AlignVCenter" in events_block
    assert "root.chronologicalEvents(root.width > 900 ? 8 : 4)" in events_block
    assert "Perché questa direzione?" in source
    assert "Target principali" in source
    assert "skyCompassCanvas" in source
    assert "skyCompassTypeIconKind" in source
    assert "skyCompassTypeLabel" not in source
    assert "skyCompassGeometricTargetCountLabel" in source
    assert "iconKind === \"planet\"" in source
    assert 'property bool sessionRecommended: root.sessionOverview.state === "recommended"' in sky_compass_block
    assert 'qsTr("Dove iniziare stasera") : qsTr("Orientamento del cielo")' in sky_compass_block
    assert 'qsTr("Inizia da") : qsTr("Guarda verso")' in sky_compass_block
    assert 'qsTr("Alternative") : qsTr("Altre direzioni")' in sky_compass_block
    assert 'qsTr("Target principali") : qsTr("Target nella direzione")' in sky_compass_block
    assert "text: modelData.typeLabel || modelData.type" in sky_compass_block
    assert "Migliore zona osservativa" not in source
    assert "targetNames" not in source
    assert "Aggiornato ora" not in source
    assert "Timer {" not in source


def test_sky_compass_payload_exposes_localizable_catalogue_target_type() -> None:
    result = SkyCompassService().compass(
        [_object("m31", "M31", "Spiral galaxy", "Est", 80)],
        [],
        None,
        has_location=True,
    )

    assert result["targets"][0]["type"] == "Spiral galaxy"
    assert result["targets"][0]["typeLabel"] == "Galassia spirale"
    assert result["targets"][0]["typeCode"] == "galaxy"


def test_home_sky_compass_filter_reacts_to_payload_and_scopes_both_cards() -> None:
    source = HOME_PAGE.read_text(encoding="utf-8")

    assert "property bool skyCompassFilterEnabled: false" in source
    assert "readonly property bool skyCompassFilterAvailable:" in source
    assert "function skyCompassTargetState(data)" in source
    assert "function syncSkyCompassFilter(data)" in source
    assert "function skyCompassScopedItems(items)" in source
    assert "state.signature === root.skyCompassFilterTargetSignature" in source
    assert "root.skyCompassFilterEnabled = false" in source
    assert "root.targetFilter = \"all\"" in source
    assert "function onSkyCompassChanged()" in source
    assert "root.syncSkyCompassFilter(root.controller" in source
    assert 'text: qsTr("Solo suggeriti ora")' in source
    assert "enabled: root.skyCompassFilterAvailable" in source
    assert "checkable: true" in source
    assert "checked: root.skyCompassFilterEnabled" in source
    assert "model: root.filteredNightPlanItems()" in source
    assert "return root.skyCompassScopedItems(root.nightPlanOverview.items || [])" in source
    assert "return root.skyCompassScopedItems(root.nightAlternativesOverview.items || [])" in source
    assert "Nessuna tappa del piano nella zona suggerita in questo momento." in source
    assert "Nessun altro oggetto fuori dal piano nella zona suggerita in questo momento." in source


def _object(object_id: str, name: str, object_type: str, direction: str, score: int) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="",
        distance="",
        max_altitude="45 gradi",
        direction=direction,
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        difficulty="Media",
    )


def _plan_item(item: CelestialObject) -> NightPlanItem:
    return NightPlanItem(
        time_label="22:00 sera",
        object_id=item.id,
        name=item.name,
        score=item.score,
        difficulty=item.difficulty,
        setup=item.recommended_setup,
        direction=item.direction,
        image=item.image,
    )


def _python_function_body(name: str) -> str:
    source = APP_CONTROLLER.read_text(encoding="utf-8")
    marker = f"def {name}"
    start = source.index(marker)
    next_def = source.find("\n    def ", start + len(marker))
    if next_def == -1:
        return source[start:]
    return source[start:next_def]
