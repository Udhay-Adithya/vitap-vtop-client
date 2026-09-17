from datetime import datetime, timezone
import time
import httpx
from typing import Union
from vitap_vtop_client.constants import VIEW_MARKS_URL, HEADERS
from vitap_vtop_client.marks.model.marks_model import MarksModel
from vitap_vtop_client.parsers.marks_parser import parse_marks
from vitap_vtop_client.exceptions.exception import (
    VtopConnectionError,
    VtopMarksError,
    VtopParsingError,
)


async def fetch_marks(
    client: httpx.AsyncClient,
    registration_number: str,
    semSubID: str,
    csrf_token: str,
) -> MarksModel:
    """
    Asynchronously retrieves all available marks for a specified semester.

    Parameters:
        client (httpx.AsyncClient): The async HTTP client used for requests.
        registration_number (str): The student's Registration number.
        semSubID (str): The semester subject ID for which marks are being fetched.
        csrf_token (str): CSRF token for authentication.

    Returns:
        dict: Parsed marks information.

    Raises:
        VtopConnectionError: If HTTP/network errors occur.
        VtopMarksError: If unexpected or parsing errors occur.
    """
    # No page-shell POST first. VTOP answers doStudentMarkView on a cold
    # session with nothing primed, so opening StudentMarkView beforehand was a
    # wasted round trip on every call.
    try:
        data = {
            "authorizedID": registration_number,
            "semesterSubId": semSubID,
            "_csrf": csrf_token,
            "x": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }

        response = await client.post(VIEW_MARKS_URL, data=data, headers=HEADERS)
        response.raise_for_status()

        return parse_marks(response.text)

    except VtopParsingError as e:
        raise e

    except httpx.RequestError as e:
        print(f"Failed to fetch marks: {e}")
        raise VtopConnectionError(
            f"Failed to fetch marks: {e}", original_exception=e, status_code=502
        )
    except Exception as e:
        print(f"Unexpected error while fetching marks: {e}")
        raise VtopMarksError(f"Unexpected error while fetching marks: {e}") from e
