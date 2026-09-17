import time
from datetime import datetime, timezone

import httpx

from vitap_vtop_client.constants import (
    DO_GRADE_VIEW_URL,
    GRADE_VIEW_DETAIL_URL,
    HEADERS,
)
from vitap_vtop_client.exceptions.exception import (
    VitapVtopClientError,
    VtopConnectionError,
    VtopParsingError,
)
from vitap_vtop_client.grade_view.model.grade_view_model import (
    GradeViewCourse,
    GradeViewDetail,
)
from vitap_vtop_client.parsers import grade_view_parser


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


async def fetch_grade_view(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
) -> list[GradeViewCourse]:
    """
    Fetches the graded courses for a semester.

    Grades are visible for a semester only once it has ended; the current
    semester returns nothing until results are published. Each returned course
    carries a course_id for looking up its detailed marks.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        semSubID (str): The semester subject ID.

    Returns:
        list[GradeViewCourse]: One entry per graded course.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    # The page shell is not required after all: VTOP answers doStudentGradeView
    # on a cold session with nothing primed, so opening StudentGradeView first
    # was a wasted round trip on every call.
    try:
        # doStudentGradeView is posted as multipart, matching the page's form.
        files = {
            "authorizedID": (None, username),
            "semesterSubId": (None, semSubID),
            "_csrf": (None, csrf_token),
        }
        response = await client.post(
            DO_GRADE_VIEW_URL, files=files, headers=HEADERS
        )
        response.raise_for_status()

        return grade_view_parser.parse_grade_view(response.text)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        print(f"Grade view fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch grade view: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching grade view: {e}")
        raise VitapVtopClientError(
            f"Failed to fetch grade view for semester {semSubID}: {e}"
        ) from e


async def fetch_grade_view_detail(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
    course_id: str,
) -> GradeViewDetail:
    """
    Fetches the mark breakdown and class statistics for one course.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        semSubID (str): The semester subject ID.
        course_id (str): The course id, from GradeViewCourse.course_id.

    Returns:
        GradeViewDetail: The per-component marks, total and class statistics.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    try:
        body = (
            f"authorizedID={username}"
            f"&x={_timestamp()}"
            f"&semesterSubId={semSubID}"
            f"&courseId={course_id}"
            f"&_csrf={csrf_token}"
        )
        response = await client.post(
            GRADE_VIEW_DETAIL_URL,
            content=body,
            headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        return grade_view_parser.parse_grade_view_detail(response.text)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        print(f"Grade view detail fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch grade view detail: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching grade view detail: {e}")
        raise VitapVtopClientError(
            f"Failed to fetch grade view detail for course {course_id}: {e}"
        ) from e
