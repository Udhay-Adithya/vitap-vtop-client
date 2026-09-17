"""
Tests for the student profile parser.

VTOP renders a two-word label across two lines, so the cell text is
"APPLICATION\r\n\t\t\t\tNUMBER" rather than "APPLICATION NUMBER". The parser
compared with str.strip(), which only removes whitespace at the ends, so every
multi-word label silently failed to match. The model then refused to construct,
because `Optional[str]` without a default is required in pydantic v2 -- so a
label change turned into get_profile() failing outright.
"""

import pytest

from vitap_vtop_client.exceptions import VtopParsingError
from vitap_vtop_client.parsers.profile_parser import parse_student_profile
from vitap_vtop_client.profile.model import StudentProfileModel

# The labels exactly as VTOP renders them, tabs and all.
SPLIT_LABEL_PAGE = """
<table>
  <tr><td>APPLICATION\r\n\t\t\t\t\t\t\t\tNUMBER</td><td>2023046196</td></tr>
  <tr><td>STUDENT\r\n\t\t\t\t\t\t\t\tNAME</td><td>A Student</td></tr>
  <tr><td>DATE OF\r\n\t\t\t\t\t\t\t\tBIRTH</td><td>01-JAN-2005</td></tr>
  <tr><td>GENDER</td><td>Male</td></tr>
  <tr><td>BLOOD\r\n\t\t\t\t\t\t\t\tGROUP</td><td>O+</td></tr>
  <tr><td>EMAIL</td><td>student@example.com</td></tr>
</table>
"""


def test_labels_split_across_lines_are_matched():
    """This is the exact shape that broke get_profile against live VTOP."""
    profile = parse_student_profile(SPLIT_LABEL_PAGE)
    assert profile.application_number == "2023046196"
    assert profile.student_name == "A Student"
    assert profile.dob == "01-JAN-2005"
    assert profile.gender == "Male"
    assert profile.blood_group == "O+"
    assert profile.email == "student@example.com"


def test_a_page_missing_fields_degrades_instead_of_raising():
    """
    A missing blood group is not a reason to fail the whole call. Before the
    model carried defaults, one absent label raised a validation error.
    """
    profile = parse_student_profile(
        "<table><tr><td>GENDER</td><td>Male</td></tr></table>"
    )
    assert profile.gender == "Male"
    assert profile.student_name is None
    assert profile.blood_group is None


def test_the_first_email_wins():
    """
    The live page carries four cells labelled exactly EMAIL, one per contact
    block. The first follows the student's own personal details; the rest
    follow other contacts. The loop used to run on and keep whichever came
    last, which was never the student's.

    Note none of them is a VIT-issued address -- the profile page does not
    render one, so `email` is whatever personal address is on file.
    """
    html = """
    <table>
      <tr><td>EMAIL</td><td>student@example.com</td></tr>
      <tr><td>EMAIL</td><td>other-contact@example.com</td></tr>
      <tr><td>FACULTY EMAIL</td><td>faculty@vitap.ac.in</td></tr>
    </table>
    """
    assert parse_student_profile(html).email == "student@example.com"


def test_a_faculty_email_is_not_mistaken_for_the_student_one():
    html = "<table><tr><td>FACULTY EMAIL</td><td>faculty@vitap.ac.in</td></tr></table>"
    assert parse_student_profile(html).email is None


def test_a_label_in_the_last_cell_does_not_read_past_the_end():
    profile = parse_student_profile("<table><tr><td>EMAIL</td></tr></table>")
    assert profile.email is None


def test_an_empty_page_still_returns_a_model():
    assert isinstance(parse_student_profile("<html></html>"), StudentProfileModel)


def test_the_error_names_the_profile_rather_than_biometrics():
    """The except block used to say "Failed to parse biometric data"."""
    with pytest.raises(VtopParsingError) as excinfo:
        parse_student_profile(None)          # type: ignore[arg-type]
    assert "student profile" in str(excinfo.value)
    assert "biometric" not in str(excinfo.value)
