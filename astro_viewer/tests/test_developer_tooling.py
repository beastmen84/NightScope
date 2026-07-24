from __future__ import annotations

import hashlib
import logging
import re
import sys
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
from tools.audit_qt_bundle import (
    LINUX_NATIVE_MANIFEST,
    LINUX_NATIVE_MANIFEST_FIELDS,
    REQUIRED_DATA_FILES,
    REQUIRED_DLLS,
    REQUIRED_LINUX_LIBRARIES,
    audit_bundle,
)
from tools.generate_linux_native_notices import (
    _common_license_source,
    linux_package_origin,
    read_collected_system_binaries,
    source_package_url,
)
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
REQUIRED_RELEASE_LEGAL_FILES = (
    "LICENSE",
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
        "mpc-observatories",
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
    states = [
        main_module._initialization_progress_state(message)
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


def test_first_run_city_progress_is_bounded_and_readable() -> None:
    from astro_viewer.app.services.localization import tr

    early = main_module._initialization_progress_state(
        tr("Importazione catalogo città... {rows} righe", rows=500)
    )
    late = main_module._initialization_progress_state(
        tr("Importazione catalogo città... {rows} righe", rows=50_000)
    )

    assert early.stage == late.stage == 1
    assert early.percent < late.percent <= 68
    assert early.detail == "Importing the city catalogue - 500 rows processed"
    assert late.detail == "Importing the city catalogue - 50,000 rows processed"


def test_first_run_splash_waits_for_first_qml_frame() -> None:
    app = Mock()
    dialog = Mock()
    splash = main_module._InitializationSplash(
        dialog=dialog,
        status=Mock(),
        progress=Mock(),
        step_labels=(),
        step_counter=Mock(),
    )
    frame_swapped = Mock()
    root_object = Mock(frameSwapped=frame_swapped)

    with (
        patch.object(main_module, "_update_initialization_splash") as update_splash,
        patch("PySide6.QtCore.QTimer.singleShot") as single_shot,
    ):
        main_module._close_initialization_splash_after_first_frame(
            app,
            splash,
            root_object,
            fallback_ms=1_234,
        )

        dialog.close.assert_not_called()
        frame_callback = frame_swapped.connect.call_args.args[0]
        frame_callback()
        immediate_close = next(
            call.args[2] for call in single_shot.call_args_list if call.args[0] == 0
        )
        immediate_close()

        update_splash.assert_called_once_with(
            app,
            splash,
            main_module._STARTUP_READY_MESSAGE,
        )
        dialog.close.assert_called_once_with()
        frame_swapped.disconnect.assert_called_once_with(frame_callback)
        assert any(call.args[0] == 1_234 for call in single_shot.call_args_list)


def test_first_run_splash_has_a_readiness_fallback() -> None:
    app = Mock()
    dialog = Mock()
    splash = main_module._InitializationSplash(
        dialog=dialog,
        status=Mock(),
        progress=Mock(),
        step_labels=(),
        step_counter=Mock(),
    )
    frame_swapped = Mock()
    root_object = Mock(frameSwapped=frame_swapped)

    with (
        patch.object(main_module, "_update_initialization_splash") as update_splash,
        patch("PySide6.QtCore.QTimer.singleShot") as single_shot,
    ):
        main_module._close_initialization_splash_after_first_frame(
            app,
            splash,
            root_object,
            fallback_ms=1_234,
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

    assert readme.startswith("# NightScope\n")
    assert "Windows and Linux desktop application" in readme
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


def test_source_version_matches_current_release_documents() -> None:
    version = (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    source_notice = (PROJECT_ROOT / "SOURCE_CODE.md").read_text(encoding="utf-8")
    changelog = (PROJECT_ROOT / "astro_viewer" / "CHANGELOG.md").read_text(
        encoding="utf-8"
    )
    handoff = (PROJECT_ROOT / "docs" / "NEXT_CHAT_HANDOFF.md").read_text(
        encoding="utf-8"
    )

    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert f"Source version {version}" in readme
    assert f"NightScope {version}" in source_notice
    assert f"/v{version}" in source_notice
    assert f"## NightScope {version} -" in changelog
    assert f"Versione sorgente: `{version}`" in handoff


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
    assert "sha256sum --check NightScope-v1.41.0-debian-12-x64" in readme
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
    assert "current Linux release candidate" in render_archive(
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
