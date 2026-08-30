"""
Capstone/SDP attendance tests.

VTOP reaches this through a button on the attendance page, which POSTs to
`processSdpAttendance` and drops the returned fragment into the page. The
response carries three tables: registration info, the present/OD/absent tally,
and a day-by-day punch calendar.
"""

import httpx
import pytest

from tests._capstone_sample import CAPSTONE_RESPONSE
from vitap_vtop_client.attendance import fetch_capstone_attendance
from vitap_vtop_client.constants import SDP_ATTENDANCE_URL
from vitap_vtop_client.parsers.capstone_attendance_parser import (
    parse_capstone_attendance,
)


def test_parses_the_registration_info():
    result = parse_capstone_attendance(CAPSTONE_RESPONSE)

    assert result is not None
    assert result.info.title == "Capstone"
    assert result.info.date_of_registration == "2026-07-06 00:00:00.0"
    assert "Approved" in result.info.guide_evaluation_status


def test_parses_the_attendance_summary():
    summary = parse_capstone_attendance(CAPSTONE_RESPONSE).summary

    assert summary.present == "14"
    assert summary.on_duty == "4"
    assert summary.absent == "12"
    # The % sign is stripped, matching AttendanceModel.attendance_percentage.
    assert summary.percentage == "60"


def test_parses_the_punch_calendar():
    punches = parse_capstone_attendance(CAPSTONE_RESPONSE).punches

    assert punches, "no calendar rows parsed"
    first = punches[0]
    assert first.serial == "1"
    assert first.date == "17-07-2026"
    assert first.day == "FRIDAY"
    assert first.day_type == "Instructional"
    # The status is wrapped in nested spans; only the text matters.
    assert first.status == "Absent"


def test_reads_every_status_variant():
    by_serial = {p.serial: p for p in parse_capstone_attendance(CAPSTONE_RESPONSE).punches}

    assert by_serial["1"].status == "Absent"
    assert by_serial["9"].status == "On Duty"
    assert by_serial["19"].status == "Present"
    assert by_serial["19"].punch_time == "09:49:13"


def test_a_dash_becomes_empty_rather_than_leaking():
    """
    VTOP renders "-" for days with no status and no punch (holidays,
    non-instructional days). Callers should see an empty value, not a dash.
    """
    by_serial = {p.serial: p for p in parse_capstone_attendance(CAPSTONE_RESPONSE).punches}

    holiday = by_serial["3"]
    assert holiday.day_type == "Holiday"
    assert holiday.status == ""
    assert holiday.punch_time == ""


def test_commented_out_markup_does_not_leak():
    """
    The response embeds a dead Thymeleaf info table (with Rejected/Approved/
    Pending badges) and a commented-out Description column. Neither may appear.
    """
    result = parse_capstone_attendance(CAPSTONE_RESPONSE)

    assert result.info.guide_evaluation_status not in ("Rejected", "Approved", "Pending")
    for punch in result.punches:
        assert "Description" not in (punch.day_type, punch.status)


def test_no_capstone_returns_none():
    """A student without a capstone gets a fragment carrying no summary."""
    assert parse_capstone_attendance('<div id="sdpAttendanceFragment"></div>') is None
    assert parse_capstone_attendance("") is None


async def test_fetch_sends_what_vtops_own_javascript_sends():
    """
    viewSDPAttendance() posts _csrf, semesterSubId, regNo, authorizedID and a
    timestamp as an AJAX request. The registration number goes in twice, under
    two different names, and VTOP wants both.
    """
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.content.decode()
        seen["ajax"] = request.headers.get("x-requested-with")
        return httpx.Response(200, html=CAPSTONE_RESPONSE, request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://vtop.vitap.ac.in"
    ) as client:
        result = await fetch_capstone_attendance(
            client, "00XXX0000", "AP2026272", "tok"
        )

    assert seen["path"] == SDP_ATTENDANCE_URL
    assert seen["ajax"] == "XMLHttpRequest"
    body = seen["body"]
    for field in ("_csrf=tok", "semesterSubId=AP2026272", "regNo=00XXX0000",
                  "authorizedID=00XXX0000", "x="):
        assert field in body, f"{field} missing from {body}"
    assert result is not None and result.summary.present == "14"


async def test_fetch_returns_none_for_a_student_without_a_capstone():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html="<div id='sdpAttendanceFragment'></div>",
                              request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://vtop.vitap.ac.in"
    ) as client:
        assert await fetch_capstone_attendance(
            client, "00XXX0000", "AP2026272", "tok"
        ) is None
