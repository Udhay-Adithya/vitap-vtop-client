import httpx
from .model.biometric_model import BiometricModel
from vitap_vtop_client.constants import HEADERS, BIOMETRIC_LOG_URL, GET_BIOMETRIC_LOG_URL
import time
from datetime import datetime, timezone

from vitap_vtop_client.exceptions.exception import VtopBiometricError, VtopConnectionError, VtopParsingError, VtopMenuUnavailableError
from vitap_vtop_client.parsers import biometric_parser

async def fetch_biometric(
        client: httpx.AsyncClient,
        registration_number: str,
        date: str,
        csrf_token: str,
        ) -> list[BiometricModel]:
    """
    Retrieves biometric log details for a specific student and date.

    This function sends two HTTP POST requests to the VTOP Portal. The first request verifies the user's menu/session,
    and the second request retrieves the biometric log data for the given date.

    Parameters:
        client (httpx.AsyncClient): 
            The active httpx async client.
        username (str): 
            The username of the student whose biometric data is being retrieved.
        date (str): 
            The date for which the biometric log is requested, in 'dd/mm/yyyy' format.
        csrf_token (str): 
            The CSRF token required to authenticate the request.

    Returns:
        dict: 
            A dictionary containing the biometric logs, with each entry's time and location. 
            The key is the specific entry date and time.
    """
    try:
        data = {
            'verifyMenu': 'true',
            'authorizedID': registration_number,
            '_csrf': csrf_token,
            'nocache': int(round(time.time() * 1000))
        }
        await client.post(BIOMETRIC_LOG_URL, data=data, headers=HEADERS)
    except httpx.RequestError as e:
        print(f"Attendance initial POST failed: {e}")
        raise VtopConnectionError(
                f"Failed to initialize attendance page: {e}",
                original_exception=e,
                status_code=502
            )
    except Exception as e:
         print(f"An unexpected error occurred during attendance initial POST: {e}")
         raise VtopBiometricError(f"Failed to initialize attendance page: {e}") from e
    
    try:
        data = {
            '_csrf': csrf_token,
            'fromDate': date,
            'authorizedID': registration_number,
            'x': datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        }
        biometric_response = await client.post(GET_BIOMETRIC_LOG_URL, data=data, headers=HEADERS)
        biometric_response.raise_for_status() # Raise exception for bad status codes

        # Parse the HTML content
        parsed_data = biometric_parser.parse_biometric(biometric_response.text)

        return parsed_data
    
    except (VtopParsingError, VtopMenuUnavailableError) as e:
        raise e

    except httpx.RequestError as e:
        print(f"Biometric fetch failed for the date {date}: {e}")
        raise VtopConnectionError(
                f"Biometric fetch failed for the date {date}: {e}",
                original_exception=e,
                status_code=502
            )
    except Exception as e:
        print(f"An unexpected error occurred while fetching or parsing biometric: {e}")
        raise VtopBiometricError(f"An unexpected error occurred while fetching or parsing biometric for the data {date}: {e}") from e
