import httpx
import time
from vitap_vtop_client.constants import HEADERS, GRADE_HISTORY_URL
from .model import GradeHistoryModel
from vitap_vtop_client.parsers import grade_history_parser
from vitap_vtop_client.exceptions import VtopConnectionError, VtopGradeHistoryError, VtopParsingError, VtopMenuUnavailableError, VtopSessionError

async def fetch_grade_history(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str
) -> GradeHistoryModel:
    """
    Asynchronously fetches the grade history of a student from the VTOP system.

    Parameters:
        client (httpx.AsyncClient): The async HTTP client used for requests.
        registration_number (str): The student's username.
        csrf_token (str): CSRF token for authentication.

    Returns:
        dict: Parsed grade history data.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopGradeHistoryError: If initialization or data fetch fails.
        VtopParsingError: If parsing fails.
    """
    try:
        data = {
            'verifyMenu': 'true',
            'authorizedID': registration_number,
            '_csrf': csrf_token,
            'nocache': int(round(time.time() * 1000))
        }

        response = await client.post(GRADE_HISTORY_URL, data=data, headers=HEADERS)
        response.raise_for_status()

        return grade_history_parser.parse_grade_history(response.text)

    except (VtopParsingError, VtopMenuUnavailableError, VtopSessionError) as e:
        raise e

    except httpx.RequestError as e:
        print(f"Grade history fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch grade history: {e}",
            original_exception=e,
            status_code=502
        )
    except Exception as e:
        print(f"Unexpected error while fetching grade history: {e}")
        raise VtopGradeHistoryError(f"Unexpected error while fetching grade history: {e}") from e
