from bs4 import BeautifulSoup

from vitap_vtop_client.exceptions.exception import VtopParsingError
from vitap_vtop_client.faculty.model.faculty_model import (
    FacultyDetailsModel,
    FacultyModel,
    OfficeHourModel,
)


def _clean(text: str) -> str:
    return text.strip().replace("\t", "").replace("\n", "")


def _cell_text(cell) -> str:
    return _clean(cell.get_text())


def _extract_emp_id(row) -> str:
    """
    Pulls the employee id out of the row's action button.

    The id is normally on the button itself; older pages only carry it inside
    the onclick handler, quoted either literally or HTML escaped.
    """
    button = row.find("button")
    if button is None:
        return ""

    emp_id = button.get("id")
    if emp_id:
        return emp_id

    onclick = button.get("onclick")
    if not onclick:
        return ""

    if "&quot;" in onclick:
        parts = onclick.split("&quot;")
        return parts[1] if len(parts) > 1 else ""
    if '"' in onclick:
        parts = onclick.split('"')
        return parts[1] if len(parts) > 1 else ""

    return "".join(c for c in onclick if c.isdigit())


def parse_all_faculty_search(html: str) -> list[FacultyModel]:
    """
    Parses every row of a faculty search response.

    Args:
        html (str): The raw HTML of the faculty search response.

    Returns:
        list[FacultyModel]: One entry per matched faculty member.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        results: list[FacultyModel] = []

        # Skip the header row.
        for row in soup.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            emp_id = _extract_emp_id(row)
            if not emp_id:
                # Rows without an employee button are not real results.
                continue

            results.append(
                FacultyModel(
                    faculty_name=_cell_text(cells[0]),
                    designation=_cell_text(cells[1]),
                    school_or_centre=_cell_text(cells[2]),
                    emp_id=emp_id,
                )
            )

        return results

    except Exception as e:
        raise VtopParsingError(f"Failed to parse faculty search data: {e}") from e


def parse_faculty_search(html: str) -> FacultyModel:
    """
    Parses the first matching faculty member from a search response.

    Args:
        html (str): The raw HTML of the faculty search response.

    Returns:
        FacultyModel: The first match, or an empty model when there are none.
    """
    results = parse_all_faculty_search(html)
    return results[0] if results else FacultyModel()


def parse_faculty_data(html: str) -> FacultyDetailsModel:
    """
    Parses a faculty member's profile and office hours.

    The response carries two bordered tables: the first holds labelled profile
    rows, the second holds the weekly office hours.

    Args:
        html (str): The raw HTML of the faculty detail response.

    Returns:
        FacultyDetailsModel: The parsed profile.

    Raises:
        VtopParsingError: If parsing fails.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        details = FacultyDetailsModel()
        tables = soup.find_all("table", class_="table table-bordered")

        if tables:
            for row in tables[0].find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue

                label = _cell_text(cells[0]).lower()
                value = _cell_text(cells[1])

                if "name of the faculty" in label:
                    details.name = value
                elif "designation" in label:
                    details.designation = value
                elif "name of department" in label:
                    details.department = value
                elif "school" in label or "centre" in label:
                    details.school_centre = value
                elif "e-mail" in label:
                    details.email = value
                elif "cabin number" in label:
                    details.cabin_number = value

        if len(tables) > 1:
            for row in tables[1].find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue

                day = _cell_text(cells[0])
                timings = _cell_text(cells[1])

                # Skip header and section rows.
                if not day or not timings:
                    continue
                if "week day" in day.lower() or "open hours" in day.lower():
                    continue

                details.office_hours.append(
                    OfficeHourModel(day=day, timings=timings)
                )

        return details

    except Exception as e:
        raise VtopParsingError(f"Failed to parse faculty details: {e}") from e
