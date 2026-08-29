"""
Tests for the semester lookup fallback.

The semester dropdown appears on several VTOP pages but they do not list the
same semesters: the timetable page shows only the semesters the student already
has a timetable for and is **empty for freshers**, while the marks and exam
schedule pages render the full institutional list for anyone who can log in.
Falling back is what stops a fresh login dead-ending on "No semesters available".
"""

import httpx
import pytest

from vitap_vtop_client.constants import EXAM_SCHEDULE_URL, MARKS_URL, TIME_TABLE_URL
from vitap_vtop_client.semester import fetch_semesters

PLACEHOLDER = '<option value="">-- Choose Semester --</option>'
EMPTY_DROPDOWN = f'<select name="semesterSubId">{PLACEHOLDER}</select>'
FULL_DROPDOWN = (
    '<select name="semesterSubId">'
    f"{PLACEHOLDER}"
    '<option value="AP2026273">Fall Semester 2026-27 Freshers</option>'
    '<option value="AP2026272">Fall Semester 2026-27</option>'
    "</select>"
)


def client_for(pages: dict[str, str], visited: list[str]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        visited.append(request.url.path)
        return httpx.Response(
            200, html=pages.get(request.url.path, EMPTY_DROPDOWN), request=request
        )

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://vtop.vitap.ac.in"
    )


async def test_timetable_is_preferred_when_it_has_semesters():
    """The timetable list is the student's own, so it wins when populated."""
    visited: list[str] = []
    async with client_for({TIME_TABLE_URL: FULL_DROPDOWN}, visited) as client:
        data = await fetch_semesters(client, "00XXX0000", "tok")

    assert [s.id for s in data.semesters] == ["AP2026273", "AP2026272"]
    # The fallbacks must not be requested needlessly.
    assert visited == [TIME_TABLE_URL]


async def test_falls_back_to_marks_when_the_timetable_is_empty():
    """The fresher case: no timetable yet, so the marks page supplies the list."""
    visited: list[str] = []
    async with client_for({MARKS_URL: FULL_DROPDOWN}, visited) as client:
        data = await fetch_semesters(client, "00XXX0000", "tok")

    assert data.semesters, "the fallback produced no semesters"
    assert data.semesters[0].name == "Fall Semester 2026-27 Freshers"
    assert visited == [TIME_TABLE_URL, MARKS_URL]


async def test_falls_back_again_to_the_exam_schedule():
    visited: list[str] = []
    async with client_for({EXAM_SCHEDULE_URL: FULL_DROPDOWN}, visited) as client:
        data = await fetch_semesters(client, "00XXX0000", "tok")

    assert data.semesters
    assert visited == [TIME_TABLE_URL, MARKS_URL, EXAM_SCHEDULE_URL]


async def test_all_sources_empty_returns_an_empty_list_not_an_error():
    """The caller shows its own message; an empty result is not an exception."""
    visited: list[str] = []
    async with client_for({}, visited) as client:
        data = await fetch_semesters(client, "00XXX0000", "tok")

    assert data.semesters == []
    assert len(visited) == 3
