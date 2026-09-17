"""
Tests that a dead session stays a session error.

#27 made an expired token raise VtopSessionError with a 401 and a message
saying to log in again. The feature modules then wrapped it in their own error
via `except Exception`, so the caller got, say, VtopAttendanceError with no
status code and the actionable part buried in a string. Downstream that becomes
a 500: "the server broke" instead of "your session expired".
"""

import httpx
import pytest

from vitap_vtop_client import VtopClient
from vitap_vtop_client.exceptions import VtopSessionError

SEM = "AP2026272"


def dead_session_client() -> VtopClient:
    """A restored client whose every request gets the Tomcat 404 of a dead token."""
    client = VtopClient.restore("00XXX0000", "JSESSIONID=dead", "dead-token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="<h1>HTTP Status 404 - Not Found</h1>")

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://vtop.vitap.ac.in",
        event_hooks=client._client.event_hooks,
        cookies=client._client.cookies,
    )
    return client


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.get_attendance(sem_sub_id=SEM),
        lambda c: c.get_marks(sem_sub_id=SEM),
        lambda c: c.get_timetable(sem_sub_id=SEM),
        lambda c: c.get_exam_schedule(sem_sub_id=SEM),
        lambda c: c.get_grade_history(),
        lambda c: c.get_mentor(),
        lambda c: c.get_profile(),
        lambda c: c.get_biometric(date="01-09-2026"),
        lambda c: c.get_pending_payments(),
        lambda c: c.get_general_outing_requests(),
        lambda c: c.get_weekend_outing_requests(),
    ],
)
async def test_a_dead_session_surfaces_as_a_session_error(call):
    client = dead_session_client()
    with pytest.raises(VtopSessionError) as excinfo:
        await call(client)
    # The status code is what a caller maps onto HTTP; losing it was the bug.
    assert excinfo.value.status_code == 401
    assert "log in again" in str(excinfo.value).lower()
    await client._client.aclose()
