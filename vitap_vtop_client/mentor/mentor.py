import httpx
import time
from vitap_vtop_client.constants import HEADERS, MENTOR_DETAILS_URL
from .model import MentorModel
from vitap_vtop_client.parsers.mentor_parser import parse_mentor_details
from vitap_vtop_client.exceptions import VtopConnectionError, VtopMentorError, VtopParsingError, VtopMenuUnavailableError

async def fetch_mentor_info(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str
) -> MentorModel:
    """
    Retrieves the mentor details for a specified user from the VTOP system asynchronously.

    Parameters:
        client (httpx.AsyncClient): The async HTTP client used for requests.
        registration_number (str): The student's username.
        csrf_token (str): CSRF token for authentication.

    Returns:
        dict: Parsed mentor details or an error message.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopMentorError: If initialization or data fetch fails.
        VtopParsingError: If parsing fails.
    """
    try:
        data = {
            'verifyMenu': 'true',
            'authorizedID': registration_number,
            '_csrf': csrf_token,
            'nocache': int(round(time.time() * 1000))
        }

        response = await client.post(MENTOR_DETAILS_URL, data=data, headers=HEADERS)
        response.raise_for_status()

        return parse_mentor_details(response.text)

    except (VtopParsingError, VtopMenuUnavailableError) as e:
        raise e

    except httpx.RequestError as e:
        print(f"Mentor details fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch mentor details: {e}",
            original_exception=e,
            status_code=502
        )
    except Exception as e:
        print(f"Unexpected error while fetching mentor details: {e}")
        raise VtopMentorError(f"Unexpected error while fetching mentor details: {e}") from e
