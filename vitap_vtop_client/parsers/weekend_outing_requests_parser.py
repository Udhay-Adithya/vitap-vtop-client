from bs4 import BeautifulSoup

from vitap_vtop_client.exceptions.exception import VtopParsingError
from vitap_vtop_client.outing.model.weekend_outing_model import (
    WeekendOutingModel,
    WeekendOutingRequest,
)


def _clean(cell) -> str:
    return cell.get_text().replace("\t", "").replace("\n", " ").strip()


def _booking_id_from_link(cell) -> str:
    """Reads the booking id from the download button's data-leave-url."""
    anchor = cell.find("a", attrs={"data-leave-url": True})
    if anchor is None:
        return ""
    return (anchor["data-leave-url"] or "").rstrip("/").split("/")[-1]


def parse_weekend_outing_requests(html: str) -> WeekendOutingModel:
    """
    Parses the weekend outing requests table.

    VTOP serves this table in two shapes. The current one has 11 columns and
    omits the contact numbers and a dedicated booking id column, carrying the
    booking id only inside the download link. An older 14 column form kept
    those as their own columns. Both are handled, keyed off the column count,
    mirroring the lib_vtop rust crate.
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="BookingRequests")
    requests: list[WeekendOutingRequest] = []

    try:
        if table is None:
            return WeekendOutingModel(root=requests)

        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 11:
                continue

            def col(index: int) -> str:
                return _clean(cols[index]) if index < len(cols) else ""

            is_wide_format = len(cols) >= 14
            if is_wide_format:
                # Contact (7), Parent contact (8), Date (9), Booking id (10),
                # Action (11), Status (12), Download (13).
                contact_number = col(7)
                parent_contact_number = col(8)
                date = col(9)
                action = col(11)
                status = col(12)
                download_index = 13
                booking_id = col(10) or _booking_id_from_link(cols[download_index])
            else:
                # Date (7), Action (8), Status (9), Download (10). No contact
                # columns, and the booking id lives in the download link.
                contact_number = ""
                parent_contact_number = ""
                date = col(7)
                action = col(8)
                status = col(9)
                download_index = 10
                booking_id = _booking_id_from_link(cols[download_index])

            requests.append(
                WeekendOutingRequest(
                    serial=col(0),
                    registration_number=col(1),
                    hostel_block=col(2),
                    room_number=col(3),
                    place_of_visit=col(4),
                    purpose_of_visit=col(5),
                    time=col(6),
                    contact_number=contact_number,
                    parent_contact_number=parent_contact_number,
                    date=date,
                    booking_id=booking_id,
                    action=action,
                    status=status,
                    # VTOP only issues the form once the request is accepted,
                    # so the status is checked alongside the booking id.
                    can_download=bool(booking_id)
                    and status.lower().strip() == "outing request accepted",
                )
            )

        return WeekendOutingModel(root=requests)

    except Exception as e:
        raise VtopParsingError(f"Error parsing weekend outing requests: {e}") from e
