"""
Academic calendar tests.

The calendar is a three step drill-down: pick a semester (which yields the
class groups and the month buttons), pick a class group, then open a month.
VTOP renders each month as a Sunday-to-Saturday week grid; the parser flattens
it into dated days, because the grid is a display concern.
"""

import httpx
import pytest

from vitap_vtop_client.academic_calendar import (
    fetch_academic_calendar,
    fetch_calendar_month,
)
from vitap_vtop_client.constants import CALENDAR_MONTHS_URL, VIEW_CALENDAR_URL
from vitap_vtop_client.exceptions import VtopParsingError
from vitap_vtop_client.parsers.calendar_parser import (
    parse_calendar_month,
    parse_calendar_months,
    parse_class_groups,
)


def month_buttons(*cal_dates: str) -> str:
    """VTOP HTML-escapes the quotes inside these onclick handlers."""
    return "".join(
        '<a class="btn" href="javascript:void(0);" '
        f"onclick=\"javascript:processViewCalendar(&#39;{c}&#39;);\">"
        f"{c[3:]}</a>"
        for c in cal_dates
    )


def day_cell(day: str, description: str = "", label: str = "") -> str:
    inner = f"<span>{day}</span>"
    if description:
        inner += f'<span style="color: green;">{description}</span>'
    if label:
        inner += f'<span style="color: #eb556e;">({label})</span>'
    return f"<td>{inner}</td>"


def month_grid(*week_rows: str) -> str:
    header = (
        "<tr><th>Sunday</th><th>Monday</th><th>Tuesday</th><th>Wednesday</th>"
        "<th>Thursday</th><th>Friday</th><th>Saturday</th></tr>"
    )
    return f'<table class="table calendar-table">{header}{"".join(week_rows)}</table>'


def test_parses_class_groups():
    html = (
        '<select id="classGroupId" name="classGroupId">'
        '<option value="">--Choose--</option>'
        '<option value="COMB">All Class Group (Combined)</option>'
        '<option value="ALL">General (Semester)</option>'
        "</select>"
    )

    groups = parse_class_groups(html)

    assert [(g.id, g.name) for g in groups] == [
        ("COMB", "All Class Group (Combined)"),
        ("ALL", "General (Semester)"),
    ]


def test_month_buttons_keep_label_and_caldate_separately():
    """
    The button reads "AUG-2026" but processViewCalendar wants "01-AUG-2026",
    and the quotes around it are HTML-escaped in the markup.
    """
    months = parse_calendar_months(month_buttons("01-JUL-2026", "01-AUG-2026"))

    assert [(m.label, m.cal_date) for m in months] == [
        ("JUL-2026", "01-JUL-2026"),
        ("AUG-2026", "01-AUG-2026"),
    ]


def test_month_grid_becomes_dated_days():
    """The week grid is flattened; the weekday comes from the column."""
    html = month_grid(
        "<tr>"
        + "<td></td>" * 6
        + day_cell("1", "Instructional Day - General (Semester)", "WorkingDay")
        + "</tr>"
        + "<tr>"
        + day_cell("2", "Holiday - General (Semester)", "Independence Day")
        + day_cell("3", "No Instructional Day - General (Semester)", "No Instructional Day")
        + "</tr>"
    )

    days = parse_calendar_month(html, "01-AUG-2026")

    assert [d.date for d in days] == ["2026-08-01", "2026-08-02", "2026-08-03"]
    assert days[0].weekday == "Saturday"
    assert days[1].weekday == "Sunday"
    assert days[0].events[0].description == "Instructional Day - General (Semester)"
    # The brackets around the qualifier are stripped.
    assert days[1].events[0].label == "Independence Day"


def test_padding_cells_are_skipped():
    """Cells before the 1st and after the last hold no day number."""
    html = month_grid(
        "<tr>" + "<td><span></span></td>" * 5 + day_cell("1", "Instructional Day") + "</tr>"
    )

    days = parse_calendar_month(html, "01-AUG-2026")

    assert len(days) == 1 and days[0].day == 1


def test_a_day_can_carry_more_than_one_event():
    """
    Not seen in the sampled semester, but the markup allows it: a second
    description span starts a new event rather than overwriting the first.
    """
    cell = (
        "<td><span>5</span>"
        "<span>Instructional Day - General (Semester)</span><span>(WorkingDay)</span>"
        "<span>Guest Lecture</span><span>(Event)</span></td>"
    )
    days = parse_calendar_month(month_grid(f"<tr>{cell}</tr>"), "01-AUG-2026")

    assert len(days[0].events) == 2
    assert days[0].events[1].description == "Guest Lecture"
    assert days[0].events[1].label == "Event"


def test_an_unusable_caldate_is_reported():
    with pytest.raises(VtopParsingError):
        parse_calendar_month(month_grid("<tr></tr>"), "not-a-date")


def test_an_empty_response_yields_no_days():
    assert parse_calendar_month("<html></html>", "01-AUG-2026") == []


async def test_fetch_month_sends_the_expected_request():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.content.decode()
        seen["ajax"] = request.headers.get("x-requested-with", "")
        return httpx.Response(
            200,
            html=month_grid("<tr>" + day_cell("1", "Instructional Day", "WorkingDay") + "</tr>"),
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://vtop.vitap.ac.in"
    ) as client:
        days = await fetch_calendar_month(
            client, "00XXX0000", "tok", "AP2026272", "01-AUG-2026", "COMB"
        )

    assert seen["path"] == VIEW_CALENDAR_URL
    assert seen["ajax"] == "XMLHttpRequest"
    for field in ("calDate=01-AUG-2026", "semSubId=AP2026272", "classGroupId=COMB",
                  "authorizedID=00XXX0000", "_csrf=tok"):
        assert field in seen["body"], f"{field} missing from {seen['body']}"
    assert days[0].date == "2026-08-01"


async def test_the_whole_calendar_fetches_every_month_and_sorts_by_date():
    """The convenience walks the month list and flattens the result."""
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        if request.url.path == CALENDAR_MONTHS_URL:
            return httpx.Response(
                200, html=month_buttons("01-JUL-2026", "01-AUG-2026"), request=request
            )
        cal_date = [p.split("=")[1] for p in body.split("&") if p.startswith("calDate=")][0]
        requested.append(cal_date)
        # Return August first to prove the days come back sorted, not in
        # request order.
        return httpx.Response(
            200,
            html=month_grid("<tr>" + day_cell("2", "Instructional Day", "WorkingDay") + "</tr>"),
            request=request,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://vtop.vitap.ac.in"
    ) as client:
        calendar = await fetch_academic_calendar(client, "00XXX0000", "tok", "AP2026272")

    assert requested == ["01-JUL-2026", "01-AUG-2026"]
    assert calendar.semester_id == "AP2026272"
    assert calendar.class_group_id == "COMB"
    assert len(calendar.months) == 2
    assert [d.date for d in calendar.days] == ["2026-07-02", "2026-08-02"]
