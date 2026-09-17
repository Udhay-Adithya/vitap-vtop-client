from typing import List, Dict, Union
import time
import httpx
from vitap_vtop_client.constants import (
    EXAM_SCHEDULE_URL,
    GET_EXAM_SCHEDULE_URL,
    HEADERS,
)
from vitap_vtop_client.exam_schedule.model.exam_schedule_model import ExamScheduleModel
from vitap_vtop_client.parsers.exam_schedule_parser import parse_exam_schedule
from vitap_vtop_client.exceptions.exception import (
    VtopMenuUnavailableError,
    VtopConnectionError,
    VtopExamScheduleError,
    VtopParsingError,
)


async def fetch_exam_schedule(
    client: httpx.AsyncClient,
    registration_number: str,
    semSubID: str,
    csrf_token: str,
) -> ExamScheduleModel:
    """
    Asynchronously retrieves the exam schedule for a specific user and semester.

    Parameters:
        client (httpx.AsyncClient): The async HTTP client used for requests.
        registration_number (str): The student's Registration number.
        semSubID (str): The semester identifier for the exam schedule.
        csrf_token (str): CSRF token for authentication.

    Returns:
        ExamScheduleModel: Parsed exam schedule information as ExamScheduleModel.

    Raises:
        VtopConnectionError: If network or HTTP issues occur.
        VtopAttendanceError: For unexpected or parsing-related issues.
    """
    try:
        verify_data = {
            "verifyMenu": "true",
            "authorizedID": registration_number,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }
        await client.post(EXAM_SCHEDULE_URL, data=verify_data, headers=HEADERS)

    except httpx.RequestError as e:
        print(f"Attendance initial POST failed: {e}")
        raise VtopConnectionError(
            f"Failed to initialize attendance page: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred during exam schedule initial POST: {e}")
        raise VtopExamScheduleError(
            f"Failed to initialize exam schedule page: {e}"
        ) from e

    try:

        data = {
            "authorizedID": registration_number,
            "semesterSubId": semSubID,
            "_csrf": csrf_token,
        }

        response = await client.post(GET_EXAM_SCHEDULE_URL, data=data, headers=HEADERS)
        response.raise_for_status()

        return parse_exam_schedule(response.text)

    except (VtopParsingError, VtopMenuUnavailableError) as e:
        raise e

    except httpx.RequestError as e:
        print(f"Exam schedule fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch exam schedule: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"Unexpected error while fetching exam schedule: {e}")
        raise VtopExamScheduleError(
            f"Unexpected error while fetching exam schedule: {e}"
        ) from e
