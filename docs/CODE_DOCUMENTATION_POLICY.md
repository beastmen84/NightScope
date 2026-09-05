# NightScope Code Documentation Policy

This document defines what a complete code-documentation pass means for the
NightScope repository. Documentation is part of the source contract: it must
explain ownership, boundaries, invariants, side effects, and operational risk
without paraphrasing every statement.

## Audited Scope

The pass covers every hand-written executable or operational source file:

- Python application, tests, maintenance tools, and PyInstaller hooks;
- every QML page and reusable component;
- PowerShell and shell automation;
- the PyInstaller specification and Debian build container;
- GitHub workflow and funding configuration;
- Ruff, pytest, runtime and development dependency configuration;
- the SQLite schema and the self-contained HTML manual.

Generated translation catalogues, catalogue seeds, external snapshots, image
and icon assets, license texts, archived evidence, virtual environments,
`build`, and `dist` are excluded. Their provenance and generation processes are
documented by the source files that own them.

## Required Documentation

Every Python module must start with a concise module docstring describing its
responsibility. Package `__init__.py` files describe the package boundary.
Public classes and functions need their own docstrings when their contract,
invariants, side effects, failure modes, thread ownership, or compatibility
role are not obvious from the name and signature.

Every QML file starts with a purpose comment and states the controller,
context-property, or reusable-component contract it consumes. It does not
duplicate property names line by line.

Automation and configuration files start with a comment explaining what they
control and, where relevant, whether they modify source data, build artifacts,
or external state. Destructive and network behavior must be explicit.

Tests use a module docstring to state the behavior or boundary protected by the
suite. Individual test names remain the primary description of each scenario.

## Comment Quality

Useful documentation answers at least one of these questions:

- Why does this file exist, and which layer owns it?
- Which inputs and outputs cross its boundary?
- Which invariant must callers preserve?
- Which external system, persistent state, thread, or generated artifact can it
  affect?
- Which compatibility behavior would be risky to remove?

Comments that merely restate syntax, stale implementation histories, or
unverifiable design intentions are defects. A large file does not need a large
header; it needs an accurate one and focused documentation around non-obvious
contracts.

## Enforcement

The documentation series landed in bounded `1.45.x` batches. Version `1.45.13`
completed a file-by-file pass and introduced
`tools/check_code_documentation.py`, which is part of the standard source gate.
Its current audited inventory is:

- 250 Python modules: 124 production modules, 93 test/support modules, and 33
  maintenance or packaging modules;
- 34 QML pages and components;
- 17 automation, packaging, CI, configuration, dependency, schema, and manual
  files.

Python and QML families are discovered recursively. Operational families are
discovered from their governed extensions and locations, with explicit entries
for the schema, manual, and dependency manifests. A new undocumented source file
therefore cannot silently reduce coverage. The gate validates presence and
structure; code review remains responsible for accuracy.
