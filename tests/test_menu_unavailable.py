"""
Tests for VTOP's catch-all rejection.

VTOP answers a rejected request with a small fragment saying the menu is not
available, served with an HTTP 200. Because it is a 200 with a body,
raise_for_status() passes and the fragment used to reach a parser that could
not recognise it, so the caller saw a parsing error pointing at our code
instead of at what VTOP did.
"""

import httpx
import pytest

from vitap_vtop_client import VtopClient
from vitap_vtop_client.exceptions import VtopMenuUnavailableError
from vitap_vtop_client.utils import MENU_UNAVAILABLE_MARKER, is_menu_unavailable

# The real body, trimmed. The wording is the only signal VTOP gives us.
REJECTION = """
    <div class="modal" tabindex="-1" id="msgBox">
      <div class="modal-body">
        <span class="text-danger fw-bold h6" id="msgBoxInfoText">
          This menu is not available at present!!!
        </span>
      </div>
    </div>
"""

REAL_PAGE = '<table id="AttendanceDetailDataTable"><tr><td>1</td></tr></table>'


def test_the_marker_is_found_in_a_real_rejection():
    assert is_menu_unavailable(REJECTION)


def test_a_real_page_is_not_mistaken_for_a_rejection():
    assert not is_menu_unavailable(REAL_PAGE)


def test_the_marker_stops_short_of_the_exclamation_marks():
    """VTOP writes "!!!" today. Matching them would make this brittle."""
    assert not MENU_UNAVAILABLE_MARKER.endswith("!")


async def test_the_client_raises_rather_than_handing_the_modal_to_a_parser():
    """
    The check lives in a response hook so it applies to every fetch function,
    including ones added later, rather than being repeated in each of them.
    """
    client = VtopClient("00XXX0000", "pw")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=REJECTION)

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://vtop.vitap.ac.in",
        event_hooks=client._client.event_hooks,
    )

    with pytest.raises(VtopMenuUnavailableError) as excinfo:
        await client._client.post("/vtop/processViewStudentAttendance")

    message = str(excinfo.value)
    assert "/vtop/processViewStudentAttendance" in message
    # The three causes are indistinguishable from the response, so the message
    # must not claim to know which one it was.
    assert "switched off" in message
    await client._client.aclose()


async def test_a_normal_response_passes_through_untouched():
    client = VtopClient("00XXX0000", "pw")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=REAL_PAGE)

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://vtop.vitap.ac.in",
        event_hooks=client._client.event_hooks,
    )

    response = await client._client.post("/vtop/processViewStudentAttendance")
    assert response.status_code == 200
    assert "AttendanceDetailDataTable" in response.text
    await client._client.aclose()
