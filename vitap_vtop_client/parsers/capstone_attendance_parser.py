from bs4 import BeautifulSoup

from vitap_vtop_client.attendance.model.capstone_model import (
    CapstoneAttendanceModel,
    CapstoneInfoModel,
    CapstonePunchModel,
    CapstoneSummaryModel,
)
from vitap_vtop_client.exceptions.exception import VtopParsingError

# VTOP renders "nothing here" as a dash: no status on a holiday, no punch on an
# absent day. Normalised to an empty string so callers can just check falsiness.
_PLACEHOLDER = "-"

# Labels in the info table, mapped to model fields. Matched case-insensitively
# on a prefix so minor wording changes ("E-Mail ID" style) do not drop a field.
_INFO_LABELS = {
    "title": "title",
    "guide evaluation status": "guide_evaluation_status",
    "date of registration": "date_of_registration",
}


def _clean(node) -> str:
    """Collapses VTOP's heavy tab/newline padding inside a cell."""
    return " ".join(node.get_text().split())


def _value(text: str) -> str:
    return "" if text == _PLACEHOLDER else text


def _header_index(row) -> dict[str, int]:
    """Maps lower-cased header labels to their column positions."""
    cells = row.find_all(["td", "th"])
    return {_clean(cell).lower(): i for i, cell in enumerate(cells)}


def _parse_info(soup) -> CapstoneInfoModel:
    """
    Reads the label/value table above the summary.

    Rows are `<th>label</th><td>value</td>`, so this matches on the label rather
    than a row position. A commented-out Thymeleaf copy of this table sits above
    the real one in the response; BeautifulSoup keeps comments out of the parsed
    tree, so it cannot be picked up by mistake.
    """
    info = CapstoneInfoModel()

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            header = row.find("th")
            value = row.find("td")
            if header is None or value is None:
                continue
            label = _clean(header).lower()
            for known, field in _INFO_LABELS.items():
                if label.startswith(known):
                    setattr(info, field, _value(_clean(value)))
                    break

    return info


def _parse_summary(soup) -> CapstoneSummaryModel | None:
    """
    Reads the present / on-duty / absent tally.

    Columns are located by header label, not index — the response carries a
    commented-out column elsewhere, and VTOP has reordered tables before.
    Returns None when the summary table is absent, which is how a student
    without a capstone is detected.
    """
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        headers = _header_index(rows[0])
        if "present" not in headers or "absent" not in headers:
            continue

        # The first row after the header carries the tally.
        for row in rows[1:]:
            cells = row.find_all("td")
            if not cells:
                continue

            def at(*names: str) -> str:
                for name in names:
                    index = headers.get(name)
                    if index is not None and index < len(cells):
                        return _value(_clean(cells[index]))
                return ""

            return CapstoneSummaryModel(
                present=at("present"),
                on_duty=at("on duty (od)", "on duty", "od"),
                absent=at("absent"),
                percentage=at("percentage").rstrip("%"),
            )

    return None


def _parse_punches(soup) -> list[CapstonePunchModel]:
    """
    Reads the day-by-day calendar.

    The table has a stable id. Its "Description" column is commented out in both
    the header and every row, so columns are read by header label to stay
    correct if VTOP ever re-enables it.
    """
    table = soup.find(id="sdpCalendarTable")
    if table is None:
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    headers = _header_index(rows[0])
    punches: list[CapstonePunchModel] = []

    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue

        def at(*names: str) -> str:
            for name in names:
                index = headers.get(name)
                if index is not None and index < len(cells):
                    return _value(_clean(cells[index]))
            return ""

        serial = at("sl.no.", "sl.no", "s.no")
        # Real rows lead with a numeric serial; anything else is a header or
        # spacer row.
        if not serial.isdigit():
            continue

        punches.append(
            CapstonePunchModel(
                serial=serial,
                date=at("date"),
                day=at("day"),
                day_type=at("day type"),
                status=at("status"),
                punch_time=at("punch time"),
            )
        )

    return punches


def parse_capstone_attendance(html: str) -> CapstoneAttendanceModel | None:
    """
    Parses the capstone/SDP attendance fragment.

    VTOP returns this from `processSdpAttendance` as a modal fragment holding
    three tables: the registration info, the attendance tally, and a day-by-day
    punch calendar.

    Args:
        html (str): The raw HTML returned by the endpoint.

    Returns:
        CapstoneAttendanceModel | None: The parsed attendance, or None when the
            response carries no summary — which is what a student with no
            capstone registration gets.

    Raises:
        VtopParsingError: If the fragment is present but cannot be parsed.
    """
    try:
        soup = BeautifulSoup(html, "lxml")

        summary = _parse_summary(soup)
        if summary is None:
            return None

        return CapstoneAttendanceModel(
            info=_parse_info(soup),
            summary=summary,
            punches=_parse_punches(soup),
        )

    except Exception as e:
        raise VtopParsingError(f"Failed to parse capstone attendance: {e}") from e
