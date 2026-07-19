from datetime import datetime, timezone

import httpx

from vitap_vtop_client.constants import (
    DA_OTP_UPLOAD_URL,
    DA_UPLOAD_URL,
    DIGITAL_ASSIGNMENT_URL,
    HEADERS,
    PROCESS_DA_UPLOAD_URL,
    PROCESS_DIGITAL_ASSIGNMENT_URL,
)
from vitap_vtop_client.digital_assignment.model.digital_assignment_model import (
    AssignmentRecordModel,
    DigitalAssignmentModel,
)
from vitap_vtop_client.exceptions.exception import (
    VtopConnectionError,
    VtopDigitalAssignmentError,
    VtopDigitalAssignmentFileNotFoundError,
    VtopDigitalAssignmentFileSizeExceededError,
    VtopDigitalAssignmentFileTypeNotSupportedError,
    VtopDigitalAssignmentUploadOtpIncorrectError,
    VtopDigitalAssignmentUploadOtpRequiredError,
    VtopParsingError,
)
from vitap_vtop_client.parsers import digital_assignment_parser

# VTOP rejects anything larger than 4 MB or outside these types.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
_MIME_TYPES = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


async def fetch_all_digital_assignments(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
) -> list[DigitalAssignmentModel]:
    """
    Fetches every course's assignments for a semester.

    VTOP serves the course list and the per course assignments from separate
    endpoints, so this fans out one request per course to fill in the details.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        semSubID (str): The semester subject ID.

    Returns:
        list[DigitalAssignmentModel]: One entry per course, details populated.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    try:
        files = {
            "authorizedID": (None, username),
            "semesterSubId": (None, semSubID),
            "_csrf": (None, csrf_token),
        }
        response = await client.post(
            DIGITAL_ASSIGNMENT_URL, files=files, headers=HEADERS
        )
        response.raise_for_status()

        assignments = digital_assignment_parser.parse_all_assignments(response.text)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        print(f"Digital assignment fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch digital assignments: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching digital assignments: {e}")
        raise VtopDigitalAssignmentError(
            f"Failed to fetch digital assignments for semester {semSubID}: {e}"
        ) from e

    for assignment in assignments:
        assignment.details = await fetch_per_course_dassignments(
            client=client,
            username=username,
            csrf_token=csrf_token,
            class_id=assignment.class_id,
        )

    return assignments


async def fetch_per_course_dassignments(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    class_id: str,
) -> list[AssignmentRecordModel]:
    """
    Fetches the assignments for a single course.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        class_id (str): The class id, from DigitalAssignmentModel.class_id.

    Returns:
        list[AssignmentRecordModel]: One entry per assignment.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopParsingError: If parsing fails.
    """
    try:
        data = {
            "authorizedID": username,
            "x": _timestamp(),
            "classId": class_id,
            "_csrf": csrf_token,
        }
        response = await client.post(
            PROCESS_DIGITAL_ASSIGNMENT_URL, data=data, headers=HEADERS
        )
        response.raise_for_status()

        return digital_assignment_parser.parse_per_course_dassignments(response.text)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        print(f"Per course assignment fetch failed: {e}")
        raise VtopConnectionError(
            f"Failed to fetch assignments for class {class_id}: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while fetching course assignments: {e}")
        raise VtopDigitalAssignmentError(
            f"Failed to fetch assignments for class {class_id}: {e}"
        ) from e


async def fetch_da_or_qp_pdf(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    download_url: str,
) -> bytes:
    """
    Downloads an assignment question paper or a submitted assignment file.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        download_url (str): The path from AssignmentRecordModel.qp_download_url
            or AssignmentRecordModel.da_download_url.

    Returns:
        bytes: The raw file contents.

    Raises:
        VtopConnectionError: If an HTTP request fails.
        VtopDigitalAssignmentError: If no download URL was supplied.
    """
    if not download_url:
        raise VtopDigitalAssignmentError(
            "No download URL was supplied. Check can_qp_download or "
            "can_da_download before requesting the file.",
            status_code=400,
        )

    try:
        params = {
            "authorizedID": username,
            "_csrf": csrf_token,
            "x": _timestamp(),
        }
        response = await client.get(
            f"/vtop/{download_url.lstrip('/')}", params=params, headers=HEADERS
        )
        response.raise_for_status()
        return response.content

    except httpx.RequestError as e:
        print(f"Assignment file download failed: {e}")
        raise VtopConnectionError(
            f"Failed to download assignment file: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while downloading assignment file: {e}")
        raise VtopDigitalAssignmentError(
            f"Failed to download assignment file: {e}"
        ) from e


async def _prepare_upload(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    class_id: str,
    mcode: str,
) -> tuple[list[str], list[str]]:
    """
    Runs the two requests VTOP requires before it will accept an upload.

    The first POST to processDigitalAssignment carries no useful response, but
    the server refuses the subsequent upload without it.
    """
    try:
        pre_data = {
            "authorizedID": username,
            "x": _timestamp(),
            "classId": class_id,
            "_csrf": csrf_token,
        }
        await client.post(
            PROCESS_DIGITAL_ASSIGNMENT_URL, data=pre_data, headers=HEADERS
        )

        data = {
            "authorizedID": username,
            "x": _timestamp(),
            "classId": class_id,
            "mode": mcode,
            "_csrf": csrf_token,
        }
        response = await client.post(
            PROCESS_DA_UPLOAD_URL, data=data, headers=HEADERS
        )
        response.raise_for_status()

        return digital_assignment_parser.parse_process_upload_assignment_response(
            response.text
        )

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        raise VtopConnectionError(
            f"Failed to prepare the assignment upload: {e}",
            original_exception=e,
            status_code=502,
        )


def _validate_upload(file_name: str, file_bytes: bytes) -> str:
    """Checks the file against VTOP's limits and returns its MIME type."""
    if not file_name or not file_bytes:
        raise VtopDigitalAssignmentFileNotFoundError(
            "A file name and file contents are required to upload an assignment.",
            status_code=400,
        )

    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if extension not in _MIME_TYPES:
        raise VtopDigitalAssignmentFileTypeNotSupportedError(
            f"VTOP does not accept .{extension} files. Supported types are: "
            f"{', '.join(sorted(_MIME_TYPES))}.",
            status_code=400,
        )

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise VtopDigitalAssignmentFileSizeExceededError(
            f"The file is {len(file_bytes)} bytes, which exceeds VTOP's "
            f"{MAX_UPLOAD_BYTES} byte limit.",
            status_code=400,
        )

    return _MIME_TYPES[extension]


async def upload_course_dassignment(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    class_id: str,
    mcode: str,
    file_name: str,
    file_bytes: bytes,
) -> str:
    """
    Uploads a file as the submission for one assignment.

    VTOP may hold the upload pending an OTP mailed to the student, in which
    case this raises VtopDigitalAssignmentUploadOtpRequiredError and the
    caller must follow up with `verify_assignment_upload_otp`.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        class_id (str): The class id, from DigitalAssignmentModel.class_id.
        mcode (str): The assignment code, from AssignmentRecordModel.mcode.
        file_name (str): The file name, used to derive the content type.
        file_bytes (bytes): The file contents.

    Returns:
        str: VTOP's response message, "Uploaded successfully" on success.

    Raises:
        VtopDigitalAssignmentFileNotFoundError: If the file is empty.
        VtopDigitalAssignmentFileTypeNotSupportedError: If the type is rejected.
        VtopDigitalAssignmentFileSizeExceededError: If the file is over 4 MB.
        VtopDigitalAssignmentUploadOtpRequiredError: If an OTP is required.
        VtopConnectionError: If an HTTP request fails.
    """
    mime_type = _validate_upload(file_name, file_bytes)

    codes, opts = await _prepare_upload(
        client=client,
        username=username,
        csrf_token=csrf_token,
        class_id=class_id,
        mcode=mcode,
    )

    try:
        # httpx needs repeated field names expressed as a list of tuples.
        form: list[tuple[str, tuple]] = [
            ("authorizedID", (None, username)),
        ]
        for code, opt in zip(codes, opts):
            form.append(("code", (None, code)))
            form.append(("opt", (None, opt)))

        form.append(("studDaUpload", (file_name, file_bytes, mime_type)))
        form.append(("_csrf", (None, csrf_token)))
        form.append(("classId", (None, class_id)))
        form.append(("mCode", (None, mcode)))

        response = await client.post(DA_UPLOAD_URL, files=form, headers=HEADERS)
        response.raise_for_status()

        result = digital_assignment_parser.parse_upload_assignment_response(
            response.text
        )

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        print(f"Assignment upload failed: {e}")
        raise VtopConnectionError(
            f"Failed to upload the assignment: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while uploading the assignment: {e}")
        raise VtopDigitalAssignmentError(
            f"Failed to upload the assignment: {e}"
        ) from e

    if result == "OTP Required":
        raise VtopDigitalAssignmentUploadOtpRequiredError(
            "VTOP requires an OTP to confirm this assignment upload.",
            status_code=401,
        )

    return result


async def verify_assignment_upload_otp(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    otp: str,
) -> str:
    """
    Confirms a held assignment upload with the OTP VTOP mailed to the student.

    Args:
        client (httpx.AsyncClient): The active httpx async client.
        username (str): The student's registration number.
        csrf_token (str): The CSRF token used for form validation.
        otp (str): The OTP entered by the user.

    Returns:
        str: VTOP's response message, "Uploaded successfully" on success.

    Raises:
        VtopDigitalAssignmentUploadOtpIncorrectError: If the OTP is rejected.
        VtopConnectionError: If an HTTP request fails.
    """
    try:
        files = {
            "authorizedID": (None, username),
            "otpEmail": (None, otp),
            "_csrf": (None, csrf_token),
        }
        response = await client.post(DA_OTP_UPLOAD_URL, files=files, headers=HEADERS)
        response.raise_for_status()

        result = digital_assignment_parser.parse_upload_assignment_response(
            response.text
        )

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        print(f"Assignment upload OTP verification failed: {e}")
        raise VtopConnectionError(
            f"Failed to verify the assignment upload OTP: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        print(f"An unexpected error occurred while verifying the upload OTP: {e}")
        raise VtopDigitalAssignmentError(
            f"Failed to verify the assignment upload OTP: {e}"
        ) from e

    if result == "Invalid OTP. Please try again.":
        raise VtopDigitalAssignmentUploadOtpIncorrectError(result, status_code=401)

    return result
