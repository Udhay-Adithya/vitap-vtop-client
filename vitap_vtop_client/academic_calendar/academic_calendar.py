import time
from datetime import datetime, timezone

import httpx

from vitap_vtop_client.academic_calendar.model.calendar_model import (
    AcademicCalendarModel,
    CalendarDayModel,
    CalendarMonthRefModel,
    ClassGroupModel,
)
from vitap_vtop_client.constants import (
    CALENDAR_CLASS_GROUPS_URL,
    CALENDAR_MONTHS_URL,
    CALENDAR_PREVIEW_URL,
    HEADERS,
    VIEW_CALENDAR_URL,
)
from vitap_vtop_client.exceptions.exception import (
    VtopCalendarError,
    VtopConnectionError,
    VtopParsingError,
)
from vitap_vtop_client.parsers import calendar_parser

# The calendar's lookups are AJAX, matching what the page's own JS sends.
_AJAX_HEADERS = {
    **HEADERS,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

# The default class group: "All Class Group (Combined)".
DEFAULT_CLASS_GROUP = "COMB"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


async def _post(
    client: httpx.AsyncClient,
    url: str,
    username: str,
    csrf_token: str,
    extra: dict,
) -> httpx.Response:
    body = {
        "_csrf": csrf_token,
        "authorizedID": username,
        "x": _timestamp(),
        **extra,
    }
    response = await client.post(url, data=body, headers=_AJAX_HEADERS)
    response.raise_for_status()
    return response


async def init_calendar_page(
    client: httpx.AsyncClient, username: str, csrf_token: str
) -> str:
    """
    Opens the academic calendar page.

    Unlike the course page, VTOP does **not** require this before the calendar
    lookups work — verified against a fresh session. It is kept because the page
    carries the semester dropdown, and for parity with how the portal itself
    navigates.

    Returns:
        str: The calendar page markup, including the semester dropdown.
    """
    try:
        response = await client.post(
            CALENDAR_PREVIEW_URL,
            data={
                "verifyMenu": "true",
                "authorizedID": username,
                "_csrf": csrf_token,
                "nocache": int(round(time.time() * 1000)),
            },
            headers=HEADERS,
        )
        response.raise_for_status()
        return response.text

    except httpx.RequestError as e:
        raise VtopConnectionError(
            f"Failed to open the academic calendar: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        raise VtopCalendarError(f"Failed to open the academic calendar: {e}") from e


async def fetch_calendar_class_groups(
    client: httpx.AsyncClient, username: str, csrf_token: str, semSubID: str
) -> list[ClassGroupModel]:
    """
    Fetches the class groups available for a semester.

    Class groups are semester dependent, so VTOP only renders them once a
    semester is chosen.

    Returns:
        list[ClassGroupModel]: The selectable class groups.
    """
    try:
        response = await _post(
            client,
            CALENDAR_CLASS_GROUPS_URL,
            username,
            csrf_token,
            {"paramReturnId": "getDateForSemesterPreview", "semSubId": semSubID},
        )
        return calendar_parser.parse_class_groups(response.text)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        raise VtopConnectionError(
            f"Failed to fetch calendar class groups: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        raise VtopCalendarError(
            f"Failed to fetch calendar class groups for {semSubID}: {e}"
        ) from e


async def fetch_calendar_months(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
    classGroupID: str = DEFAULT_CLASS_GROUP,
) -> list[CalendarMonthRefModel]:
    """
    Fetches the months the calendar covers for a semester and class group.

    Returns:
        list[CalendarMonthRefModel]: One entry per month, each carrying the
            `cal_date` that `fetch_calendar_month` expects.
    """
    try:
        response = await _post(
            client,
            CALENDAR_MONTHS_URL,
            username,
            csrf_token,
            {
                "paramReturnId": "getListForSemester",
                "semSubId": semSubID,
                "classGroupId": classGroupID,
            },
        )
        return calendar_parser.parse_calendar_months(response.text)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        raise VtopConnectionError(
            f"Failed to fetch calendar months: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        raise VtopCalendarError(
            f"Failed to fetch calendar months for {semSubID}: {e}"
        ) from e


async def fetch_calendar_month(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
    cal_date: str,
    classGroupID: str = DEFAULT_CLASS_GROUP,
) -> list[CalendarDayModel]:
    """
    Fetches one month of the calendar.

    Args:
        cal_date (str): The month to view, from
            `CalendarMonthRefModel.cal_date` — e.g. "01-AUG-2026".

    Returns:
        list[CalendarDayModel]: The month's days, in date order.
    """
    try:
        response = await _post(
            client,
            VIEW_CALENDAR_URL,
            username,
            csrf_token,
            {
                "calDate": cal_date,
                "semSubId": semSubID,
                "classGroupId": classGroupID,
            },
        )
        return calendar_parser.parse_calendar_month(response.text, cal_date)

    except VtopParsingError:
        raise
    except httpx.RequestError as e:
        raise VtopConnectionError(
            f"Failed to fetch the calendar month: {e}",
            original_exception=e,
            status_code=502,
        )
    except Exception as e:
        raise VtopCalendarError(
            f"Failed to fetch the calendar for {cal_date}: {e}"
        ) from e


async def fetch_academic_calendar(
    client: httpx.AsyncClient,
    username: str,
    csrf_token: str,
    semSubID: str,
    classGroupID: str = DEFAULT_CLASS_GROUP,
) -> AcademicCalendarModel:
    """
    Fetches a semester's whole academic calendar.

    Convenience over the step by step calls: reads the month list, then fetches
    every month and flattens them into one date-ordered list of days. That is
    one request per month — six for a typical semester — so prefer
    `fetch_calendar_month` when only one month is needed.

    Returns:
        AcademicCalendarModel: The months and every dated day.
    """
    months = await fetch_calendar_months(
        client, username, csrf_token, semSubID, classGroupID
    )

    days: list[CalendarDayModel] = []
    for month in months:
        days.extend(
            await fetch_calendar_month(
                client, username, csrf_token, semSubID, month.cal_date, classGroupID
            )
        )

    days.sort(key=lambda day: day.date)
    return AcademicCalendarModel(
        semester_id=semSubID,
        class_group_id=classGroupID,
        months=months,
        days=days,
    )
