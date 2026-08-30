from typing import List

from pydantic import BaseModel


class CapstoneInfoModel(BaseModel):
    """The registration details shown above the capstone attendance summary."""

    title: str = ""
    guide_evaluation_status: str = ""
    date_of_registration: str = ""


class CapstoneSummaryModel(BaseModel):
    """The present / on-duty / absent tally for the capstone."""

    present: str = ""
    on_duty: str = ""
    absent: str = ""
    # The "%" sign is stripped, matching AttendanceModel.attendance_percentage.
    percentage: str = ""


class CapstonePunchModel(BaseModel):
    """One day in the capstone attendance calendar."""

    serial: str
    date: str
    day: str
    # Free text from VTOP: "Instructional", "Holiday", "No Instructional",
    # "CAT1", ... Deliberately not an enum, since VTOP adds day types.
    day_type: str
    # "Present", "Absent" or "On Duty". Empty for days with no status at all
    # (holidays, non-instructional days, days not yet reached), which VTOP
    # renders as "-".
    status: str = ""
    # Empty when there was no punch, which VTOP also renders as "-".
    punch_time: str = ""


class CapstoneAttendanceModel(BaseModel):
    """
    Capstone/SDP attendance for one semester.

    Unlike course attendance this is not per-course, so it does not fit
    `AttendanceModel`: there is no course code, faculty or slot, and the tally
    is present/on-duty/absent rather than attended/total. VTOP returns the
    summary and the day-by-day calendar in a single response, so both are here.
    """

    info: CapstoneInfoModel = CapstoneInfoModel()
    summary: CapstoneSummaryModel = CapstoneSummaryModel()
    punches: List[CapstonePunchModel] = []
