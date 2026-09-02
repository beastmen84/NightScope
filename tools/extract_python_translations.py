"""Extract literal Python tr() messages into temporary C++ input for Qt lupdate."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def translation_messages() -> list[tuple[Path, int, str]]:
    sources = sorted((PROJECT_ROOT / "astro_viewer" / "app").rglob("*.py"))
    sources.append(PROJECT_ROOT / "astro_viewer" / "main.py")
    messages: list[tuple[Path, int, str]] = []
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(PROJECT_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "tr":
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                raise ValueError(
                    f"tr() requires a literal source string: {relative_path}:{node.lineno}"
                )
            source = node.args[0].value
            if not isinstance(source, str) or not source:
                raise ValueError(
                    f"tr() requires a non-empty source string: "
                    f"{relative_path}:{node.lineno}"
                )
            messages.append((Path(relative_path), node.lineno, source))
    return sorted(messages, key=lambda item: (item[0].as_posix(), item[1], item[2]))


def write_cpp(path: Path) -> None:
    lines = [
        "#include <QtCore/QCoreApplication>",
        "",
        "static const char *nightscope_python_messages[] = {",
    ]
    for source_path, line_number, source in translation_messages():
        location = source_path.as_posix().replace('"', '\\"')
        literal = json.dumps(source, ensure_ascii=True)
        lines.extend(
            (
                f'#line {line_number} "{location}"',
                f'    QT_TRANSLATE_NOOP_UTF8("", {literal}),',
            )
        )
    lines.extend(("};", ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract NightScope Python tr() literals for Qt lupdate."
    )
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_cpp(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
