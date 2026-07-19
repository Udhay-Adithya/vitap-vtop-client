from typing import List

from pydantic import BaseModel


class FacultyModel(BaseModel):
    """A single row from the faculty search results."""

    faculty_name: str = ""
    designation: str = ""
    school_or_centre: str = ""
    emp_id: str = ""


class OfficeHourModel(BaseModel):
    day: str
    timings: str


class FacultyDetailsModel(BaseModel):
    """The full profile for one faculty member."""

    name: str = ""
    designation: str = ""
    department: str = ""
    school_centre: str = ""
    email: str = ""
    cabin_number: str = ""
    office_hours: List[OfficeHourModel] = []
