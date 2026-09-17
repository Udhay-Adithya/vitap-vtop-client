import re

from bs4 import BeautifulSoup

from vitap_vtop_client.exceptions import VtopParsingError
from vitap_vtop_client.profile.model import StudentProfileModel
from vitap_vtop_client.utils import extract_pfp_base64

# VTOP renders a two word label across two lines, e.g.
# "APPLICATION\r\n\t\t\t\t...\t\tNUMBER". str.strip() only removes whitespace at
# the ends, so comparing against "APPLICATION NUMBER" never matched and those
# fields silently went missing.
_WHITESPACE = re.compile(r"\s+")

# Label on the page -> field on the model.
_FIELDS = {
    "APPLICATION NUMBER": "application_number",
    "STUDENT NAME": "student_name",
    "DATE OF BIRTH": "dob",
    "GENDER": "gender",
    "BLOOD GROUP": "blood_group",
    "EMAIL": "email",
}


def _label(cell) -> str:
    """Collapses a cell's text to single spaces so a label can be compared."""
    return _WHITESPACE.sub(" ", cell.get_text()).strip()


def parse_student_profile(html: str) -> StudentProfileModel:
    """
    Parses the HTML content of the student profile page.

    Fields VTOP does not render are left as None rather than raising. The page
    varies, and a missing blood group is not a reason to fail the whole call.

    Args:
        html (str): The raw HTML string containing the student profile data.

    Returns:
        StudentProfileModel: The parsed profile. `grade_history` and
            `mentor_details` are left unset; the fetch layer fills them in.

    Raises:
        VtopParsingError: If parsing fails due to malformed HTML or unexpected structure.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        cells = soup.find_all("td")

        profile_data = {"base64_pfp": extract_pfp_base64(html)}

        for i, cell in enumerate(cells):
            field = _FIELDS.get(_label(cell))
            # First match wins. The page carries four cells labelled exactly
            # "EMAIL", one per contact block; the first follows the student's
            # own personal details and the rest follow other contacts. Reading
            # on overwrote it with whichever came last, which was never theirs.
            # None of them is a VIT-issued address -- the page does not render
            # one -- so this is whatever personal address is on file.
            if field is None or field in profile_data:
                continue
            if i + 1 < len(cells):
                profile_data[field] = _label(cells[i + 1])

        return StudentProfileModel(**profile_data)

    except Exception as e:
        raise VtopParsingError(f"Failed to parse student profile: {e}") from e
