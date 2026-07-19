from datetime import datetime, timezone

import httpx

from vitap_vtop_client.constants import HEADERS, PRINT_PAYMENT_RECEIPT_URL
from vitap_vtop_client.exceptions.exception import (
    VitapVtopClientError,
    VtopConnectionError,
)


async def fetch_payment_receipt_document(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str,
    receipt_no: str,
    application_number: str,
) -> str:
    """
    Downloads the printable document for a paid receipt.

    VTOP serves this as an HTML page rather than a PDF.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        registration_number (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        receipt_no (str): The receipt number, from PaymentReceipt.receipt_no.
        application_number (str): The student's application number, available
            from StudentProfileModel.application_number.

    Returns:
        str: The receipt document markup.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VitapVtopClientError: If the download fails for any other reason.
    """
    try:
        params = {
            # VTOP spells this parameter "receitNo"; do not correct it.
            "receitNo": receipt_no,
            "authorizedID": registration_number,
            "_csrf": csrf_token,
            "x": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "registerNumber": registration_number,
            "applno": application_number,
        }
        response = await client.get(
            PRINT_PAYMENT_RECEIPT_URL, params=params, headers=HEADERS
        )
        response.raise_for_status()
        return response.text

    except httpx.RequestError as e:
        print(f"Payment receipt download failed: {e}")
        raise VtopConnectionError(
            f"Failed to download payment receipt: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while downloading payment receipt: {e}")
        raise VitapVtopClientError(
            f"Failed to download payment receipt {receipt_no}: {e}"
        ) from e
