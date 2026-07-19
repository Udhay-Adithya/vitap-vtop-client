from typing import List, Optional

from pydantic import BaseModel


class CourseOptionModel(BaseModel):
    """A course from the course page dropdown."""

    value: str
    label: str
    course_code: str = ""
    course_title: str = ""
    course_type: str = ""


class SlotOptionModel(BaseModel):
    """A slot from the slot dropdown."""

    value: str
    label: str


class CourseClassEntryModel(BaseModel):
    """A class row from the course slots table."""

    sl_no: int
    class_group: str = ""
    course_code: str = ""
    course_title: str = ""
    course_type: str = ""
    class_id: str = ""
    slot: str = ""
    faculty: str = ""
    semester_id: str = ""
    # Needed alongside class_id to open the course detail page.
    erp_id: str = ""


class ReferenceMaterialModel(BaseModel):
    """A file attached to a lecture."""

    label: str
    download_path: str


class LectureEntryModel(BaseModel):
    """A lecture row from the course detail page."""

    sl_no: int
    date: str = ""
    formatted_date: str = ""
    day: str = ""
    topic: str = ""
    reference_materials: List[ReferenceMaterialModel] = []


class CourseInfoModel(BaseModel):
    """The course summary shown at the top of the detail page."""

    class_group: str = ""
    course_code: str = ""
    course_title: str = ""
    course_type: str = ""
    class_id: str = ""
    slot: str = ""
    faculty: str = ""
    course_id: str = ""


class CoursePageDetailModel(BaseModel):
    """A course's detail page, with its lectures and downloadable material."""

    course_info: CourseInfoModel = CourseInfoModel()
    semester_id: str = ""
    download_all_path: Optional[str] = None
    download_general_materials_path: Optional[str] = None
    syllabus_download_path: Optional[str] = None
    course_plan_download_path: Optional[str] = None
    lectures: List[LectureEntryModel] = []


class CoursesResponseModel(BaseModel):
    courses: List[CourseOptionModel] = []


class SlotsResponseModel(BaseModel):
    slots: List[SlotOptionModel] = []
    class_entries: List[CourseClassEntryModel] = []
