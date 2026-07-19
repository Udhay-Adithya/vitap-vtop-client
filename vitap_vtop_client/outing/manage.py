from datetime import datetime, timezone

import httpx

from vitap_vtop_client.constants import (
    DELETE_GENERAL_OUTING_URL,
    DELETE_WEEKEND_OUTING_FORM,
    DOWNLOAD_LEAVE_PASS_URL,
    DOWNLOAD_OUTING_FORM_URL,
    HEADERS,
)
from vitap_vtop_client.exceptions.exception import (
    VtopConnectionError,
    VtopGeneralOutingError,
    VtopWeekendOutingError,
)
from vitap_vtop_client.parsers.outing_response_parser import parse_outing_response

# VTOP treats the delete endpoints as AJAX and will not answer without this.
_AJAX_HEADERS = {
    **HEADERS,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


async def delete_general_outing_request(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str,
    leave_id: str,
) -> str:
    """
    Deletes a general outing request.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        registration_number (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        leave_id (str): The leave id, from GeneralOutingRequest.leave_id.

    Returns:
        str: VTOP's response message.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopGeneralOutingError: If the deletion fails for any other reason.
    """
    try:
        data = {
            "_csrf": csrf_token,
            "LeaveId": leave_id,
            "authorizedID": registration_number,
            "x": _timestamp(),
        }
        response = await client.post(
            DELETE_GENERAL_OUTING_URL, data=data, headers=_AJAX_HEADERS
        )
        response.raise_for_status()

        return parse_outing_response(response.text)

    except httpx.RequestError as e:
        print(f"General outing deletion failed: {e}")
        raise VtopConnectionError(
            f"Failed to delete general outing request: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while deleting general outing: {e}")
        raise VtopGeneralOutingError(
            f"Failed to delete general outing request {leave_id}: {e}"
        ) from e


async def delete_weekend_outing_request(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str,
    booking_id: str,
) -> str:
    """
    Deletes a weekend outing request.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        registration_number (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        booking_id (str): The booking id, from WeekendOutingRequest.booking_id.

    Returns:
        str: VTOP's response message.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopWeekendOutingError: If the deletion fails for any other reason.
    """
    try:
        data = {
            "_csrf": csrf_token,
            "BookingId": booking_id,
            "authorizedID": registration_number,
            "x": _timestamp(),
        }
        response = await client.post(
            DELETE_WEEKEND_OUTING_FORM, data=data, headers=_AJAX_HEADERS
        )
        response.raise_for_status()

        return parse_outing_response(response.text)

    except httpx.RequestError as e:
        print(f"Weekend outing deletion failed: {e}")
        raise VtopConnectionError(
            f"Failed to delete weekend outing request: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while deleting weekend outing: {e}")
        raise VtopWeekendOutingError(
            f"Failed to delete weekend outing request {booking_id}: {e}"
        ) from e


async def _download_outing_pdf(
    client: httpx.AsyncClient,
    base_url: str,
    registration_number: str,
    csrf_token: str,
    identifier: str,
) -> bytes:
    params = {
        "authorizedID": registration_number,
        "_csrf": csrf_token,
        "x": _timestamp(),
    }
    response = await client.get(
        f"{base_url}/{identifier}", params=params, headers=HEADERS
    )
    response.raise_for_status()
    return response.content


async def fetch_general_outing_pdf(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str,
    leave_id: str,
) -> bytes:
    """
    Downloads the leave pass PDF for a general outing request.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        registration_number (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        leave_id (str): The leave id, from GeneralOutingRequest.leave_id.
            Check can_download first.

    Returns:
        bytes: The raw PDF contents.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopGeneralOutingError: If no leave id was supplied or download fails.
    """
    if not leave_id:
        raise VtopGeneralOutingError(
            "No leave id was supplied. Check can_download before requesting "
            "the leave pass.",
            status_code=400,
        )

    try:
        return await _download_outing_pdf(
            client, DOWNLOAD_LEAVE_PASS_URL, registration_number, csrf_token, leave_id
        )

    except httpx.RequestError as e:
        print(f"Leave pass download failed: {e}")
        raise VtopConnectionError(
            f"Failed to download leave pass: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while downloading leave pass: {e}")
        raise VtopGeneralOutingError(
            f"Failed to download leave pass for {leave_id}: {e}"
        ) from e


async def fetch_weekend_outing_pdf(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str,
    booking_id: str,
) -> bytes:
    """
    Downloads the outing form PDF for a weekend outing request.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        registration_number (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        booking_id (str): The booking id, from WeekendOutingRequest.booking_id.
            Check can_download first.

    Returns:
        bytes: The raw PDF contents.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopWeekendOutingError: If no booking id was supplied or download fails.
    """
    if not booking_id:
        raise VtopWeekendOutingError(
            "No booking id was supplied. Check can_download before requesting "
            "the outing form.",
            status_code=400,
        )

    try:
        return await _download_outing_pdf(
            client,
            DOWNLOAD_OUTING_FORM_URL,
            registration_number,
            csrf_token,
            booking_id,
        )

    except httpx.RequestError as e:
        print(f"Outing form download failed: {e}")
        raise VtopConnectionError(
            f"Failed to download outing form: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while downloading outing form: {e}")
        raise VtopWeekendOutingError(
            f"Failed to download outing form for {booking_id}: {e}"
        ) from e
