from typing import List

from pydantic import BaseModel


class ClassGroupModel(BaseModel):
    """A class group option, e.g. `COMB` "All Class Group (Combined)"."""

    id: str
    name: str


class CalendarMonthRefModel(BaseModel):
    """A month button on the calendar page."""

    # What VTOP shows on the button, e.g. "AUG-2026".
    label: str
    # What processViewCalendar expects, e.g. "01-AUG-2026".
    cal_date: str


class CalendarEventModel(BaseModel):
    """One entry on a calendar day."""

    # e.g. "Instructional Day - General (Semester)"
    description: str
    # The parenthesised qualifier, with the brackets stripped: "WorkingDay",
    # "Exam Days", "Holiday", or a named holiday like "Independence Day".
    label: str = ""


class CalendarDayModel(BaseModel):
    """A single dated day of the academic calendar."""

    # ISO `YYYY-MM-DD`, derived from the month being viewed.
    date: str
    day: int
    # "Sunday" ... "Saturday", taken from the column the day sits in.
    weekday: str
    events: List[CalendarEventModel] = []


class AcademicCalendarModel(BaseModel):
    """
    A semester's academic calendar, flattened.

    VTOP renders each month as a week grid, but the grid is a display concern:
    the days are returned here as one date-ordered list so callers can look up a
    date, filter holidays, or lay out their own view.
    """

    semester_id: str
    class_group_id: str
    months: List[CalendarMonthRefModel] = []
    days: List[CalendarDayModel] = []
