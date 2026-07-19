from bs4 import BeautifulSoup

from vitap_vtop_client.course_page.model.course_page_model import (
    CourseClassEntryModel,
    CourseInfoModel,
    CourseOptionModel,
    CoursePageDetailModel,
    CoursesResponseModel,
    LectureEntryModel,
    ReferenceMaterialModel,
    SlotOptionModel,
    SlotsResponseModel,
)
from vitap_vtop_client.exceptions.exception import VtopParsingError


def _text(node) -> str:
    return node.get_text(strip=True) if node is not None else ""


def _is_placeholder(value: str, label: str) -> bool:
    """Dropdowns lead with a '-- Select --' style prompt carrying no value."""
    return not value or label.startswith("--")


def _extract_path_from_vtop_download(attr: str) -> str:
    """
    Pulls the path out of a vtopDownload('...') call.

    The attribute may arrive with single quotes HTML escaped.
    """
    cleaned = (attr or "").replace("&#39;", "'")
    marker = cleaned.find("vtopDownload(")
    if marker == -1:
        return ""

    start = cleaned.find("'", marker)
    if start == -1:
        return ""
    end = cleaned.find("'", start + 1)
    if end == -1:
        return ""

    return cleaned[start + 1 : end]


def _parse_erp_id_from_onclick(onclick: str) -> str:
    """
    Reads the ERP id from the course detail handler.

    Format: processViewStudentCourseDetail('AP2025264','70735','AP2025264000442')
    """
    cleaned = (onclick or "").replace("&#39;", "'")
    if "processViewStudentCourseDetail" not in cleaned:
        return ""

    start = cleaned.find("(")
    end = cleaned.rfind(")")
    if start == -1 or end == -1 or end <= start:
        return ""

    parts = cleaned[start + 1 : end].split(",")
    if len(parts) < 2:
        return ""

    return parts[1].strip().strip("'").strip("&").strip("#").strip(";")


def _to_int(value: str) -> int:
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return 0


def parse_courses_for_course_page(html: str) -> CoursesResponseModel:
    """
    Parses the course dropdown from the course page.

    Args:
        html (str): The raw HTML of the course dropdown response.

    Returns:
        CoursesResponseModel: The selectable courses.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        courses: list[CourseOptionModel] = []

        options = soup.select("select#courseCode option, select[name='courseCode'] option")
        if not options:
            options = soup.find_all("option")

        for option in options:
            value = (option.get("value") or "").strip()
            label = option.get_text(strip=True)
            if _is_placeholder(value, label):
                continue

            # "CSE2009 - Soft Computing - ETH"; the title itself may contain
            # " - ", so only the first and last segments are fixed.
            parts = label.split(" - ")
            if len(parts) >= 3:
                course_code = parts[0].strip()
                course_title = " - ".join(parts[1:-1]).strip()
                course_type = parts[-1].strip()
            elif len(parts) == 2:
                course_code, course_title, course_type = (
                    parts[0].strip(),
                    parts[1].strip(),
                    "",
                )
            else:
                course_code, course_title, course_type = label, "", ""

            courses.append(
                CourseOptionModel(
                    value=value,
                    label=label,
                    course_code=course_code,
                    course_title=course_title,
                    course_type=course_type,
                )
            )

        return CoursesResponseModel(courses=courses)

    except Exception as e:
        raise VtopParsingError(f"Failed to parse course page courses: {e}") from e


def parse_slots_for_course_page(html: str, semester_id: str) -> SlotsResponseModel:
    """
    Parses the slot dropdown and the class table for a course.

    Args:
        html (str): The raw HTML of the slot response.
        semester_id (str): The semester the request was made for, stamped onto
            each class entry since the response does not carry it.

    Returns:
        SlotsResponseModel: The selectable slots and the class rows.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        slots: list[SlotOptionModel] = []

        options = soup.select("select#slotId option, select[name='slotId'] option")
        if not options:
            options = soup.find_all("option")

        for option in options:
            value = (option.get("value") or "").strip()
            label = option.get_text(strip=True)
            if _is_placeholder(value, label):
                continue
            slots.append(SlotOptionModel(value=value, label=label))

        class_entries: list[CourseClassEntryModel] = []
        for table in soup.find_all("table"):
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 9:
                    continue

                sl_no = _to_int(_text(cells[0]))
                if sl_no <= 0:
                    continue

                erp_id = ""
                button = cells[8].find("button")
                if button is not None:
                    erp_id = _parse_erp_id_from_onclick(button.get("onclick") or "")

                class_entries.append(
                    CourseClassEntryModel(
                        sl_no=sl_no,
                        class_group=_text(cells[1]),
                        course_code=_text(cells[2]),
                        course_title=_text(cells[3]),
                        course_type=_text(cells[4]),
                        class_id=_text(cells[5]),
                        slot=_text(cells[6]),
                        faculty=_text(cells[7]),
                        semester_id=semester_id,
                        erp_id=erp_id,
                    )
                )

        return SlotsResponseModel(slots=slots, class_entries=class_entries)

    except Exception as e:
        raise VtopParsingError(f"Failed to parse course page slots: {e}") from e


def _extract_hidden_input_value(soup, name: str) -> str:
    element = soup.find("input", attrs={"name": name}) or soup.find("input", id=name)
    return (element.get("value") or "") if element is not None else ""


def _extract_download_path(soup, pattern: str) -> str | None:
    """Finds a vtopDownload link whose target contains the given pattern."""
    for link in soup.find_all("a"):
        for attribute in (link.get("href"), link.get("onclick")):
            if not attribute or "vtopDownload" not in attribute:
                continue
            if pattern in attribute.replace("&#39;", "'"):
                path = _extract_path_from_vtop_download(attribute)
                if path:
                    return path
    return None


def _extract_course_info(soup) -> CourseInfoModel:
    info = CourseInfoModel()

    table = soup.find("table")
    if table is None:
        return info

    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue

        info.class_group = _text(cells[0])
        info.course_code = _text(cells[1])
        info.course_title = _text(cells[2])
        info.course_type = _text(cells[3])
        info.class_id = _text(cells[4])
        info.slot = _text(cells[5])
        info.faculty = _text(cells[6])
        break

    return info


def _extract_lectures(soup) -> list[LectureEntryModel]:
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        # Identify the lecture table by its headers.
        header = rows[0].get_text()
        if "Lecture Date" not in header and "Lecture Topic" not in header:
            continue

        lectures: list[LectureEntryModel] = []
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            sl_no = _to_int(_text(cells[0]))
            if sl_no <= 0:
                continue

            # The date cell holds the raw date and a bracketed display date.
            spans = cells[1].find_all("span")
            if len(spans) >= 2:
                date = _text(spans[0])
                formatted_date = _text(spans[1]).strip("[]")
            elif spans:
                date = formatted_date = _text(spans[0])
            else:
                date = formatted_date = _text(cells[1])

            materials: list[ReferenceMaterialModel] = []
            for link in cells[4].find_all("a"):
                href = link.get("href") or ""
                if "vtopDownload" not in href:
                    continue
                path = _extract_path_from_vtop_download(href)
                if path:
                    materials.append(
                        ReferenceMaterialModel(
                            label=link.get_text(strip=True), download_path=path
                        )
                    )

            lectures.append(
                LectureEntryModel(
                    sl_no=sl_no,
                    date=date,
                    formatted_date=formatted_date,
                    day=_text(cells[2]),
                    topic=_text(cells[3]),
                    reference_materials=materials,
                )
            )

        if lectures:
            return lectures

    return []


def parse_course_detail_page(html: str) -> CoursePageDetailModel:
    """
    Parses a course's detail page.

    Args:
        html (str): The raw HTML of the course detail response.

    Returns:
        CoursePageDetailModel: The course summary, lectures and download paths.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")

        course_info = _extract_course_info(soup)
        course_info.course_id = _extract_hidden_input_value(soup, "courseId")

        semester_id = _extract_hidden_input_value(soup, "semesterSubId")
        class_id = _extract_hidden_input_value(soup, "classId")

        course_plan_download_path = None
        if semester_id and class_id:
            course_plan_download_path = (
                "academics/common/CoursePlanExcelDownload"
                f"?semesterSubId={semester_id}&classId={class_id}"
            )

        return CoursePageDetailModel(
            course_info=course_info,
            semester_id=semester_id,
            download_all_path=_extract_download_path(
                soup, "allCourseMeterialDownload/1/1"
            ),
            download_general_materials_path=_extract_download_path(
                soup, "allCourseMeterialDownload/2/1"
            ),
            syllabus_download_path=_extract_download_path(
                soup, "courseSyllabusDownload"
            ),
            course_plan_download_path=course_plan_download_path,
            lectures=_extract_lectures(soup),
        )

    except Exception as e:
        raise VtopParsingError(f"Failed to parse course detail page: {e}") from e
