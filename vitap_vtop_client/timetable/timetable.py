import httpx
import time
from datetime import datetime, timezone
from vitap_vtop_client.constants import GET_TIME_TABLE_URL, HEADERS
from vitap_vtop_client.parsers import timetable_parser
from vitap_vtop_client.exceptions.exception import VtopConnectionError, VtopTimetableError, VtopParsingError, VtopMenuUnavailableError
from vitap_vtop_client.timetable.model.timetable_model import TimetableModel

async def fetch_timetable(
    client: httpx.AsyncClient,
    username: str,
    semSubID: str,
    csrf_token: str
) -> TimetableModel:
    """
    Retrieves the timetable for a specified semester and user.

    Parameters:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The username of the student or user.
        semSubID (str): The semester subject ID for which the timetable is to be fetched.
        csrf_token (str): The CSRF token used for form validation.

    Returns:
        TimetableModel: A TimetableModel containing the parsed timetable details.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopTimetableError: If initialization or data fetch fails.
        VtopParsingError: If parsing fails.
    """
    # No page-shell POST first. VTOP answers processViewTimeTable on a cold
    # session with nothing primed, so opening StudentTimeTable beforehand was a
    # wasted round trip on every call.
    try:
        data_fetch = {
            "_csrf": csrf_token,
            "semesterSubId": semSubID,
            "authorizedID": username,
            "x": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }
        timetable_response = await client.post(GET_TIME_TABLE_URL, data=data_fetch, headers=HEADERS)
        timetable_response.raise_for_status()

        # Parse the response
        parsed_data = timetable_parser.parse_time_table(timetable_response.text)
        return parsed_data

    except (VtopParsingError, VtopMenuUnavailableError) as e:
        raise e

    except httpx.RequestError as e:
        print(f"Timetable data fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch timetable data: {e}",
            original_exception=e,
            status_code=502
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching or parsing timetable: {e}")
        raise VtopTimetableError(f"An unexpected error occurred while fetching timetable for semester {semSubID}: {e}") from e
