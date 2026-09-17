import time
from typing import List
import httpx

from vitap_vtop_client.constants import HEADERS, PAYMENTS_URL
from vitap_vtop_client.parsers.pending_payments_parser import parse_pending_payments
from vitap_vtop_client.exceptions import (
    VtopMenuUnavailableError,
    VtopConnectionError,
    VtopProfileError,
    VtopParsingError,
)
from vitap_vtop_client.payments.model.pending_payments_model import PendingPayment


async def fetch_pending_payments(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str,
) -> List[PendingPayment]:
    """
    Asynchronously retrieves pending payments information for a specified user from the VTOP system.

    Parameters:
        client (httpx.AsyncClient): The async HTTP client.
        registration_number (str): The student's registration number.
        csrf_token (str): CSRF token for authentication.

    Returns:
        dict: A dictionary containing details of pending payments.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
        VtopProfileError: For other unexpected errors.
    """
    try:
        data = {
            "verifyMenu": "true",
            "authorizedID": registration_number,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }

        response = await client.post(PAYMENTS_URL, data=data, headers=HEADERS)
        response.raise_for_status()

        return parse_pending_payments(response.text)

    except (VtopParsingError, VtopMenuUnavailableError) as e:
        raise e

    except httpx.RequestError as e:
        print(f"Pending payments fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch pending payments: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching pending payments: {e}")
        raise VtopProfileError(
            f"Unexpected error while fetching pending payments: {e}"
        ) from e
