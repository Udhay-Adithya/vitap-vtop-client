from pydantic import BaseModel
from typing import Optional

from vitap_vtop_client.grade_history import GradeHistoryModel
from vitap_vtop_client.mentor import MentorModel


class StudentProfileModel(BaseModel):
    # Every field carries a default. In pydantic v2 `Optional[str]` without one
    # is required-but-nullable, so a field VTOP simply did not render made the
    # whole model fail to construct rather than coming back as None.
    # VTOP's profile page does not expose the registration number; the client
    # fills it in from the `authorizedIDX` value captured during login.
    registration_number: Optional[str] = None
    application_number: Optional[str] = None
    student_name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    email: Optional[str] = None
    base64_pfp: Optional[str] = None
    grade_history: Optional[GradeHistoryModel] = None
    mentor_details: Optional[MentorModel] = None
