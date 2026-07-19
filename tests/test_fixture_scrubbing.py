"""
Tests for the fixture recorder's scrubber.

Fixtures get committed to a public repo, so anything identifying that survives
scrubbing is a leak. These tests are the guard on that.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.record_fixtures import _scrub  # noqa: E402

REAL_USER = "22BCE7777"


def test_registration_number_is_removed_in_any_case():
    html = f"<p>{REAL_USER}</p><p>{REAL_USER.lower()}</p>"

    scrubbed = _scrub(html, REAL_USER)

    assert REAL_USER not in scrubbed
    assert REAL_USER.lower() not in scrubbed


def test_other_students_registration_numbers_are_removed():
    """A roster or mentor page can carry someone else's number."""
    html = "<td>21BCE1234</td><td>23MIS5678</td>"

    scrubbed = _scrub(html, REAL_USER)

    assert "21BCE1234" not in scrubbed
    assert "23MIS5678" not in scrubbed


def test_session_tokens_are_removed():
    html = (
        '<input name="_csrf" value="9f8e7d6c-1234-5678-9abc-def012345678">'
        "<script>JSESSIONID=A1B2C3D4E5F6</script>"
    )

    scrubbed = _scrub(html, REAL_USER)

    assert "9f8e7d6c" not in scrubbed
    assert "A1B2C3D4E5F6" not in scrubbed


def test_embedded_photographs_are_removed():
    html = '<img src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBD">'

    scrubbed = _scrub(html, REAL_USER)

    assert "/9j/4AAQSkZJRgABAQEASABIAAD" not in scrubbed
    # The attribute stays structurally valid so parsers still see an image.
    assert "data:image/jpeg;base64,REDACTED" in scrubbed


def test_contact_details_are_removed():
    html = (
        "<td>udhay.22bce7777@vitapstudent.ac.in</td>"
        "<td>prof.rao@vitap.ac.in</td>"
        "<td>9876543210</td>"
    )

    scrubbed = _scrub(html, REAL_USER)

    assert "udhay.22bce7777" not in scrubbed
    assert "prof.rao" not in scrubbed
    assert "9876543210" not in scrubbed


def test_application_number_is_removed():
    html = '<a href="/vtop/receipt?applno=2022ABCD1234">receipt</a>'

    scrubbed = _scrub(html, REAL_USER)

    assert "2022ABCD1234" not in scrubbed


def test_structure_is_preserved_so_parsers_still_work():
    """Scrubbing must not damage the markup the fixtures exist to exercise."""
    html = (
        '<table id="AttendanceDetailDataTable"><tr><td>1</td>'
        f"<td>{REAL_USER}</td><td>MAT1001 - Calculus - ETH</td></tr></table>"
    )

    scrubbed = _scrub(html, REAL_USER)

    assert 'id="AttendanceDetailDataTable"' in scrubbed
    assert "MAT1001 - Calculus - ETH" in scrubbed
    assert scrubbed.count("<td>") == html.count("<td>")
