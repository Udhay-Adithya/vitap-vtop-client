import time
from datetime import datetime, timezone

import httpx

from vitap_vtop_client.constants import (
    COURSE_PAGE_URL,
    COURSE_PLAN_EXCEL_URL,
    GET_COURSE_FOR_COURSE_PAGE_URL,
    GET_SLOT_FOR_COURSE_PAGE_URL,
    HEADERS,
    VIEW_COURSE_DETAIL_URL,
)
from vitap_vtop_client.course_page.model.course_page_model import (
    CoursePageDetailModel,
    CoursesResponseModel,
    SlotsResponseModel,
)
from vitap_vtop_client.exceptions.exception import (
    VitapVtopClientError,
    VtopConnectionError,
    VtopParsingError,
)
from vitap_vtop_client.parsers import course_page_parser


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


async def init_course_page(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
) -> str:
    """
    Opens the course page.

    VTOP requires this before it will answer the course and slot lookups.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.

    Returns:
        str: The course page markup.

    Raises:
        VtopConnectionError: If an HTTP request fails.
    """
    try:
        data = {
            "verifyMenu": "true",
            "authorizedID": username,
            "_csrf": csrf_token,
            "nocache": int(round(time.time() * 1000)),
        }
        response = await client.post(COURSE_PAGE_URL, data=data, headers=HEADERS)
        response.raise_for_status()
        return response.text

    except httpx.RequestError as e:
        print(f"Course page init failed: {e}")
        raise VtopConnectionError(
            f"Failed to initialize the course page: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred during course page init: {e}")
        raise VitapVtopClientError(f"Failed to initialize the course page: {e}") from e


async def fetch_courses_for_course_page(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
) -> CoursesResponseModel:
    """
    Fetches the courses selectable on the course page for a semester.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        semSubID (str): The semester subject ID.

    Returns:
        CoursesResponseModel: The selectable courses.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    try:
        data = {
            "_csrf": csrf_token,
            "paramReturnId": "getCourseForCoursePage",
            "semSubId": semSubID,
            "authorizedID": username,
            "x": _timestamp(),
        }
        response = await client.post(
            GET_COURSE_FOR_COURSE_PAGE_URL, data=data, headers=HEADERS
        )
        response.raise_for_status()

        return course_page_parser.parse_courses_for_course_page(response.text)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        print(f"Course page course fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch course page courses: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching course page courses: {e}")
        raise VitapVtopClientError(
            f"Failed to fetch course page courses for semester {semSubID}: {e}"
        ) from e


async def fetch_slots_for_course_page(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
    class_id: str,
) -> SlotsResponseModel:
    """
    Fetches the slots and class rows for a course.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        semSubID (str): The semester subject ID.
        class_id (str): The course value, from CourseOptionModel.value.

    Returns:
        SlotsResponseModel: The selectable slots and the class rows.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    try:
        data = {
            "_csrf": csrf_token,
            "classId": class_id,
            "praType": "source",
            "paramReturnId": "getSlotIdForCoursePage",
            "semSubId": semSubID,
            "authorizedID": username,
            "x": _timestamp(),
        }
        response = await client.post(
            GET_SLOT_FOR_COURSE_PAGE_URL, data=data, headers=HEADERS
        )
        response.raise_for_status()

        return course_page_parser.parse_slots_for_course_page(response.text, semSubID)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        print(f"Course page slot fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch course page slots: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching course page slots: {e}")
        raise VitapVtopClientError(
            f"Failed to fetch course page slots for class {class_id}: {e}"
        ) from e


async def fetch_course_detail(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
    erp_id: str,
    class_id: str,
) -> CoursePageDetailModel:
    """
    Fetches a course's detail page.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        semSubID (str): The semester subject ID.
        erp_id (str): The faculty ERP id, from CourseClassEntryModel.erp_id.
        class_id (str): The class id, from CourseClassEntryModel.class_id.

    Returns:
        CoursePageDetailModel: The course summary, lectures and download paths.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    try:
        data = {
            "_csrf": csrf_token,
            "semSubId": semSubID,
            "erpId": erp_id,
            "classId": class_id,
            "authorizedID": username,
            "x": _timestamp(),
        }
        response = await client.post(
            VIEW_COURSE_DETAIL_URL, data=data, headers=HEADERS
        )
        response.raise_for_status()

        return course_page_parser.parse_course_detail_page(response.text)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        print(f"Course detail fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch course detail: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching course detail: {e}")
        raise VitapVtopClientError(
            f"Failed to fetch course detail for class {class_id}: {e}"
        ) from e


async def download_course_material(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    download_path: str,
) -> bytes:
    """
    Downloads a course material, syllabus or bundled material archive.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        download_path (str): A path from CoursePageDetailModel, such as
            download_all_path, syllabus_download_path, or a lecture's
            reference material download_path.

    Returns:
        bytes: The raw file contents.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VitapVtopClientError: If no path was supplied or the download fails.
    """
    if not download_path:
        raise VitapVtopClientError(
            "No download path was supplied.", status_code=400
        )

    try:
        params = {
            "authorizedID": username,
            "_csrf": csrf_token,
            "x": _timestamp(),
        }
        response = await client.get(
            f"/vtop/{download_path.lstrip('/')}", params=params, headers=HEADERS
        )
        response.raise_for_status()
        return response.content

    except httpx.RequestError as e:
        print(f"Course material download failed: {e}")
        raise VtopConnectionError(
            f"Failed to download course material: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while downloading course material: {e}")
        raise VitapVtopClientError(
            f"Failed to download course material: {e}"
        ) from e


async def download_course_plan_excel(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
    class_id: str,
) -> bytes:
    """
    Downloads a course plan as an Excel workbook.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        semSubID (str): The semester subject ID.
        class_id (str): The class id, from CourseClassEntryModel.class_id.

    Returns:
        bytes: The raw workbook contents.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VitapVtopClientError: If the download fails for any other reason.
    """
    try:
        params = {
            "semesterSubId": semSubID,
            "classId": class_id,
            "authorizedID": username,
            "x": _timestamp(),
        }
        response = await client.get(
            COURSE_PLAN_EXCEL_URL, params=params, headers=HEADERS
        )
        response.raise_for_status()
        return response.content

    except httpx.RequestError as e:
        print(f"Course plan download failed: {e}")
        raise VtopConnectionError(
            f"Failed to download course plan: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while downloading course plan: {e}")
        raise VitapVtopClientError(f"Failed to download course plan: {e}") from e
