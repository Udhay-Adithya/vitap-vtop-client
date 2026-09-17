"""
Tests for carrying an OTP challenge between processes.

restore() made an authenticated session portable, but a pending challenge is a
different state: verify_login_otp needs `_pending_otp_csrf`, which only the
login sequence ever set. A web service raises the challenge while answering one
request and receives the OTP on the next, by which point the client that raised
it is gone — so without this the login could never be completed.
"""

import httpx
import pytest

from vitap_vtop_client import OtpChallenge, VtopClient
from vitap_vtop_client.exceptions import VtopSessionError


def pending(client: VtopClient, token: str = "otp-csrf") -> VtopClient:
    client._pending_otp_csrf = token
    client._client.cookies.set("JSESSIONID", "abc123")
    return client


# --- exporting ---

def test_a_pending_challenge_exports_everything_needed_to_finish_it():
    challenge = pending(VtopClient("00XXX0000", "pw")).otp_challenge
    assert isinstance(challenge, OtpChallenge)
    assert challenge.registration_number == "00XXX0000"
    assert "JSESSIONID=abc123" in challenge.cookie
    assert challenge.csrf_token == "otp-csrf"
    assert challenge.user_agent


def test_exporting_without_a_pending_challenge_is_refused():
    with pytest.raises(VtopSessionError):
        _ = VtopClient("00XXX0000", "pw").otp_challenge


def test_the_cookie_is_readable_even_though_the_client_is_not_logged_in():
    """
    get_cookie() guards on being authenticated, which a pending challenge is
    not — that guard is exactly why the challenge could not be exported before.
    """
    client = pending(VtopClient("00XXX0000", "pw"))
    with pytest.raises(VtopSessionError):
        client.get_cookie()
    assert "JSESSIONID=abc123" in client.otp_challenge.cookie


# --- restoring ---

def test_a_restored_challenge_is_pending_but_not_authenticated():
    client = VtopClient.restore_otp_challenge("00XXX0000", "JSESSIONID=abc123", "tok")
    assert client.otp_pending
    assert not client.is_authenticated
    assert client.password is None
    assert dict(client._client.cookies) == {"JSESSIONID": "abc123"}


async def test_a_restored_challenge_will_not_serve_data_until_the_otp_is_verified():
    """
    A half-finished login must not look usable. The pending check runs before
    the restored-client check, so the caller is told to answer the OTP rather
    than to log in again.
    """
    client = VtopClient.restore_otp_challenge("00XXX0000", "JSESSIONID=abc123", "tok")
    with pytest.raises(VtopSessionError) as excinfo:
        await client._ensure_logged_in()
    assert "otp" in str(excinfo.value).lower()


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
        VtopClient.restore_otp_challenge(*args)


def test_a_round_trip_reproduces_the_challenge():
    original = pending(VtopClient("00XXX0000", "pw", user_agent="Device/1.0")).otp_challenge
    restored = VtopClient.restore_otp_challenge(
        original.registration_number,
        original.cookie,
        original.csrf_token,
        user_agent=original.user_agent,
    )
    assert restored.otp_challenge.model_dump() == original.model_dump()


# --- finishing the login on a restored challenge ---

async def test_verify_login_otp_submits_the_restored_token_and_cookie():
    client = VtopClient.restore_otp_challenge("00XXX0000", "JSESSIONID=abc123", "the-token")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["cookie"] = request.headers.get("cookie", "")
        seen["body"] = request.content.decode()
        # Enough of the post-login content page for the client to accept it.
        return httpx.Response(
            200,
            text='<input name="authorizedIDX" value="00XXX0000"/>'
                 '<input name="_csrf" value="post-login-token"/>',
        )

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://vtop.vitap.ac.in",
        cookies=client._client.cookies,
    )
    try:
        await client.verify_login_otp("123456")
    except Exception:
        # The parse may not satisfy the real login checks; what matters here is
        # what went on the wire.
        pass

    assert "validateSecurityOtp" in seen["url"]
    assert "JSESSIONID=abc123" in seen["cookie"]
    assert "the-token" in seen["body"]
    assert "123456" in seen["body"]
    await client._client.aclose()


async def test_resend_works_on_a_restored_challenge():
    client = VtopClient.restore_otp_challenge("00XXX0000", "JSESSIONID=abc123", "the-token")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.content.decode()
        return httpx.Response(200, text="OTP sent")

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://vtop.vitap.ac.in",
        cookies=client._client.cookies,
    )
    try:
        await client.resend_login_otp()
    except Exception:
        pass
    assert "resendSecurityOtp" in seen["url"]
    assert "the-token" in seen["body"]
    await client._client.aclose()
