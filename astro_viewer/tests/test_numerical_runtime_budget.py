"""Protect early native-thread budgeting without overriding explicit or embedded runtime policy."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


PROBE = """
import json, os, sys
from astro_viewer.main import _configure_numerical_runtime
if os.environ.get('AUDIT_PREIMPORTED_NUMPY'):
    import numpy
before = {key: os.environ.get(key) for key in ('OPENBLAS_NUM_THREADS', 'GOTO_NUM_THREADS', 'OMP_NUM_THREADS')}
_configure_numerical_runtime()
_configure_numerical_runtime()
after = {key: os.environ.get(key) for key in before}
print(json.dumps({'before': before, 'after': after, 'numpy_loaded': 'numpy' in sys.modules}))
"""


@pytest.mark.parametrize("override", [None, "OPENBLAS_NUM_THREADS", "GOTO_NUM_THREADS", "OMP_NUM_THREADS", "preimported"])
def test_native_budget_applies_only_before_import_and_without_explicit_policy(tmp_path, override):
    environment = os.environ.copy()
    for name in ("OPENBLAS_NUM_THREADS", "GOTO_NUM_THREADS", "OMP_NUM_THREADS", "AUDIT_PREIMPORTED_NUMPY"):
        environment.pop(name, None)
    environment["NIGHTSCOPE_RUNTIME_DIR"] = str(tmp_path)
    if override == "preimported":
        environment["AUDIT_PREIMPORTED_NUMPY"] = "1"
    elif override:
        environment[override] = "2"
    result = subprocess.run(
        [sys.executable, "-c", PROBE], cwd=Path(__file__).resolve().parents[2], env=environment,
        capture_output=True, text=True, check=True, timeout=30,
    )
    state = json.loads(result.stdout)
    if override is None:
        assert state["after"]["OPENBLAS_NUM_THREADS"] == "1"
        assert not state["numpy_loaded"]
    else:
        assert state["after"] == state["before"]
    assert not result.stderr
