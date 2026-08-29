from pydantic import BaseModel
from typing import Optional

from vitap_vtop_client.grade_history import GradeHistoryModel
from vitap_vtop_client.mentor import MentorModel


class StudentProfileModel(BaseModel):
    # VTOP's profile page does not expose the registration number; the client
    # fills it in from the `authorizedIDX` value captured during login.
    registration_number: Optional[str] = None
    application_number: Optional[str]
    student_name: Optional[str]
    dob: Optional[str]
    gender: Optional[str]
    blood_group: Optional[str]
    email: Optional[str]
    base64_pfp: Optional[str]
    grade_history: Optional[GradeHistoryModel]
    mentor_details: Optional[MentorModel]
