from typing import List

from pydantic import BaseModel


class GradeViewCourse(BaseModel):
    """One course row from the grade view for a semester."""

    serial_number: str
    course_code: str
    course_title: str
    course_type: str
    grading_type: str
    grand_total: str
    grade: str
    # Needed to request the per-course detail.
    course_id: str = ""


class MarkComponent(BaseModel):
    """One assessment component of a course (CAT1, FAT, a quiz, ...)."""

    serial_number: str
    mark_title: str
    max_mark: str
    weightage: str
    status: str
    scored_mark: str
    weightage_mark: str


class GradeRange(BaseModel):
    """The mark range that maps to one letter grade for the class."""

    grade: str
    range: str


class GradeStatistics(BaseModel):
    """Class-level statistics shown alongside a course's grade."""

    class_strength: str = ""
    grading_strength: str = ""
    mean: str = ""
    sd: str = ""
    grade_ranges: List[GradeRange] = []


class GradeViewDetail(BaseModel):
    """The expanded detail for a single course in the grade view."""

    class_number: str = ""
    course_type: str = ""
    marks: List[MarkComponent] = []
    total: str = ""
    statistics: GradeStatistics = GradeStatistics()
