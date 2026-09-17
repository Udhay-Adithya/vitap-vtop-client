"""
Tests for detecting a session VTOP has stopped honouring.

The working notes say a dead session shows up as the login page coming back
where data was expected. That is not what an expired CSRF token looks like:
Spring's CSRF filter refuses the request before it is routed, so Tomcat answers
with its own 404 and the caller used to see a bare HTTPStatusError wrapped in
whichever feature error they happened to be in.
"""

import httpx
import pytest

from vitap_vtop_client import VtopClient
from vitap_vtop_client.exceptions import VtopSessionError

# Trimmed from a real response to a POST carrying an invalid _csrf.
TOMCAT_404 = (
    "<!doctype html><html lang=\"en\"><head>"
    "<title>HTTP Status 404 – Not Found</title></head><body>"
    "<h1>HTTP Status 404 – Not Found</h1>"
    "<h3>Apache Tomcat/9.0.85</h3></body></html>"
)


def client_returning(status: int, text: str = "", method_seen=None) -> VtopClient:
    client = VtopClient("00XXX0000", "pw")

    def handler(request: httpx.Request) -> httpx.Response:
        if method_seen is not None:
            method_seen.append(request.method)
        return httpx.Response(status, text=text)

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://vtop.vitap.ac.in",
        event_hooks=client._client.event_hooks,
    )
    return client


async def test_a_404_on_a_post_is_reported_as_an_expired_session():
    client = client_returning(404, TOMCAT_404)
    with pytest.raises(VtopSessionError) as excinfo:
        await client._client.post("/vtop/processViewStudentAttendance")
    assert "log in again" in str(excinfo.value).lower()
    await client._client.aclose()


async def test_the_error_carries_401_not_404():
    """
    The caller's problem is authentication, not a missing resource, and the API
    service maps status codes straight through.
    """
    client = client_returning(404, TOMCAT_404)
    with pytest.raises(VtopSessionError) as excinfo:
        await client._client.post("/vtop/processViewStudentAttendance")
    assert excinfo.value.status_code == 401
    await client._client.aclose()


async def test_a_404_on_a_get_is_left_alone():
    """
    Only the data posts carry a CSRF token. A GET 404 is an ordinary missing
    resource and should not be disguised as a session problem.
    """
    client = client_returning(404, TOMCAT_404)
    response = await client._client.get("/vtop/something")
    assert response.status_code == 404
    await client._client.aclose()


async def test_a_normal_response_is_untouched():
    client = client_returning(200, "<table id='AttendanceDetailDataTable'></table>")
    response = await client._client.post("/vtop/processViewStudentAttendance")
    assert response.status_code == 200
    await client._client.aclose()
