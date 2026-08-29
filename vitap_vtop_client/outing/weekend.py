import time
from datetime import datetime, timezone
import httpx

from vitap_vtop_client.constants import (
    HEADERS,
    WEEKEND_OUTING_URL,
    SAVE_WEEKEND_OUTING_URL,
)
from .model.weekend_outing_model import WeekendOutingModel
from vitap_vtop_client.parsers.outing_form_parser import parse_outing_form
from vitap_vtop_client.parsers.weekend_outing_requests_parser import parse_weekend_outing_requests
from vitap_vtop_client.parsers.outing_response_parser import parse_outing_response
from vitap_vtop_client.exceptions.exception import (
    VtopConnectionError,
    VtopWeekendOutingError,
    VtopParsingError,
)


async def submit_weekend_outing_request(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str,
    outPlace: str,
    purposeOfVisit: str,
    outingDate: str,
    outTime: str,
    contactNumber: str,
) -> str:
    """
    Submits a weekend outing request form for a student.

    This function first initializes a request to fetch the necessary form information. It then
    sends the outing details to the server to save the form data. The response is processed to
    determine the outcome of the request.

    Args:
        session (Session): The session object used for making HTTP requests.
        registration_number (str): The Registration number of the student submitting the outing request.
        csrf_token (str): The CSRF token used for form validation.
        outPlace (str): The place where the student plans to visit.
        purposeOfVisit (str): The reason for the outing.
        outingDate (str): The date of the outing in the format "DD-MMM-YYYY".
        outTime (str): The time of departure in the format "HH:MM".
        contactNumber (str): The contact number of the student.

    Returns:
        str: A message indicating the result of the outing request submission.
    """
    try:
        # Step 1: Fetch the outing form
        init_data = {
            "verifyMenu": "true",
            "authorizedID": registration_number,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }

        init_response = await client.post(
            WEEKEND_OUTING_URL, data=init_data, headers=HEADERS
        )
        init_response.raise_for_status()
        form_info = parse_outing_form(init_response.text)

    except VtopParsingError as e:
        raise e

    except httpx.RequestError as e:
        raise VtopConnectionError(
            f"An unexpected error occurred during weekend outing initial POST: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        raise VtopWeekendOutingError(
            f"An unexpected error occurred during weekend outing initial POST: {e}"
        )

    try:

        # Step 2: Submit the filled form
        submit_data = {
            "authorizedID": registration_number,
            "BookingId": "",
            "regNo": registration_number,
            "name": form_info.name,
            "applicationNo": form_info.application_no,
            "gender": form_info.gender,
            "hostelBlock": form_info.hostel_block,
            "roomNo": form_info.room_number,
            "outPlace": outPlace,
            "purposeOfVisit": purposeOfVisit,
            "outingDate": outingDate,
            "outTime": outTime,
            "contactNumber": contactNumber,
            "parentContactNumber": form_info.parent_contact_number,
            "_csrf": csrf_token,
            "x": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }

        response = await client.post(
            SAVE_WEEKEND_OUTING_URL, data=submit_data, headers=HEADERS
        )
        response.raise_for_status()
        return parse_outing_response(
            response.text,
            "Outing applied successfully. It is now waiting for your warden's approval.",
        )

    except VtopParsingError as e:
        raise e

    except httpx.RequestError as e:
        raise VtopConnectionError(
            "Failed to submit weekend outing form",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        raise VtopWeekendOutingError(
            f"Unexpected error during weekend outing form submission: {e}"
        )


async def fetch_weekend_outing_requests(
    client: httpx.AsyncClient, registration_number: str, csrf_token: str
) -> WeekendOutingModel:
    """
    Asynchronously fetches previously submitted weekend outing requests.
    """
    try:
        data = {
            "verifyMenu": "true",
            "authorizedID": registration_number,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }

        response = await client.post(WEEKEND_OUTING_URL, data=data, headers=HEADERS)
        response.raise_for_status()
        return parse_weekend_outing_requests(
            response.text
        )

    except VtopParsingError as e:
        raise e

    except httpx.RequestError as e:
        raise VtopConnectionError(
            "Failed to fetch weekend outing requests",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        raise VtopWeekendOutingError(
            f"Unexpected error while fetching weekend outing responses: {e}"
        )
