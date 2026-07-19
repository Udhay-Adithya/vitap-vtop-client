from .course_page import (
    init_course_page,
    fetch_courses_for_course_page,
    fetch_slots_for_course_page,
    fetch_course_detail,
    download_course_material,
    download_course_plan_excel,
)
from .model.course_page_model import (
    CourseOptionModel,
    SlotOptionModel,
    CourseClassEntryModel,
    ReferenceMaterialModel,
    LectureEntryModel,
    CourseInfoModel,
    CoursePageDetailModel,
    CoursesResponseModel,
    SlotsResponseModel,
)
