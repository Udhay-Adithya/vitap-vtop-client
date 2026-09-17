"""
Tests for session identity: the User-Agent and cookie export.

The identity is fixed for the life of a client so a session presents one
consistent User-Agent, and is readable by anything reusing the session out of
process (an in-app VTOP WebView). VTOP was not observed to require a reused
session to match it, so these tests pin our own behaviour, not a VTOP rule.
"""

import httpx
import pytest

from vitap_vtop_client import VtopClient
from vitap_vtop_client.constants import DEFAULT_USER_AGENT, HEADERS, build_headers
from vitap_vtop_client.exceptions import VtopSessionError
from vitap_vtop_client.login.model.logged_in_student_model import LoggedInStudent


def logged_in(client: VtopClient) -> VtopClient:
    client._logged_in_student = LoggedInStudent(
        registration_number="00XXX0000", post_login_csrf_token="tok"
    )
    return client


def test_defaults_to_the_bundled_user_agent():
    assert VtopClient("00XXX0000", "pw").user_agent == DEFAULT_USER_AGENT


def test_a_caller_supplied_user_agent_is_used():
    client = VtopClient("00XXX0000", "pw", user_agent="DeviceBrowser/9.9")
    assert client.user_agent == "DeviceBrowser/9.9"


def test_a_blank_user_agent_falls_back_to_the_default():
    assert VtopClient("00XXX0000", "pw", user_agent="   ").user_agent == DEFAULT_USER_AGENT


async def test_the_session_user_agent_wins_over_per_request_headers():
    """
    Fetch functions pass the module HEADERS, which carry the default agent.
    httpx lets request headers win over client defaults, so the client pins its
    own agent after the merge — otherwise a caller's agent would be silently
    ignored and the session would not carry the identity they asked for.
    """
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, text="ok", request=request)

    client = VtopClient("00XXX0000", "pw", user_agent="DeviceBrowser/9.9")
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://vtop.vitap.ac.in",
        event_hooks=client._client.event_hooks,
    )
    await client._client.post("/vtop/anything", data={"a": 1}, headers=HEADERS)
    await client.close()

    assert seen["ua"] == "DeviceBrowser/9.9"


def test_build_headers_overrides_only_when_given_a_value():
    assert build_headers("Custom/1.0")["User-Agent"] == "Custom/1.0"
    assert build_headers(None)["User-Agent"] == DEFAULT_USER_AGENT
    assert build_headers("  ")["User-Agent"] == DEFAULT_USER_AGENT
    # The shared dict must not be mutated by building a variant.
    assert HEADERS["User-Agent"] == DEFAULT_USER_AGENT


def test_get_cookie_requires_a_session():
    with pytest.raises(VtopSessionError, match="Not logged in"):
        VtopClient("00XXX0000", "pw").get_cookie()


def test_get_cookie_exports_the_session_cookies():
    client = logged_in(VtopClient("00XXX0000", "pw"))
    client._client.cookies.set("JSESSIONID", "ABC123", "vtop.vitap.ac.in", "/")

    assert client.get_cookie() == "JSESSIONID=ABC123"


def test_is_authenticated_reflects_the_session():
    client = VtopClient("00XXX0000", "pw")
    assert client.is_authenticated is False
    assert logged_in(client).is_authenticated is True
