"""
Tests for exporting a session and rebuilding a client from it.

VTOP keeps the session server side against the JSESSIONID cookie, so a client
holding that cookie and the post-login CSRF token can make data requests
without ever authenticating. That is what lets a caller stay stateless instead
of keeping a live VtopClient in memory, which matters because VTOP's login is
captcha gated and may demand an OTP a human has to read from their email.
"""

import httpx
import pytest

from vitap_vtop_client import RestorableSession, VtopClient
from vitap_vtop_client.exceptions import VtopLoginError, VtopSessionError
from vitap_vtop_client.login.model.logged_in_student_model import LoggedInStudent


def logged_in(client: VtopClient) -> VtopClient:
    client._logged_in_student = LoggedInStudent(
        registration_number="00XXX0000", post_login_csrf_token="tok"
    )
    client._client.cookies.set("JSESSIONID", "abc123")
    return client


# --- exporting ---

def test_session_carries_everything_restore_needs():
    session = logged_in(VtopClient("00XXX0000", "pw")).session
    assert isinstance(session, RestorableSession)
    assert session.registration_number == "00XXX0000"
    assert "JSESSIONID=abc123" in session.cookie
    assert session.csrf_token == "tok"
    assert session.user_agent


def test_exporting_before_login_is_refused():
    with pytest.raises(VtopSessionError):
        _ = VtopClient("00XXX0000", "pw").session


# --- restoring ---

def test_a_restored_client_is_authenticated_without_a_password():
    client = VtopClient.restore("00XXX0000", "JSESSIONID=abc123", "tok")
    assert client.is_authenticated
    assert client.password is None
    assert dict(client._client.cookies) == {"JSESSIONID": "abc123"}


def test_a_multi_value_cookie_header_is_split_back_out():
    client = VtopClient.restore("00XXX0000", "JSESSIONID=abc123; other=xyz", "tok")
    assert dict(client._client.cookies) == {"JSESSIONID": "abc123", "other": "xyz"}


def test_the_registration_number_is_normalised_like_a_login():
    assert VtopClient.restore("00xxx0000", "JSESSIONID=a", "tok").username == "00XXX0000"


@pytest.mark.parametrize(
    "args",
    [
        ("", "JSESSIONID=a", "tok"),
        ("00XXX0000", "", "tok"),
        ("00XXX0000", "JSESSIONID=a", ""),
    ],
)
def test_restoring_without_all_three_values_is_refused(args):
    with pytest.raises(VtopSessionError):
        VtopClient.restore(*args)


def test_a_round_trip_reproduces_the_session():
    original = logged_in(VtopClient("00XXX0000", "pw", user_agent="Device/1.0")).session
    restored = VtopClient.restore(
        original.registration_number,
        original.cookie,
        original.csrf_token,
        user_agent=original.user_agent,
    )
    assert restored.session.model_dump() == original.model_dump()


# --- the password guard ---

async def test_a_restored_client_refuses_to_log_itself_back_in():
    """
    It has no password, so a dead session cannot be recovered here. Saying so
    is more use than failing a login with an empty credential -- and repeated
    failed logins can lock a VTOP account.
    """
    client = VtopClient.restore("00XXX0000", "JSESSIONID=abc123", "tok")
    client._logged_in_student = None

    with pytest.raises(VtopSessionError) as excinfo:
        await client._ensure_logged_in()
    assert "log in again" in str(excinfo.value).lower()


def test_a_normal_client_still_demands_a_password():
    with pytest.raises(VtopLoginError):
        VtopClient("00XXX0000", "")
    with pytest.raises(VtopLoginError):
        VtopClient("00XXX0000")


async def test_a_restored_client_sends_the_cookie_and_token():
    client = VtopClient.restore("00XXX0000", "JSESSIONID=abc123", "tok")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["cookie"] = request.headers.get("cookie", "")
        return httpx.Response(200, text="<table id='AttendanceDetailDataTable'></table>")

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://vtop.vitap.ac.in",
        cookies=client._client.cookies,
    )
    await client._client.post("/vtop/processViewStudentAttendance")
    assert "JSESSIONID=abc123" in seen["cookie"]
    await client._client.aclose()
