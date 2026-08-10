import re

from bs4 import BeautifulSoup

from vitap_vtop_client.exceptions.exception import VtopParsingError
from vitap_vtop_client.grade_view.model.grade_view_model import (
    GradeRange,
    GradeStatistics,
    GradeViewCourse,
    GradeViewDetail,
    MarkComponent,
)

# The course id sits in the "View Mark" button, e.g.
# getGradeViewDetails('AM_CSE1008_00200').
_COURSE_ID_RE = re.compile(r"getGradeViewDetails\(\s*'([^']+)'\s*\)")

_GRADE_LABELS = ("S", "A", "B", "C", "D", "E", "F")


def _clean(node) -> str:
    """Collapses the heavy tab/newline whitespace VTOP pads cells with."""
    return " ".join(node.get_text(strip=True).split())


def _find_leaf_table(soup, marker: str):
    """
    Finds the innermost table containing `marker`.

    The detail response injects the stats and marks tables inside a cell of the
    outer grade table, so a plain "table containing X" search matches the
    wrapper. Restricting to leaf tables (no nested table) selects the real one.
    """
    for candidate in soup.find_all("table"):
        if candidate.find("table") is not None:
            continue
        if marker in candidate.get_text():
            return candidate
    return None


def parse_grade_view(html: str) -> list[GradeViewCourse]:
    """
    Parses the per-course grade list for a semester.

    Args:
        html (str): The HTML returned by doStudentGradeView.

    Returns:
        list[GradeViewCourse]: One entry per graded course.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        courses: list[GradeViewCourse] = []

        # The grade list is the table carrying a "View Mark" column.
        table = None
        for candidate in soup.find_all("table"):
            if "View Mark" in candidate.get_text():
                table = candidate
                break
        if table is None:
            return courses

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 8:
                continue

            serial = _clean(cells[0])
            if not serial.isdigit():
                # Header or spacer row.
                continue

            match = _COURSE_ID_RE.search(str(cells[7]))
            course_id = match.group(1) if match else ""

            courses.append(
                GradeViewCourse(
                    serial_number=serial,
                    course_code=_clean(cells[1]),
                    course_title=_clean(cells[2]),
                    course_type=_clean(cells[3]),
                    grading_type=_clean(cells[4]),
                    grand_total=_clean(cells[5]),
                    grade=_clean(cells[6]),
                    course_id=course_id,
                )
            )

        return courses

    except Exception as e:
        raise VtopParsingError(f"Failed to parse grade view: {e}") from e


def _parse_statistics(soup) -> GradeStatistics:
    """Reads the class statistics table (mean, SD, grade cutoffs)."""
    stats = GradeStatistics()

    table = _find_leaf_table(soup, "Range of Grades")
    if table is None:
        return stats

    # Three meaningful rows: the grade labels (S..F), then the values row
    # holding class strength, grading strength, mean, SD, and one range per
    # grade. A trailing footnote row is ignored.
    rows = [
        [_clean(c) for c in row.find_all(["td", "th"])]
        for row in table.find_all("tr")
    ]
    values = next(
        (r for r in rows if len(r) >= 4 and r[0] not in ("S", "Class Strength")
         and _looks_numeric(r[0])),
        None,
    )
    if values is not None:
        stats.class_strength = values[0]
        stats.grading_strength = values[1] if len(values) > 1 else ""
        stats.mean = values[2] if len(values) > 2 else ""
        stats.sd = values[3] if len(values) > 3 else ""
        ranges = values[4:]
        stats.grade_ranges = [
            GradeRange(grade=label, range=rng)
            for label, rng in zip(_GRADE_LABELS, ranges)
        ]

    return stats


def _looks_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _parse_marks(soup) -> tuple[str, str, list[MarkComponent], str]:
    """Reads the marks breakdown table. Returns class number, course type,
    the mark rows, and the total."""
    class_number = ""
    course_type = ""
    marks: list[MarkComponent] = []
    total = ""

    table = _find_leaf_table(soup, "Mark Title")
    if table is None:
        return class_number, course_type, marks, total

    for row in table.find_all("tr"):
        cells = [_clean(c) for c in row.find_all(["td", "th"])]
        if not cells:
            continue

        # Title row: "Class Number : ...", "Course Type : ...".
        joined = " ".join(cells)
        if "Class Number" in joined and not class_number:
            for cell in cells:
                if cell.startswith("Class Number"):
                    class_number = cell.split(":", 1)[-1].strip()
                elif cell.startswith("Course Type"):
                    course_type = cell.split(":", 1)[-1].strip()
            continue

        # Total row.
        if cells[0].lower() == "total":
            total = cells[1] if len(cells) > 1 else ""
            continue

        # A mark component always leads with a numeric serial.
        if len(cells) >= 7 and cells[0].isdigit():
            marks.append(
                MarkComponent(
                    serial_number=cells[0],
                    mark_title=cells[1],
                    max_mark=cells[2],
                    weightage=cells[3],
                    status=cells[4],
                    scored_mark=cells[5],
                    weightage_mark=cells[6],
                )
            )

    return class_number, course_type, marks, total


def parse_grade_view_detail(html: str) -> GradeViewDetail:
    """
    Parses the expanded detail for a single course.

    Args:
        html (str): The HTML returned by getGradeViewDetails.

    Returns:
        GradeViewDetail: The mark breakdown and class statistics.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        class_number, course_type, marks, total = _parse_marks(soup)

        return GradeViewDetail(
            class_number=class_number,
            course_type=course_type,
            marks=marks,
            total=total,
            statistics=_parse_statistics(soup),
        )

    except Exception as e:
        raise VtopParsingError(f"Failed to parse grade view detail: {e}") from e
