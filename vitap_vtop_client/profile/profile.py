import asyncio
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
    VtopMenuUnavailableError,
    VtopSessionError,
)

async def fetch_profile(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str,
    include_grade_history: bool = True,
    include_mentor: bool = True,
) -> StudentProfileModel:
    """
    Retrieves and compiles the student profile information from the VTOP Portal.

    The profile page itself does not carry the grade history or the mentor, so
    those are two further requests. They do not depend on each other or on the
    profile response, so they run concurrently.

    Grade history is the largest response the client fetches anywhere, around
    137KB, so a caller that only wants the name and photo should turn it off
    rather than pay for it on every call.

    Parameters:
        client (httpx.AsyncClient): The async HTTP client.
        registration_number (str): The student's username.
        csrf_token (str): CSRF token for authentication.
        include_grade_history (bool): Fetch the nested grade history. Defaults
            to True. Costs one extra request of roughly 137KB.
        include_mentor (bool): Fetch the nested mentor details. Defaults to
            True. Costs one extra request.

    Returns:
        StudentProfileModel: The student's profile information. Fields that
            were not requested are left at their model defaults.

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

        # Up to three requests, and any of them can be the one that fails. Say
        # which, rather than reporting whichever error happened to surface -- a
        # timeout on the profile page itself used to come back blaming grade
        # history, because that was the next call in the sequence.
        response = await client.post(PROFILE_URL, data=data, headers=HEADERS)
        response.raise_for_status()
        profile = parse_student_profile(response.text)

        # Neither nested fetch depends on the other or on the profile response,
        # so they go out together rather than one after the other.
        nested = {}
        if include_grade_history:
            nested["grade history"] = fetch_grade_history(
                client, registration_number, csrf_token
            )
        if include_mentor:
            nested["mentor details"] = fetch_mentor_info(
                client, registration_number, csrf_token
            )

        if nested:
            labels = list(nested)
            results = await asyncio.gather(*nested.values(), return_exceptions=True)
            for label, result in zip(labels, results):
                if isinstance(result, BaseException):
                    raise VtopProfileError(
                        f"Fetched the profile, but its {label} failed: {result}"
                    ) from result
                if label == "grade history":
                    profile.grade_history = result
                else:
                    profile.mentor_details = result

        return profile

    except (
        VtopParsingError,
        VtopMenuUnavailableError,
        VtopSessionError,
        VtopProfileError,
        VtopConnectionError,
    ) as e:
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
