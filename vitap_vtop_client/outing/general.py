import time
from datetime import datetime, timezone
from typing import Union
import httpx

from vitap_vtop_client.constants import (
    HEADERS,
    GENERAL_OUTING_URL,
    SAVE_GENERAL_OUTING_URL,
)
from .model.general_outing_model import GeneralOutingModel
from vitap_vtop_client.parsers.outing_form_parser import parse_outing_form
from vitap_vtop_client.parsers.general_outing_requests_parser import (
    parse_general_outing_requests,
)
from vitap_vtop_client.parsers.outing_response_parser import parse_outing_response
from vitap_vtop_client.exceptions.exception import (
    VtopConnectionError,
    VtopGeneralOutingError,
    VtopParsingError,
)


async def submit_general_outing_request(
    client: httpx.AsyncClient,
    registration_number: str,
    csrf_token: str,
    outPlace: str,
    purposeOfVisit: str,
    outingDate: str,
    outTime: str,
    inDate: str,
    inTime: str,
) -> str:
    """
    Submits a general outing form for a student in the VTOP Portal.

    This function handles the submission of a general outing form by first retrieving the student's form details
    and then posting the filled form data to the server. The form includes information such as the place of visit,
    purpose, outing date, and time, as well as contact details.

    Parameters:
        session (Session):
            The active session object used to maintain the user's session.
        registration_number (str):
            The Registration number of the student submitting the outing form.
        csrf_token (str):
            The CSRF token required to authenticate the request.
        outPlace (str):
            The place of visit for the outing.
        purposeOfVisit (str):
            The purpose of the visit.
        outingDate (str):
            The date of the outing in the format 'DD-MMM-YYYY'.
        outTime (str):
            The time of departure in the format 'HH:MM'.
        inDate (str):
            The date of return from outing in the format 'DD-MMM-YYYY'.
        inTime (str):
            The expected time of return in the format 'HH:MM'.
        contactNumber (str):
            The contact number of the student.

    Returns:
        str:
            A string indicating the result of the outing form submission, such as success or failure messages.
    """
    try:
        # Step 1: Fetch form info
        init_data = {
            "verifyMenu": "true",
            "authorizedID": registration_number,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }
        init_response = await client.post(
            GENERAL_OUTING_URL, data=init_data, headers=HEADERS
        )
        init_response.raise_for_status()
        form_info = parse_outing_form(init_response.text)

    except VtopParsingError as e:
        raise e

    except httpx.RequestError as e:
        raise VtopConnectionError(
            f"An unexpected error occurred during general outing initial POST: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        raise VtopGeneralOutingError(
            f"An unexpected error occurred during general outing initial POST: {e}"
        )

    try:
        # Step 2: Submit the form
        data = {
            "authorizedID": registration_number,
            "LeaveId": "",
            "regNo": registration_number,
            "name": form_info.name,
            "applicationNo": form_info.application_no,
            "gender": form_info.gender,
            "hostelBlock": form_info.hostel_block,
            "roomNo": form_info.room_number,
            "placeOfVisit": outPlace,
            "purposeOfVisit": purposeOfVisit,
            "outDate": outingDate,
            "outTimeHr": outTime.split(":")[0],
            "outTimeMin": outTime.split(":")[1],
            "inDate": inDate,
            "inTimeHr": inTime.split(":")[0],
            "inTimeMin": inTime.split(":")[1],
            "parentContactNumber": form_info.parent_contact_number,
            "_csrf": csrf_token,
            "x": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }

        response = await client.post(
            SAVE_GENERAL_OUTING_URL, data=data, headers=HEADERS
        )
        response.raise_for_status()

        return parse_outing_response(
            response.text,
            "Outing applied successfully. It is now waiting for your mentor's approval.",
        )

    except VtopParsingError as e:
        raise e

    except httpx.RequestError as e:
        raise VtopConnectionError(
            "Failed to submit general outing form", original_exception=e, status_code=502
        )
    except Exception as e:
        raise VtopGeneralOutingError(f"Unexpected error in general outing form submission: {e}")


async def fetch_general_outing_requests(
    client: httpx.AsyncClient, registration_number: str, csrf_token: str
) -> GeneralOutingModel:
    
    """
    Asynchronously fetches previously submitted general outing requests.
    """
    
    try:
        data = {
            "verifyMenu": "true",
            "authorizedID": registration_number,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }

        response = await client.post(GENERAL_OUTING_URL, data=data, headers=HEADERS)
        response.raise_for_status()
        return parse_general_outing_requests(response.text)

    except VtopParsingError as e:
        raise e

    except httpx.RequestError as e:
        raise VtopConnectionError(
            "Failed to fetch outing response", original_exception=e, status_code=502
        )
    except Exception as e:
        raise VtopGeneralOutingError(
            f"Unexpected error while fetching outing response: {e}"
        )
