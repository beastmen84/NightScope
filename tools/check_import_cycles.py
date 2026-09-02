"""Reject production import cycles and forbidden dependencies across protected layers."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable
from pathlib import Path


EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        "__pycache__",
        "tests",
        "tools",
    }
)
FORBIDDEN_DEPENDENCY_PREFIXES = {
    "astro_viewer.app.models": (
        "astro_viewer.app.application",
        "astro_viewer.app.database",
        "astro_viewer.app.viewmodels",
    ),
    "astro_viewer.app.database": (
        "astro_viewer.app.application",
        "astro_viewer.app.viewmodels",
    ),
    "astro_viewer.app.astronomy": (
        "astro_viewer.app.application",
        "astro_viewer.app.viewmodels",
    ),
    "astro_viewer.app.services": (
        "astro_viewer.app.application",
        "astro_viewer.app.viewmodels",
    ),
}


def production_modules(source_root: Path) -> dict[str, Path]:
    modules = {}
    for path in source_root.rglob("*.py"):
        relative = path.relative_to(source_root.parent)
        if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative.parts):
            continue
        module = ".".join(relative.with_suffix("").parts)
        if module.endswith(".__init__"):
            module = module.removesuffix(".__init__")
        modules[module] = path
    return modules


def import_graph(source_root: Path) -> dict[str, set[str]]:
    modules = production_modules(source_root)
    graph = {module: set() for module in modules}
    for module, path in modules.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        is_package = path.name == "__init__.py"
        package = module if is_package else module.rpartition(".")[0]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _add_known_module(graph[module], alias.name, modules)
            elif isinstance(node, ast.ImportFrom):
                base = _resolved_import_base(node, package)
                _add_known_module(graph[module], base, modules)
                for alias in node.names:
                    _add_known_module(
                        graph[module],
                        f"{base}.{alias.name}" if base else alias.name,
                        modules,
                    )
    return graph


def find_import_cycles(source_root: Path) -> list[tuple[str, ...]]:
    graph = import_graph(source_root)
    index = 0
    stack: list[str] = []
    indices: dict[str, int] = {}
    low_links: dict[str, int] = {}
    on_stack: set[str] = set()
    cycles: list[tuple[str, ...]] = []

    def visit(module: str) -> None:
        nonlocal index
        indices[module] = index
        low_links[module] = index
        index += 1
        stack.append(module)
        on_stack.add(module)

        for dependency in graph[module]:
            if dependency not in indices:
                visit(dependency)
                low_links[module] = min(
                    low_links[module],
                    low_links[dependency],
                )
            elif dependency in on_stack:
                low_links[module] = min(
                    low_links[module],
                    indices[dependency],
                )

        if low_links[module] != indices[module]:
            return
        component = []
        while stack:
            dependency = stack.pop()
            on_stack.remove(dependency)
            component.append(dependency)
            if dependency == module:
                break
        if len(component) > 1 or module in graph[module]:
            cycles.append(tuple(sorted(component)))

    for module in graph:
        if module not in indices:
            visit(module)
    return sorted(cycles)


def find_layer_violations(source_root: Path) -> list[tuple[str, str]]:
    graph = import_graph(source_root)
    violations = []
    for module, dependencies in graph.items():
        forbidden_prefixes = next(
            (
                prefixes
                for layer, prefixes in FORBIDDEN_DEPENDENCY_PREFIXES.items()
                if _is_module_or_child(module, layer)
            ),
            (),
        )
        for dependency in dependencies:
            if any(
                _is_module_or_child(dependency, prefix)
                for prefix in forbidden_prefixes
            ):
                violations.append((module, dependency))
    return sorted(violations)


def render_cycles(cycles: Iterable[tuple[str, ...]]) -> str:
    return "\n\n".join(" -> ".join(cycle) for cycle in cycles)


def render_layer_violations(violations: Iterable[tuple[str, str]]) -> str:
    return "\n".join(
        f"{module} -> {dependency}" for module, dependency in violations
    )


def _resolved_import_base(node: ast.ImportFrom, package: str) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = package.split(".") if package else []
    keep = max(0, len(package_parts) - node.level + 1)
    prefix = package_parts[:keep]
    if node.module:
        prefix.extend(node.module.split("."))
    return ".".join(prefix)


def _add_known_module(
    dependencies: set[str],
    imported_name: str,
    modules: dict[str, Path],
) -> None:
    candidate = imported_name
    while candidate:
        if candidate in modules:
            dependencies.add(candidate)
            return
        candidate = candidate.rpartition(".")[0]


def _is_module_or_child(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reject circular imports in NightScope production modules."
    )
    parser.add_argument(
        "source_root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "astro_viewer",
    )
    args = parser.parse_args()
    cycles = find_import_cycles(args.source_root)
    layer_violations = find_layer_violations(args.source_root)
    if cycles:
        print("Circular production imports detected:")
        print(render_cycles(cycles))
    if layer_violations:
        print("Protected production layer dependencies violated:")
        print(render_layer_violations(layer_violations))
    if cycles or layer_violations:
        return 1
    print("Production import graph is acyclic and protected layer boundaries are intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
