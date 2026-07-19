from typing import List

from pydantic import BaseModel


class AssignmentRecordModel(BaseModel):
    """A single assignment within a course."""

    serial_number: str
    assignment_title: str
    max_assignment_mark: str
    assignment_weightage_mark: str
    due_date: str
    # Question paper download, when the faculty attached one.
    can_qp_download: bool = False
    qp_download_url: str = ""
    submission_status: str = ""
    # Whether the submission can still be replaced, and the code needed to do so.
    can_update: bool = False
    mcode: str = ""
    # Download of the student's own submitted file.
    can_da_download: bool = False
    da_download_url: str = ""


class DigitalAssignmentModel(BaseModel):
    """One registered course and its assignments."""

    serial_number: str
    class_id: str
    course_code: str
    course_title: str
    course_type: str
    faculty: str
    details: List[AssignmentRecordModel] = []
