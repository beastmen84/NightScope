# NightScope Testing Workflow

NightScope has more than one thousand tests. The full serial suite is useful
before releases and high-risk runtime changes, but it is too slow for every
small NSOM commit.

## Recommended Commands

Fast syntax validation:

```powershell
.\.venv\Scripts\python.exe -m compileall astro_viewer
```

Focused area validation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer/tests/test_observation_conditions_service.py
```

Focused NSOM/report validation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer/tests/test_nsom*.py
```

Parallel full suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -n auto
```

Serial full suite fallback:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Developer Dependency

Parallel execution uses `pytest-xdist`. Install developer-only test dependencies
with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Measured Baseline

Measured on the current Windows development environment:

| Command | Result | Time |
| --- | --- | ---: |
| `python -m pytest -q` | `1036 passed, 7 subtests passed` | `0:06:06` |
| `python -m pytest -q -n auto` | `1036 passed, 7 subtests passed` | `0:01:14` |

Use the parallel full suite for normal pre-commit validation when the change
touches shared runtime services. Use the serial suite only as a fallback if a
parallel-only failure appears or before a release build where maximum
conservatism is preferred.

## Validation Policy

For small developer-only documentation or report updates:

1. Run `compileall astro_viewer`.
2. Run focused tests for the files or reports touched.

For shared runtime changes:

1. Run `compileall astro_viewer`.
2. Run focused tests for the touched area.
3. Run `pytest -q -n auto`.

For default-on switches, release candidates or broad refactors:

1. Run `compileall astro_viewer`.
2. Run focused tests for the touched area.
3. Run `pytest -q -n auto`.
4. Run serial `pytest -q` only if parallel execution reports a failure that may
   be order- or worker-dependent.
