from bs4 import BeautifulSoup

from vitap_vtop_client.exceptions import VtopParsingError
from vitap_vtop_client.grade_history.model import (
    GradeCourseHistoryModel,
    GradeHistoryModel,
)

# Column positions in the per course grade table.
_COURSE_CODE_COL = 1
_COURSE_TITLE_COL = 2
_COURSE_TYPE_COL = 3
_CREDITS_COL = 4
_GRADE_COL = 5
_EXAM_MONTH_COL = 6
_COURSE_DISTRIBUTION_COL = 8
_MIN_COLUMNS = 10


def _parse_summary(soup) -> dict[str, str]:
    """Reads credits registered, credits earned and CGPA from the summary table."""
    summary = {
        "credits_registered": "N/A",
        "credits_earned": "N/A",
        "cgpa": "N/A",
    }

    # There can be several tables sharing this class, so pick the one that
    # actually carries the CGPA summary.
    for table in soup.find_all("table", class_="table table-hover table-bordered"):
        if "CGPA" not in table.get_text():
            continue

        tbody = table.find("tbody")
        if tbody is None:
            continue

        row = tbody.find("tr")
        if row is None:
            continue

        columns = row.find_all("td")
        if len(columns) < 3:
            continue

        summary["credits_registered"] = columns[0].get_text(strip=True)
        summary["credits_earned"] = columns[1].get_text(strip=True)
        summary["cgpa"] = columns[2].get_text(strip=True)
        break

    return summary


def _parse_courses(soup) -> list[GradeCourseHistoryModel]:
    """Reads every graded course from the course history tables."""
    courses: list[GradeCourseHistoryModel] = []

    for table in soup.find_all("table", class_="customTable"):
        if "Course Code" not in table.get_text():
            continue

        for row in table.find_all("tr", class_="tableContent"):
            columns = row.find_all("td")
            if len(columns) < _MIN_COLUMNS:
                continue

            course_code = columns[_COURSE_CODE_COL].get_text(strip=True)
            # Skip repeated header rows and blank entries.
            if not course_code or course_code == "Course Code":
                continue

            courses.append(
                GradeCourseHistoryModel(
                    course_code=course_code,
                    course_title=columns[_COURSE_TITLE_COL].get_text(strip=True),
                    course_type=columns[_COURSE_TYPE_COL].get_text(strip=True),
                    credits=columns[_CREDITS_COL].get_text(strip=True),
                    grade=columns[_GRADE_COL].get_text(strip=True),
                    exam_month=columns[_EXAM_MONTH_COL].get_text(strip=True),
                    course_distribution=columns[
                        _COURSE_DISTRIBUTION_COL
                    ].get_text(strip=True),
                )
            )

    return courses


def parse_grade_history(html: str) -> GradeHistoryModel:
    """
    Parses the grade history page into the CGPA summary and per course grades.

    Args:
        html (str): The raw HTML string of the grade history page.

    Returns:
        GradeHistoryModel: The summary totals and every graded course.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        return GradeHistoryModel(
            **_parse_summary(soup),
            courses=_parse_courses(soup),
        )

    except Exception as e:
        print(f"Error parsing grade history: {str(e)}")
        raise VtopParsingError(
            f"An error occured while parsing grade history: {e}"
        ) from e
