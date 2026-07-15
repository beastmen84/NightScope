from PyInstaller.utils.hooks.qt import add_qt6_dependencies


def _is_allowed_qtgui_binary(item: tuple[str, str]) -> bool:
    source, destination = item
    combined = f"{source}/{destination}".replace("\\", "/").lower()
    return "qtvirtualkeyboardplugin.dll" not in combined


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
binaries = [item for item in binaries if _is_allowed_qtgui_binary(item)]
