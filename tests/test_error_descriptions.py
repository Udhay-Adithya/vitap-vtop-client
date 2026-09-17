"""
Tests that a failed request says what failed.

httpx raises its transport errors with an empty message, so a message built
with f"...: {e}" stops at the colon. A live timeout surfaced as

    VtopProfileError: Unexpected error while fetching student profile:
    Failed to fetch grade history:

with nothing after either colon, and blaming grade history for a timeout that
happened on the profile page request.
"""

import httpx
import pytest

from vitap_vtop_client.exceptions import VtopConnectionError


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ReadTimeout(""),
        httpx.ConnectTimeout(""),
        httpx.PoolTimeout(""),
        httpx.WriteTimeout(""),
        httpx.ConnectError(""),
    ],
)
def test_a_silent_transport_error_is_named(exc):
    """Every one of these stringifies to "" and used to vanish from the message."""
    error = VtopConnectionError(
        f"Failed to fetch grade history: {exc}", original_exception=exc, status_code=502
    )
    assert str(error).endswith(type(exc).__name__)
    assert not str(error).endswith(": ")


def test_an_exception_that_describes_itself_is_left_alone():
    exc = httpx.ConnectError("nodename nor servname provided")
    error = VtopConnectionError(f"Failed: {exc}", original_exception=exc)
    assert str(error) == "Failed: nodename nor servname provided"
    assert "ConnectError" not in str(error)


def test_no_original_exception_means_no_change():
    assert str(VtopConnectionError("Plain message")) == "Plain message"


def test_the_status_code_and_original_are_still_carried():
    exc = httpx.ReadTimeout("")
    error = VtopConnectionError("Failed: ", original_exception=exc, status_code=502)
    assert error.status_code == 502
    assert error.original_exception is exc
