"""
Parser tests over recorded VTOP responses.

These run the parsers against real HTML captured by scripts/record_fixtures.py.
They assert on shape and invariants, never on specific values: a fixture is a
snapshot of one student at one moment, so asserting "CGPA is 9.12" would break
the moment the fixture is re-recorded.

What they are really checking is that the parser still finds the fields it
expects in real markup. When VTOP changes, re-record the fixtures and these
tests tell you which parsers need attention.

Every test skips cleanly when its fixture has not been recorded, so a fresh
clone still runs green.
"""

import re

from vitap_vtop_client.parsers.attendance_parser import parse_attendance
from vitap_vtop_client.parsers.biometric_parser import parse_biometric
from vitap_vtop_client.parsers.grade_history_parser import parse_grade_history
from vitap_vtop_client.parsers.marks_parser import parse_marks
from vitap_vtop_client.parsers.semester_parser import (
    parse_semester_id_from_timetable,
)
from vitap_vtop_client.parsers.timetable_parser import parse_time_table

# Semester ids look like AP2024252 / AMR2017181.
SEMESTER_ID = re.compile(r"^[A-Z]{2,3}\d{6,}$")


def test_semesters_parse_from_the_real_timetable_page(fixture):
    data = parse_semester_id_from_timetable(fixture("semesters.html"))

    assert data.semesters, "no semesters found in the recorded page"
    for semester in data.semesters:
        assert SEMESTER_ID.match(semester.id), f"unexpected semester id {semester.id!r}"
        assert semester.name, f"semester {semester.id} has no name"
        # The placeholder option must never survive.
        assert not semester.name.startswith("--")


def test_attendance_parses_from_a_real_response(fixture):
    records = parse_attendance(fixture("attendance.html"))

    assert records, "no attendance rows found in the recorded response"
    for record in records:
        assert record.course_code, "a row is missing its course code"
        assert record.total_classes, "a row is missing its total classes"
        # course_id drives the detail lookup; losing it silently breaks that.
        assert record.course_id, f"{record.course_code} has no course_id"
        assert record.course_type_code, f"{record.course_code} has no type code"
        # The percentage should be numeric once the % sign is stripped.
        assert re.match(r"^\d+(\.\d+)?$", record.attendance_percentage or "0")


def test_attendance_distinguishes_class_number_from_course_id(fixture):
    """
    These were conflated before. They have visibly different formats, so a
    regression would show up here.
    """
    records = parse_attendance(fixture("attendance.html"))

    for record in records:
        if record.class_number and record.course_id:
            assert record.class_number != record.course_id


def test_biometric_parses_from_a_real_response(fixture):
    records = parse_biometric(fixture("biometric_page.html"))

    # A student may genuinely have no punches on the recorded day, so an empty
    # list is legitimate. Only the shape of what is present is asserted.
    for record in records:
        assert record.serial, "a punch is missing its serial"
        assert record.date, "a punch is missing its date"
        assert record.in_time, "a punch is missing its time"


def test_grade_history_parses_summary_and_courses(fixture):
    result = parse_grade_history(fixture("grade_history.html"))

    assert result.cgpa != "N/A", "cgpa fell back to its placeholder"
    assert result.credits_registered != "N/A"
    assert result.courses, "no graded courses found; the course table was missed"
    for course in result.courses:
        assert course.course_code
        assert course.grade
        assert course.course_code != "Course Code", "a header row leaked through"


def test_timetable_parses_from_a_real_response(fixture):
    timetable = parse_time_table(fixture("timetable.html"))

    days = [
        timetable.Monday,
        timetable.Tuesday,
        timetable.Wednesday,
        timetable.Thursday,
        timetable.Friday,
        timetable.Saturday,
        timetable.Sunday,
    ]
    assert any(days), "no classes found on any day"
    for day in days:
        for entry in day:
            assert entry.course_code
            assert entry.slot


def test_marks_parse_from_a_real_response(fixture):
    marks = parse_marks(fixture("marks.html"))

    # Marks may not be published yet, so emptiness is allowed.
    for subject in marks.root:
        assert subject.course_code
        for detail in subject.details:
            assert detail.mark_title


def test_grade_view_parses_from_a_real_response(fixture):
    from vitap_vtop_client.parsers.grade_view_parser import parse_grade_view

    courses = parse_grade_view(fixture("grade_view.html"))

    assert courses, "no graded courses found in the recorded grade view"
    for course in courses:
        assert course.course_code
        assert course.grade
        # course_id is needed to open the detail; losing it breaks that.
        assert course.course_id, f"{course.course_code} has no course_id"


def test_grade_view_detail_parses_from_a_real_response(fixture):
    from vitap_vtop_client.parsers.grade_view_parser import parse_grade_view_detail

    detail = parse_grade_view_detail(fixture("grade_view_detail.html"))

    assert detail.marks, "no mark components found; the marks table was missed"
    for mark in detail.marks:
        assert mark.mark_title
        assert mark.max_mark
    assert detail.total, "the course total was not read"
    # The statistics table (nested inside the grade table) must be found too.
    assert detail.statistics.grade_ranges, "class grade cutoffs were not parsed"


def test_capstone_attendance_parses_from_a_real_response(fixture):
    from vitap_vtop_client.parsers.capstone_attendance_parser import (
        parse_capstone_attendance,
    )

    result = parse_capstone_attendance(fixture("capstone_attendance.html"))

    # The fixture is only recorded for a student who has a capstone, so a None
    # here means the parser stopped recognising a real response.
    assert result is not None, "the summary table was not found"
    assert result.summary.present, "the present tally was not read"
    assert result.punches, "no calendar rows were parsed"
    for punch in result.punches:
        assert punch.date
        assert punch.day_type
        # "-" is VTOP's placeholder and must never reach the model.
        assert punch.status != "-"
        assert punch.punch_time != "-"
