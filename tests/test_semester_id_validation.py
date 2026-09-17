"""
Tests for semester id validation.

VTOP does not reject an unknown semester id. It answers with a normal, empty
table, so a wrong semester is indistinguishable from a semester the student
genuinely has no data for. We cannot fix that from here -- empty is a
legitimate result for unpublished marks, a quiet biometric day, and the current
semester's grades -- so the check is deliberately shallow: it catches a typo,
not a stale id.
"""

import pytest

from vitap_vtop_client import VtopClient
from vitap_vtop_client.exceptions import VtopSessionError
from vitap_vtop_client.utils import SEMESTER_ID_PATTERN, validate_semester_id

# Every id VTOP served on 2026-09-17, taken from a live get_semesters().
REAL_IDS = [
    "AP2026272", "AP2025264", "AP2025262", "AP2024258",
    "AP2024254", "AP2024252", "AP2023247", "AP2023243",
]


@pytest.mark.parametrize("sem_sub_id", REAL_IDS)
def test_every_id_vtop_actually_served_is_accepted(sem_sub_id):
    validate_semester_id(sem_sub_id)
    assert SEMESTER_ID_PATTERN.fullmatch(sem_sub_id)


@pytest.mark.parametrize(
    "bad",
    [
        "",                 # empty
        "NOPE9999",         # the id I probed VTOP with; it returned an empty table
        "AP202627",         # six digits
        "AP20262722",       # eight digits
        "ap2026272",        # lower case
        "AP2026272 ",       # trailing space, the kind of thing a config file adds
        " AP2026272",
        "VL2026272",        # another campus's prefix
        "AP20262A2",        # letter among the digits
        "Fall Semester 2026-27",  # the name rather than the id
    ],
)
def test_a_malformed_id_is_refused(bad):
    with pytest.raises(VtopSessionError):
        validate_semester_id(bad)


def test_the_error_says_where_to_get_a_real_id():
    """
    The caller's actual fix is get_semesters(), so the message has to name it.
    """
    with pytest.raises(VtopSessionError) as excinfo:
        validate_semester_id("NOPE9999")
    message = str(excinfo.value)
    assert "get_semesters()" in message
    assert "AP2026272" in message          # shows the shape
    assert "empty result" in message       # explains why a wrong id is dangerous
    assert excinfo.value.status_code == 400


def test_a_well_formed_but_unknown_id_is_deliberately_allowed():
    """
    AP9999999 is not a real semester, but nothing offline can know that, and
    guessing would reject ids from a term we have not seen.
    """
    validate_semester_id("AP9999999")


async def test_the_check_runs_before_any_network_call():
    """
    A client that has never logged in should still reject a bad id, rather than
    attempting a captcha-gated login first and failing later.
    """
    client = VtopClient("00XXX0000", "pw")
    with pytest.raises(VtopSessionError):
        await client.get_attendance(sem_sub_id="not-an-id")
    assert not client.is_authenticated


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.get_attendance(sem_sub_id="bad"),
        lambda c: c.get_timetable(sem_sub_id="bad"),
        lambda c: c.get_marks(sem_sub_id="bad"),
        lambda c: c.get_exam_schedule(sem_sub_id="bad"),
        lambda c: c.get_grade_view(sem_sub_id="bad"),
        lambda c: c.get_capstone_attendance(sem_sub_id="bad"),
        lambda c: c.get_digital_assignments(sem_sub_id="bad"),
        lambda c: c.get_course_page_courses(sem_sub_id="bad"),
    ],
)
async def test_every_semester_scoped_method_validates(call):
    client = VtopClient("00XXX0000", "pw")
    with pytest.raises(VtopSessionError):
        await call(client)
