import time

import httpx

from vitap_vtop_client.constants import HEADERS, TIME_TABLE_URL
from vitap_vtop_client.exceptions.exception import (
    VtopConnectionError,
    VtopParsingError,
    VitapVtopClientError,
)
from vitap_vtop_client.parsers import semester_parser
from vitap_vtop_client.semester.model.semester_model import SemesterData


async def fetch_semesters(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
) -> SemesterData:
    """
    Retrieves the semesters available to the authenticated student.

    The ids returned here are what every semester scoped call expects, so this
    should be preferred over hardcoding semester ids.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.

    Returns:
        SemesterData: The available semesters and the time they were read.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
        VitapVtopClientError: If the fetch fails for any other reason.
    """
    try:
        data = {
            "verifyMenu": "true",
            "authorizedID": username,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }
        response = await client.post(TIME_TABLE_URL, data=data, headers=HEADERS)
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
