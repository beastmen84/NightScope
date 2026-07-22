from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from astro_viewer import main as main_module
from astro_viewer.app.services.logging_service import (
    LOG_HANDLER_NAME,
    configure_logging,
)
from tools.audit_qt_bundle import REQUIRED_DLLS, audit_bundle
from tools.generate_third_party_licenses import render_archive
from tools.run_checks import Check, _checks, _run_check
from tools.translation_provider import (
    GOOGLE_TRANSLATE_URL,
    MAX_TRANSLATION_CHARACTERS,
    REQUEST_TIMEOUT,
    GoogleTranslator,
    TranslationProviderError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class _ManualStructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.article_languages: list[str] = []
        self.internal_links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(str(attributes["id"]))
        if attributes.get("data-article"):
            self.article_languages.append(str(attributes["data-article"]))
        href = str(attributes.get("href") or "")
        if href.startswith("#"):
            self.internal_links.append(href[1:])


def _response(*, text: str, status_code: int = 200) -> Mock:
    response = Mock(spec=requests.Response)
    response.text = text
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"HTTP {status_code}"
        )
    else:
        response.raise_for_status.return_value = None
    return response


def test_translation_provider_uses_bounded_request_and_parses_result() -> None:
    http_get = Mock(
        return_value=_response(
            text='<html><div class="result-container">Clear &amp; dark</div></html>'
        )
    )
    translator = GoogleTranslator("it", "en", http_get=http_get)

    assert translator.translate("Limpido e buio") == "Clear & dark"
    http_get.assert_called_once_with(
        GOOGLE_TRANSLATE_URL,
        params={"sl": "it", "tl": "en", "q": "Limpido e buio"},
        headers={
            "Accept": "text/html",
            "User-Agent": "NightScope translation maintenance tool",
        },
        timeout=REQUEST_TIMEOUT,
    )


def test_translation_provider_handles_local_and_invalid_responses() -> None:
    http_get = Mock()
    same_language = GoogleTranslator("it", "it", http_get=http_get)
    assert same_language.translate(" Testo ") == "Testo"
    assert same_language.translate("") == ""
    http_get.assert_not_called()

    missing = GoogleTranslator(
        "it",
        "en",
        http_get=Mock(return_value=_response(text="<html></html>")),
    )
    with pytest.raises(TranslationProviderError, match="unrecognized"):
        missing.translate("Testo")

    failed = GoogleTranslator(
        "it",
        "en",
        http_get=Mock(return_value=_response(text="", status_code=503)),
    )
    with pytest.raises(TranslationProviderError, match="HTTPError"):
        failed.translate("Testo")

    with pytest.raises(ValueError, match="exceeds"):
        missing.translate("x" * (MAX_TRANSLATION_CHARACTERS + 1))


def test_standard_check_plan_runs_one_test_suite_and_optional_security() -> None:
    fast = _checks(include_coverage=False, include_security=False)
    assert [check.name for check in fast] == [
        "pip-check",
        "ruff",
        "compileall",
        "third-party-licenses",
        "pytest",
        "smoke-test",
        "qml-smoke-test",
    ]
    assert sum(check.name.startswith("pytest") for check in fast) == 1
    pytest_check = next(check for check in fast if check.name == "pytest")
    assert pytest_check.args[pytest_check.args.index("-n") + 1] == "4"

    release = _checks(include_coverage=True, include_security=True)
    assert [check.name for check in release].count("pip-audit") == 1
    assert [check.name for check in release].count("pytest-cov") == 1
    assert sum(check.name.startswith("pytest") for check in release) == 1
    coverage_check = next(check for check in release if check.name == "pytest-cov")
    assert "--cov=astro_viewer.app" in coverage_check.args
    assert "--cov=astro_viewer.main" in coverage_check.args
    assert "--cov=astro_viewer" not in coverage_check.args
    assert all(
        check.isolated_runtime
        for check in release
        if check.name in {"smoke-test", "qml-smoke-test"}
    )


def test_smoke_check_uses_and_removes_a_disposable_runtime() -> None:
    completed = Mock(returncode=0)
    with patch(
        "tools.run_checks.subprocess.run", return_value=completed
    ) as run:
        assert (
            _run_check(
                Check("test-smoke", ("-c", "pass"), isolated_runtime=True)
            )
            == 0
        )

    environment = run.call_args.kwargs["env"]
    runtime_dir = Path(environment["NIGHTSCOPE_RUNTIME_DIR"])
    assert run.call_args.kwargs["cwd"] == PROJECT_ROOT
    assert not runtime_dir.exists()


def test_runtime_override_and_log_path_share_the_same_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NIGHTSCOPE_RUNTIME_DIR", str(tmp_path))
    runtime_dir = main_module._resolve_runtime_dir()
    log_path = configure_logging(runtime_dir)

    try:
        assert runtime_dir == tmp_path.resolve()
        assert log_path == runtime_dir / "logs" / "nightscope.log"
        assert log_path.parent.is_dir()
    finally:
        root_logger = logging.getLogger()
        for handler in tuple(root_logger.handlers):
            if handler.get_name() == LOG_HANDLER_NAME:
                root_logger.removeHandler(handler)
                handler.close()


def test_main_falls_back_to_console_when_runtime_log_is_not_writable() -> None:
    args = Mock(qml_smoke_test=False, smoke_test=True)
    with patch(
        "astro_viewer.app.services.logging_service.configure_logging",
        side_effect=PermissionError("read-only runtime"),
    ), patch.object(main_module, "parse_args", return_value=args), patch.object(
        main_module,
        "run_smoke_test",
        return_value=0,
    ) as smoke_test:
        result = main_module.main()

    assert result == 0
    smoke_test.assert_called_once_with()


def test_developer_requirements_include_validation_tools_without_deep_translator() -> None:
    requirements = (PROJECT_ROOT / "requirements-dev.txt").read_text(
        encoding="utf-8"
    )
    for package in ("bandit", "pip-audit", "pytest", "pytest-cov", "pytest-xdist", "ruff"):
        assert package in requirements
    assert "deep-translator" not in requirements


def test_manual_is_packaged_and_linked_from_the_sidebar() -> None:
    spec = (PROJECT_ROOT / "packaging" / "NightScope.spec").read_text(
        encoding="utf-8"
    )
    qml = (
        PROJECT_ROOT / "astro_viewer" / "app" / "ui" / "main.qml"
    ).read_text(encoding="utf-8")
    controller = (
        PROJECT_ROOT
        / "astro_viewer"
        / "app"
        / "viewmodels"
        / "app_controller.py"
    ).read_text(encoding="utf-8")

    assert '(str(ROOT / "manuale.html"), ".")' in spec
    assert "def manualUrl" in controller
    assert 'self._base_dir.parent / "manuale.html"' in controller
    assert "appController.manualUrl" in qml
    assert 'qsTr("Apri manuale")' in qml
    assert 'translationManager.languageCode' in qml


def test_main_exposes_platform_capabilities_to_both_qml_startup_paths() -> None:
    main_source = (PROJECT_ROOT / "astro_viewer" / "main.py").read_text(
        encoding="utf-8"
    )

    assert main_source.count(
        'setContextProperty(\n        "platformCapabilities",'
    ) == 2
    assert main_source.count("PLATFORM_CAPABILITIES.as_qml_context()") == 2


def test_multilingual_manual_has_complete_navigation_and_current_provider_semantics() -> None:
    manual = (PROJECT_ROOT / "manuale.html").read_text(encoding="utf-8")
    parser = _ManualStructureParser()
    parser.feed(manual)

    assert len(parser.ids) == len(set(parser.ids))
    assert parser.internal_links
    assert set(parser.internal_links).issubset(set(parser.ids))
    assert parser.article_languages.count("it") == 2
    assert parser.article_languages.count("en") == 2
    assert parser.article_languages.count("es") == 2
    for language in ("it", "en", "es"):
        for section in (
            "start",
            "location",
            "profiles",
            "home",
            "logic",
            "equipment",
            "catalogue",
            "calendar",
            "weather",
            "log",
            "data-states",
            "privacy",
            "troubleshooting",
            "limits",
        ):
            assert f'{language}-{section}' in parser.ids

    assert 'new URLSearchParams(window.location.search).get("lang")' in manual
    assert "fallback non additivo" in manual
    assert "non-additive fallback" in manual
    assert "alternativa no aditiva" in manual
    assert "NightScope non usa OpenAQ per raccomandazioni" not in manual
    assert "Do not use eyepiece solar filters" in manual
    assert "Non usare filtri solari da oculare" in manual
    assert "No utilice filtros solares de ocular" in manual
    assert "Pupila de salida = apertura del telescopio / aumento" in manual
    assert "Pupila de salida = abertura del telescopio / aumento" not in manual
    assert "El catálogo reúne objetos del sistema solar" in manual
    assert manual.count('class="steps"') == 9
    assert (
        "compila tutti i campi, anche quelli indicati come facoltativi" in manual
    )
    assert "complete every field, including those marked optional" in manual
    assert "complete todos los campos, también los indicados como opcionales" in manual
    assert manual.count("NightScope 1.34.2") == 3
    assert "independent from recommendations" not in manual
    assert "independent of recommendations" in manual
    assert manual.count("LAADS OPeNDAP") >= 3
    assert manual.count("API Keys") >= 3
    assert "NightScope usa il provider Windows su Windows e GeoClue 2 su Linux" in manual
    assert "NightScope uses the Windows provider on Windows and GeoClue 2 on Linux" in manual
    assert "NightScope utiliza el proveedor de Windows en Windows y GeoClue 2 en Linux" in manual


def test_manual_language_switch_keeps_all_languages_on_one_row() -> None:
    manual = (PROJECT_ROOT / "manuale.html").read_text(encoding="utf-8")
    language_switch = re.search(
        r"\.language-switch\s*\{(?P<declarations>.*?)\}",
        manual,
        flags=re.DOTALL,
    )

    assert language_switch is not None
    declarations = language_switch.group("declarations")
    assert re.search(
        r"grid-template-columns:\s*repeat\(3,\s*minmax\(44px,\s*1fr\)\)",
        declarations,
    )
    assert re.search(r"flex:\s*0\s+0\s+auto", declarations)


def test_localization_release_workflow_reapplies_reviewed_ts_overlay() -> None:
    documentation = (PROJECT_ROOT / "docs" / "LOCALIZATION.md").read_text(
        encoding="utf-8"
    )
    release_commands = documentation.split("Before a release run:", maxsplit=1)[1]

    update_catalogues = release_commands.index(
        ".\\tools\\update_translations.ps1 -UpdateOnly"
    )
    apply_reviews = release_commands.index(
        ".\\.venv\\Scripts\\python.exe tools\\update_ts_translations.py"
    )
    compile_catalogues = release_commands.index(
        ".\\tools\\update_translations.ps1 -CompileOnly"
    )
    assert update_catalogues < apply_reviews < compile_catalogues


def test_github_readme_is_product_focused_and_links_release_documents() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("# NightScope\n")
    assert "Windows desktop application" in readme
    assert "pre-release" in readme
    assert "docs/RELEASE_CANDIDATE_REVIEW.md" in readme
    assert "docs/RELEASE_CHECKLIST.md" in readme
    assert "astro_viewer/CHANGELOG.md" in readme
    assert "Versione corrente sorgente" not in readme

    local_targets = {
        target.split("#", 1)[0]
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)
        if target and not target.startswith(("#", "http://", "https://"))
    }
    assert local_targets
    assert not [
        target for target in sorted(local_targets) if not (PROJECT_ROOT / target).exists()
    ]


def test_legal_files_are_current_and_windows_build_enforces_them() -> None:
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    notices = (PROJECT_ROOT / "THIRD_PARTY_NOTICES.md").read_text(
        encoding="utf-8"
    )
    archive = (PROJECT_ROOT / "THIRD_PARTY_LICENSES.txt").read_text(
        encoding="utf-8"
    )
    build_script = (PROJECT_ROOT / "packaging" / "build_windows.ps1").read_text(
        encoding="utf-8"
    )
    requirements = (
        PROJECT_ROOT / "astro_viewer" / "requirements.txt"
    ).read_text(encoding="utf-8")

    assert license_text.startswith("Mozilla Public License Version 2.0")
    assert "Copyright 2026 Davide Marchi" in notices
    assert "LGPL-3.0-only" in notices
    assert archive == render_archive()
    assert "THIRD_PARTY_LICENSES.txt" in build_script
    assert "audit_qt_bundle.py" in build_script
    assert "PySide6_Essentials" in requirements
    assert "PySide6_Addons" in requirements
    assert "PySide6>=" not in requirements

    spec = (PROJECT_ROOT / "packaging" / "NightScope.spec").read_text(
        encoding="utf-8"
    )
    assert '"PySide6.QtPositioning"' in spec


def test_qt_bundle_audit_rejects_gpl_only_modules(tmp_path: Path) -> None:
    for filename in REQUIRED_DLLS:
        (tmp_path / filename).touch()
    for filename in ("LICENSE", "THIRD_PARTY_LICENSES.txt", "THIRD_PARTY_NOTICES.md"):
        (tmp_path / filename).touch()

    assert audit_bundle(tmp_path) == []

    forbidden = tmp_path / "_internal" / "PySide6" / "qml" / "QtQuick3D"
    forbidden.mkdir(parents=True)
    (forbidden / "qmldir").touch()
    errors = audit_bundle(tmp_path)

    assert len(errors) == 1
    assert "unexpected GPL-only Qt modules" in errors[0]

    (forbidden / "qmldir").unlink()
    forbidden.rmdir()
    timeline = (
        tmp_path
        / "_internal"
        / "PySide6"
        / "qml"
        / "QtQuick"
        / "Timeline"
        / "qmldir"
    )
    timeline.parent.mkdir(parents=True)
    timeline.touch()

    timeline_errors = audit_bundle(tmp_path)
    assert len(timeline_errors) == 1
    assert "QtQuick/Timeline/qmldir" in timeline_errors[0]


def test_qt_bundle_audit_rejects_runtime_state(tmp_path: Path) -> None:
    for filename in REQUIRED_DLLS:
        (tmp_path / filename).touch()
    for filename in ("LICENSE", "THIRD_PARTY_LICENSES.txt", "THIRD_PARTY_NOTICES.md"):
        (tmp_path / filename).touch()

    (tmp_path / "nightscope.db").touch()
    (tmp_path / "nightscope.db.backup").touch()
    (tmp_path / "logs").mkdir()

    errors = audit_bundle(tmp_path)

    assert len(errors) == 1
    assert errors[0] == (
        "runtime state present in release bundle: "
        "logs, nightscope.db, nightscope.db.backup"
    )
