from datetime import datetime, timezone

import httpx

from vitap_vtop_client.constants import (
    FACULTY_DETAIL_URL,
    FACULTY_SEARCH_URL,
    HEADERS,
)
from vitap_vtop_client.exceptions.exception import (
    VitapVtopClientError,
    VtopConnectionError,
    VtopParsingError,
)
from vitap_vtop_client.faculty.model.faculty_model import (
    FacultyDetailsModel,
    FacultyModel,
)
from vitap_vtop_client.parsers import faculty_parser


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


async def fetch_faculty_search(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    search_term: str,
) -> FacultyModel:
    """
    Searches for a faculty member and returns the first match.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        search_term (str): A faculty name or employee id to search for.

    Returns:
        FacultyModel: The first match, or an empty model when there are none.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    html = await _post_faculty_search(client, username, csrf_token, search_term)
    return faculty_parser.parse_faculty_search(html)


async def fetch_all_faculty(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
) -> list[FacultyModel]:
    """
    Fetches the full faculty directory.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.

    Returns:
        list[FacultyModel]: Every faculty member VTOP returns.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    html = await _post_faculty_search(client, username, csrf_token, "")
    return faculty_parser.parse_all_faculty_search(html)


async def _post_faculty_search(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    search_term: str,
) -> str:
    """Posts to the faculty search endpoint. An empty term returns everyone."""
    try:
        data = {
            "_csrf": csrf_token,
            "empId": search_term,
            "authorizedID": username,
            "x": _timestamp(),
        }
        response = await client.post(FACULTY_SEARCH_URL, data=data, headers=HEADERS)
        response.raise_for_status()
        return response.text

    except httpx.RequestError as e:
        print(f"Faculty search failed: {e}")
        raise VtopConnectionError(
            f"Failed to search faculty: {e}", original_exception=e, status_code=502
        )
    except Exception as e:
        print(f"An unexpected error occurred during faculty search: {e}")
        raise VitapVtopClientError(f"Failed to search faculty: {e}") from e


async def fetch_faculty_details(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    emp_id: str,
) -> FacultyDetailsModel:
    """
    Fetches a faculty member's profile and office hours.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        emp_id (str): The employee id, from FacultyModel.emp_id.

    Returns:
        FacultyDetailsModel: The parsed profile.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    try:
        data = {
            "_csrf": csrf_token,
            "empId": emp_id,
            "authorizedID": username,
            "x": _timestamp(),
        }
        response = await client.post(FACULTY_DETAIL_URL, data=data, headers=HEADERS)
        response.raise_for_status()

        return faculty_parser.parse_faculty_data(response.text)

    except VtopParsingError:
        raise

    except httpx.RequestError as e:
        print(f"Faculty detail fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch faculty details: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching faculty details: {e}")
        raise VitapVtopClientError(
            f"Failed to fetch faculty details for {emp_id}: {e}"
        ) from e
