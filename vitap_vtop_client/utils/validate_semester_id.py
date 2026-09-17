import re

from vitap_vtop_client.exceptions.exception import VtopSessionError

# Every semester id VTOP served on 2026-09-17 matched this: the AP campus
# prefix and seven digits, e.g. AP2026272, AP2023243.
SEMESTER_ID_PATTERN = re.compile(r"^AP\d{7}$")


def validate_semester_id(sem_sub_id: str) -> None:
    """
    Checks that a semester id is the right shape before it is sent.

    This catches a typo or an empty string. It deliberately does **not** catch
    an id that is well formed but wrong, such as one cached from a previous
    term, because nothing here can tell the difference -- the only way to know
    an id is real is to find it in `get_semesters()`.

    That matters more than it sounds. VTOP does not reject an unknown semester
    id: it answers with a normal, empty table, so a wrong semester is
    indistinguishable from a semester the student genuinely has no data for.
    Take ids from `get_semesters()` rather than storing them.

    Args:
        sem_sub_id (str): The semester id to check.

    Raises:
        VtopSessionError: If the id is empty or not `AP` followed by seven
            digits.
    """
    if not sem_sub_id or not SEMESTER_ID_PATTERN.fullmatch(sem_sub_id):
        raise VtopSessionError(
            f"{sem_sub_id!r} is not a semester id. They look like 'AP2026272' "
            "-- 'AP' and seven digits. Call get_semesters() for the ids this "
            "student can actually use; VTOP answers an unknown id with an "
            "empty result rather than an error, so a wrong one fails silently.",
            status_code=400,
        )
