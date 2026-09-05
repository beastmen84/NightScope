"""Scope opt-in seeded database preparation to one pytest session per worker."""

from collections.abc import Iterator

import pytest

from astro_viewer.tests.database_fixture import database_fixture_session


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--fresh-test-databases",
        action="store_true",
        help="Rebuild each opted-in setup database for fixture-equivalence diagnostics.",
    )


@pytest.fixture(scope="session", autouse=True)
def seeded_database_session(request: pytest.FixtureRequest) -> Iterator[None]:
    """Share only a pristine setup template, including for unittest-style tests."""
    if request.config.getoption("--fresh-test-databases"):
        yield
        return
    with database_fixture_session():
        yield
