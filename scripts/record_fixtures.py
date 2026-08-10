"""
Captures real VTOP responses and writes them to tests/fixtures/ as test data.

This is the only part of the test setup that sees a password, and it reads it
from the environment rather than taking it as an argument, so credentials never
land in your shell history.

    cp .env.example .env    # fill in VTOP_USERNAME and VTOP_PASSWORD
    python scripts/record_fixtures.py

VTOP will usually ask for a login OTP; the script prompts for it.

Everything captured is scrubbed of personal data before it hits disk. The
fixtures are meant to be committed, so read what lands in tests/fixtures/
before pushing.

Re-run this whenever the live contract tests start failing: that failure means
VTOP changed shape, and the fixtures need to catch up.
"""

import asyncio
import os
import re
import sys
from pathlib import Path

# Allow running straight from a checkout without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from vitap_vtop_client import VtopClient  # noqa: E402
from vitap_vtop_client.exceptions import (  # noqa: E402
    VtopLoginOtpRequiredError,
)

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# Placeholders substituted in for real values. Kept structurally realistic so
# the parsers still exercise the same code paths.
FAKE_REG_NO = "00XXX0000"
FAKE_NAME = "Test Student"
FAKE_EMAIL = "test.student@vitapstudent.ac.in"
FAKE_PHONE = "9000000000"


def _scrub(html: str, real_username: str, real_name: str = "") -> str:
    """
    Strips personal data out of a captured response.

    Fixtures get committed, so anything identifying has to go: the student's
    registration number, name, contact details, photo, and any session token
    that could be replayed.
    """
    # The registration number, in whatever case VTOP echoed it back.
    for variant in {real_username, real_username.upper(), real_username.lower()}:
        html = html.replace(variant, FAKE_REG_NO)

    # The student's full name, which VTOP embeds on several pages. Each
    # whitespace collapsed word is removed so spacing quirks do not let a part
    # of the name survive.
    if real_name:
        for word in real_name.split():
            if len(word) >= 2:
                html = re.sub(rf"\b{re.escape(word)}\b", FAKE_NAME, html, flags=re.IGNORECASE)

    # Any other registration number shaped token (e.g. a mentor's or a
    # classmate's on a shared roster page).
    html = re.sub(r"\b\d{2}[A-Z]{3}\d{4,5}\b", FAKE_REG_NO, html)

    # Session tokens. Replayable, and useless as test data.
    html = re.sub(
        r'(name="_csrf"[^>]*value=")[^"]*"', r"\g<1>00000000-0000-0000-0000-000000000000\"", html
    )
    html = re.sub(r"(JSESSIONID=)[^;\"'\s]+", r"\g<1>REDACTED", html)

    # Embedded photographs, which are both identifying and enormous.
    html = re.sub(
        r"data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=\s]+",
        "data:image/jpeg;base64,REDACTED",
        html,
    )

    # Contact details.
    html = re.sub(r"[\w.+-]+@vitapstudent\.ac\.in", FAKE_EMAIL, html)
    html = re.sub(r"[\w.+-]+@vitap\.ac\.in", "faculty@vitap.ac.in", html)
    html = re.sub(r"\b[6-9]\d{9}\b", FAKE_PHONE, html)

    # Application number, which appears on the profile and payment receipts.
    html = re.sub(
        r"(applno=)[A-Za-z0-9]+", r"\g<1>APP000000", html, flags=re.IGNORECASE
    )

    return html


def _write(name: str, html: str, real_username: str, real_name: str) -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_DIR / name
    path.write_text(_scrub(html, real_username, real_name), encoding="utf-8")
    print(f"  wrote {path.relative_to(FIXTURE_DIR.parent.parent)} ({len(html):,} bytes raw)")


async def _capture(label: str, name: str, coro, real_username: str, real_name: str) -> None:
    """Runs one capture, reporting rather than aborting when an endpoint fails."""
    print(f"- {label}")
    try:
        html = await coro
        _write(name, html, real_username, real_name)
    except Exception as e:
        print(f"  SKIPPED: {type(e).__name__}: {e}")


async def main() -> None:
    username = os.environ.get("VTOP_USERNAME")
    password = os.environ.get("VTOP_PASSWORD")
    if not username or not password:
        sys.exit(
            "VTOP_USERNAME and VTOP_PASSWORD must be set.\n"
            "Copy .env.example to .env and fill it in, or export them."
        )

    client = VtopClient(username, password)

    print(f"Logging in as {username[:5]}****")
    try:
        await client.login()
        print("Logged in without an OTP.")
    except VtopLoginOtpRequiredError:
        otp = input("VTOP sent an OTP. Enter it: ").strip()
        await client.verify_login_otp(otp)
        print("OTP accepted.")

    student = await client._ensure_logged_in()
    reg_no = student.registration_number
    csrf = student.post_login_csrf_token
    http = client._client

    # The student's name is embedded on several pages, so it has to be scrubbed
    # too. Fetch it up front and hand it to every capture.
    real_name = ""
    try:
        profile = await client.get_profile()
        real_name = profile.student_name or ""
        if real_name:
            print(f"Will scrub the name: {real_name[:3]}****")
    except Exception as e:
        print(f"WARNING: could not read the profile name to scrub it ({e}).")
        print("Review the fixtures carefully before committing.")

    # Raw page captures, taken through the same requests the library makes so
    # the fixture matches what the parsers will actually receive.
    from vitap_vtop_client.constants import (
        ATTENDANCE_URL,
        BIOMETRIC_LOG_URL,
        GRADE_HISTORY_URL,
        HEADERS,
        TIME_TABLE_URL,
    )

    print("\nCapturing pages:")

    async def post(url: str, data: dict) -> str:
        response = await http.post(url, data={**data, "_csrf": csrf}, headers=HEADERS)
        response.raise_for_status()
        return response.text

    # The timetable page carries the semester dropdown, so it doubles as the
    # semester fixture.
    await _capture(
        "semester dropdown / timetable page",
        "semesters.html",
        post(TIME_TABLE_URL, {"verifyMenu": "true", "authorizedID": reg_no}),
        username,
        real_name,
    )

    await _capture(
        "attendance page",
        "attendance_page.html",
        post(ATTENDANCE_URL, {"verifyMenu": "true", "authorizedID": reg_no}),
        username,
        real_name,
    )

    await _capture(
        "grade history",
        "grade_history.html",
        post(GRADE_HISTORY_URL, {"verifyMenu": "true", "authorizedID": reg_no}),
        username,
        real_name,
    )

    await _capture(
        "biometric page",
        "biometric_page.html",
        post(BIOMETRIC_LOG_URL, {"verifyMenu": "true", "authorizedID": reg_no}),
        username,
        real_name,
    )

    # Semester scoped captures need a real semester id.
    semesters = await client.get_semesters()
    if semesters.semesters:
        sem_id = semesters.semesters[0].id
        print(f"\nUsing semester {sem_id} for semester scoped captures:")

        from vitap_vtop_client.constants import (
            GET_TIME_TABLE_URL,
            VIEW_ATTENDANCE_URL,
            VIEW_MARKS_URL,
        )

        for label, name, url in (
            ("attendance data", "attendance.html", VIEW_ATTENDANCE_URL),
            ("timetable data", "timetable.html", GET_TIME_TABLE_URL),
            ("marks data", "marks.html", VIEW_MARKS_URL),
        ):
            await _capture(
                label,
                name,
                post(url, {"semesterSubId": sem_id, "authorizedID": reg_no}),
                username,
                real_name,
            )
    else:
        print("\nNo semesters returned; skipping semester scoped captures.")

    await client.close()

    print(
        "\nDone. Review tests/fixtures/ for anything identifying before "
        "committing:\n  git diff --stat tests/fixtures/"
    )


if __name__ == "__main__":
    asyncio.run(main())
