import time

from bs4 import BeautifulSoup

from vitap_vtop_client.exceptions.exception import VtopParsingError
from vitap_vtop_client.semester.model.semester_model import SemesterData, SemesterInfo


def parse_semester_id_from_timetable(html: str) -> SemesterData:
    """
    Parses the available semesters from the timetable page.

    The timetable page carries a `semesterSubId` select whose options hold the
    semester ids used by every semester scoped endpoint. The first option is a
    placeholder prompt and is skipped.

    Args:
        html (str): The HTML of the timetable page.

    Returns:
        SemesterData: The available semesters and the time they were read.

    Raises:
        VtopParsingError: If the HTML cannot be parsed.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        semesters: list[SemesterInfo] = []

        select = soup.select_one('select[name="semesterSubId"]')
        if select is not None:
            for option in select.find_all("option")[1:]:
                semester_id = (option.get("value") or "").strip()
                name = option.get_text(strip=True).replace("- AMR", "").strip()
                if semester_id and name:
                    semesters.append(SemesterInfo(id=semester_id, name=name))

        return SemesterData(
            semesters=semesters,
            update_time=int(time.time()),
        )

    except Exception as e:
        print(f"Error parsing semester data: {e}")
        raise VtopParsingError(f"Failed to parse semester data: {e}") from e
