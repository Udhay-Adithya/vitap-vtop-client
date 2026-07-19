import re

from bs4 import BeautifulSoup

from vitap_vtop_client.attendance.model.attendance_model import (
    AttendanceDetailModel,
    AttendanceModel,
)
from vitap_vtop_client.exceptions.exception import VtopParsingError

# Pulls the course id and course type code out of the detail link on each row,
# e.g. callStudentAttendanceDetailDisplay('AP2025264','23BCEXXXX','AM_CSE1008_00200','TH')
_DETAIL_ONCLICK_RE = re.compile(
    r"callStudentAttendanceDetailDisplay\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*\)"
)


def _cell_text(cell) -> str:
    return cell.get_text(strip=True).replace("\t", "").replace("\n", "")


def parse_attendance(html: str) -> list[AttendanceModel]:
    """
    Parses the attendance table into one record per registered course.

    Args:
        html (str): The raw HTML string containing the attendance table.

    Returns:
        list[AttendanceModel]: One entry per course.

    Raises:
        VtopParsingError: When the attendance data cannot be parsed.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        data_list: list[AttendanceModel] = []

        for row in soup.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) <= 9:
                continue

            # The detail link carries the real course id. It sits in the last
            # cell, or cell 10 when the full column set is present.
            info_cell_index = 10 if len(cells) >= 11 else len(cells) - 1
            match = _DETAIL_ONCLICK_RE.search(str(cells[info_cell_index]))
            course_id = match.group(1) if match else ""
            course_type_code = match.group(2) if match else ""

            # "MAT1001 - Calculus for Engineers - Embedded Lab"
            course_parts = _cell_text(cells[2]).split(" - ")
            course_code = course_parts[0] if course_parts else ""
            course_name = course_parts[1] if len(course_parts) > 1 else ""
            course_type = course_parts[-1] if course_parts else ""

            # "AP2024258000131 - L27+L28+L39+L40 - 119"
            class_parts = _cell_text(cells[3]).split(" - ")
            class_number = class_parts[0] if class_parts else ""
            course_slot = class_parts[1] if len(class_parts) > 1 else ""

            # VTOP dropped the "attendance between" column on some views, which
            # shifts debar status left by one.
            has_between_column = len(cells) > 11
            attendance_between_percentage = (
                _cell_text(cells[8]).rstrip("%") if has_between_column else "0"
            )
            debar_status = (
                _cell_text(cells[9]) if has_between_column else _cell_text(cells[8])
            )

            data_list.append(
                AttendanceModel(
                    class_number=class_number,
                    course_code=course_code,
                    course_name=course_name,
                    course_type=course_type,
                    course_type_code=course_type_code,
                    course_slot=course_slot,
                    faculty=_cell_text(cells[4]),
                    attended_classes=_cell_text(cells[5]),
                    total_classes=_cell_text(cells[6]),
                    attendance_percentage=_cell_text(cells[7]).rstrip("%"),
                    attendance_between_percentage=attendance_between_percentage,
                    debar_status=debar_status,
                    course_id=course_id,
                )
            )

        return data_list

    except Exception as e:
        raise VtopParsingError(f"Failed to parse attendance data: {e}") from e


def parse_full_attendance(html: str) -> list[AttendanceDetailModel]:
    """
    Parses the per class attendance detail table for a single course.

    Args:
        html (str): The raw HTML string containing the attendance detail table.

    Returns:
        list[AttendanceDetailModel]: One entry per class held.

    Raises:
        VtopParsingError: When the attendance detail cannot be parsed.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        records: list[AttendanceDetailModel] = []

        table = soup.find(id="StudentAttendanceDetailDataTable")
        if table is None:
            return records

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            records.append(
                AttendanceDetailModel(
                    serial=_cell_text(cells[0]),
                    date=_cell_text(cells[1]),
                    slot=_cell_text(cells[2]),
                    day_time=_cell_text(cells[3]),
                    status=_cell_text(cells[4]),
                    remark=_cell_text(cells[5]),
                )
            )

        return records

    except Exception as e:
        raise VtopParsingError(f"Failed to parse attendance detail data: {e}") from e
