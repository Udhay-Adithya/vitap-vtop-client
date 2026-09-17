import httpx
import time
from datetime import datetime, timezone
from vitap_vtop_client.attendance.model.attendance_model import (
    AttendanceDetailModel,
    AttendanceModel,
)
from vitap_vtop_client.attendance.model.capstone_model import CapstoneAttendanceModel
from vitap_vtop_client.exceptions.exception import VtopAttendanceError, VtopConnectionError, VtopParsingError, VtopMenuUnavailableError
from vitap_vtop_client.parsers import attendance_parser
from vitap_vtop_client.constants import (
    VIEW_ATTENDANCE_URL,
    VIEW_ATTENDANCE_DETAIL_URL,
    ATTENDANCE_URL,
    SDP_ATTENDANCE_URL,
    HEADERS,
)
from vitap_vtop_client.parsers import capstone_attendance_parser

async def fetch_attendance(
    client: httpx.AsyncClient,
    registration_number: str,
    semSubID: str,
    csrf_token: str
) -> list[AttendanceModel]:
    """
    Retrieves the attendance details for a specific user and semester subject.

    Parameters:
        client (httpx.AsyncClient): The active httpx async client.
        registration_number (str): The registration_number of the student.
        semSubID (str): The identifier for the semester subject.
        csrf_token (str): The CSRF token.

    Returns:
        list[AttendanceModel]: A list containing the parsed attendance data.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopAttendanceError: If the initial POST or the attendance data request fails or returns unexpected content.
        VtopParsingError: For parsing errors.
    """
    try:
        # First POST to verify menu/session
        data_initial = {
            "verifyMenu": "true",
            "authorizedID": registration_number,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }
        # Use await client.post
        initial_response = await client.post(ATTENDANCE_URL, data=data_initial, headers=HEADERS)
        initial_response.raise_for_status() # Raise exception for bad status codes

        # Check if the initial POST was successful in setting up the page context
        # This might involve checking the response content or status,
        # but raise_for_status is a good start for HTTP errors.
        # More specific checks might be needed based on VTOP's responses.
    
    except httpx.RequestError as e:
        print(f"Attendance initial POST failed: {e}")
        raise VtopConnectionError(
                f"Failed to initialize attendance page: {e}",
                original_exception=e,
                status_code=502
            )
    except Exception as e:
         print(f"An unexpected error occurred during attendance initial POST: {e}")
         raise VtopAttendanceError(f"Failed to initialize attendance page: {e}") from e

    try:
        # Second POST to fetch attendance data
        data_fetch = {
            "_csrf": csrf_token,
            "semesterSubId": semSubID,
            "authorizedID": registration_number,
            "x": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }
        attendance_response = await client.post(VIEW_ATTENDANCE_URL, data=data_fetch, headers=HEADERS)
        attendance_response.raise_for_status() # Raise exception for bad status codes

        # Parse the HTML content
        parsed_data = attendance_parser.parse_attendance(attendance_response.text)

        return parsed_data
    
    except (VtopParsingError, VtopMenuUnavailableError) as e:
        raise e

    except httpx.RequestError as e:
        print(f"Attendance data fetch failed: {e}")
        raise VtopConnectionError(
                f"Failed to fetch attendance data: {e}",
                original_exception=e,
                status_code=502
            )
    except Exception as e:
        print(f"An unexpected error occurred while fetching or parsing attendance: {e}")
        raise VtopAttendanceError(f"An unexpected error occurred while fetching attendance for semester {semSubID}: {e}") from e

async def fetch_attendance_detail(
    client: httpx.AsyncClient,
    registration_number: str,
    semSubID: str,
    course_id: str,
    course_type: str,
    csrf_token: str
) -> list[AttendanceDetailModel]:
    """
    Retrieves the per class attendance detail for a single course.

    Parameters:
        client (httpx.AsyncClient): The active httpx async client.
        registration_number (str): The registration_number of the student.
        semSubID (str): The identifier for the semester subject.
        course_id (str): The course id, from AttendanceModel.course_id.
        course_type (str): The short course type code, from
            AttendanceModel.course_type_code.
        csrf_token (str): The CSRF token.

    Returns:
        list[AttendanceDetailModel]: One entry per class held.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopAttendanceError: If the request fails or returns unexpected content.
        VtopParsingError: For parsing errors.
    """
    try:
        data = {
            "_csrf": csrf_token,
            "semesterSubId": semSubID,
            "registerNumber": registration_number,
            "courseId": course_id,
            "courseType": course_type,
            "authorizedID": registration_number,
            "x": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }
        response = await client.post(
            VIEW_ATTENDANCE_DETAIL_URL, data=data, headers=HEADERS
        )
        response.raise_for_status()

        return attendance_parser.parse_full_attendance(response.text)

    except (VtopParsingError, VtopMenuUnavailableError) as e:
        raise e

    except httpx.RequestError as e:
        print(f"Attendance detail fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch attendance detail: {e}",
            original_exception=e,
            status_code=502
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching attendance detail: {e}")
        raise VtopAttendanceError(
            f"An unexpected error occurred while fetching attendance detail for course {course_id}: {e}"
        ) from e


# VTOP serves the capstone fragment only to an AJAX request, matching what the
# attendance page's viewSDPAttendance() sends.
_AJAX_HEADERS = {
    **HEADERS,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}


async def fetch_capstone_attendance(
    client: httpx.AsyncClient,
    registration_number: str,
    semSubID: str,
    csrf_token: str,
) -> CapstoneAttendanceModel | None:
    """
    Retrieves capstone/SDP attendance for a semester.

    This is separate from course attendance: it is per semester rather than per
    course, and counts present / on duty / absent instead of attended / total.
    Only students registered for a capstone or SDP have it.

    Parameters:
        client (httpx.AsyncClient): The active httpx async client.
        registration_number (str): The registration_number of the student.
        semSubID (str): The identifier for the semester subject.
        csrf_token (str): The CSRF token.

    Returns:
        CapstoneAttendanceModel | None: The attendance, or None when the student
            has no capstone registered for this semester.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopAttendanceError: If the request fails or returns unexpected content.
        VtopParsingError: For parsing errors.
    """
    try:
        # VTOP's own JS sends the registration number twice, as regNo and as
        # authorizedID. Both are required.
        data = {
            "_csrf": csrf_token,
            "semesterSubId": semSubID,
            "regNo": registration_number,
            "authorizedID": registration_number,
            "x": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }
        response = await client.post(
            SDP_ATTENDANCE_URL, data=data, headers=_AJAX_HEADERS
        )
        response.raise_for_status()

        return capstone_attendance_parser.parse_capstone_attendance(response.text)

    except (VtopParsingError, VtopMenuUnavailableError) as e:
        raise e

    except httpx.RequestError as e:
        print(f"Capstone attendance fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch capstone attendance: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching capstone attendance: {e}")
        raise VtopAttendanceError(
            f"An unexpected error occurred while fetching capstone attendance "
            f"for semester {semSubID}: {e}"
        ) from e
