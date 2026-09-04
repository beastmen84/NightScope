"""Protect maintenance tools, release audits, smoke isolation, and manual structure."""

from __future__ import annotations

import hashlib
import importlib.metadata
import inspect
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from astro_viewer import main as main_module
from astro_viewer.app.services.logging_service import (
    LOG_HANDLER_NAME,
    configure_logging,
)
from tools.audit_qt_bundle import (
    LINUX_NATIVE_MANIFEST,
    LINUX_NATIVE_MANIFEST_FIELDS,
    REQUIRED_DATA_FILES,
    REQUIRED_DLLS,
    REQUIRED_LINUX_LIBRARIES,
    audit_bundle,
)
from tools.check_code_documentation import (
    documentation_counts,
    documentation_errors,
    operational_documentation_error,
    python_documentation_error,
    qml_documentation_error,
)
from tools.generate_linux_native_notices import (
    _common_license_source,
    linux_package_origin,
    read_collected_system_binaries,
    source_package_url,
)
from tools.generate_third_party_licenses import _is_notice_path, render_archive
from tools.run_checks import Check, _checks, _run_check
from tools.translation_provider import (
    GOOGLE_TRANSLATE_URL,
    MAX_TRANSLATION_CHARACTERS,
    REQUEST_TIMEOUT,
    GoogleTranslator,
    TranslationProviderError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_RELEASE_LEGAL_FILES = (
    "LICENSE",
    "OPENNGC_LICENSE.txt",
    "SOURCE_CODE.md",
    "THIRD_PARTY_LICENSES.txt",
    "THIRD_PARTY_NOTICES.md",
)


def _create_release_legal_files(bundle_dir: Path, *, linux: bool = False) -> None:
    for filename in REQUIRED_RELEASE_LEGAL_FILES:
        (bundle_dir / filename).touch()
    if linux:
        (bundle_dir / LINUX_NATIVE_MANIFEST).write_text(
            "\t".join(LINUX_NATIVE_MANIFEST_FIELDS) + "\n",
            encoding="utf-8",
        )


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


class _WebsitePageParser(HTMLParser):
    """Collect links and SEO metadata from one committed static website page."""

    def __init__(self) -> None:
        super().__init__()
        self.document_language = ""
        self.ids: list[str] = []
        self.references: list[str] = []
        self.canonical = ""
        self.alternates: dict[str, str] = {}
        self.json_ld_blocks: list[str] = []
        self._json_ld_parts: list[str] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "html":
            self.document_language = str(attributes.get("lang") or "")
        if attributes.get("id"):
            self.ids.append(str(attributes["id"]))

        for attribute in ("href", "src"):
            reference = str(attributes.get(attribute) or "")
            if reference:
                self.references.append(reference)

        relation = set(str(attributes.get("rel") or "").split())
        href = str(attributes.get("href") or "")
        if tag == "link" and "canonical" in relation:
            self.canonical = href
        if tag == "link" and "alternate" in relation and attributes.get("hreflang"):
            self.alternates[str(attributes["hreflang"])] = href
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._json_ld_parts is not None:
            self.json_ld_blocks.append("".join(self._json_ld_parts))
            self._json_ld_parts = None


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
        "code-documentation",
        "import-cycles",
        "bandit-baseline",
        "compileall",
        "third-party-licenses",
        "mpc-observatories",
        "ngc-catalogue",
        "catalogue-editorial",
        "pytest",
        "smoke-test",
        "qml-smoke-test",
        "qml-red-night-vision-smoke-test",
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
        if check.name
        in {"smoke-test", "qml-smoke-test", "qml-red-night-vision-smoke-test"}
    )


def test_code_documentation_gate_covers_the_repository_and_rejects_empty_headers(
    tmp_path: Path,
) -> None:
    assert documentation_errors(PROJECT_ROOT) == []
    assert documentation_counts(PROJECT_ROOT) == {
        "Python": 247,
        "QML": 34,
        "operational": 17,
    }

    python_source = tmp_path / "undocumented.py"
    python_source.write_text("VALUE = 1\n", encoding="utf-8")
    assert python_documentation_error(python_source) == "missing module responsibility docstring"
    python_source.write_text('"""Own a synthetic test boundary."""\n', encoding="utf-8")
    assert python_documentation_error(python_source) is None

    qml_source = tmp_path / "Undocumented.qml"
    qml_source.write_text("// Purpose:\nItem {}\n", encoding="utf-8")
    assert "non-empty // Purpose:" in (qml_documentation_error(qml_source) or "")
    qml_source.write_text(
        "// Purpose: Render a synthetic component.\n"
        "// Contract: Consume no external state.\n"
        "Item {}\n",
        encoding="utf-8",
    )
    assert qml_documentation_error(qml_source) is None

    script = tmp_path / "script.sh"
    script.write_text("#!/usr/bin/env sh\n# Purpose: Run a probe.\n", encoding="utf-8")
    assert "Contract" in (operational_documentation_error(script) or "")
    script.write_text(
        "#!/usr/bin/env sh\n# Purpose: Run a probe.\n# Contract: Write no state.\n",
        encoding="utf-8",
    )
    assert operational_documentation_error(script) is None


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
    runtime_paths = main_module._resolve_runtime_paths()
    runtime_dir = main_module._resolve_runtime_dir()
    log_path = configure_logging(runtime_dir)

    try:
        assert runtime_paths.data_dir == tmp_path.resolve()
        assert runtime_paths.config_dir == tmp_path.resolve()
        assert runtime_paths.cache_dir == tmp_path.resolve()
        assert runtime_paths.state_dir == tmp_path.resolve()
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
    ) as configure_logging_mock, patch.object(
        main_module, "parse_args", return_value=args
    ), patch.object(
        main_module,
        "run_smoke_test",
        return_value=0,
    ) as smoke_test:
        result = main_module.main()

    assert result == 0
    configure_logging_mock.assert_called_once_with(
        main_module.RUNTIME_PATHS.state_dir
    )
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


def test_main_exposes_appearance_manager_to_both_qml_startup_paths() -> None:
    main_source = (PROJECT_ROOT / "astro_viewer" / "main.py").read_text(
        encoding="utf-8"
    )

    assert main_source.count(
        'setContextProperty("appearanceManager", appearance_manager)'
    ) == 2


def test_first_run_progress_uses_english_stage_copy() -> None:
    context = main_module._StartupContext(first_use=True, existing_database=False)
    states = [
        main_module._startup_progress_state(message, context)
        for message in (
            "Creazione database...",
            "Importazione cataloghi...",
            main_module._STARTUP_SERVICES_MESSAGE,
            main_module._STARTUP_INTERFACE_MESSAGE,
            main_module._STARTUP_READY_MESSAGE,
        )
    ]

    assert [state.stage for state in states] == [0, 1, 2, 3, 3]
    assert [state.percent for state in states] == [12, 28, 82, 94, 100]
    assert all(
        italian_word not in " ".join(state.detail for state in states).lower()
        for italian_word in ("creazione", "importazione", "preparazione", "finalizzazione")
    )


def test_first_use_startup_copy_remains_english() -> None:
    context = main_module._StartupContext(first_use=True, existing_database=False)

    copy = main_module._startup_copy(context)

    assert copy.message == "Preparing NightScope for first use"
    assert copy.secondary == "This one-time setup may take a minute."
    assert copy.step_labels == (
        "Database",
        "Local catalogues",
        "Application services",
        "Interface",
    )
    assert copy.initial_status == "Creating the local database..."


def test_startup_context_distinguishes_new_and_existing_runtime_state(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "nightscope.db"
    preferences_path = tmp_path / "user_preferences.json"
    runtime_paths = Mock(
        database_path=database_path,
        preferences_path=preferences_path,
    )

    with (
        patch.object(main_module, "RUNTIME_PATHS", runtime_paths),
        patch.object(main_module, "_legacy_runtime_paths", return_value=[]),
    ):
        assert main_module._startup_context() == main_module._StartupContext(
            first_use=True,
            existing_database=False,
        )

        preferences_path.write_text('{"language": "es"}', encoding="utf-8")
        assert main_module._startup_context() == main_module._StartupContext(
            first_use=False,
            existing_database=False,
        )

        preferences_path.unlink()
        database_path.touch()
        assert main_module._startup_context() == main_module._StartupContext(
            first_use=False,
            existing_database=True,
        )


def test_startup_context_recognizes_a_legacy_database(tmp_path: Path) -> None:
    legacy_database_path = tmp_path / "legacy" / "nightscope.db"
    legacy_database_path.parent.mkdir()
    legacy_database_path.touch()
    runtime_paths = Mock(
        database_path=tmp_path / "runtime" / "nightscope.db",
        preferences_path=tmp_path / "state" / "user_preferences.json",
    )

    with (
        patch.object(main_module, "RUNTIME_PATHS", runtime_paths),
        patch.object(
            main_module,
            "_legacy_runtime_paths",
            return_value=[legacy_database_path],
        ),
    ):
        assert main_module._startup_context() == main_module._StartupContext(
            first_use=False,
            existing_database=True,
        )


def test_startup_completion_preserves_existing_preferences(tmp_path: Path) -> None:
    preferences_path = tmp_path / "state" / "user_preferences.json"
    preferences_path.parent.mkdir()
    preferences_path.write_text(
        json.dumps({"language": "es", "red_night_vision_enabled": True}),
        encoding="utf-8",
    )
    runtime_paths = Mock(preferences_path=preferences_path)

    with patch.object(main_module, "RUNTIME_PATHS", runtime_paths):
        main_module._mark_startup_completed()

    assert json.loads(preferences_path.read_text(encoding="utf-8")) == {
        "language": "es",
        "red_night_vision_enabled": True,
        "startup_completed": True,
    }
    assert not preferences_path.with_suffix(".json.tmp").exists()


def test_run_app_always_creates_the_startup_splash() -> None:
    source = inspect.getsource(main_module.run_app)

    assert "splash = _create_startup_splash(app, startup_context)" in source
    assert "_database_initialization_required" not in source


def test_github_source_validation_reuses_the_local_gate() -> None:
    workflow = (
        PROJECT_ROOT / ".github" / "workflows" / "source-validation.yml"
    ).read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow
    assert workflow.count("actions/checkout@v7") == 2
    assert workflow.count("actions/setup-python@v7") == 2
    assert 'python-version: "3.14.5"' in workflow
    assert workflow.count('python-version: "3.14"') == 1
    assert 'python-version: "3.12"' in workflow
    assert 'constraints: "-c packaging/windows-release-constraints.txt"' in workflow
    assert workflow.count("${{ matrix.constraints }}") == 2
    assert "python tools/run_checks.py --fast" in workflow
    assert "python -m pip_audit --progress-spinner off" in workflow
    assert "QT_QPA_PLATFORM: offscreen" in workflow
    assert "dist/" not in workflow


def test_windows_release_constraints_match_the_legal_archive() -> None:
    constraints_path = PROJECT_ROOT / "packaging" / "windows-release-constraints.txt"
    constraints = constraints_path.read_text(encoding="utf-8")
    pins: dict[str, str] = {}
    for raw_line in constraints.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        specifiers = list(requirement.specifier)
        assert len(specifiers) == 1
        assert specifiers[0].operator == "=="
        canonical_name = canonicalize_name(requirement.name)
        assert canonical_name not in pins
        pins[canonical_name] = specifiers[0].version

    archive = (PROJECT_ROOT / "THIRD_PARTY_LICENSES.txt").read_text(
        encoding="utf-8"
    )
    inventory = archive.split(
        "Component inventory\n-------------------\n",
        maxsplit=1,
    )[1].split("\n\nNightScope selects", maxsplit=1)[0]
    archive_pins: dict[str, str] = {}
    for line in inventory.splitlines():
        match = re.fullmatch(r"- (?P<name>\S+) (?P<version>\S+): .+", line)
        assert match is not None
        archive_pins[canonicalize_name(match["name"])] = match["version"]

    assert pins == archive_pins
    python_version = re.search(
        r"^Python runtime: (?P<version>\S+) ",
        archive,
        flags=re.MULTILINE,
    )
    assert python_version is not None
    workflow = (
        PROJECT_ROOT / ".github" / "workflows" / "source-validation.yml"
    ).read_text(encoding="utf-8")
    assert f'python-version: "{python_version["version"]}"' in workflow


@pytest.mark.parametrize(
    ("path", "expected"),
    (
        ("packaging/licenses/__init__.py", False),
        ("packaging/licenses/__pycache__/_spdx.cpython-314.pyc", False),
        ("packaging-26.2.dist-info/licenses/LICENSE", True),
        ("astropy-8.0.1.dist-info/licenses/licenses/ERFA.rst", True),
        ("tzdata/licenses/LICENSE_APACHE", True),
    ),
)
def test_third_party_license_notice_filter_excludes_code_and_bytecode(
    path: str,
    expected: bool,
) -> None:
    assert _is_notice_path(importlib.metadata.PackagePath(path)) is expected


def test_first_run_city_progress_is_bounded_and_readable() -> None:
    from astro_viewer.app.services.localization import tr

    context = main_module._StartupContext(first_use=True, existing_database=False)
    early = main_module._startup_progress_state(
        tr("Importazione catalogo città... {rows} righe", rows=500),
        context,
    )
    late = main_module._startup_progress_state(
        tr("Importazione catalogo città... {rows} righe", rows=50_000),
        context,
    )

    assert early.stage == late.stage == 1
    assert early.percent < late.percent <= 68
    assert early.detail == "Importing the city catalogue - 500 rows processed"
    assert late.detail == "Importing the city catalogue - 50,000 rows processed"


def test_first_run_splash_has_real_transparent_rounded_corners() -> None:
    source = inspect.getsource(main_module._create_startup_splash)

    assert "dialog.setAttribute(Qt.WA_TranslucentBackground, True)" in source
    assert 'surface.setObjectName("splashSurface")' in source
    assert "surface.setAttribute(Qt.WA_StyledBackground, True)" in source
    assert "QWidget#splashSurface {" in source
    assert "QDialog {\n            background-color: transparent;" in source


def test_first_run_splash_waits_for_first_qml_frame() -> None:
    app = Mock()
    dialog = Mock()
    ready_callback = Mock()
    splash = main_module._StartupSplash(
        dialog=dialog,
        status=Mock(),
        progress=Mock(),
        step_labels=(),
        step_counter=Mock(),
        context=main_module._StartupContext(
            first_use=True,
            existing_database=False,
        ),
    )
    frame_swapped = Mock()
    root_object = Mock(frameSwapped=frame_swapped)

    with (
        patch.object(main_module, "_update_startup_splash") as update_splash,
        patch("PySide6.QtCore.QTimer.singleShot") as single_shot,
    ):
        main_module._close_startup_splash_after_first_frame(
            app,
            splash,
            root_object,
            fallback_ms=1_234,
            ready_callback=ready_callback,
        )

        dialog.close.assert_not_called()
        frame_callback = frame_swapped.connect.call_args.args[0]
        frame_callback()
        immediate_close = next(
            call.args[2] for call in single_shot.call_args_list if call.args[0] == 0
        )
        immediate_close()
        fallback_close = next(
            call.args[2]
            for call in single_shot.call_args_list
            if call.args[0] == 1_234
        )
        fallback_close()

        update_splash.assert_called_once_with(
            app,
            splash,
            main_module._STARTUP_READY_MESSAGE,
        )
        dialog.close.assert_called_once_with()
        ready_callback.assert_called_once_with()
        frame_swapped.disconnect.assert_called_once_with(frame_callback)
        assert any(call.args[0] == 1_234 for call in single_shot.call_args_list)


def test_first_run_splash_has_a_readiness_fallback() -> None:
    app = Mock()
    dialog = Mock()
    ready_callback = Mock()
    splash = main_module._StartupSplash(
        dialog=dialog,
        status=Mock(),
        progress=Mock(),
        step_labels=(),
        step_counter=Mock(),
        context=main_module._StartupContext(
            first_use=True,
            existing_database=False,
        ),
    )
    frame_swapped = Mock()
    root_object = Mock(frameSwapped=frame_swapped)

    with (
        patch.object(main_module, "_update_startup_splash") as update_splash,
        patch("PySide6.QtCore.QTimer.singleShot") as single_shot,
    ):
        main_module._close_startup_splash_after_first_frame(
            app,
            splash,
            root_object,
            fallback_ms=1_234,
            ready_callback=ready_callback,
        )

        fallback_close = next(
            call.args[2]
            for call in single_shot.call_args_list
            if call.args[0] == 1_234
        )
        fallback_close()

        update_splash.assert_called_once_with(
            app,
            splash,
            main_module._STARTUP_READY_MESSAGE,
        )
        dialog.close.assert_called_once_with()
        ready_callback.assert_called_once_with()


def test_multilingual_manual_has_complete_navigation_and_current_provider_semantics() -> None:
    manual = (PROJECT_ROOT / "manuale.html").read_text(encoding="utf-8")
    release_checklist = (
        PROJECT_ROOT / "docs" / "RELEASE_CHECKLIST.md"
    ).read_text(encoding="utf-8")
    public_windows_release_match = re.search(
        r"Current public Windows release: `v(\d+\.\d+\.\d+)`",
        release_checklist,
    )
    public_linux_release_match = re.search(
        r"public Linux release: `v(\d+\.\d+\.\d+)`",
        release_checklist,
    )
    parser = _ManualStructureParser()
    parser.feed(manual)

    assert public_windows_release_match is not None
    assert public_linux_release_match is not None
    public_windows_release = public_windows_release_match.group(1)
    public_linux_release = public_linux_release_match.group(1)
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
    assert manual.count("<h3>Imaging plan</h3>") == 1
    assert "<h3>Photographic plan</h3>" not in manual
    assert "single-exposure" not in manual
    assert "Il piano fotografico usa un riferimento a banda larga" in manual
    assert "El plan fotográfico usa una referencia de banda ancha" in manual
    assert "piano still" not in manual
    assert "referencia broadband" not in manual
    assert "Pupila de salida = apertura del telescopio / aumento" in manual
    assert "Pupila de salida = abertura del telescopio / aumento" not in manual
    assert "El catálogo reúne objetos del sistema solar" in manual
    assert manual.count('class="steps"') == 9
    assert (
        "compila tutti i campi, anche quelli indicati come facoltativi" in manual
    )
    assert "complete every field, including those marked optional" in manual
    assert "complete todos los campos, también los indicados como opcionales" in manual
    assert manual.count(f"NightScope {public_windows_release}") == 3
    assert manual.count(f"NightScope {public_linux_release}") == 3
    assert "independent from recommendations" not in manual
    assert "independent of recommendations" in manual
    assert manual.count("LAADS OPeNDAP") >= 3
    assert manual.count("API Keys") >= 3
    assert "NightScope usa il provider Windows su Windows e GeoClue 2 su Linux" in manual
    assert "NightScope uses the Windows provider on Windows and GeoClue 2 on Linux" in manual
    assert "NightScope utiliza el proveedor de Windows en Windows y GeoClue 2 en Linux" in manual
    assert "osservatori terrestri fissi registrati nel catalogo MPC" in manual
    assert "fixed terrestrial observatories registered in the MPC catalogue" in manual
    assert "observatorios terrestres fijos registrados en el catálogo MPC" in manual


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
    screenshot = PROJECT_ROOT / "docs" / "images" / "nightscope-home.png"

    assert readme.startswith("# NightScope\n")
    assert "Windows and Linux desktop application" in readme
    assert "NightScope is a released application" in readme
    assert "pre-release" not in readme.lower()
    assert "docs/RELEASE_AUDIT.md" in readme
    assert "docs/RELEASE_CHECKLIST.md" in readme
    assert "astro_viewer/CHANGELOG.md" in readme
    assert "Versione corrente sorgente" not in readme
    assert '<img src="docs/images/nightscope-home.png"' in readme
    assert (
        '<a href="https://beastmen84.github.io/NightScope/">Official website</a>'
        in readme
    )
    assert (PROJECT_ROOT / "website" / "index.html").is_file()
    assert screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    local_targets = {
        target.split("#", 1)[0]
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)
        if target and not target.startswith(("#", "http://", "https://"))
    }
    assert local_targets
    assert not [
        target for target in sorted(local_targets) if not (PROJECT_ROOT / target).exists()
    ]


def test_multilingual_website_has_complete_local_links_and_seo_metadata() -> None:
    website_root = PROJECT_ROOT / "website"
    pages = {
        "en": (website_root / "index.html", "https://beastmen84.github.io/NightScope/"),
        "it": (
            website_root / "it" / "index.html",
            "https://beastmen84.github.io/NightScope/it/",
        ),
        "es": (
            website_root / "es" / "index.html",
            "https://beastmen84.github.io/NightScope/es/",
        ),
    }
    expected_alternates = {
        "en": "https://beastmen84.github.io/NightScope/",
        "it": "https://beastmen84.github.io/NightScope/it/",
        "es": "https://beastmen84.github.io/NightScope/es/",
        "x-default": "https://beastmen84.github.io/NightScope/",
    }

    for language, (page_path, canonical_url) in pages.items():
        source = page_path.read_text(encoding="utf-8")
        parser = _WebsitePageParser()
        parser.feed(source)

        assert parser.document_language == language
        assert parser.canonical == canonical_url
        assert parser.alternates == expected_alternates
        assert len(parser.ids) == len(set(parser.ids))
        assert {"main-content", "why", "features", "downloads", "faq"}.issubset(
            parser.ids
        )
        assert "v1.45.21" in source
        assert "v1.43.0" in source
        assert "1.46.0" not in source
        assert "1.46.1" not in source
        assert "1.46.2" not in source
        assert "1.46.3" not in source

        assert len(parser.json_ld_blocks) == 1
        structured_data = json.loads(parser.json_ld_blocks[0])
        assert structured_data["@type"] == "SoftwareApplication"
        assert structured_data["name"] == "NightScope"
        assert structured_data["url"] == canonical_url
        assert structured_data["offers"]["price"] == "0"
        assert structured_data["downloadUrl"] == [
            "https://github.com/beastmen84/NightScope/releases/tag/v1.45.21",
            "https://github.com/beastmen84/NightScope/releases/tag/v1.43.0",
        ]

        for reference in parser.references:
            if reference.startswith(("http://", "https://", "/")):
                continue
            if reference.startswith("#"):
                assert reference[1:] in parser.ids
                continue
            relative_path, _, fragment = reference.partition("#")
            destination = (page_path.parent / relative_path).resolve()
            assert destination.is_relative_to(website_root.resolve())
            assert destination.exists(), f"Missing website target: {reference}"
            if fragment:
                assert fragment in parser.ids


def test_website_assets_sitemap_and_pages_workflow_are_consistent() -> None:
    website_root = PROJECT_ROOT / "website"
    for source, deployed in (
        (
            PROJECT_ROOT / "docs" / "images" / "nightscope-home.png",
            website_root / "assets" / "nightscope-home.png",
        ),
        (
            PROJECT_ROOT / "astro_viewer" / "resources" / "icons" / "nightscope.ico",
            website_root / "assets" / "nightscope.ico",
        ),
    ):
        assert hashlib.sha256(deployed.read_bytes()).digest() == hashlib.sha256(
            source.read_bytes()
        ).digest()

    sitemap = ET.parse(website_root / "sitemap.xml")
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = {
        element.text
        for element in sitemap.findall("sitemap:url/sitemap:loc", namespace)
    }
    assert locations == {
        "https://beastmen84.github.io/NightScope/",
        "https://beastmen84.github.io/NightScope/it/",
        "https://beastmen84.github.io/NightScope/es/",
    }
    robots = (website_root / "robots.txt").read_text(encoding="utf-8")
    assert "Allow: /" in robots
    assert "https://beastmen84.github.io/NightScope/sitemap.xml" in robots
    assert (website_root / ".nojekyll").is_file()

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "pages.yml").read_text(
        encoding="utf-8"
    )
    assert "branches: [master]" in workflow
    assert "path: website" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    for action in (
        "actions/checkout@v6",
        "actions/configure-pages@v5",
        "actions/upload-pages-artifact@v4",
        "actions/deploy-pages@v4",
    ):
        assert action in workflow


def test_source_and_platform_release_versions_are_documented_separately() -> None:
    version = (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    manual = (PROJECT_ROOT / "manuale.html").read_text(encoding="utf-8")
    source_notice = (PROJECT_ROOT / "SOURCE_CODE.md").read_text(encoding="utf-8")
    changelog = (PROJECT_ROOT / "astro_viewer" / "CHANGELOG.md").read_text(
        encoding="utf-8"
    )
    handoff = (PROJECT_ROOT / "docs" / "NEXT_CHAT_HANDOFF.md").read_text(
        encoding="utf-8"
    )
    third_party_notices = (PROJECT_ROOT / "THIRD_PARTY_NOTICES.md").read_text(
        encoding="utf-8"
    )
    release_checklist = (
        PROJECT_ROOT / "docs" / "RELEASE_CHECKLIST.md"
    ).read_text(encoding="utf-8")
    public_windows_release_match = re.search(
        r"Current public Windows release: `v(\d+\.\d+\.\d+)`",
        release_checklist,
    )
    public_linux_release_match = re.search(
        r"public Linux release: `v(\d+\.\d+\.\d+)`",
        release_checklist,
    )

    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert public_windows_release_match is not None
    assert public_linux_release_match is not None
    public_windows_release = public_windows_release_match.group(1)
    public_linux_release = public_linux_release_match.group(1)
    assert f"Source version {version}" in readme
    assert f"Current target: `v{version}`" in release_checklist
    assert (
        f"[NightScope {public_windows_release}]"
        f"(https://github.com/beastmen84/NightScope/releases/tag/v{public_windows_release})"
    ) in readme
    assert (
        f"[NightScope {public_linux_release}]"
        f"(https://github.com/beastmen84/NightScope/releases/tag/v{public_linux_release})"
    ) in readme
    assert f"NightScope {version}" in source_notice
    assert f"/v{version}" in source_notice
    assert f"NightScope {version}" in third_party_notices
    assert f"tag `v{version}`" in third_party_notices
    assert f"## NightScope {version} -" in changelog
    assert f"Source version: `{version}`" in handoff
    assert f"Current public Windows release: `v{public_windows_release}`" in handoff
    assert f"Current public Linux release: `v{public_linux_release}`" in handoff
    assert manual.count(f"NightScope {public_windows_release}") == 3
    assert manual.count(f"NightScope {public_linux_release}") == 3


def test_living_architecture_documents_keep_history_separate() -> None:
    docs_root = PROJECT_ROOT / "docs"
    testing = (docs_root / "TESTING.md").read_text(encoding="utf-8")
    handoff = (docs_root / "NEXT_CHAT_HANDOFF.md").read_text(encoding="utf-8")
    architecture = (docs_root / "ARCHITECTURE.md").read_text(encoding="utf-8")
    review = (docs_root / "ARCHITECTURE_REVIEW_1_45.md").read_text(
        encoding="utf-8"
    )

    assert (docs_root / "archive" / "TESTING_HISTORY_THROUGH_1.45.6.md").is_file()
    assert (docs_root / "archive" / "NEXT_CHAT_HANDOFF_1.45.6.md").is_file()
    assert "docs/archive/TESTING_HISTORY_THROUGH_1.45.6.md" in testing
    assert "docs/archive/NEXT_CHAT_HANDOFF_1.45.6.md" in handoff
    assert "docs/ARCHITECTURE_REVIEW_1_45.md" in architecture
    assert "docs/CATALOGUE_EDITORIAL_WORKFLOW.md" in review
    assert "docs/CATALOGUE_EDITORIAL_WORKFLOW.md" in handoff


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
    rendered_archive = render_archive()
    if sys.platform == "win32":
        assert archive == rendered_archive
    else:
        assert rendered_archive.startswith("NightScope Third-Party License Archive")
        assert "Python runtime license" in rendered_archive
    assert "THIRD_PARTY_LICENSES.txt" in build_script
    assert "OPENNGC_LICENSE.txt" in build_script
    assert "audit_qt_bundle.py" in build_script
    assert "PySide6_Essentials" in requirements
    assert "PySide6_Addons" in requirements
    assert "PySide6>=" not in requirements

    spec = (PROJECT_ROOT / "packaging" / "NightScope.spec").read_text(
        encoding="utf-8"
    )
    assert '"PySide6.QtPositioning"' in spec
    assert '"mpc_observatories_seed.csv"' in spec
    assert "Minor Planet Center Observatory Codes" in notices
    assert "data.minorplanetcenter.net/api/obscodes" in notices
    assert "### OpenNGC" in notices
    assert "CC-BY-SA-4.0" in notices
    assert (
        PROJECT_ROOT / "OPENNGC_LICENSE.txt"
    ).read_text(encoding="utf-8").startswith(
        "Creative Commons Attribution-ShareAlike 4.0 International"
    )


def test_earthdata_dependencies_are_constrained_as_one_resolver_unit() -> None:
    requirements = {
        line.strip()
        for line in (
            PROJECT_ROOT / "astro_viewer" / "requirements.txt"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert {
        "earthaccess>=0.18,<0.19",
        "s3fs==2026.7.0",
        "fsspec==2026.7.0",
        "aiobotocore>=3.9,<3.10",
        "botocore>=1.43.3,<1.43.57",
    } <= requirements


def test_linux_build_enforces_licenses_and_platform_bundle_audit() -> None:
    build_script_path = PROJECT_ROOT / "packaging" / "build_linux.sh"
    build_script = build_script_path.read_text(encoding="utf-8")
    archive_script = (
        PROJECT_ROOT / "packaging" / "archive_linux.sh"
    ).read_text(encoding="utf-8")
    container_script_path = (
        PROJECT_ROOT / "packaging" / "build_linux_debian12.sh"
    )
    container_script = container_script_path.read_text(encoding="utf-8")
    dockerfile = (
        PROJECT_ROOT / "packaging" / "Dockerfile.debian12"
    ).read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    spec = (PROJECT_ROOT / "packaging" / "NightScope.spec").read_text(
        encoding="utf-8"
    )
    qtgui_hook = (
        PROJECT_ROOT
        / "packaging"
        / "pyinstaller_hooks"
        / "hook-PySide6.QtGui.py"
    ).read_text(encoding="utf-8")

    assert build_script.startswith("#!/usr/bin/env bash\n")
    assert "generate_third_party_licenses.py" in build_script
    assert "generate_linux_native_notices.py" in build_script
    assert "LINUX_NATIVE_COMPONENTS.tsv" in (
        PROJECT_ROOT / "tools" / "generate_linux_native_notices.py"
    ).read_text(encoding="utf-8")
    assert "THIRD_PARTY_LICENSES.txt" in build_script
    assert "SOURCE_CODE.md" in build_script
    assert "OPENNGC_LICENSE.txt" in build_script
    assert "PyInstaller --clean --noconfirm" in build_script
    assert "audit_qt_bundle.py" in build_script
    assert "--platform linux" in build_script
    assert '--output "$license_archive"' in build_script
    assert "--platform-label Linux" in build_script
    assert "NIGHTSCOPE_BUILD_PYTHON" in build_script
    assert archive_script.startswith("#!/usr/bin/env bash\n")
    assert "audit_qt_bundle.py" in archive_script
    assert "--sort=name" in archive_script
    assert '--mtime="@0"' in archive_script
    assert "gzip -n -9" in archive_script
    assert "sha256sum" in archive_script
    assert 'chmod 0644 "$archive_path"' in archive_script
    assert 'chmod 0644 "$checksum_path"' in archive_script
    assert "NightScope-v${version}-${distribution_id}" in archive_script
    assert "NIGHTSCOPE_BUILD_PYTHON" in archive_script
    assert container_script.startswith("#!/usr/bin/env bash\n")
    if sys.platform != "win32":
        assert container_script_path.stat().st_mode & 0o111
    assert "Dockerfile.debian12" in container_script
    assert "command -v podman" in container_script
    assert "command -v docker" in container_script
    assert "./packaging/build_linux.sh" in container_script
    assert "./packaging/archive_linux.sh" in container_script
    assert "FROM python:3.12-bookworm" in dockerfile
    assert "astro_viewer/requirements.txt" in dockerfile
    assert "requirements-dev.txt" in dockerfile
    assert "## Install The Portable Linux Bundle" in readme
    assert "sudo apt install dbus-user-session geoclue-2.0 gnome-keyring" in readme
    assert re.search(
        r"sha256sum --check NightScope-v\d+\.\d+\.\d+-debian-12-x64",
        readme,
    )
    version = (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert f"`dist/NightScope-v{version}-debian-12-x64.tar.gz`" in readme
    assert "./packaging/build_linux_debian12.sh" in readme
    assert "./NightScope/NightScope" in readme
    assert '"keyring.backends.Windows"' in spec
    assert '"keyring.backends.SecretService"' in spec
    assert 'sys.platform == "win32"' in spec
    assert 'sys.platform.startswith("linux")' in spec
    assert 'excludes.append("keyring.backends.Windows")' in spec
    assert '"runtime_hooks" / "linux_gio.py"' in spec
    linux_gio_hook = (
        PROJECT_ROOT
        / "packaging"
        / "runtime_hooks"
        / "linux_gio.py"
    ).read_text(encoding="utf-8")
    assert 'os.environ["GIO_MODULE_DIR"]' in linux_gio_hook
    assert "qtvirtualkeyboardplugin" in qtgui_hook
    assert "libqtiff.so" in qtgui_hook
    assert "current Linux release build" in render_archive(
        environment_label="Linux"
    )


def test_qt_bundle_audit_rejects_gpl_only_modules(tmp_path: Path) -> None:
    for filename in REQUIRED_DLLS:
        (tmp_path / filename).touch()
    for filename in REQUIRED_DATA_FILES:
        (tmp_path / filename).touch()
    _create_release_legal_files(tmp_path)

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


def test_qt_bundle_audit_accepts_linux_libraries_and_rejects_plugins(
    tmp_path: Path,
) -> None:
    for filename in REQUIRED_LINUX_LIBRARIES:
        (tmp_path / filename).touch()
    for filename in REQUIRED_DATA_FILES:
        (tmp_path / filename).touch()
    _create_release_legal_files(tmp_path, linux=True)

    assert audit_bundle(tmp_path, platform_name="linux") == []

    missing_library = tmp_path / "libqt6core.so.6"
    missing_library.unlink()
    missing_library_errors = audit_bundle(tmp_path, platform_name="linux")
    assert missing_library_errors == [
        "missing required Qt shared libraries: libqt6core.so.6"
    ]
    missing_library.touch()

    plugin_dir = tmp_path / "_internal" / "PySide6" / "Qt" / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "libqtvirtualkeyboardplugin.so").touch()
    (plugin_dir / "libqtiff.so").touch()

    errors = audit_bundle(tmp_path, platform_name="linux")

    assert len(errors) == 2
    assert "unexpected GPL-only Qt modules" in errors[0]
    assert "unsupported Linux Qt plugins" in errors[1]


def test_linux_native_manifest_covers_files_hashes_and_common_licenses(
    tmp_path: Path,
) -> None:
    for filename in REQUIRED_LINUX_LIBRARIES:
        (tmp_path / filename).touch()
    for filename in REQUIRED_DATA_FILES:
        (tmp_path / filename).touch()
    _create_release_legal_files(tmp_path, linux=True)

    native_file = tmp_path / "_internal" / "libexample.so.1"
    native_file.parent.mkdir()
    native_file.write_bytes(b"native-library")

    errors = audit_bundle(tmp_path, platform_name="linux")
    assert errors == [
        "unmanifested Linux native files: _internal/libexample.so.1"
    ]

    notice_path = Path("legal/linux-native/example/copyright")
    notice_file = tmp_path / notice_path
    notice_file.parent.mkdir(parents=True)
    notice_file.write_text(
        "See /usr/share/common-licenses/LGPL-2.1\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(native_file.read_bytes()).hexdigest()
    (tmp_path / LINUX_NATIVE_MANIFEST).write_text(
        "\t".join(LINUX_NATIVE_MANIFEST_FIELDS)
        + "\n"
        + "\t".join(
            (
                "_internal/libexample.so.1",
                digest,
                "libexample1:amd64",
                "1.0-1",
                "example",
                "1.0-1",
                notice_path.as_posix(),
                "https://launchpad.net/ubuntu/+source/example/1.0-1",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    errors = audit_bundle(tmp_path, platform_name="linux")
    assert errors == ["missing Linux native common-license texts: LGPL-2.1"]

    common_license = tmp_path / "legal/linux-native/common-licenses/LGPL-2.1"
    common_license.parent.mkdir(parents=True)
    common_license.touch()
    assert audit_bundle(tmp_path, platform_name="linux") == []

    manifest = tmp_path / LINUX_NATIVE_MANIFEST
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "https://launchpad.net/ubuntu/+source/example/1.0-1",
            "https://sources.debian.org/src/example/1.0-1/",
        ),
        encoding="utf-8",
    )
    assert audit_bundle(tmp_path, platform_name="linux") == []


def test_linux_native_generator_reads_only_system_collected_binaries(
    tmp_path: Path,
) -> None:
    collect_toc = tmp_path / "COLLECT-00.toc"
    collect_toc.write_text(
        repr(
            (
                [
                    ("libexample.so.1", "/usr/lib/libexample.so.1", "BINARY"),
                    ("wheel.so", "/venv/site-packages/wheel.so", "BINARY"),
                    (
                        "local-wheel.so",
                        "/usr/local/lib/python3.12/site-packages/local-wheel.so",
                        "BINARY",
                    ),
                    ("data.txt", "/usr/share/example/data.txt", "DATA"),
                ],
            )
        ),
        encoding="utf-8",
    )

    binaries = read_collected_system_binaries(collect_toc)

    assert len(binaries) == 1
    assert binaries[0].bundle_path.as_posix() == "_internal/libexample.so.1"
    assert binaries[0].source_path == Path("/usr/lib/libexample.so.1")


def test_linux_native_source_urls_support_debian_ubuntu_and_python() -> None:
    assert linux_package_origin({"ID": "debian"}) == "debian"
    assert (
        linux_package_origin({"ID": "linuxmint", "ID_LIKE": "ubuntu debian"})
        == "ubuntu"
    )
    assert source_package_url("ubuntu", "glibc", "2.43-0ubuntu1") == (
        "https://launchpad.net/ubuntu/+source/glibc/2.43-0ubuntu1"
    )
    assert source_package_url("debian", "zlib", "1:1.2.13.dfsg-1") == (
        "https://sources.debian.org/src/zlib/1%3A1.2.13.dfsg-1/"
    )
    assert source_package_url("python", "Python", "3.12.11") == (
        "https://github.com/python/cpython/archive/refs/tags/v3.12.11.tar.gz"
    )
    with pytest.raises(RuntimeError, match="Debian- or Ubuntu-derived"):
        linux_package_origin({"ID": "fedora"})


def test_linux_native_common_license_accepts_debian_version_alias(
    tmp_path: Path,
) -> None:
    license_file = tmp_path / "GPL-2"
    license_file.touch()

    assert _common_license_source(
        "GPL-2.0",
        common_license_root=tmp_path,
    ) == license_file


def test_qt_bundle_audit_rejects_runtime_state(tmp_path: Path) -> None:
    for filename in REQUIRED_DLLS:
        (tmp_path / filename).touch()
    for filename in REQUIRED_DATA_FILES:
        (tmp_path / filename).touch()
    _create_release_legal_files(tmp_path)

    (tmp_path / "nightscope.db").touch()
    (tmp_path / "nightscope.db.backup").touch()
    (tmp_path / "logs").mkdir()

    errors = audit_bundle(tmp_path)

    assert len(errors) == 1
    assert errors[0] == (
        "runtime state present in release bundle: "
        "logs, nightscope.db, nightscope.db.backup"
    )
