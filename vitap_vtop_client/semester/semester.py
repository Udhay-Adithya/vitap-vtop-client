import time

import httpx

from vitap_vtop_client.constants import (
    EXAM_SCHEDULE_URL,
    HEADERS,
    MARKS_URL,
    TIME_TABLE_URL,
)
from vitap_vtop_client.exceptions.exception import (
    VtopConnectionError,
    VtopParsingError,
    VitapVtopClientError,
)
from vitap_vtop_client.parsers import semester_parser
from vitap_vtop_client.semester.model.semester_model import SemesterData

# Pages that carry the `semesterSubId` dropdown, in the order they are tried.
#
# They are not equivalent:
#   - The timetable page lists only the semesters the student actually has a
#     timetable for. That is the nicest list to show, but it is empty for
#     freshers (and others) before their timetable is set up, which surfaced as
#     "No semesters available" right after login.
#   - The marks and exam schedule pages render the full institutional semester
#     list server-side, so their dropdown is populated for anyone who can log
#     in, regardless of their own records.
#
# Try the timetable first for the better list, then fall back to the fuller
# pages so a login never dead-ends on an empty semester list.
SEMESTER_PAGES = (TIME_TABLE_URL, MARKS_URL, EXAM_SCHEDULE_URL)


async def fetch_semesters(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
) -> SemesterData:
    """
    Retrieves the semesters available to the authenticated student.

    The ids returned here are what every semester scoped call expects, so this
    should be preferred over hardcoding semester ids.

    Several VTOP pages expose the semester dropdown but they do not all list the
    same semesters, so this walks [`SEMESTER_PAGES`] and returns the first
    non-empty result.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.

    Returns:
        SemesterData: The available semesters and the time they were read. The
            list is empty only when every source was empty.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
        VitapVtopClientError: If the fetch fails for any other reason.
    """
    last = SemesterData(semesters=[], update_time=int(time.time()))

    for page_url in SEMESTER_PAGES:
        data = await _fetch_semesters_from(client, username, csrf_token, page_url)
        if data.semesters:
            return data
        last = data

    # Every source was empty. Return the empty result so the caller can show its
    # own "try again later" message rather than raising.
    return last


async def _fetch_semesters_from(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    page_url: str,
) -> SemesterData:
    """Loads one VTOP page and parses its `semesterSubId` dropdown."""
    try:
        data = {
            "verifyMenu": "true",
            "authorizedID": username,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }
        response = await client.post(page_url, data=data, headers=HEADERS)
        response.raise_for_status()

        return semester_parser.parse_semester_id_from_timetable(response.text)

    except VtopParsingError:
        raise

    except httpx.RequestError as e:
        print(f"Semester fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch semesters: {e}", original_exception=e, status_code=502
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching semesters: {e}")
        raise VitapVtopClientError(f"Failed to fetch semesters: {e}") from e
