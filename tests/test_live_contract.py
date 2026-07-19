"""
Contract tests against the live VTOP portal.

These are the only tests that can tell you VTOP changed. Everything else tests
your own code against a snapshot; this tests the assumption the snapshot was
built on.

They are deselected by default. To run them:

    cp .env.example .env        # fill in your credentials
    pytest -m live

VTOP will usually ask for a login OTP, which is prompted for on stdin, so
these cannot run unattended. That is deliberate: an unattended runner would
need a stored password, and repeated failed logins can lock the account.

Run them on a schedule you drive by hand, or nightly on a machine where you
can answer the prompt. A failure here means: re-record the fixtures with
scripts/record_fixtures.py, see what moved, and fix the parsers.

These are read only. Nothing here submits, deletes, or uploads anything.
"""

import os
import re

import pytest

from tests.conftest import require_credentials
from vitap_vtop_client import VtopClient
from vitap_vtop_client.exceptions import VtopLoginOtpRequiredError

pytestmark = pytest.mark.live

SEMESTER_ID = re.compile(r"^[A-Z]{2,3}\d{6,}$")


@pytest.fixture(scope="module")
async def client():
    """
    One authenticated session shared by every live test.

    Logging in repeatedly would burn OTPs and risk locking the account, so the
    session is established once per run.
    """
    username, password = require_credentials()
    session = VtopClient(username, password)

    try:
        await session.login()
    except VtopLoginOtpRequiredError:
        otp = os.environ.get("VTOP_OTP")
        if not otp:
            otp = input("\nVTOP sent a login OTP. Enter it: ").strip()
        await session.verify_login_otp(otp)

    yield session
    await session.close()


async def test_login_establishes_a_session(client):
    """If this fails, the login flow itself has changed."""
    student = await client._ensure_logged_in()

    assert student.registration_number
    assert student.post_login_csrf_token


async def test_semesters_are_live_and_well_formed(client):
    data = await client.get_semesters()

    assert data.semesters, "VTOP returned no semesters; the dropdown may have moved"
    for semester in data.semesters:
        assert SEMESTER_ID.match(semester.id), f"unexpected id {semester.id!r}"
        assert semester.name


async def test_attendance_still_carries_the_fields_we_depend_on(client):
    semesters = await client.get_semesters()
    records = await client.get_attendance(semesters.semesters[0].id)

    if not records:
        pytest.skip("no attendance registered for the newest semester")

    for record in records:
        assert record.course_code
        # Losing course_id would silently break get_attendance_detail.
        assert record.course_id, f"{record.course_code} lost its course_id"
        assert record.course_type_code


async def test_attendance_detail_resolves_for_a_real_course(client):
    """
    Exercises the chain end to end: the id parsed out of the listing has to be
    accepted by the detail endpoint. This is the assertion that would have
    caught course_id holding the class number.
    """
    semesters = await client.get_semesters()
    sem_id = semesters.semesters[0].id
    records = await client.get_attendance(sem_id)

    if not records:
        pytest.skip("no attendance registered for the newest semester")

    target = records[0]
    detail = await client.get_attendance_detail(
        sem_sub_id=sem_id,
        course_id=target.course_id,
        course_type=target.course_type_code,
    )

    # A course with zero classes held is possible early in a semester.
    for entry in detail:
        assert entry.date
        assert entry.status


async def test_grade_history_returns_courses_not_just_a_summary(client):
    result = await client.get_grade_history()

    assert result.cgpa != "N/A", "cgpa fell back to its placeholder"
    assert result.courses, "the per course grade table was not found"


async def test_profile_is_populated(client):
    profile = await client.get_profile()

    assert profile.student_name
    assert profile.application_number


async def test_timetable_parses_live(client):
    semesters = await client.get_semesters()
    timetable = await client.get_timetable(semesters.semesters[0].id)

    days = [
        timetable.Monday,
        timetable.Tuesday,
        timetable.Wednesday,
        timetable.Thursday,
        timetable.Friday,
        timetable.Saturday,
        timetable.Sunday,
    ]
    if not any(days):
        pytest.skip("no classes scheduled in the newest semester")

    for day in days:
        for entry in day:
            assert entry.course_code


async def test_faculty_search_returns_results(client):
    faculty = await client.get_all_faculty()

    assert faculty, "the faculty directory came back empty"
    for member in faculty[:20]:
        assert member.emp_id, f"{member.faculty_name} has no emp_id"


async def test_digital_assignments_list_live(client):
    semesters = await client.get_semesters()
    assignments = await client.get_digital_assignments(semesters.semesters[0].id)

    if not assignments:
        pytest.skip("no courses with digital assignments this semester")

    for course in assignments:
        assert course.class_id
        assert course.course_code
