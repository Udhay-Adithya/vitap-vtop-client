import httpx
import time
from vitap_vtop_client.constants import PROFILE_URL, HEADERS
from vitap_vtop_client.mentor import fetch_mentor_info
from vitap_vtop_client.grade_history import fetch_grade_history
from vitap_vtop_client.parsers.profile_parser import parse_student_profile
from .model import StudentProfileModel

from vitap_vtop_client.exceptions import (
    VitapVtopClientError,
    VtopConnectionError,
    VtopProfileError,
    VtopParsingError,
)

async def fetch_profile(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str
) -> StudentProfileModel:
    """
    Retrieves and compiles the student profile information from the VTOP Portal.

    Parameters:
        client (httpx.AsyncClient): The async HTTP client.
        registration_number (str): The student's username.
        csrf_token (str): CSRF token for authentication.

    Returns:
        StudentProfileModel: The student's profile information.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopProfileError: If initialization or data fetch fails.
        VtopParsingError: If parsing fails.
    """
    try:
        data = {
            'verifyMenu': 'true',
            'authorizedID': registration_number,
            '_csrf': csrf_token,
            'nocache': int(round(time.time() * 1000))
        }

        # Three requests, and any of them can be the one that fails. Say which,
        # rather than reporting whichever error happened to surface -- a
        # timeout on the profile page itself used to come back blaming grade
        # history, because that is the next call in the sequence.
        response = await client.post(PROFILE_URL, data=data, headers=HEADERS)
        response.raise_for_status()
        profile = parse_student_profile(response.text)

        try:
            profile.grade_history = await fetch_grade_history(
                client, registration_number, csrf_token
            )
        except VitapVtopClientError as e:
            raise VtopProfileError(
                f"Fetched the profile, but its grade history failed: {e}"
            ) from e

        try:
            profile.mentor_details = await fetch_mentor_info(
                client, registration_number, csrf_token
            )
        except VitapVtopClientError as e:
            raise VtopProfileError(
                f"Fetched the profile, but its mentor details failed: {e}"
            ) from e

        return profile

    except (VtopParsingError, VtopProfileError, VtopConnectionError) as e:
        # Already described; wrapping again would only bury the cause.
        raise e

    except httpx.RequestError as e:
        print(f"Student profile fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch student profile: {e}",
            original_exception=e,
            status_code=502
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching student profile: {e}")
        raise VtopProfileError(f"Unexpected error while fetching student profile: {e}") from e
