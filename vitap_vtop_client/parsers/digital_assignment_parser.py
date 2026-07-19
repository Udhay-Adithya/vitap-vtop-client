import re

from bs4 import BeautifulSoup

from vitap_vtop_client.digital_assignment.model.digital_assignment_model import (
    AssignmentRecordModel,
    DigitalAssignmentModel,
)
from vitap_vtop_client.exceptions.exception import VtopParsingError

# Download links are wrapped in a vtopDownload('...') call rather than a plain href.
_DOWNLOAD_URL_RE = re.compile(r"vtopDownload\('([^']+)'\)")


def _cell_text(cell) -> str:
    return cell.get_text(strip=True).replace("\t", "").replace("\n", "")


def _download_url(cell) -> str:
    """Pulls the download path out of the cell's vtopDownload link."""
    anchor = cell.find("a")
    if anchor is None:
        return ""
    match = _DOWNLOAD_URL_RE.search(anchor.get("href") or "")
    return match.group(1) if match else ""


def parse_all_assignments(html: str) -> list[DigitalAssignmentModel]:
    """
    Parses the course list from the digital assignment page.

    The per course assignments are not present on this page and must be
    fetched separately using each course's class_id.

    Args:
        html (str): The raw HTML of the digital assignment page.

    Returns:
        list[DigitalAssignmentModel]: One entry per registered course, with
            an empty details list.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        assignments: list[DigitalAssignmentModel] = []

        for row in soup.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) != 7:
                continue

            assignments.append(
                DigitalAssignmentModel(
                    serial_number=_cell_text(cells[0]),
                    class_id=_cell_text(cells[1]),
                    course_code=_cell_text(cells[2]),
                    course_title=_cell_text(cells[3]),
                    course_type=_cell_text(cells[4]),
                    faculty=_cell_text(cells[5]),
                    details=[],
                )
            )

        return assignments

    except Exception as e:
        raise VtopParsingError(f"Failed to parse digital assignments: {e}") from e


def parse_per_course_dassignments(html: str) -> list[AssignmentRecordModel]:
    """
    Parses the assignments listed for a single course.

    Args:
        html (str): The raw HTML of the per course assignment response.

    Returns:
        list[AssignmentRecordModel]: One entry per assignment.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        records: list[AssignmentRecordModel] = []

        # The first four rows are page and table headers.
        for row in soup.find_all("tr")[4:]:
            cells = row.find_all("td")
            if len(cells) != 9:
                continue

            submission_status = _cell_text(cells[6])

            can_qp_download = "Download" in cells[5].decode_contents()
            qp_download_url = _download_url(cells[5]) if can_qp_download else ""

            # The update control is rendered as a pencil icon.
            can_update = "pencil" in cells[7].decode_contents()
            mcode = ""
            if can_update:
                code_input = cells[7].find("input", attrs={"name": "code"})
                if code_input is not None:
                    mcode = code_input.get("value") or ""

            # A download link is rendered even when nothing was submitted, so
            # the submission status has to be checked as well.
            can_da_download = (
                "Download" in cells[8].decode_contents()
                and submission_status != ""
                and "File Not Uploaded" not in submission_status
            )
            da_download_url = _download_url(cells[8]) if can_da_download else ""

            records.append(
                AssignmentRecordModel(
                    serial_number=_cell_text(cells[0]),
                    assignment_title=_cell_text(cells[1]),
                    max_assignment_mark=_cell_text(cells[2]),
                    assignment_weightage_mark=_cell_text(cells[3]),
                    due_date=_cell_text(cells[4]),
                    can_qp_download=can_qp_download,
                    qp_download_url=qp_download_url,
                    submission_status=submission_status,
                    can_update=can_update,
                    mcode=mcode,
                    can_da_download=can_da_download,
                    da_download_url=da_download_url,
                )
            )

        return records

    except Exception as e:
        raise VtopParsingError(
            f"Failed to parse per course digital assignments: {e}"
        ) from e


def parse_process_upload_assignment_response(html: str) -> tuple[list[str], list[str]]:
    """
    Reads the hidden code and opt pairs required to authorise an upload.

    Args:
        html (str): The raw HTML of the upload preparation response.

    Returns:
        tuple[list[str], list[str]]: The code values and the opt values.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        codes: list[str] = []
        opts: list[str] = []

        for element in soup.find_all("input"):
            name = element.get("name")
            if name == "code":
                codes.append(element.get("value") or "")
            elif name == "opt":
                opts.append(element.get("value") or "")

        return codes, opts

    except Exception as e:
        raise VtopParsingError(
            f"Failed to parse the assignment upload preparation response: {e}"
        ) from e


def parse_upload_assignment_response(html: str) -> str:
    """
    Interprets the response returned after submitting an assignment file.

    VTOP does not use status codes here, so the outcome has to be read from
    the rendered spans. When the first span is the student's email address the
    upload has been held for OTP confirmation.

    Args:
        html (str): The raw HTML of the upload response.

    Returns:
        str: "Uploaded successfully", "OTP Required", an error message from
            VTOP, or a fallback description.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        spans = [span.get_text(strip=True) for span in soup.find_all("span")]

        if not spans:
            return "Failed - Unknown Error"

        if spans[0] == "Uploaded successfully":
            return spans[0]

        if spans[0].endswith("@vitapstudent.ac.in"):
            # The OTP page echoes the address the code was sent to.
            if len(spans) > 2 and not spans[1] and not spans[2]:
                return "OTP Required"
            if len(spans) > 2 and spans[2] == "Invalid OTP. Please try again.":
                return spans[2]
            return "Unknown error from OTP page try re-uploading."

        if len(spans) > 1:
            return spans[1]

        return "Failed - Unknown Error"

    except Exception as e:
        raise VtopParsingError(
            f"Failed to parse the assignment upload response: {e}"
        ) from e
