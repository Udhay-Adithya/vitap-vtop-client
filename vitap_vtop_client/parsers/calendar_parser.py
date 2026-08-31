import re

from bs4 import BeautifulSoup

from vitap_vtop_client.academic_calendar.model.calendar_model import (
    CalendarDayModel,
    CalendarEventModel,
    CalendarMonthRefModel,
    ClassGroupModel,
)
from vitap_vtop_client.exceptions.exception import VtopParsingError

# Month buttons call processViewCalendar('01-AUG-2026'). VTOP HTML-escapes the
# quotes, so the raw markup carries &#39; rather than '.
_CAL_DATE_RE = re.compile(r"processViewCalendar\(\s*'([^']+)'\s*\)")

# VTOP writes months as the three letter English abbreviation.
_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _clean(node) -> str:
    return " ".join(node.get_text().split())


def _is_placeholder(value: str, label: str) -> bool:
    return not value or label.startswith("--")


def parse_class_groups(html: str) -> list[ClassGroupModel]:
    """
    Reads the class group options.

    The class groups depend on the semester, so VTOP returns this select from
    `getDateForSemesterPreview` once a semester is chosen rather than rendering
    it up front.

    Args:
        html (str): The HTML returned by getDateForSemesterPreview.

    Returns:
        list[ClassGroupModel]: The selectable class groups.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        groups: list[ClassGroupModel] = []

        options = soup.select("select#classGroupId option, select[name='classGroupId'] option")
        for option in options:
            value = (option.get("value") or "").strip()
            label = option.get_text(strip=True)
            if _is_placeholder(value, label):
                continue
            groups.append(ClassGroupModel(id=value, name=label))

        return groups

    except Exception as e:
        raise VtopParsingError(f"Failed to parse calendar class groups: {e}") from e


def parse_calendar_months(html: str) -> list[CalendarMonthRefModel]:
    """
    Reads the month buttons for a semester.

    Each button is an anchor whose onclick carries the `calDate` that
    `processViewCalendar` expects — the label ("AUG-2026") and that value
    ("01-AUG-2026") differ, so both are kept.

    Args:
        html (str): The HTML from getDateForSemesterPreview or
            getListForSemester, both of which render these buttons.

    Returns:
        list[CalendarMonthRefModel]: One entry per month, in VTOP's order.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        months: list[CalendarMonthRefModel] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a"):
            match = _CAL_DATE_RE.search(anchor.get("onclick") or "")
            if match is None:
                continue
            cal_date = match.group(1).strip()
            if cal_date in seen:
                continue
            seen.add(cal_date)
            months.append(
                CalendarMonthRefModel(
                    label=anchor.get_text(strip=True) or cal_date,
                    cal_date=cal_date,
                )
            )

        return months

    except Exception as e:
        raise VtopParsingError(f"Failed to parse calendar months: {e}") from e


def _parse_events(cell) -> list[CalendarEventModel]:
    """
    Reads the entries in one day cell.

    A day renders as `<span>5</span><span>description</span><span>(label)</span>`.
    The parenthesised span qualifies the one before it, so lines are folded into
    events that way — which also tolerates a day carrying more than one entry.
    """
    lines = [_clean(span) for span in cell.find_all("span")][1:]
    events: list[CalendarEventModel] = []

    for line in lines:
        if not line:
            continue
        if line.startswith("(") and line.endswith(")") and events:
            events[-1].label = line[1:-1].strip()
            continue
        events.append(CalendarEventModel(description=line))

    return events


def parse_calendar_month(html: str, cal_date: str) -> list[CalendarDayModel]:
    """
    Parses one month's grid into dated days.

    VTOP lays the month out as a Sunday-to-Saturday week grid padded with blank
    cells. The grid is a display concern, so this returns a flat, date-ordered
    list instead; the weekday comes from the column each day sits in, and the
    month and year from `cal_date`.

    Args:
        html (str): The HTML returned by processViewCalendar.
        cal_date (str): The month that was requested, e.g. "01-AUG-2026".

    Returns:
        list[CalendarDayModel]: The month's days, in date order.

    Raises:
        VtopParsingError: If parsing fails or `cal_date` is not understood.
    """
    try:
        parts = cal_date.split("-")
        if len(parts) != 3 or parts[1].upper() not in _MONTHS:
            raise ValueError(f"unrecognised calDate {cal_date!r}")
        month = _MONTHS[parts[1].upper()]
        year = int(parts[2])

        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", class_="calendar-table") or soup.find("table")
        if table is None:
            return []

        rows = table.find_all("tr")
        if not rows:
            return []

        weekdays = [_clean(cell) for cell in rows[0].find_all(["th", "td"])]
        days: list[CalendarDayModel] = []

        for row in rows[1:]:
            for index, cell in enumerate(row.find_all("td")):
                spans = cell.find_all("span")
                if not spans:
                    continue
                number = _clean(spans[0])
                # Blank cells pad the start and end of the grid.
                if not number.isdigit():
                    continue

                day = int(number)
                days.append(
                    CalendarDayModel(
                        date=f"{year:04d}-{month:02d}-{day:02d}",
                        day=day,
                        weekday=weekdays[index] if index < len(weekdays) else "",
                        events=_parse_events(cell),
                    )
                )

        days.sort(key=lambda d: d.day)
        return days

    except Exception as e:
        raise VtopParsingError(f"Failed to parse the calendar month: {e}") from e
