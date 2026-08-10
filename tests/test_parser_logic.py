"""
Parser logic tests over hand built markup.

These pin down decisions the parsers make about structure: which column wins
when one is missing, when a rendered link is actually usable, how a label is
split. They use synthetic HTML on purpose, because they are testing the
parser's rules rather than VTOP's current output. The fixture tests in
test_parser_contracts.py cover the real shape.
"""

import pytest

from vitap_vtop_client.parsers.attendance_parser import (
    parse_attendance,
    parse_full_attendance,
)
from vitap_vtop_client.parsers.biometric_parser import parse_biometric
from vitap_vtop_client.parsers.course_page_parser import (
    parse_course_detail_page,
    parse_courses_for_course_page,
    parse_slots_for_course_page,
)
from vitap_vtop_client.parsers.digital_assignment_parser import (
    parse_per_course_dassignments,
    parse_upload_assignment_response,
)
from vitap_vtop_client.parsers.faculty_parser import parse_all_faculty_search
from vitap_vtop_client.parsers.grade_history_parser import parse_grade_history
from vitap_vtop_client.parsers.outing_response_parser import parse_outing_response
from vitap_vtop_client.parsers.payments_receipts_parser import parse_payment_receipts
from vitap_vtop_client.parsers.weekend_outing_requests_parser import (
    parse_weekend_outing_requests,
)
from vitap_vtop_client.parsers.semester_parser import (
    parse_semester_id_from_timetable,
)


def row(cells: list[str]) -> str:
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def table(*rows: str) -> str:
    return "<table>" + "".join(rows) + "</table>"


# --------------------------------------------------------------------------
# Attendance
# --------------------------------------------------------------------------

DETAIL_ONCLICK = (
    "callStudentAttendanceDetailDisplay('AP2025264','00XXX0000',"
    "'AM_CSE1008_00200','TH')"
)
DETAIL_LINK = f'<td><a onclick="{DETAIL_ONCLICK}">view</a></td>'

ATTENDANCE_CELLS = [
    "1",
    "x",
    "MAT1001 - Calculus for Engineers - Embedded Lab",
    "AP2024258000131 - L27+L28 - 119",
    "Dr. Rao",
    "40",
    "45",
    "88.88",
]


def test_attendance_reads_course_id_from_the_detail_link():
    """course_id drives the detail lookup and only exists in the onclick."""
    cells = ATTENDANCE_CELLS + ["75", "Not Debarred"]
    html = table(row(["h"]), "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + DETAIL_LINK + "<td>z</td></tr>")

    record = parse_attendance(html)[0]

    assert record.course_id == "AM_CSE1008_00200"
    assert record.course_type_code == "TH"
    # The class number is a different value and must not be confused with it.
    assert record.class_number == "AP2024258000131"


def test_attendance_splits_a_course_label_into_its_parts():
    cells = ATTENDANCE_CELLS + ["75", "Not Debarred"]
    html = table(row(["h"]), "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + DETAIL_LINK + "<td>z</td></tr>")

    record = parse_attendance(html)[0]

    assert record.course_code == "MAT1001"
    assert record.course_name == "Calculus for Engineers"
    assert record.course_type == "Embedded Lab"
    assert record.course_slot == "L27+L28"
    assert record.faculty == "Dr. Rao"


def test_attendance_survives_the_between_column_being_dropped():
    """
    VTOP does not always render the "attendance between" column. When it is
    gone, debar status shifts left and must not be read from the wrong cell.
    """
    with_column = table(
        row(["h"]),
        "<tr>"
        + "".join(f"<td>{c}</td>" for c in ATTENDANCE_CELLS + ["75", "Not Debarred"])
        + DETAIL_LINK
        + "<td>z</td></tr>",
    )
    without_column = table(
        row(["h"]),
        "<tr>"
        + "".join(f"<td>{c}</td>" for c in ATTENDANCE_CELLS + ["Not Debarred", "q"])
        + DETAIL_LINK
        + "</tr>",
    )

    present = parse_attendance(with_column)[0]
    absent = parse_attendance(without_column)[0]

    assert present.attendance_between_percentage == "75"
    assert absent.attendance_between_percentage == "0"
    # Either way the debar status is correct.
    assert present.debar_status == "Not Debarred"
    assert absent.debar_status == "Not Debarred"


def test_attendance_detail_returns_empty_when_the_table_is_absent():
    assert parse_full_attendance("<html></html>") == []


# --------------------------------------------------------------------------
# Biometric
# --------------------------------------------------------------------------


def test_biometric_keeps_the_serial_and_date():
    """These were silently dropped before the parser was rebuilt row wise."""
    html = table(
        row(["S.No", "Date", "Time", "Location"]),
        row(["1", "01-Jan-2026", "08:45", "MB Gate 1"]),
    )

    record = parse_biometric(html)[0]

    assert record.serial == "1"
    assert record.date == "01-Jan-2026"
    assert record.in_time == "08:45"
    assert record.location == "MB Gate 1"


# --------------------------------------------------------------------------
# Grade history
# --------------------------------------------------------------------------


def test_grade_history_picks_the_cgpa_table_not_the_first_match():
    """Several tables share the class; only one carries the summary."""
    html = (
        '<table class="table table-hover table-bordered"><thead><tr><th>Other</th>'
        "</tr></thead><tbody><tr><td>zz</td><td>yy</td><td>xx</td></tr></tbody></table>"
        '<table class="table table-hover table-bordered"><thead><tr>'
        "<th>Credits Registered</th><th>Credits Earned</th><th>CGPA</th></tr></thead>"
        "<tbody><tr><td>160</td><td>152</td><td>9.12</td></tr></tbody></table>"
    )

    result = parse_grade_history(html)

    assert result.credits_registered == "160"
    assert result.cgpa == "9.12"


def test_grade_history_skips_repeated_header_rows():
    html = (
        '<table class="customTable"><tr><th>Course Code</th></tr>'
        + '<tr class="tableContent">'
        + "".join(
            f"<td>{c}</td>"
            for c in ["1", "CSE1008", "Data Structures", "ETH", "4", "A", "Nov 2025", "-", "Core", "x"]
        )
        + "</tr>"
        + '<tr class="tableContent">'
        + "".join(f"<td>{c}</td>" for c in ["2", "Course Code", "hdr", "x", "x", "x", "x", "x", "x", "x"])
        + "</tr></table>"
    )

    courses = parse_grade_history(html).courses

    assert len(courses) == 1
    assert courses[0].course_code == "CSE1008"
    assert courses[0].grade == "A"


def test_grade_history_degrades_to_placeholders_on_an_empty_page():
    result = parse_grade_history("<html></html>")

    assert result.cgpa == "N/A"
    assert result.courses == []


# --------------------------------------------------------------------------
# Semesters
# --------------------------------------------------------------------------


def test_semester_parser_skips_the_placeholder_and_strips_the_amr_suffix():
    html = (
        '<select name="semesterSubId">'
        '<option value="">-- Choose Semester --</option>'
        '<option value="AP2024252">FALL SEM 2024-25</option>'
        '<option value=" AP2024254 ">Winter Semester 2024-25 - AMR</option>'
        "</select>"
    )

    semesters = parse_semester_id_from_timetable(html).semesters

    assert [s.id for s in semesters] == ["AP2024252", "AP2024254"]
    assert semesters[1].name == "Winter Semester 2024-25"


# --------------------------------------------------------------------------
# Faculty
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "button,expected",
    [
        ('<button id="70447">view</button>', "70447"),
        ('<button onclick="getEmp(&quot;80551&quot;)">view</button>', "80551"),
        ("<button onclick='getEmp(\"90112\")'>view</button>", "90112"),
    ],
)
def test_faculty_reads_the_employee_id_from_every_button_form(button, expected):
    html = table(
        row(["Name", "Desig", "School", ""]),
        f"<tr><td>Dr. A</td><td>Prof</td><td>SCOPE</td><td>{button}</td></tr>",
    )

    assert parse_all_faculty_search(html)[0].emp_id == expected


def test_faculty_skips_rows_without_an_employee_button():
    html = table(
        row(["Name", "Desig", "School", ""]),
        row(["No Button", "x", "y", "z"]),
    )

    assert parse_all_faculty_search(html) == []


# --------------------------------------------------------------------------
# Digital assignments
# --------------------------------------------------------------------------

QP_LINK = "<a href=\"javascript:vtopDownload('examinations/qp/ABC')\">Download</a>"
DA_LINK = "<a href=\"javascript:vtopDownload('examinations/da/XYZ')\">Download</a>"


def test_assignment_download_requires_an_actual_submission():
    """
    VTOP renders the submission download link whether or not anything was
    uploaded, so the status has to gate it.
    """
    submitted = table(
        row(["h"]) * 4,
        row(["1", "DA-1", "10", "5", "20-Jan", QP_LINK, "Uploaded on 15-Jan", "-", DA_LINK]),
    )
    not_submitted = table(
        row(["h"]) * 4,
        row(["1", "DA-1", "10", "5", "20-Jan", QP_LINK, "File Not Uploaded", "-", DA_LINK]),
    )

    assert parse_per_course_dassignments(submitted)[0].can_da_download is True
    assert parse_per_course_dassignments(not_submitted)[0].can_da_download is False


def test_assignment_update_code_comes_from_the_pencil_control():
    pencil = '<i class="fa fa-pencil"></i><input name="code" value="MC001">'
    html = table(
        row(["h"]) * 4,
        row(["1", "DA-1", "10", "5", "20-Jan", QP_LINK, "Uploaded", pencil, DA_LINK]),
    )

    record = parse_per_course_dassignments(html)[0]

    assert record.can_update is True
    assert record.mcode == "MC001"


@pytest.mark.parametrize(
    "html,expected",
    [
        ("<span>Uploaded successfully</span>", "Uploaded successfully"),
        (
            "<span>a@vitapstudent.ac.in</span><span></span><span></span>",
            "OTP Required",
        ),
        (
            "<span>a@vitapstudent.ac.in</span><span>x</span>"
            "<span>Invalid OTP. Please try again.</span>",
            "Invalid OTP. Please try again.",
        ),
        ("<span>hdr</span><span>File too large</span>", "File too large"),
        ("<html></html>", "Failed - Unknown Error"),
    ],
)
def test_upload_response_states(html, expected):
    assert parse_upload_assignment_response(html) == expected


# --------------------------------------------------------------------------
# Outing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "html,expected",
    [
        ('<span style="color: red">Dates overlap</span>', "Error: Dates overlap"),
        (
            '<span class="col-md-12" style="color: green">Applied Successfully</span>',
            "Applied Successfully",
        ),
        (
            '<div class="sweet-alert"><h2>Leave Applied Successfully</h2></div>',
            "Leave Applied Successfully",
        ),
        ("<h2>Request Deleted Successfully</h2>", "Request Deleted Successfully"),
    ],
)
def test_outing_response_shapes(html, expected):
    """VTOP answers these endpoints in several different shapes."""
    assert parse_outing_response(html) == expected


def test_outing_response_ignores_the_form_boilerplate():
    """
    The form page carries a standing notice about disciplinary measures that
    must not be mistaken for an error message.
    """
    html = (
        "<html>outingForm Weekend Outing Request "
        '<span class="col-sm-12" style="color:grey">disciplinary measures apply'
        "</span></html>"
    )

    assert "disciplinary" not in parse_outing_response(html)
    assert "may have failed" in parse_outing_response(html)


# --------------------------------------------------------------------------
# Course page
# --------------------------------------------------------------------------


def test_course_label_split_keeps_a_title_containing_a_dash():
    html = (
        '<select id="courseCode">'
        '<option value="">-- Select --</option>'
        '<option value="C1">MAT1001 - Calculus - Part II - TH</option>'
        "</select>"
    )

    course = parse_courses_for_course_page(html).courses[0]

    assert course.course_code == "MAT1001"
    assert course.course_title == "Calculus - Part II"
    assert course.course_type == "TH"


def test_course_slots_read_the_erp_id_from_an_escaped_onclick():
    onclick = (
        "javascript: processViewStudentCourseDetail(&#39;AP2025264&#39;,"
        "&#39;70735&#39;,&#39;AP2025264000442&#39;);"
    )
    html = table(
        row(["h"]),
        row(
            [
                "1",
                "General",
                "CSE2009",
                "Soft Computing",
                "ETH",
                "AP2025264000442",
                "E1/TE1",
                "70735 - S Subhani - SCOPE",
                f'<button onclick="{onclick}">view</button>',
            ]
        ),
    )

    entry = parse_slots_for_course_page(html, "AP2025264").class_entries[0]

    assert entry.erp_id == "70735"
    assert entry.semester_id == "AP2025264"


def test_course_detail_keeps_both_lecture_dates():
    """The date cell holds a raw date and a bracketed display date."""
    material = (
        "<a href=\"javascript:vtopDownload(&#39;downloadPdf/A/B/19&#39;)\">"
        "Reference Material I</a>"
    )
    html = (
        '<table><tr><th>Sl.No.</th><th>Lecture Date</th><th>Lecture Day</th>'
        "<th>Lecture Topic</th><th>Reference Material</th></tr>"
        + row(
            [
                "1",
                "<span>10-12-2025</span><span>[10-Dec-2025]</span>",
                "WED",
                "Fuzzy Logic",
                material,
            ]
        )
        + "</table>"
    )

    lecture = parse_course_detail_page(html).lectures[0]

    assert lecture.date == "10-12-2025"
    assert lecture.formatted_date == "10-Dec-2025"
    assert lecture.reference_materials[0].download_path == "downloadPdf/A/B/19"


# --------------------------------------------------------------------------
# Regressions found by running against live VTOP. The synthetic markup here
# mirrors the real structures those live responses turned out to have.
# --------------------------------------------------------------------------


def test_attendance_detail_skips_the_td_header_row():
    """
    Live VTOP renders the detail header with <td> cells inside the same table,
    so the cell count does not skip it. A real row leads with a numeric serial.
    """
    html = (
        '<table id="StudentAttendanceDetailDataTable">'
        + row(["Sl.No.", "Date", "Slot", "Day / Time", "Status", "Remarks"])
        + row(["1", "08-08-2026", "C1", "SAT / 10:00-10:50", "Present", ""])
        + "</table>"
    )

    records = parse_full_attendance(html)

    assert len(records) == 1
    assert records[0].serial == "1"
    assert records[0].status == "Present"


def test_weekend_outing_reads_the_11_column_layout():
    """
    The live table has 11 columns and no contact or booking-id columns; the
    booking id lives in the download link. The parser used to assume 13
    columns and crashed on cols[12].
    """
    link = (
        '<a data-leave-url="/vtop/hostel/downloadOutingForm/W25256643577" '
        'href="javascript:void(0);">Download</a>'
    )
    html = (
        '<table id="BookingRequests">'
        + row(
            ["S.No", "Registration Number", "Hostel Block", "Room Number",
             "Place Of Visit", "Purpose Of Visit", "Time", "Date", "Action",
             "Status", "Download OutPass"]
        )
        + row(
            ["1", "00XXX0000", "MH-1", "812", "Vijayawada", "Shopping",
             "10:30 AM- 4:30PM", "2026-07-26", "", "Outing Request Accepted", link]
        )
        + "</table>"
    )

    requests = parse_weekend_outing_requests(html).root

    assert len(requests) == 1
    entry = requests[0]
    assert entry.hostel_block == "MH-1"
    assert entry.date == "2026-07-26"
    # Pulled out of the download link, not a column.
    assert entry.booking_id == "W25256643577"
    assert entry.can_download is True


def test_weekend_outing_download_needs_an_accepted_status():
    link = (
        '<a data-leave-url="/vtop/hostel/downloadOutingForm/W1" '
        'href="javascript:void(0);">Download</a>'
    )
    html = (
        '<table id="BookingRequests">'
        + row(["h"] * 11)
        + row(
            ["1", "00XXX0000", "MH-1", "812", "Vijayawada", "Shopping",
             "10:30 AM", "2026-07-26", "", "Waiting for Warden Approval", link]
        )
        + "</table>"
    )

    entry = parse_weekend_outing_requests(html).root[0]

    # The link is present but the request is not accepted yet.
    assert entry.booking_id == "W1"
    assert entry.can_download is False


def test_payment_receipts_locate_columns_by_header():
    """
    Live VTOP inserted invoice and fee columns, pushing amount to index 5 and
    the button to the last cell. Header lookup keeps the parser correct.
    """
    button = (
        "<button onclick=\"javascript:doDuplicateReceipt('78323/27/AMR');\">"
        "View</button>"
    )
    html = (
        "<table>"
        + row(
            ["RECEIPT NUMBER", "DATE", "INVOICE NUMBER", "FEE GROUP",
             "FEE SUBGROUP", "AMOUNT", "CAMPUS CODE", "VIEW"]
        )
        + row(
            ["78323", "08-JUL-2026", "AM2600123276", "HOSTEL FEE",
             "Hostelfee", "199300.0", "AMR", button]
        )
        + "</table>"
    )

    receipts = parse_payment_receipts(html)

    assert len(receipts) == 1
    assert receipts[0].amount == "199300.0"
    assert receipts[0].campus_code == "AMR"
    assert receipts[0].receipt_no == "78323/27/AMR"


def test_payment_receipts_skip_rows_without_a_receipt_button():
    """A totals or empty-state row must be skipped, not raise."""
    html = (
        "<table>"
        + row(["RECEIPT NUMBER", "DATE", "AMOUNT", "CAMPUS CODE", "VIEW"])
        + row(["", "", "Total", "", ""])
        + "</table>"
    )

    assert parse_payment_receipts(html) == []


# --------------------------------------------------------------------------
# Outing form (student details pre-fill). Live VTOP showed the general form
# has no parentContactNumber input, and the weekend form renders nothing
# outside its eligibility window; the parser must tolerate both.
# --------------------------------------------------------------------------

from vitap_vtop_client.exceptions import VtopParsingError as _VtopParsingError
from vitap_vtop_client.parsers.outing_form_parser import parse_outing_form


def test_outing_form_tolerates_missing_optional_inputs():
    """
    The live general form has no parentContactNumber input. The parser must
    leave it empty rather than crash, which used to break general outing
    submission entirely.
    """
    html = (
        '<input id="regNo" value="00XXX0000">'
        '<input id="name" value="Test Student">'
        '<input id="applicationNo" value="123">'
        '<input id="gender" value="MALE">'
        '<input id="hostelBlock" value="MH-1">'
        '<input id="roomNo" value="812">'
        # no parentContactNumber input
    )

    info = parse_outing_form(html)

    assert info.registration_number == "00XXX0000"
    assert info.hostel_block == "MH-1"
    assert info.parent_contact_number == ""


def test_outing_form_errors_clearly_when_it_did_not_render():
    """
    Outside the weekend eligibility window VTOP serves no form fields. The
    parser should raise a clear error, not an opaque NoneType crash.
    """
    with pytest.raises(_VtopParsingError, match="did not render"):
        parse_outing_form("<html><body>Not eligible right now</body></html>")
