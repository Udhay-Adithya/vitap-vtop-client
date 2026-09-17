from typing import List, Dict, Union
import time
import httpx
from vitap_vtop_client.constants import (
    GET_EXAM_SCHEDULE_URL,
    HEADERS,
)
from vitap_vtop_client.exam_schedule.model.exam_schedule_model import ExamScheduleModel
from vitap_vtop_client.parsers.exam_schedule_parser import parse_exam_schedule
from vitap_vtop_client.exceptions.exception import (
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
    # No page-shell POST first. VTOP answers doSearchExamScheduleForStudent on a
    # cold session with nothing primed, so opening StudExamSchedule beforehand
    # was a wasted round trip on every call.
    try:

        data = {
            "authorizedID": registration_number,
            "semesterSubId": semSubID,
            "_csrf": csrf_token,
        }

        response = await client.post(GET_EXAM_SCHEDULE_URL, data=data, headers=HEADERS)
        response.raise_for_status()

        return parse_exam_schedule(response.text)

    except VtopParsingError as e:
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
