import httpx
from vitap_vtop_client.constants import VTOP_URL, HEADERS 
from vitap_vtop_client.exceptions.exception import VtopConnectionError, VtopCsrfError
from vitap_vtop_client.utils import find_csrf
import asyncio

async def fetch_csrf_token(client: httpx.AsyncClient, max_retries: int = 3) -> str:
    """
    Fetches CSRF token from the VTOP website.

    Args:
        client (httpx.AsyncClient): Async client object for making HTTP requests.
        max_retries (int): Maximum attempts to fetch the token.

    Returns:
        str: CSRF token if found.

    Raises:
        VtopConnectionError: If the HTTP request fails after all retries.
        VtopCsrfError: If csrf_token is not found in the response after all retries.
    """
    for attempt in range(max_retries):
        print(f"Fetching initial CSRF token, attempt {attempt + 1}/{max_retries}...")
        try:
            response = await client.get(VTOP_URL, headers=HEADERS)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            csrf_token = find_csrf(response.text)

            if csrf_token:
                print("Initial CSRF token found.")
                return csrf_token
            else:
                print("Initial CSRF token not found in response.")
                if attempt < max_retries - 1:
                    print("Retrying fetch_csrf_token...")
                    await asyncio.sleep(1) # Small delay before retry
                else:\
                    raise VtopCsrfError(
                        f"Initial CSRF token not found in response after {attempt + 1} attempts.",
                        status_code=response.status_code
                    )

        except httpx.RequestError as e:
            print("RequestError type:", type(e))
            print("RequestError details:", repr(e))
            raise VtopConnectionError(
                f"Failed to fetch csrf page after {attempt + 1} attempts.",
                original_exception=e,
                status_code=502
            )
        except VtopCsrfError as e:
            raise e
        
        except Exception as e:
            print(f"An unexpected error occurred during fetch_csrf_token attempt {attempt + 1}: {e}")
            raise VtopCsrfError(
                    f"Unexpected error during csrf fetch after {attempt + 1} attempts: {e}",
                    status_code=getattr(getattr(e, 'response', None), 'status_code', None)
            ) from e
        
    raise RuntimeError("Unexpected flow in fetch_csrf_token — reached end of function unexpectedly.")
