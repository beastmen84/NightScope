from pathlib import PurePosixPath

from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info


# The upstream hook collects every QML module installed by PySide6. NightScope
# needs only these LGPL-compatible modules and their control-style subtrees.
_QML_ROOT_MODULES = {"QtCore", "QtQml", "QtQuick"}
_QML_SUBTREES = {
    PurePosixPath("QtQml/Models"),
    PurePosixPath("QtQml/WorkerScript"),
    PurePosixPath("QtQuick/Controls"),
    PurePosixPath("QtQuick/Effects"),
    PurePosixPath("QtQuick/Layouts"),
    PurePosixPath("QtQuick/NativeStyle"),
    PurePosixPath("QtQuick/Shapes"),
    PurePosixPath("QtQuick/Templates"),
    PurePosixPath("QtQuick/Window"),
}


def _qml_relative_destination(destination: str) -> PurePosixPath | None:
    path = PurePosixPath(destination.replace("\\", "/"))
    try:
        qml_index = path.parts.index("qml")
    except ValueError:
        return None
    relative = PurePosixPath(*path.parts[qml_index + 1 :])
    return relative if relative.parts else None


def _is_allowed_qml_item(item: tuple[str, str]) -> bool:
    relative = _qml_relative_destination(item[1])
    if relative is None:
        return False
    if len(relative.parts) == 1 and relative.parts[0] in _QML_ROOT_MODULES:
        return True
    return any(
        relative == subtree or subtree in relative.parents
        for subtree in _QML_SUBTREES
    )


def _is_allowed_qtqml_binary(item: tuple[str, str]) -> bool:
    source, destination = item
    combined = f"{source}/{destination}".replace("\\", "/").lower()
    return "/qmltooling/" not in combined


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
binaries = [item for item in binaries if _is_allowed_qtqml_binary(item)]
qml_binaries, qml_datas = pyside6_library_info.collect_qtqml_files()
binaries += [item for item in qml_binaries if _is_allowed_qml_item(item)]
datas += [item for item in qml_datas if _is_allowed_qml_item(item)]
