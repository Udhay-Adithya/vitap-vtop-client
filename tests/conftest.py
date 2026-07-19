import os
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """
    Reads a recorded VTOP response.

    Fixtures are real HTML captured by scripts/record_fixtures.py and scrubbed
    of personal data. Tests that need one skip cleanly when it has not been
    recorded yet, so a fresh clone still runs green.
    """
    path = FIXTURE_DIR / name
    if not path.exists():
        pytest.skip(
            f"fixture {name} not recorded. Run: python scripts/record_fixtures.py"
        )
    return path.read_text(encoding="utf-8")


@pytest.fixture
def fixture():
    """Gives a test access to the recorded fixtures."""
    return load_fixture


def require_credentials() -> tuple[str, str]:
    """
    Reads VTOP credentials from the environment for live tests.

    Credentials are never stored in the repo. Copy .env.example to .env and
    fill it in, or export the variables in your shell.
    """
    username = os.environ.get("VTOP_USERNAME")
    password = os.environ.get("VTOP_PASSWORD")
    if not username or not password:
        pytest.skip(
            "VTOP_USERNAME and VTOP_PASSWORD are not set. "
            "See .env.example for how to run live tests."
        )
    return username, password
