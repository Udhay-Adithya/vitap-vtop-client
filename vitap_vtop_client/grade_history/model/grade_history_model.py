from typing import List

from pydantic import BaseModel


class GradeCourseHistoryModel(BaseModel):
    course_code: str
    course_title: str
    course_type: str
    credits: str
    grade: str
    exam_month: str
    course_distribution: str


class GradeHistoryModel(BaseModel):
    credits_registered: str = "N/A"
    credits_earned: str = "N/A"
    cgpa: str = "N/A"
    courses: List[GradeCourseHistoryModel] = []
